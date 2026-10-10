"""FastAPI application adapter for GeCompose backend facade."""
from __future__ import annotations
import base64
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from backend import api, config
from backend.models import Conflict, Roster, Rule, Schedule
from backend.http.auth import (
    SESSION_COOKIE_NAME,
    create_session,
    create_user,
    delete_session,
    get_user_by_email,
    get_user_or_demo,
    require_coordinator,
    require_user,
    seed_demo_users,
    verify_password,
)
from backend.http.schemas import (
    ApproveOptionRequest,
    DashboardSummaryResponse,
    EditRuleRequest,
    ExplainConflictRequest,
    ForgotPasswordRequest,
    MedOpsApproveRequest,
    MedOpsDispatchIntakeRequest,
    MedOpsExplainRequest,
    MedOpsOptimizeRequest,
    MedOpsSimulateRequest,
    ReliefApproveRequest,
    ReliefDispatchIntakeRequest,
    ReliefExplainRequest,
    ReliefOptimizeRequest,
    ReliefSimulateRequest,
    ResetPasswordRequest,
    ScoreboardRequest,
    SolveRequest,
    TextIntakeRequest,
    UniversalSolveRequest,
    UserResponse,
    UserSignInRequest,
    UserSignUpRequest,
)
from backend.universal import (
    UniversalConstraintSolver,
    UniversalProblem,
    UniversalResource,
    UniversalTask,
)
from backend.medops import (
    HospitalORPlan,
    PatientCase,
    WhatIfHospitalDelta,
    get_medops_service,
)
from backend.reliefops import (
    AllocationPlan,
    DisasterIncident,
    PlanExplanation,
    ReliefCamp,
    ReliefRequest,
    ScenarioComparison,
    WhatIfDelta,
    get_reliefops_service,
    validate_allocation_plan,
)




@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables and default users exist
    seed_demo_users()
    yield


