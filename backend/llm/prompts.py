"""Prompt templates with bounded, schema-constrained model tasks."""
from backend.models import Roster

def extract_rules(roster: Roster) -> str:
    teachers=", ".join(roster.teachers); rooms=", ".join(r.name for r in roster.rooms)
    sessions=", ".join(f"{s.id}: {s.course}" for s in roster.sessions)
    return f"""You extract scheduling rules for a college timetable from the coordinator's input.
The input may be Hindi, Marathi or English (speech, a photo, or typed text).
Allowed rule types and EXACT params:
- teacher_unavailable: {{"teacher": <name>, "day": <0-4>, "slots": [<0-5>, ...]}}
- room_unavailable: {{"room": <name>, "day": <0-4>, "slots": [<0-5>, ...]}}
- pin_session: {{"session_id": <id>, "day": <0-4>, "slots": [<0-5>, ...]}}
- only_qualified: {{"session_id": <id>, "teachers": [<name>, ...]}}
Day 0=Monday ... 4=Friday. Slots 0-2 are morning, 3-5 afternoon.
Known teachers: {teachers}\nKnown rooms: {rooms}\nKnown sessions (id: course): {sessions}
Return JSON only: {{"rules":[{{"type": ..., "params": {{...}}, "evidence_ref": "<source location>"}}]}}
Use only names and ids from the known lists. If unsure, omit the rule. Never invent anything."""

def gen_sheet_parser(sample_rows_text: str, last_error: str="") -> str:
    return f"""Write a Python function `parse(path: str) -> list[dict]` that reads the Excel file at `path`
using only pandas and openpyxl, and returns one dict per data row:
{{"course": <str>, "teachers": [<str>, ...], "source_cell": <str like "B7">}}
"teachers" is the list of qualified faculty for that course. Split comma/semicolon-separated names. Trim spaces.
Do not use the network, do not write files, do not import other libraries.
First rows of the sheet (row number, then cell values):\n{sample_rows_text}
{('Previous parser error: '+last_error) if last_error else ''}
Return JSON only: {{"code": "<the full python source>"}}"""

def explain_conflict(rules_text: str) -> str:
    return f"""A timetable solver proved these rules cannot all hold at the same time:
{rules_text}
Write a 2-3 sentence plain-English explanation naming the people and rules. Provide up to 3 options. Each option changes params of exactly ONE listed rule, keeping the same params shape.
Return JSON only: {{"summary": str, "options": [{{"rule_id": str, "new_params": {{...}}, "description": str}}]}}
Do not change rules that are not listed. Do not claim an option works; the solver will check it."""
