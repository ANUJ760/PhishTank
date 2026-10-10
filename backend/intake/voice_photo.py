"""Text, audio, and image intake; model output remains draft until reviewed."""
from __future__ import annotations
import base64, logging
from pathlib import Path
from backend import config
from backend.llm.client import call_json
from backend.llm.prompts import extract_rules
from backend.models import DraftRulesOut, Evidence, Rule, Roster, validate_params
from backend.registry import db

log=logging.getLogger(__name__)
def _to_rules(out: DraftRulesOut, kind: str, filename: str, roster: Roster, data: bytes | None=None) -> list[Rule]:
    if data is not None: db.save_upload(filename,data)
    result=[]
    for draft in out.rules:
        try: validate_params(draft.type,draft.params,roster)
        except (ValueError,KeyError,TypeError) as exc:
            log.warning("Skipping invalid extracted %s rule: %s",draft.type,exc); continue
        owner=config.DEFAULT_OWNER[draft.type] or draft.params.get("teacher")
        rule=Rule(id=db.next_rule_id(),type=draft.type,owner=owner,params=draft.params,evidence=[Evidence(kind=kind,ref=f"{filename}@{draft.evidence_ref or 'unknown'}")])
        db.save_rule(rule); result.append(rule)
    return result

def ingest_text(text: str, roster: Roster | None=None) -> list[Rule]:
    if not text.strip(): raise ValueError("Text input cannot be empty")
    roster=roster or db.get_roster()
    out=call_json("extract_rules_text","intake",[{"role":"system","content":extract_rules(roster)},{"role":"user","content":text}],DraftRulesOut)
    return _to_rules(out,"text","typed-input.txt",roster)

def ingest_audio(wav: bytes, filename: str, roster: Roster | None=None) -> list[Rule]:
    if config.AUDIO_MODE!="native": raise ValueError("Audio input is disabled; use typed text in transcript mode")
    if not wav: raise ValueError("Audio upload is empty")
    if len(wav)>25*1024*1024: raise ValueError("Audio upload exceeds the 25 MiB limit")
    roster=roster or db.get_roster(); encoded=base64.b64encode(wav).decode("ascii")
    out=call_json("extract_rules_audio","intake",[{"role":"system","content":extract_rules(roster)},{"role":"user","content":[{"type":"input_audio","input_audio":{"data":encoded,"format":"wav"}},{"type":"text","text":"Extract the rules."}]}],DraftRulesOut)
    return _to_rules(out,"audio",Path(filename).name,roster,wav)

def ingest_image(img: bytes, filename: str, roster: Roster | None=None) -> list[Rule]:
    if not img: raise ValueError("Image upload is empty")
    if len(img)>25*1024*1024: raise ValueError("Image upload exceeds the 25 MiB limit")
    name=Path(filename).name; ext=Path(name).suffix.lower(); mime={".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".webp":"image/webp"}.get(ext)
    if not mime: raise ValueError("Image must be PNG, JPEG, or WebP")
    roster=roster or db.get_roster(); encoded=base64.b64encode(img).decode("ascii")
    out=call_json("extract_rules_image","intake",[{"role":"system","content":extract_rules(roster)},{"role":"user","content":[{"type":"image_url","image_url":{"url":f"data:{mime};base64,{encoded}"}},{"type":"text","text":"Extract the rules."}]}],DraftRulesOut)
    return _to_rules(out,"image",name,roster,img)