app = FastAPI(
    title="GeCompose Enterprise API",
    description="Universal Constraint-Satisfaction Scheduling & Multi-Party Consent Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS setup for Vite frontend (http://localhost:5173 and others)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# Authentication Endpoints
# =========================================================================

@app.post("/api/v1/auth/sign-up", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@app.post("/auth/sign-up", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(body: UserSignUpRequest, response: Response):
    try:
        user = await run_in_threadpool(create_user, body.name, body.email, body.password)
        session_id = await run_in_threadpool(create_session, user["id"])
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="lax",
            secure=False,  # Set True in production HTTPS
            max_age=7 * 24 * 3600,
        )
        return UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            token=session_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/v1/auth/sign-in", response_model=UserResponse)
@app.post("/auth/sign-in", response_model=UserResponse)
async def sign_in(body: UserSignInRequest, response: Response):
    user = await run_in_threadpool(get_user_by_email, body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    session_id = await run_in_threadpool(create_session, user["id"])
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=7 * 24 * 3600,
    )
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        token=session_id,
    )


@app.get("/api/v1/auth/me", response_model=UserResponse)
@app.get("/auth/me", response_model=UserResponse)
async def get_me(user: UserResponse = Depends(require_user)):
    return user


@app.post("/api/v1/auth/sign-out", status_code=status.HTTP_204_NO_CONTENT)
@app.post("/auth/sign-out", status_code=status.HTTP_204_NO_CONTENT)
async def sign_out(request: Request, response: Response):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_id = auth_header[7:].strip()
    if session_id:
        await run_in_threadpool(delete_session, session_id)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return None


@app.post("/api/v1/auth/forgot-password")
@app.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    # Generic response non-enumerating whether email exists
    return {"message": "If this email is registered, instructions will be delivered."}


@app.post("/api/v1/auth/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(body: ResetPasswordRequest):
    return None


# =========================================================================
# Domain & Scheduling Endpoints
# =========================================================================

@app.get("/api/v1/health")
async def health_check():
    health = await run_in_threadpool(api.health)
    return health.model_dump()


@app.get("/api/v1/dashboard/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(user: UserResponse = Depends(require_user)):
    rules = await run_in_threadpool(api.list_rules)
    confirmed_count = sum(1 for r in rules if r.status == "confirmed")
    draft_count = sum(1 for r in rules if r.status == "draft")

    latest = await run_in_threadpool(api.get_latest_schedule)
    pending = await run_in_threadpool(api.get_pending_schedule)
    active_sched = pending or latest

    h = await run_in_threadpool(api.health)
    healthy = all(item.get("ok", False) for item in h.items.values())

    # Check conflict state by dry run or latest known
    conflict_active = False
    conflict_ids = []
    try:
        sol = await run_in_threadpool(api.solve, True)
        if sol.status == "infeasible" and sol.conflict:
            conflict_active = True
            conflict_ids = sol.conflict.rule_ids
    except Exception:
        pass

    latest_schedule_hash = hashing.hexs(hashing.schedule_hash(latest)) if latest else None

    return DashboardSummaryResponse(
        confirmed_rules_count=confirmed_count,
        draft_rules_count=draft_count,
        conflict_active=conflict_active,
        conflict_rule_ids=conflict_ids,
        scheduled_sessions_count=len(active_sched.placements) if active_sched else 0,
        published_version=latest.version if latest else None,
        latest_schedule_hash=latest_schedule_hash,
        system_healthy=healthy,
    )


@app.get("/api/v1/roster")
async def get_roster(user: UserResponse = Depends(require_user)):
    try:
        roster = await run_in_threadpool(api.get_roster)
        return roster.model_dump()
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/rules")
async def list_rules(
    status: Optional[str] = Query(None),
    user: UserResponse = Depends(require_user),
):
    rules = await run_in_threadpool(api.list_rules, status)
    return [r.model_dump() for r in rules]


@app.patch("/api/v1/rules/{rule_id}")
async def edit_rule(
    rule_id: str,
    body: EditRuleRequest,
    user: UserResponse = Depends(require_coordinator),
):
    try:
        updated = await run_in_threadpool(api.edit_rule, rule_id, body.params, body.owner)
        return updated.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/rules/{rule_id}/confirm")
async def confirm_rule(
    rule_id: str,
    user: UserResponse = Depends(require_coordinator),
):
    try:
        confirmed = await run_in_threadpool(api.confirm_rule, rule_id)
        return confirmed.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/rules/{rule_id}/reject")
async def reject_rule(
    rule_id: str,
    user: UserResponse = Depends(require_coordinator),
):
    try:
        rejected = await run_in_threadpool(api.reject_rule, rule_id)
        return rejected.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/intake/text")
async def intake_text(
    body: TextIntakeRequest,
    user: UserResponse = Depends(require_user),
):
    try:
        rules = await run_in_threadpool(api.ingest_text, body.text)
        return [r.model_dump() for r in rules]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/intake/audio")
async def intake_audio(
    file: UploadFile = File(...),
    user: UserResponse = Depends(require_user),
):
    content = await file.read()
    try:
        rules = await run_in_threadpool(api.ingest_audio, content, file.filename or "audio.wav")
        return [r.model_dump() for r in rules]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/intake/image")
async def intake_image(
    file: UploadFile = File(...),
    user: UserResponse = Depends(require_user),
):
    content = await file.read()
    try:
        rules = await run_in_threadpool(api.ingest_image, content, file.filename or "image.png")
        return [r.model_dump() for r in rules]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/intake/sheet")
async def intake_sheet(
    file: UploadFile = File(...),
    user: UserResponse = Depends(require_user),
):
    content = await file.read()
    try:
        result = await run_in_threadpool(api.ingest_sheet, content, file.filename or "sheet.xlsx")
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/intake/dump")
@app.post("/intake/dump")
@app.post("/api/v1/intake/data-dump")
@app.post("/intake/data-dump")
async def intake_data_dump(
    files: list[UploadFile] = File(default=[]),
    instructions: str = Form(default=""),
    notes: str = Form(default=""),
    user: UserResponse = Depends(get_user_or_demo),
):
    try:
        file_payloads: list[tuple[str, bytes]] = []
        for f in files:
            content = await f.read()
            file_payloads.append((f.filename or "uploaded_file", content))
        result = await run_in_threadpool(api.ingest_dump, file_payloads, instructions, notes)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/solve")
async def solve(
    body: SolveRequest,
    user: UserResponse = Depends(require_user),
):
    result = await run_in_threadpool(api.solve, body.minimal_change)
    return result.model_dump()


@app.get("/api/v1/schedules/latest")
async def get_latest_schedule(user: UserResponse = Depends(require_user)):
    sched = await run_in_threadpool(api.get_latest_schedule)
    if not sched:
        raise HTTPException(status_code=404, detail="No published schedule found")
    return sched.model_dump()


@app.get("/api/v1/schedules/pending")
async def get_pending_schedule(user: UserResponse = Depends(require_user)):
    sched = await run_in_threadpool(api.get_pending_schedule)
    if not sched:
        raise HTTPException(status_code=404, detail="No pending schedule in solver memory")
    return sched.model_dump()


@app.get("/api/v1/schedule/why/{session_id}")
async def why_cell(
    session_id: str,
    user: UserResponse = Depends(require_user),
):
    influences = await run_in_threadpool(api.why_cell, session_id)
    return [r.model_dump() for r in influences]


@app.post("/api/v1/conflicts/explain")
async def explain_conflict(
    body: ExplainConflictRequest,
    user: UserResponse = Depends(require_user),
):
    try:
        explanation = await run_in_threadpool(api.explain_conflict, body.conflict)
        return explanation.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/options/{option_id}/approve")
async def approve_option(
    option_id: str,
    body: ApproveOptionRequest,
    user: UserResponse = Depends(require_user),
):
    result = await run_in_threadpool(api.approve_option, option_id, body.as_user)
    return result.model_dump()


@app.post("/api/v1/options/{option_id}/apply")
async def apply_option(
    option_id: str,
    user: UserResponse = Depends(require_coordinator),
):
    try:
        updated = await run_in_threadpool(api.apply_option, option_id)
        return updated.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/publish")
async def publish(user: UserResponse = Depends(require_coordinator)):
    try:
        res = await run_in_threadpool(api.publish)
        return {
            "hash": res.hash,
            "tx_hash": res.tx_hash,
            "version": res.version,
            "json_bytes_b64": base64.b64encode(res.json_bytes).decode("ascii"),
            "csv_bytes_b64": base64.b64encode(res.csv_bytes).decode("ascii"),
            "ics_bytes_b64": base64.b64encode(res.ics_bytes).decode("ascii"),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/verify")
async def verify_file(
    file: UploadFile = File(None),
    raw_json: Optional[str] = None,
    user: UserResponse = Depends(require_user),
):
    if file:
        data = await file.read()
    elif raw_json:
        data = raw_json.encode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Provide file or raw_json")

    res = await run_in_threadpool(api.verify_file, data)
    return res.model_dump()


@app.post("/api/v1/scoreboard")
async def scoreboard(
    body: ScoreboardRequest,
    user: UserResponse = Depends(require_user),
):
    res = await run_in_threadpool(api.run_scoreboard, body.runs)
    return res.model_dump()


@app.get("/api/v1/ledger/events")
@app.get("/api/v1/chain/events")
async def ledger_events(
    event: Optional[str] = Query(None),
    limit: int = Query(200),
    user: UserResponse = Depends(require_user),
):
    try:
        events = await run_in_threadpool(api.ledger_events, event, limit)
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ledger/verify")
async def ledger_verify(user: UserResponse = Depends(require_user)):
    try:
        result = await run_in_threadpool(api.verify_ledger)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/demo/seed")
async def seed_demo(user: UserResponse = Depends(require_coordinator)):
    try:
        await run_in_threadpool(api.seed_demo)
        return {"ok": True, "message": "Demo data seeded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/demo/reset")
async def reset_demo(user: UserResponse = Depends(require_coordinator)):
    try:
        await run_in_threadpool(api.reset_demo)
        return {"ok": True, "message": "Demo state reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Export download endpoints

@app.get("/api/v1/exports/schedule.json")
async def export_json():
    sched = await run_in_threadpool(api.get_latest_schedule)
    if not sched:
        raise HTTPException(status_code=404, detail="No published schedule")
    data = api.export.json_bytes(sched)
    return Response(content=data, media_type="application/json", headers={"Content-Disposition": f"attachment; filename=schedule_v{sched.version}.json"})


@app.get("/api/v1/exports/schedule.csv")
async def export_csv():
    sched = await run_in_threadpool(api.get_latest_schedule)
    if not sched:
        raise HTTPException(status_code=404, detail="No published schedule")
    data = api.export.csv_bytes(sched)
    return Response(content=data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=schedule_v{sched.version}.csv"})


@app.get("/api/v1/exports/schedule.ics")
async def export_ics():
    sched = await run_in_threadpool(api.get_latest_schedule)
    if not sched:
        raise HTTPException(status_code=404, detail="No published schedule")
    roster = await run_in_threadpool(api.get_roster)
    data = api.export.ics_bytes(sched, roster)
    return Response(content=data, media_type="text/calendar", headers={"Content-Disposition": f"attachment; filename=schedule_v{sched.version}.ics"})


# =========================================================================
# GeCompose ReliefOps — Disaster Relief Supply Allocation Engine Endpoints
# =========================================================================

@app.get("/api/v1/reliefops/overview")
async def reliefops_overview():
    srv = get_reliefops_service()
    return await run_in_threadpool(srv.get_overview)


@app.get("/api/v1/reliefops/camps")
async def reliefops_list_camps():
    srv = get_reliefops_service()
    camps = await run_in_threadpool(srv.registry.get_camps)
    return [c.model_dump() for c in camps]


@app.get("/api/v1/reliefops/inventory")
async def reliefops_list_inventory():
    srv = get_reliefops_service()
    inv = await run_in_threadpool(srv.registry.get_inventory)
    return [i.model_dump() for i in inv]


@app.get("/api/v1/reliefops/warehouses")
async def reliefops_list_warehouses():
    srv = get_reliefops_service()
    wh = await run_in_threadpool(srv.registry.get_warehouses)
    return [w.model_dump() for w in wh]


@app.get("/api/v1/reliefops/vehicles")
async def reliefops_list_vehicles():
    srv = get_reliefops_service()
    v = await run_in_threadpool(srv.registry.get_vehicles)
    return [veh.model_dump() for veh in v]


@app.get("/api/v1/reliefops/resources")
async def reliefops_list_resources():
    srv = get_reliefops_service()
    res = await run_in_threadpool(srv.registry.get_resources)
    return [r.model_dump() for r in res]


@app.get("/api/v1/reliefops/requests")
async def reliefops_list_requests():
    srv = get_reliefops_service()
    reqs = await run_in_threadpool(srv.registry.get_requests)
    return [r.model_dump() for r in reqs]


@app.post("/api/v1/reliefops/intake/csv")
async def reliefops_intake_csv(file: UploadFile = File(...)):
    content = await file.read()
    srv = get_reliefops_service()
    reqs = await run_in_threadpool(srv.intake_csv, content)
    return [r.model_dump() for r in reqs]


@app.post("/api/v1/reliefops/intake/dispatch")
async def reliefops_intake_dispatch(body: ReliefDispatchIntakeRequest):
    srv = get_reliefops_service()
    reqs = await run_in_threadpool(srv.intake_dispatch_report, body.text)
    return [r.model_dump() for r in reqs]


@app.post("/api/v1/reliefops/optimize")
async def reliefops_optimize(body: ReliefOptimizeRequest | None = None):
    scenario_id = body.scenario_id if body else "SCENARIO-MAIN"
    scenario_name = body.scenario_name if body else "Optimal Relief Allocation"
    srv = get_reliefops_service()
    plan = await run_in_threadpool(srv.optimize_allocation, scenario_id, scenario_name)
    return plan.model_dump()


@app.get("/api/v1/reliefops/plan/latest")
async def reliefops_latest_plan():
    srv = get_reliefops_service()
    plan = await run_in_threadpool(srv.registry.get_latest_plan)
    if not plan:
        raise HTTPException(status_code=404, detail="No allocation plan generated yet")
    return plan.model_dump()


@app.get("/api/v1/reliefops/plan/{plan_id}")
async def reliefops_get_plan(plan_id: str):
    srv = get_reliefops_service()
    plan = await run_in_threadpool(srv.registry.get_plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found")
    return plan.model_dump()


@app.post("/api/v1/reliefops/simulate")
async def reliefops_simulate(body: ReliefSimulateRequest):
    srv = get_reliefops_service()
    delta = WhatIfDelta.model_validate(body.delta)
    sim_plan, comparison = await run_in_threadpool(
        srv.run_simulation, delta, body.scenario_id, body.scenario_name
    )
    return {
        "simulation_plan": sim_plan.model_dump(),
        "comparison": comparison.model_dump(),
    }


@app.post("/api/v1/reliefops/explain")
async def reliefops_explain(body: ReliefExplainRequest | None = None):
    plan_id = body.plan_id if body else None
    srv = get_reliefops_service()
    explanation = await run_in_threadpool(srv.explain_plan, plan_id)
    return explanation.model_dump()


@app.post("/api/v1/reliefops/approve")
async def reliefops_approve(body: ReliefApproveRequest):
    srv = get_reliefops_service()
    try:
        record = await run_in_threadpool(
            srv.approve_plan, body.plan_id, body.approved_by, body.notes
        )
        return record.model_dump()
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/reliefops/audit")
async def reliefops_audit(plan_id: Optional[str] = Query(None)):
    srv = get_reliefops_service()
    records = await run_in_threadpool(srv.audit.get_records, plan_id)
    is_valid, msg = await run_in_threadpool(srv.audit.verify_chain_integrity)
    return {
        "verified": is_valid,
        "message": msg,
        "records": [r.model_dump() for r in records],
    }


@app.post("/api/v1/reliefops/demo/seed")
async def reliefops_demo_seed():
    srv = get_reliefops_service()
    await run_in_threadpool(srv.registry.seed_cyclone_disaster_demo)
    return {"ok": True, "message": "Disaster relief demo environment seeded"}


# =========================================================================
# Universal Global Constraint Solver Endpoints
# =========================================================================

@app.post("/api/v1/universal/solve")
async def universal_solve(body: UniversalSolveRequest):
    try:
        problem = UniversalProblem.model_validate(body.problem)
        solver = UniversalConstraintSolver()
        solution = await run_in_threadpool(solver.solve, problem)
        return solution.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================================
# GeCompose MedOps — Hospital Emergency Surgical Theatre Endpoints
# =========================================================================

@app.get("/api/v1/medops/overview")
async def medops_overview():
    srv = get_medops_service()
    return await run_in_threadpool(srv.get_overview)


@app.get("/api/v1/medops/rooms")
async def medops_list_rooms():
    srv = get_medops_service()
    rooms = await run_in_threadpool(srv.registry.get_rooms)
    return [r.model_dump() for r in rooms]


@app.get("/api/v1/medops/staff")
async def medops_list_staff():
    srv = get_medops_service()
    staff = await run_in_threadpool(srv.registry.get_staff)
    return [s.model_dump() for s in staff]


@app.get("/api/v1/medops/cases")
async def medops_list_cases():
    srv = get_medops_service()
    cases = await run_in_threadpool(srv.registry.get_cases)
    return [c.model_dump() for c in cases]


@app.post("/api/v1/medops/intake/csv")
async def medops_intake_csv(file: UploadFile = File(...)):
    content = await file.read()
    srv = get_medops_service()
    cases = await run_in_threadpool(srv.intake_csv, content)
    return [c.model_dump() for c in cases]


@app.post("/api/v1/medops/intake/dispatch")
async def medops_intake_dispatch(body: MedOpsDispatchIntakeRequest):
    srv = get_medops_service()
    cases = await run_in_threadpool(srv.intake_dispatch, body.text)
    return [c.model_dump() for c in cases]


@app.post("/api/v1/medops/optimize")
async def medops_optimize(body: MedOpsOptimizeRequest | None = None):
    plan_id = body.plan_id if body else None
    srv = get_medops_service()
    plan = await run_in_threadpool(srv.optimize_schedule, plan_id)
    return plan.model_dump()


@app.get("/api/v1/medops/plan/latest")
async def medops_latest_plan():
    srv = get_medops_service()
    plan = await run_in_threadpool(srv.registry.get_latest_plan)
    if not plan:
        raise HTTPException(status_code=404, detail="No surgical master plan generated yet")
    return plan.model_dump()


@app.get("/api/v1/medops/plan/{plan_id}")
async def medops_get_plan(plan_id: str):
    srv = get_medops_service()
    plan = await run_in_threadpool(srv.registry.get_plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Hospital plan '{plan_id}' not found")
    return plan.model_dump()


@app.post("/api/v1/medops/simulate")
async def medops_simulate(body: MedOpsSimulateRequest):
    srv = get_medops_service()
    delta = WhatIfHospitalDelta.model_validate(body.delta)
    sim_plan, comparison = await run_in_threadpool(
        srv.run_simulation, delta, body.scenario_id
    )
    return {
        "simulation_plan": sim_plan.model_dump(),
        "comparison": comparison.model_dump(),
    }


@app.post("/api/v1/medops/explain")
async def medops_explain(body: MedOpsExplainRequest | None = None):
    plan_id = body.plan_id if body else None
    srv = get_medops_service()
    explanation = await run_in_threadpool(srv.explain_schedule, plan_id)
    return explanation.model_dump()


@app.post("/api/v1/medops/approve")
async def medops_approve(body: MedOpsApproveRequest):
    srv = get_medops_service()
    try:
        record = await run_in_threadpool(
            srv.approve_schedule, body.plan_id, body.approved_by, body.notes
        )
        return record.model_dump()
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/medops/audit")
async def medops_audit(plan_id: Optional[str] = Query(None)):
    srv = get_medops_service()
    records = await run_in_threadpool(srv.audit.get_records, plan_id)
    is_valid, msg = await run_in_threadpool(srv.audit.verify_chain_integrity)
    return {
        "verified": is_valid,
        "message": msg,
        "records": [r.model_dump() for r in records],
    }


@app.post("/api/v1/medops/demo/seed")
async def medops_demo_seed():
    srv = get_medops_service()
    await run_in_threadpool(srv.registry.seed_level1_trauma_benchmark)
    return {"ok": True, "message": "Level-1 Trauma hospital surgical demo environment seeded"}


