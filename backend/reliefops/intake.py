"""Request intake and consolidation service supporting structured data, CSV, and AI extraction."""
from __future__ import annotations

import csv
import io
import logging
import time
import uuid
from typing import Any
from pydantic import BaseModel, Field

from backend import config
from backend.llm.gemma import GemmaService, get_gemma_service
from backend.reliefops.models import ReliefCamp, ReliefRequest, ResourceType, UrgencyLevel

log = logging.getLogger(__name__)


class ExtractedFieldRequest(BaseModel):
    """Schema for individual request extracted by Gemma 4B from field dispatches."""
    camp_name_or_id: str
    resource_type: str  # e.g., "WATER_LITERS", "FOOD_RATIONS", "BLANKETS", "MEDICAL_KITS"
    quantity: int
    urgency: str = "HIGH"  # CRITICAL, HIGH, MEDIUM, LOW
    notes: str = ""


class FieldReportExtractionResult(BaseModel):
    """Consolidated response from Gemma 4B field dispatch parsing."""
    incident_context: str = ""
    requests: list[ExtractedFieldRequest] = Field(default_factory=list)
    confidence: float = 0.95


class RequestIntakeService:
    """Ingests, parses, normalizes, and validates camp supply requests."""

    def __init__(self, gemma_service: GemmaService | None = None):
        self.gemma = gemma_service or get_gemma_service()

    def parse_csv_requests(
        self,
        csv_content: str | bytes,
        camps: list[ReliefCamp],
        resources: list[ResourceType],
    ) -> list[ReliefRequest]:
        """Parse structured CSV file containing camp relief supply requests."""
        if isinstance(csv_content, bytes):
            text = csv_content.decode("utf-8-sig", errors="replace")
        else:
            text = csv_content

        reader = csv.DictReader(io.StringIO(text))
        camp_lookup = {c.id.upper(): c.id for c in camps}
        camp_lookup.update({c.name.upper(): c.id for c in camps})
        res_lookup = {r.id.upper(): r.id for r in resources}
        res_lookup.update({r.name.upper(): r.id for r in resources})

        results: list[ReliefRequest] = []
        for i, row in enumerate(reader, start=1):
            camp_raw = str(row.get("camp_id", row.get("camp", row.get("camp_name", "")))).strip().upper()
            res_raw = str(row.get("resource_id", row.get("resource", row.get("item", "")))).strip().upper()
            qty_raw = row.get("quantity_requested", row.get("quantity", row.get("qty", 0)))
            urgency_raw = str(row.get("urgency", "HIGH")).strip().upper()
            notes = str(row.get("evidence_notes", row.get("notes", ""))).strip()

            camp_id = camp_lookup.get(camp_raw)
            if not camp_id:
                # Try matching by partial string
                camp_id = next(
                    (c.id for c in camps if camp_raw in c.name.upper() or camp_raw in c.id.upper()),
                    None,
                )
            if not camp_id and camps:
                camp_id = camps[0].id

            res_id = res_lookup.get(res_raw)
            if not res_id:
                # Fuzzy match
                res_id = next(
                    (r.id for r in resources if res_raw in r.name.upper() or res_raw in r.id.upper()),
                    None,
                )
            if not res_id and resources:
                res_id = resources[0].id

            try:
                quantity = max(1, int(float(qty_raw)))
            except (ValueError, TypeError):
                quantity = 100

            urgency = self._parse_urgency(urgency_raw)

            req = ReliefRequest(
                id=f"REQ-CSV-{i}-{uuid.uuid4().hex[:6]}",
                camp_id=camp_id or "CAMP-1",
                resource_id=res_id or "WATER_LITERS",
                quantity_requested=quantity,
                urgency=urgency,
                evidence_notes=notes or f"Imported via CSV row {i}",
                status="pending",
                created_at=time.time(),
            )
            results.append(req)

        return results

    def extract_from_unstructured_text(
        self,
        report_text: str,
        camps: list[ReliefCamp],
        resources: list[ResourceType],
    ) -> list[ReliefRequest]:
        """Extract structured ReliefRequest objects from field dispatches using Gemma 4B."""
        camp_lookup = {c.id.upper(): c.id for c in camps}
        camp_lookup.update({c.name.upper(): c.id for c in camps})
        res_lookup = {r.id.upper(): r.id for r in resources}
        res_lookup.update({r.name.upper(): r.id for r in resources})

        if config.MOCK_LLM:
            return self._heuristic_text_extraction(report_text, camps, resources)

        known_camps = [f"{c.id}: {c.name}" for c in camps]
        known_resources = [f"{r.id}: {r.name} ({r.unit})" for r in resources]

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a Disaster Intake Intelligence Specialist using Gemma 4B. "
                    "Extract structured emergency supply requests from field radio transcripts, incident notes, or dispatches. "
                    "Map camp mentions to known relief camps and resource needs to standard resource IDs. "
                    "Classify urgency as CRITICAL, HIGH, MEDIUM, or LOW based on distress indicators. "
                    "Return strictly valid JSON conforming to the requested schema."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Registered camps: {known_camps}\n"
                    f"Valid resource types: {known_resources}\n\n"
                    f"Field dispatch report:\n\"\"\"{report_text}\"\"\"\n\n"
                    f"Extract requests into JSON matching schema:\n"
                    f"{FieldReportExtractionResult.model_json_schema()}"
                ),
            },
        ]

        try:
            extraction, _ = self.gemma.generate_json(
                tier="4b",
                messages=messages,
                schema=FieldReportExtractionResult,
                retries=1,
            )
            requests: list[ReliefRequest] = []
            for item in extraction.requests:
                c_id = self._match_camp(item.camp_name_or_id, camps)
                r_id = self._match_resource(item.resource_type, resources)
                urgency = self._parse_urgency(item.urgency)
                requests.append(
                    ReliefRequest(
                        id=f"REQ-AI-{uuid.uuid4().hex[:8]}",
                        camp_id=c_id,
                        resource_id=r_id,
                        quantity_requested=max(1, item.quantity),
                        urgency=urgency,
                        evidence_notes=item.notes or f"Extracted via Gemma 4B: {report_text[:80]}...",
                        status="pending",
                        created_at=time.time(),
                    )
                )
            if requests:
                return requests
            return self._heuristic_text_extraction(report_text, camps, resources)
        except Exception as exc:
            log.warning("Gemma 4B extraction error (%s), using heuristic parser", exc)
            return self._heuristic_text_extraction(report_text, camps, resources)

    def _heuristic_text_extraction(
        self,
        text: str,
        camps: list[ReliefCamp],
        resources: list[ResourceType],
    ) -> list[ReliefRequest]:
        """Robust fallback heuristic extractor for offline/mock test execution."""
        import re

        text_lower = text.lower()
        matched_camp = camps[0] if camps else None
        for camp in camps:
            if camp.name.lower() in text_lower or camp.id.lower() in text_lower:
                matched_camp = camp
                break

        results: list[ReliefRequest] = []
        # Look for numbers near keywords
        keywords = {
            "WATER_LITERS": ["water", "drinking water", "liters", "bottles"],
            "FOOD_RATIONS": ["food", "ration", "meal", "packet", "rice", "wheat"],
            "MEDICAL_KITS": ["medical", "medicine", "first aid", "bandage", "doctor", "health"],
            "BLANKETS": ["blanket", "warmth", "sheet", "bedding"],
            "TENTS": ["tent", "shelter", "tarpaulin", "tarp"],
        }

        urgency = UrgencyLevel.HIGH
        if any(w in text_lower for w in ["critical", "emergency", "urgent", "dying", "severe", "life-threatening"]):
            urgency = UrgencyLevel.CRITICAL
        elif any(w in text_lower for w in ["moderate", "normal", "low"]):
            urgency = UrgencyLevel.MEDIUM

        for res in resources:
            kws = keywords.get(res.id, [res.name.lower()])
            for kw in kws:
                pattern = rf"(\d+)\s*(?:units|cases|liters|packets|kits|pieces|boxes)?\s*(?:of\s+)?{kw}"
                match = re.search(pattern, text_lower)
                if match:
                    qty = int(match.group(1))
                    results.append(
                        ReliefRequest(
                            id=f"REQ-HEUR-{uuid.uuid4().hex[:8]}",
                            camp_id=matched_camp.id if matched_camp else "CAMP-1",
                            resource_id=res.id,
                            quantity_requested=qty,
                            urgency=urgency,
                            evidence_notes=f"Heuristic extraction: matched '{kw}'",
                            status="pending",
                        )
                    )
                    break

        if not results and camps and resources:
            # Fallback sample request if nothing was matched
            results.append(
                ReliefRequest(
                    id=f"REQ-HEUR-{uuid.uuid4().hex[:8]}",
                    camp_id=camps[0].id,
                    resource_id=resources[0].id,
                    quantity_requested=250,
                    urgency=urgency,
                    evidence_notes=f"Fallback request from dispatch: {text[:60]}",
                    status="pending",
                )
            )

        return results

    def _match_camp(self, name_or_id: str, camps: list[ReliefCamp]) -> str:
        s = name_or_id.strip().upper()
        for c in camps:
            if c.id.upper() == s or c.name.upper() == s:
                return c.id
        for c in camps:
            if s in c.name.upper() or c.name.upper() in s:
                return c.id
        return camps[0].id if camps else "CAMP-1"

    def _match_resource(self, name_or_id: str, resources: list[ResourceType]) -> str:
        s = name_or_id.strip().upper()
        for r in resources:
            if r.id.upper() == s or r.name.upper() == s:
                return r.id
        for r in resources:
            if s in r.name.upper() or r.name.upper() in s:
                return r.id
        return resources[0].id if resources else "WATER_LITERS"

    def _parse_urgency(self, val: str) -> UrgencyLevel:
        v = val.strip().upper()
        if "CRIT" in v or v == "1":
            return UrgencyLevel.CRITICAL
        if "HIGH" in v or v == "2":
            return UrgencyLevel.HIGH
        if "MED" in v or v == "3":
            return UrgencyLevel.MEDIUM
        if "LOW" in v or v == "4":
            return UrgencyLevel.LOW
        return UrgencyLevel.HIGH
