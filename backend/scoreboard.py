"""Compare fixture/LLM baseline violations against deterministic solver output."""
from __future__ import annotations
import json
from pathlib import Path
from backend import config
from backend.llm.client import call_json
from backend.models import DraftRulesOut, Placement, Roster, Schedule
from backend.registry import db
from backend.solver.checker import check
from backend.solver.model import solve
from backend.api import ScoreboardResult,ScoreboardRow

def run(runs:int=5)->ScoreboardResult:
    if not 1<=runs<=50:raise ValueError("runs must be between 1 and 50")
    roster=db.get_roster();rules=db.list_rules("confirmed");rows=[]
    fixtures=Path(__file__).parent/"llm"/"fixtures"/"baseline_runs.json"
    if config.MOCK_LLM:
        raw=json.loads(fixtures.read_text(encoding="utf-8")) if fixtures.exists() else []
        baselines=(raw* ((runs+len(raw)-1)//len(raw)))[:runs] if raw else [{} for _ in range(runs)]
    else:baselines=None
    for index in range(runs):
        detail=[]
        try:
            if baselines is None:
                prompt=json.dumps({"roster":roster.model_dump(),"rules":[r.model_dump() for r in rules],"schema":{"placements":[{"session_id":"","teacher":"","room":"","day":0,"slot":0}],"version":1}},ensure_ascii=False)
                from backend.models import Schedule as ScheduleSchema
                output=call_json("baseline_schedule","reason",[{"role":"system","content":"Produce a complete timetable as JSON. Follow the schema exactly."},{"role":"user","content":prompt}],ScheduleSchema)
                baseline=output
            else:
                baseline=Schedule.model_validate(baselines[index])
            detail=check(baseline,roster,rules)
            baseline_count=len(detail)
        except Exception as exc:baseline_count=1;detail=[f"invalid output: {exc}"]
        status,schedule,_=solve(roster,rules)
        deterministic=check(schedule,roster,rules) if status=="feasible" and schedule else ["solver did not find a feasible schedule"]
        rows.append(ScoreboardRow(run=index+1,baseline_violations=baseline_count,baseline_details=detail,gecompose_violations=len(deterministic)))
    return ScoreboardResult(rows=rows)
