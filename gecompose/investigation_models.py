"""Domain models and schemas for the GeCompose AI Incident Investigation Engine."""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


class EvidenceSourceType(str, Enum):
    """Origin source of gathered incident evidence."""
    LOGS = "logs"
    ALERTS = "alerts"
    TICKETS = "tickets"
    DOCUMENTS = "documents"
    OBSERVATIONS = "observations"
    METRICS = "metrics"


class IncidentSeverity(str, Enum):
    """Operational severity level of the incident."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus(str, Enum):
    """Lifecycle status of the incident investigation."""
    OPEN = "open"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"


class EvidenceRelationshipType(str, Enum):
    """Semantic relationship between an item of evidence and a hypothesis."""
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    INCONCLUSIVE = "inconclusive"


class HypothesisStatus(str, Enum):
    """Evaluation verdict of a competing explanation."""
    PLAUSIBLE = "plausible"
    STRONGLY_SUPPORTED = "strongly_supported"
    REFUTED = "refuted"
    INSUFFICIENT_DATA = "insufficient_data"


class Evidence(BaseModel):
    """An individual piece of empirical or reported evidence."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="Unique evidence identifier")
    source_type: EvidenceSourceType = Field(..., description="Origin source type of the evidence")
    summary: str = Field(..., min_length=1, description="Concise statement of observed fact")
    timestamp: str | None = Field(default=None, description="Timestamp when evidence was observed or recorded")
    source_ref: str = Field(default="", description="Reference to source artifact (e.g. log file, URL, ticket #)")
    details: dict[str, Any] = Field(default_factory=dict, description="Structured metadata and telemetry attributes")
    reliability: float = Field(default=1.0, ge=0.0, le=1.0, description="Assessed reliability of source (0.0 to 1.0)")

    @field_validator("id", "summary", mode="before")
    @classmethod
    def strip_text(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("String field cannot be empty or whitespace.")
        return v


class Incident(BaseModel):
    """Incident definition describing the anomalous event under investigation."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="Unique incident identifier")
    title: str = Field(..., min_length=1, description="Human-readable incident title")
    description: str = Field(default="", description="Detailed narrative of incident manifestation")
    affected_component: str = Field(..., min_length=1, description="Primary service, system, or facility affected")
    severity: IncidentSeverity = Field(default=IncidentSeverity.MEDIUM, description="Impact severity")
    status: IncidentStatus = Field(default=IncidentStatus.OPEN, description="Current investigation status")
    start_time: str | None = Field(default=None, description="Start of the incident window")
    end_time: str | None = Field(default=None, description="End of the incident window if bounded")
    environment: str = Field(default="production", description="Environment affected (e.g. production, staging)")
    tags: set[str] = Field(default_factory=set, description="Classification tags")

    @field_validator("id", "title", "affected_component", mode="before")
    @classmethod
    def strip_text(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("String field cannot be empty or whitespace.")
        return v


class EvidenceLink(BaseModel):
    """Association linking an evidence observation to a candidate hypothesis."""
    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(..., min_length=1, description="ID of the associated evidence")
    relationship: EvidenceRelationshipType = Field(..., description="SUPPORTS, CONTRADICTS, or INCONCLUSIVE")
    explanation: str = Field(default="", description="Causal reasoning linking the evidence to the hypothesis")
    weight: float = Field(default=1.0, ge=0.0, le=5.0, description="Relative significance of this evidence link")

    @field_validator("evidence_id", mode="before")
    @classmethod
    def strip_id(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Evidence ID cannot be empty.")
        return v


class Hypothesis(BaseModel):
    """A competing causal explanation for an incident."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="Unique hypothesis identifier")
    title: str = Field(..., min_length=1, description="Hypothesis summary name")
    description: str = Field(default="", description="Detailed explanation of the proposed failure mechanism")
    root_cause_category: str = Field(default="general", description="Categorization (e.g. hardware, network, software, config)")
    assumptions: list[str] = Field(default_factory=list, description="Unverified assumptions required for this explanation to hold")
    unresolved_questions: list[str] = Field(default_factory=list, description="Open unknowns regarding this explanation")
    evidence_links: list[EvidenceLink] = Field(default_factory=list, description="Associated evidence items and relationships")
    status: HypothesisStatus = Field(default=HypothesisStatus.PLAUSIBLE, description="Current status verdict")
    plausibility_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Evidence-backed plausibility score (0.0 to 1.0)")
    rationale: str = Field(default="", description="Deterministic justification of the status verdict")

    @field_validator("id", "title", mode="before")
    @classmethod
    def strip_text(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("String field cannot be empty or whitespace.")
        return v

    @computed_field
    @property
    def supporting_evidence_ids(self) -> list[str]:
        """IDs of evidence directly supporting this hypothesis."""
        return [link.evidence_id for link in self.evidence_links if link.relationship == EvidenceRelationshipType.SUPPORTS]

    @computed_field
    @property
    def contradicting_evidence_ids(self) -> list[str]:
        """IDs of evidence directly refuting or contradicting this hypothesis."""
        return [link.evidence_id for link in self.evidence_links if link.relationship == EvidenceRelationshipType.CONTRADICTS]

    @computed_field
    @property
    def inconclusive_evidence_ids(self) -> list[str]:
        """IDs of evidence that are ambiguous or inconclusive for this hypothesis."""
        return [link.evidence_id for link in self.evidence_links if link.relationship == EvidenceRelationshipType.INCONCLUSIVE]

    @computed_field
    @property
    def is_refuted(self) -> bool:
        """Returns True if there is at least one fatal contradicting evidence link."""
        return len(self.contradicting_evidence_ids) > 0


class DiagnosticTest(BaseModel):
    """An active probe or verification step designed to discriminate between competing hypotheses."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="Unique diagnostic test identifier")
    name: str = Field(..., min_length=1, description="Name of the diagnostic test")
    purpose: str = Field(..., min_length=1, description="Objective of executing this test")
    target_component: str = Field(..., description="Target system, host, or resource to inspect")
    procedure: str = Field(..., min_length=1, description="Detailed command, query, or check procedure")
    expected_observations: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping from hypothesis_id to observation expected if that hypothesis is true"
    )
    discriminates_hypotheses: list[str] = Field(
        default_factory=list,
        description="List of competing hypothesis IDs distinguished by this test"
    )
    risk_level: str = Field(default="low", description="Operational risk of running this test (low, medium, high)")

    @field_validator("id", "name", "purpose", "procedure", mode="before")
    @classmethod
    def strip_text(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Diagnostic test fields cannot be empty or whitespace.")
        return v


class InvestigationReport(BaseModel):
    """Comprehensive investigation report synthesizing findings, hypotheses, and diagnostic steps."""
    model_config = ConfigDict(frozen=True)

    incident: Incident = Field(..., description="The incident investigated")
    hypotheses: list[Hypothesis] = Field(default_factory=list, description="All evaluated competing explanations")
    evidence_trail: list[Evidence] = Field(default_factory=list, description="Verified chronological evidence repository")
    missing_evidence: list[str] = Field(default_factory=list, description="Explicit data gaps preventing decisive conclusion")
    proposed_tests: list[DiagnosticTest] = Field(default_factory=list, description="Diagnostic probes to resolve ambiguity")
    leading_hypothesis_id: str | None = Field(default=None, description="Hypothesis with strongest non-refuted support, if any")
    confidence_assessment: str = Field(default="", description="Transparent explanation of certainty vs unknowns")
    investigation_status: IncidentStatus = Field(default=IncidentStatus.INVESTIGATING, description="Report investigation status")
    statistics: dict[str, Any] = Field(default_factory=dict, description="Analytical metrics of the investigation")

    @computed_field
    @property
    def has_unrefuted_hypothesis(self) -> bool:
        """Returns True if at least one hypothesis remains plausible and unrefuted."""
        return any(not h.is_refuted for h in self.hypotheses)

    @computed_field
    @property
    def total_evidence_count(self) -> int:
        return len(self.evidence_trail)

    @computed_field
    @property
    def total_hypotheses_count(self) -> int:
        return len(self.hypotheses)
