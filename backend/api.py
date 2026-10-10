"""Stable facade consumed by the Streamlit frontend."""
from __future__ import annotations
import json, logging, shutil, threading, time
from pathlib import Path
from typing import Literal
from pydantic import BaseModel
from backend import config, hashing
from backend.export import csv_bytes,ics_bytes,json_bytes
from backend.intake import sheet_parser,voice_photo
from backend.llm.client import call_json
from backend.llm.prompts import explain_conflict as explain_prompt
from backend.models import Conflict,ExplainOut,Explanation,RelaxOption,Rule,Roster,Schedule,validate_params
from backend.registry import db
from backend.solver.checker import check
from backend.solver.conflicts import shrink_core,verify_option
from backend.solver.model import solve as solve_model
from backend.solver.trace import why

log=logging.getLogger(__name__)
class IngestSheetResult(BaseModel): rules:list[Rule];cache_hit:bool;attempts:int;tokens_used:int;seconds:float
class SolveResult(BaseModel): status:Literal["feasible","infeasible","unknown","error"];schedule:Schedule|None=None;conflict:Conflict|None=None;moved:list[str]=[];solve_ms:int=0;message:str=""
class ApprovalResult(BaseModel):ok:bool;tx_hash:str|None=None;error:str|None=None
class PublishResult(BaseModel):hash:str;tx_hash:str="";version:int;json_bytes:bytes;csv_bytes:bytes;ics_bytes:bytes
class VerifyResult(BaseModel):match:bool;recomputed_hash:str;anchored:bool=True;error:str|None=None
class ScoreboardRow(BaseModel):run:int;baseline_violations:int;baseline_details:list[str];gecompose_violations:int
class ScoreboardResult(BaseModel):rows:list[ScoreboardRow]
class Health(BaseModel):items:dict[str,dict]

_lock=threading.RLock(); _pending:Schedule|None=None; _cycles=0
def health()->Health:
    from backend.healthcheck import inspect
    return Health(items=inspect())
def get_roster()->Roster:return db.get_roster()
def ingest_audio(wav:bytes,filename:str)->list[Rule]:return voice_photo.ingest_audio(wav,filename)
def ingest_image(img:bytes,filename:str)->list[Rule]:return voice_photo.ingest_image(img,filename)
def ingest_text(text:str)->list[Rule]:return voice_photo.ingest_text(text)
def ingest_sheet(xlsx:bytes,filename:str)->IngestSheetResult:
    if len(xlsx)>50*1024*1024: raise ValueError("Spreadsheet exceeds 50 MiB")
    path=config.UPLOAD_DIR/(Path(filename).name+".staging.xlsx"); path.parent.mkdir(parents=True,exist_ok=True)
    try:
        path.write_bytes(xlsx); result=sheet_parser.ingest_sheet(path,Path(filename).name)
        db.save_upload(Path(filename).name,xlsx); return IngestSheetResult(**result.model_dump())
    finally:path.unlink(missing_ok=True)
def list_rules(status:str|None=None)->list[Rule]:return db.list_rules(status)
def edit_rule(rule_id:str,params:dict|None=None,owner:str|None=None)->Rule:
    rule=db.get_rule(rule_id)
    if rule.status=="confirmed":raise ValueError("Confirmed rules cannot be edited; create a reviewed replacement")
    roster=db.get_roster()
    if params is not None:validate_params(rule.type,params,roster);rule=rule.model_copy(update={"params":params})
    if owner is not None:
        if not owner.strip():raise ValueError("Rule owner cannot be empty")
        rule=rule.model_copy(update={"owner":owner.strip()})
    db.save_rule(rule);return rule
def confirm_rule(rule_id:str)->Rule:
    rule=db.get_rule(rule_id)
    if rule.status!="draft":raise ValueError("Only draft rules can be confirmed")
    validate_params(rule.type,rule.params,db.get_roster()); salt=hashing.new_salt(); digest=hashing.rule_hash(rule.id,rule.type,rule.owner,salt); hex_digest=hashing.hexs(digest)
    db.save_rule(rule.model_copy(update={"status":"confirmed"}),salt,hex_digest)
    db.log_audit_event("RuleConfirmed",rule.id,rule.owner,{"rule_hash":hex_digest})
    return db.get_rule(rule_id)
