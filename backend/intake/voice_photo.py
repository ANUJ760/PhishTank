"""Text, audio, and image intake; model output remains draft until reviewed."""
from __future__ import annotations
import base64, logging
from pathlib import Path
from backend import config
from backend.llm.client import call_json
from backend.llm.prompts import extract_rules
from backend.models import DraftRule, DraftRulesOut, Evidence, Rule, Roster, Room, Session, validate_params
from backend.registry import db

log = logging.getLogger(__name__)


def _to_rules(out: DraftRulesOut, kind: str, filename: str, roster: Roster, data: bytes | None = None) -> list[Rule]:
    if data is not None:
        db.save_upload(filename, data)
    result = []
    for draft in out.rules:
        # If roster is missing entities from draft, ensure them so validation passes
        if draft.type == "teacher_unavailable" and draft.params.get("teacher"):
            if draft.params["teacher"] not in roster.teachers:
                roster.teachers.append(draft.params["teacher"])
                db.save_roster(roster)
        elif draft.type == "room_unavailable" and draft.params.get("room"):
            if not any(r.name == draft.params["room"] for r in roster.rooms):
                roster.rooms.append(Room(name=draft.params["room"], capacity=30))
                db.save_roster(roster)
        elif draft.type in {"pin_session", "only_qualified"} and draft.params.get("session_id"):
            if not any(s.id == draft.params["session_id"] for s in roster.sessions):
                roster.sessions.append(Session(
                    id=draft.params["session_id"],
                    course=draft.params["session_id"],
                    teachers=draft.params.get("teachers", roster.teachers[:1] if roster.teachers else ["Faculty"]),
                    size=30,
                ))
                db.save_roster(roster)
        try:
            validate_params(draft.type, draft.params, roster)
        except (ValueError, KeyError, TypeError) as exc:
            log.warning("Skipping invalid extracted %s rule: %s", draft.type, exc)
            continue
        owner = config.DEFAULT_OWNER.get(draft.type) or draft.params.get("teacher") or "Coordinator"
        rule = Rule(
            id=db.next_rule_id(),
            type=draft.type,
            owner=owner,
            params=draft.params,
            evidence=[Evidence(kind=kind, ref=f"{filename}@{draft.evidence_ref or 'unknown'}")],
        )
        db.save_rule(rule)
        result.append(rule)
    return result


def ingest_text(text: str, roster: Roster | None = None) -> list[Rule]:
    if not text.strip():
        raise ValueError("Text input cannot be empty")
    roster = roster or db.get_roster()
    out = call_json("extract_rules_text", "intake", [{"role": "system", "content": extract_rules(roster)}, {"role": "user", "content": text}], DraftRulesOut)
    return _to_rules(out, "text", "typed-input.txt", roster)


def extract_rules_from_audio(wav: bytes, filename: str, roster: Roster | None = None) -> list[DraftRule]:
    if config.AUDIO_MODE != "native":
        raise ValueError("Audio input is disabled; use typed text in transcript mode")
    if not wav:
        raise ValueError("Audio upload is empty")
    if len(wav) > 25 * 1024 * 1024:
        raise ValueError("Audio upload exceeds the 25 MiB limit")
    roster = roster or db.get_roster()
    encoded = base64.b64encode(wav).decode("ascii")
    fmt = Path(filename).suffix.lstrip(".").lower() or "wav"
    out = call_json(
        "extract_rules_audio",
        "intake",
        [
            {"role": "system", "content": extract_rules(roster)},
            {"role": "user", "content": [
                {"type": "input_audio", "input_audio": {"data": encoded, "format": fmt}},
                {"type": "text", "text": "Extract the rules from this audio recording."}
            ]}
        ],
        DraftRulesOut,
    )
    return out.rules


def ingest_audio(wav: bytes, filename: str, roster: Roster | None = None) -> list[Rule]:
    roster = roster or db.get_roster()
    drafts = extract_rules_from_audio(wav, filename, roster)
    out = DraftRulesOut(rules=drafts)
    return _to_rules(out, "audio", Path(filename).name, roster, wav)


def extract_rules_from_image(img: bytes, filename: str, roster: Roster | None = None) -> list[DraftRule]:
    if not img:
        raise ValueError("Image upload is empty")
    if len(img) > 25 * 1024 * 1024:
        raise ValueError("Image upload exceeds the 25 MiB limit")
    name = Path(filename).name
    ext = Path(name).suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext)
    if not mime:
        raise ValueError("Image must be PNG, JPEG, or WebP")
    roster = roster or db.get_roster()
    encoded = base64.b64encode(img).decode("ascii")
    out = call_json(
        "extract_rules_image",
        "intake",
        [
            {"role": "system", "content": extract_rules(roster)},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
                {"type": "text", "text": "Extract the rules from this image."}
            ]}
        ],
        DraftRulesOut,
    )
    return out.rules


def ingest_image(img: bytes, filename: str, roster: Roster | None = None) -> list[Rule]:
    roster = roster or db.get_roster()
    drafts = extract_rules_from_image(img, filename, roster)
    out = DraftRulesOut(rules=drafts)
    return _to_rules(out, "image", Path(filename).name, roster, img)
