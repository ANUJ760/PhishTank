"""Production-grade unified HTTP REST API server exposing GeCompose services."""
from __future__ import annotations

import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path for direct script execution
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

from backend import api, config
from backend.models import Conflict, Rule
from backend.http.app import app


# -------------------------------------------------------------------------
# Direct Convenience Endpoints (for Streamlit, direct curl, and testing)
# -------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    h = api.health().items
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>GeCompose Backend API & Gemma Engine</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 960px; margin: 40px auto; line-height: 1.6; padding: 0 20px; color: #1e293b; background: #fafafa; }}
            h1 {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }}
            .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px 24px; margin: 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            .pill-ok {{ background: #dcfce7; color: #15803d; padding: 3px 10px; border-radius: 999px; font-weight: 600; font-size: 0.85em; }}
            .pill-fail {{ background: #fee2e2; color: #b91c1c; padding: 3px 10px; border-radius: 999px; font-weight: 600; font-size: 0.85em; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
            th, td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; text-align: left; }}
            th {{ background: #f8fafc; font-weight: 600; color: #475569; }}
            a {{ color: #2563eb; text-decoration: none; font-weight: 500; }}
            a:hover {{ text-decoration: underline; }}
            code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; color: #0f172a; }}
            ul {{ columns: 2; -webkit-columns: 2; -moz-columns: 2; }}
            li {{ margin-bottom: 8px; }}
        </style>
    </head>
    <body>
        <h1>GeCompose Backend Engine</h1>
        <p>Constraint-Satisfaction Timetable Scheduling with Ollama / Gemma 4B & 12B Intelligence and Deterministic Verification.</p>
        
        <div class="card">
            <h3>System Status</h3>
            <table>
                <tr><th>Component</th><th>Status</th><th>Details</th></tr>
                {''.join(f"<tr><td><b>{k}</b></td><td><span class='{'pill-ok' if v.get('ok') else 'pill-fail'}'>{'OK' if v.get('ok') else 'FAIL'}</span></td><td>{v.get('detail')}</td></tr>" for k, v in h.items())}
            </table>
        </div>

        <div class="card">
            <h3>Available REST API Endpoints</h3>
            <ul>
                <li><a href="/health"><code>GET /health</code></a> - Health status of all services</li>
                <li><a href="/roster"><code>GET /roster</code></a> - Active university roster</li>
                <li><a href="/rules"><code>GET /rules</code></a> - List active constraints (?status=)</li>
                <li><a href="/schedule"><code>GET /schedule</code></a> - Current verified schedule</li>
                <li><a href="/events"><code>GET /events</code></a> - Audit ledger events</li>
                <li><a href="/scoreboard"><code>GET /scoreboard</code></a> - Constraint violation benchmarks</li>
                <li><code>POST /solve</code> - Trigger CP-SAT solver</li>
                <li><code>POST /publish</code> - Publish verified schedule</li>
                <li><code>POST /verify</code> - Verify schedule hash against registry</li>
                <li><code>POST /intake/text</code> - Ingest text rule (Gemma 4B)</li>
                <li><code>POST /intake/audio</code> - Ingest speech rule (Gemma 4B)</li>
                <li><code>POST /intake/image</code> - Ingest photo rule (Gemma 4B)</li>
                <li><code>POST /intake/sheet</code> - Ingest Excel workload sheet</li>
                <li><code>POST /rules/{{id}}/confirm</code> - Confirm draft rule</li>
                <li><code>POST /rules/{{id}}/reject</code> - Reject draft rule</li>
                <li><code>POST /conflicts/explain</code> - Explain conflict (Gemma 12B)</li>
                <li><code>POST /options/{{id}}/approve</code> - Multi-party consent approval</li>
                <li><code>POST /options/{{id}}/apply</code> - Apply approved option</li>
                <li><code>POST /demo/seed</code> - Seed baseline demo environment</li>
                <li><code>POST /demo/reset</code> - Reset database to clean state</li>
                <li><a href="/api/v1/reliefops/overview"><code>GET /api/v1/reliefops/overview</code></a> - ReliefOps disaster status</li>
                <li><a href="/api/v1/reliefops/camps"><code>GET /api/v1/reliefops/camps</code></a> - Relief camps and access</li>
                <li><code>POST /api/v1/reliefops/optimize</code> - CP-SAT supply allocation</li>
                <li><code>POST /api/v1/reliefops/simulate</code> - What-If counterfactual simulation</li>
                <li><code>POST /api/v1/reliefops/explain</code> - Gemma 12B plan rationale</li>
                <li><a href="/api/v1/reliefops/audit"><code>GET /api/v1/reliefops/audit</code></a> - SHA-256 audit ledger</li>
                <li><a href="/api/v1/medops/overview"><code>GET /api/v1/medops/overview</code></a> - MedOps hospital surgical status</li>
                <li><a href="/api/v1/medops/rooms"><code>GET /api/v1/medops/rooms</code></a> - Operating theatre suites</li>
                <li><a href="/api/v1/medops/cases"><code>GET /api/v1/medops/cases</code></a> - Emergency surgical triage cases</li>
                <li><code>POST /api/v1/medops/optimize</code> - CP-SAT surgical master schedule</li>
                <li><code>POST /api/v1/medops/simulate</code> - Mass-casualty surge simulation</li>
                <li><code>POST /api/v1/medops/explain</code> - Gemma 12B clinical operational explanation</li>
                <li><a href="/api/v1/medops/audit"><code>GET /api/v1/medops/audit</code></a> - Surgical audit ledger</li>
                <li><code>POST /api/v1/universal/solve</code> - Domain-agnostic global constraint solver</li>
            </ul>
        </div>
    </body>
    </html>
    """)


@app.get("/health")
async def get_health():
    try:
        return JSONResponse(api.health().model_dump())
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@app.get("/roster")
async def get_roster():
    try:
        return JSONResponse(api.get_roster().model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)


@app.get("/rules")
async def get_rules(status: str | None = None):
    try:
        rules = [r.model_dump() for r in api.list_rules(status)]
        return JSONResponse({"rules": rules})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/intake/dump")
async def post_intake_dump(request: Request):
    try:
        form = await request.form()
        instructions = form.get("instructions", "")
        notes = form.get("notes", "")
        files_list = form.getlist("files")
        file_payloads = []
        for item in files_list:
            if hasattr(item, "read"):
                content = await item.read()
                filename = getattr(item, "filename", "dump_file")
                file_payloads.append((filename, content))
        res = api.ingest_dump(file_payloads, instructions=str(instructions), notes=str(notes))
        return JSONResponse(res.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/rules", status_code=201)
async def post_rule(rule_data: dict):
    try:
        rule = Rule.model_validate(rule_data)
        api.db.save_rule(rule)
        return JSONResponse(rule.model_dump(), status_code=201)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/rules/{id}")
async def edit_rule(id: str, edit_data: dict):
    try:
        updated = api.edit_rule(id, params=edit_data.get("params"), owner=edit_data.get("owner"))
        return JSONResponse(updated.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/rules/{id}/confirm")
async def confirm_rule(id: str):
    try:
        rule = api.confirm_rule(id)
        return JSONResponse(rule.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/rules/{id}/reject")
async def reject_rule(id: str):
    try:
        rule = api.reject_rule(id)
        return JSONResponse(rule.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.get("/schedule")
async def get_schedule():
    sched = api.db.latest_schedule()
    if sched:
        return JSONResponse(sched.model_dump())
    return JSONResponse({"message": "No published schedule available yet"}, status_code=404)


@app.post("/solve")
async def post_solve(minimal_change: bool = True):
    try:
        result = api.solve(minimal_change=minimal_change)
        return JSONResponse(result.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/conflicts/explain")
async def explain_conflict(conflict_data: dict):
    try:
        conflict = Conflict.model_validate(conflict_data)
        explanation = api.explain_conflict(conflict)
        return JSONResponse(explanation.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/options/{id}/approve")
async def approve_option(id: str, body: dict):
    try:
        as_user = body.get("as_user", "")
        result = api.approve_option(id, as_user=as_user)
        return JSONResponse(result.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/options/{id}/apply")
async def apply_option(id: str):
    try:
        rule = api.apply_option(id)
        return JSONResponse(rule.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.get("/why/{session_id}")
async def get_why(session_id: str):
    try:
        rules = api.why_cell(session_id)
        return JSONResponse({"session_id": session_id, "rules": [r.model_dump() for r in rules]})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/publish")
async def post_publish():
    try:
        pub = api.publish()
        return JSONResponse({
            "hash": pub.hash,
            "tx_hash": pub.tx_hash,
            "version": pub.version,
            "published": True,
            "anchored": True,
        })
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/verify")
async def post_verify(request: Request):
    try:
        body = await request.body()
        result = api.verify_file(body)
        return JSONResponse(result.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.get("/events")
@app.get("/ledger/events")
async def get_events(event: str | None = None, limit: int = 200):
    try:
        return JSONResponse({"events": api.ledger_events(event, limit)})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/ledger/verify")
async def verify_ledger():
    try:
        return JSONResponse(api.verify_ledger())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/audit")
async def get_audit():
    try:
        return JSONResponse({"events": api.audit_events()})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/scoreboard")
async def get_scoreboard(runs: int = 3):
    try:
        res = api.run_scoreboard(runs)
        return JSONResponse(res.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/demo/seed")
async def post_seed():
    try:
        api.seed_demo()
        return JSONResponse({"status": "seeded", "ok": True})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/demo/reset")
async def post_reset():
    try:
        api.reset_demo()
        return JSONResponse({"status": "reset", "ok": True})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/export/{format}")
async def export_format(format: str):
    fmt = format.lower()
    sched = api.db.latest_schedule()
    if not sched:
        return JSONResponse({"error": "No schedule to export"}, status_code=404)
    roster = api.db.get_roster()

    if fmt == "csv":
        from backend.export import csv_bytes
        return Response(csv_bytes(sched), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=schedule.csv"})
    elif fmt == "ics":
        from backend.export import ics_bytes
        return Response(ics_bytes(sched, roster), media_type="text/calendar", headers={"Content-Disposition": "attachment; filename=schedule.ics"})
    else:
        from backend.export import json_bytes
        return Response(json_bytes(sched), media_type="application/json", headers={"Content-Disposition": "attachment; filename=schedule.json"})


@app.get("/uploads/{filename}")
async def get_upload(filename: str):
    data = api.get_upload(filename)
    if data is None:
        return JSONResponse({"error": "Upload not found"}, status_code=404)
    return Response(data, media_type="application/octet-stream")


def run():
    import uvicorn
    uvicorn.run("backend.server:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