def reject_rule(rule_id:str)->Rule:
    rule=db.get_rule(rule_id)
    if rule.status!="draft":raise ValueError("Only draft rules can be rejected")
    rejected=rule.model_copy(update={"status":"rejected"});db.save_rule(rejected);return rejected
def get_upload(filename:str)->bytes|None:return db.get_upload(filename)
def solve(minimal_change:bool=True)->SolveResult:
    global _pending,_cycles
    with _lock:
        start=time.monotonic()
        try:
            roster=db.get_roster(); rules=db.list_rules("confirmed"); prev=db.latest_schedule() if minimal_change else None
            status,schedule,core=solve_model(roster,rules,prev)
            elapsed=int((time.monotonic()-start)*1000)
            if status=="infeasible":
                core=shrink_core(roster,rules,core or []); indexed={r.id:r for r in rules}; conflict=Conflict(rule_ids=core,owners=[indexed[r].owner for r in core])
                return SolveResult(status="infeasible",conflict=conflict,solve_ms=elapsed,message="The confirmed rules have no feasible schedule.")
            if status!="feasible" or schedule is None:return SolveResult(status="unknown",solve_ms=elapsed,message="The solver could not find a schedule within its time limit.")
            violations=check(schedule,roster,rules)
            if violations:return SolveResult(status="error",solve_ms=elapsed,message="Independent schedule check failed: "+"; ".join(violations))
            schedule=schedule.model_copy(update={"version":(prev.version+1 if prev else 1)})
            before={p.session_id:p for p in prev.placements} if prev else {}; after={p.session_id:p for p in schedule.placements}
            moved=[sid for sid,p in after.items() if sid in before and p!=before[sid]]
            _pending=schedule;_cycles=0
            return SolveResult(status="feasible",schedule=schedule,moved=moved,solve_ms=elapsed)
        except Exception as exc:
            log.exception("Schedule solve failed");return SolveResult(status="error",solve_ms=int((time.monotonic()-start)*1000),message=str(exc))
def explain_conflict(conflict:Conflict)->Explanation:
    global _cycles
    with _lock:
        if _cycles>=3:raise ValueError("Maximum of three conflict resolution cycles reached")
        _cycles+=1
    by_id={r.id:r for r in db.list_rules("confirmed")}; core=[by_id[r] for r in conflict.rule_ids if r in by_id]
    text="\n".join(f"{r.id} [{r.type}] owner={r.owner} params={json.dumps(r.params,ensure_ascii=False)}" for r in core)
    out=call_json("explain_conflict","reason",[{"role":"system","content":"Explain rule conflicts clearly and propose bounded alternatives."},{"role":"user","content":explain_prompt(text)}],ExplainOut)
    options=[];roster=db.get_roster()
    for candidate in out.options:
        rule=by_id.get(candidate.rule_id)
        if rule is None:continue
        try:validate_params(rule.type,candidate.new_params,roster)
        except (ValueError,KeyError,TypeError):continue
        if not verify_option(roster,core,rule.id,candidate.new_params):continue
        digest=hashing.option_hash(rule.id,candidate.new_params)
        option=RelaxOption(id=db.next_option_id(),rule_id=rule.id,new_params=candidate.new_params,description=candidate.description,approver=rule.owner,verified=True,option_hash=hashing.hexs(digest));db.save_option(option);options.append(option)
    return Explanation(summary=out.summary,options=options)
def approve_option(option_id:str,as_user:str)->ApprovalResult:
    try:
        option=db.get_option(option_id)
        if not option.verified:return ApprovalResult(ok=False,error="This option was not solver-verified")
        rule=db.get_rule(option.rule_id)
        if as_user!=option.approver and as_user!=rule.owner:
            return ApprovalResult(ok=False,error=f"Only {option.approver} can approve this relaxation (attempted by {as_user})")
        if option.approved:
            return ApprovalResult(ok=False,error="Option is already approved")
        updated=option.model_copy(update={"approved":True,"approved_by":as_user})
        db.save_option(updated)
        audit_ref=f"appr_{option.id}_{int(time.time())}"
        db.log_audit_event("RelaxationApproved",option.id,as_user,{"rule_id":option.rule_id,"option_hash":option.option_hash})
        return ApprovalResult(ok=True,tx_hash=audit_ref)
    except Exception as exc:log.warning("Consent approval failed: %s",exc);return ApprovalResult(ok=False,error=str(exc))
def apply_option(option_id:str)->Rule:
    option=db.get_option(option_id)
    if not option.verified:raise ValueError("Option was not verified")
    if not option.approved:raise ValueError("The rule owner has not approved this option")
    rule=db.get_rule(option.rule_id)
    validate_params(rule.type,option.new_params,db.get_roster())
    updated=rule.model_copy(update={"params":option.new_params});db.save_rule(updated)
    db.log_audit_event("RuleUpdated",rule.id,option.approved_by or option.approver,{"new_params":option.new_params})
    return updated
def why_cell(session_id:str)->list[Rule]:
    schedule=_pending or db.latest_schedule()
    return why(session_id,schedule,db.list_rules("confirmed")) if schedule else []
def publish()->PublishResult:
    global _pending
    with _lock:
        if _pending is None:raise ValueError("Solve a feasible schedule before publishing")
        violations=check(_pending,db.get_roster(),db.list_rules("confirmed"))
        if violations:raise ValueError("Schedule failed independent verification: "+"; ".join(violations))
        digest=hashing.schedule_hash(_pending)
        hex_digest=hashing.hexs(digest)
        db.save_schedule(_pending,hex_digest,hex_digest)
        db.log_audit_event("SchedulePublished",hex_digest,"Coordinator",{"version":_pending.version,"hash":hex_digest})
        schedule=_pending;_pending=None
        return PublishResult(hash=hex_digest,tx_hash=hex_digest,version=schedule.version,json_bytes=json_bytes(schedule),csv_bytes=csv_bytes(schedule),ics_bytes=ics_bytes(schedule,db.get_roster()))
def verify_file(data:bytes)->VerifyResult:
    try:
        raw=json.loads(data);schedule=Schedule.model_validate(raw);digest=hashing.schedule_hash(schedule);hex_digest=hashing.hexs(digest);anchored=db.is_schedule_published(hex_digest)
        return VerifyResult(match=anchored,recomputed_hash=hex_digest,anchored=anchored,error=None if anchored else "Schedule hash is not found in published registry")
    except Exception as exc:return VerifyResult(match=False,recomputed_hash="",anchored=False,error=str(exc))
def run_scoreboard(runs:int=5)->ScoreboardResult:
    from backend.scoreboard import run
    return run(runs)
def chain_events()->list[dict]:return db.list_audit_events()
def audit_events()->list[dict]:return db.list_audit_events()
def seed_demo()->None:
    from backend.samples import DEMO_ROSTER
    reset_demo();roster=Roster.model_validate(DEMO_ROSTER);db.save_roster(roster)
    for rid,rtype,owner,params in [("R1","pin_session","Dept Head",{"session_id":"DB_LAB","day":0,"slots":[0,1,2]}),("R2","only_qualified","Dean",{"session_id":"DB_LAB","teachers":["Prof. Rao"]})]:
        rule=Rule(id=rid,type=rtype,owner=owner,params=params,status="draft");db.save_rule(rule);confirm_rule(rid)
    result=solve(False)
    if result.status!="feasible":raise RuntimeError(result.message)
    publish()
def reset_demo(keep_parsers:bool=False)->None:
    global _pending,_cycles
    with _lock:_pending=None;_cycles=0
    db.reset_db(keep_parsers=keep_parsers)
    uploads=config.UPLOAD_DIR
    if uploads.exists():shutil.rmtree(uploads)
