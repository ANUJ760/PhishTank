"""Production-grade HTTP REST API server exposing GeCompose services with CORS and full endpoint coverage."""
from __future__ import annotations

import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path for direct script execution
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from backend import api, config
from backend.models import Conflict, Rule


async def index(request):
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
            </ul>
        </div>
    </body>
    </html>
    """)


async def get_health(request):
    try:
        return JSONResponse(api.health().model_dump())
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def get_roster(request):
    try:
        return JSONResponse(api.get_roster().model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)


async def get_rules(request):
    try:
        status = request.query_params.get("status")
        rules = [r.model_dump() for r in api.list_rules(status)]
        return JSONResponse({"rules": rules})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


async def post_rule(request):
    try:
        data = await request.json()
        rule = Rule.model_validate(data)
        api.db.save_rule(rule)
        return JSONResponse(rule.model_dump(), status_code=201)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def edit_rule(request):
    rule_id = request.path_params["id"]
    try:
        data = await request.json()
        updated = api.edit_rule(rule_id, params=data.get("params"), owner=data.get("owner"))
        return JSONResponse(updated.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def confirm_rule(request):
    rule_id = request.path_params["id"]
    try:
        rule = api.confirm_rule(rule_id)
        return JSONResponse(rule.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def reject_rule(request):
    rule_id = request.path_params["id"]
    try:
        rule = api.reject_rule(rule_id)
        return JSONResponse(rule.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def intake_text(request):
    try:
        data = await request.json()
        text = data.get("text", "")
        rules = api.ingest_text(text)
        return JSONResponse({"rules": [r.model_dump() for r in rules]})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def intake_sheet(request):
    try:
        form = await request.form()
        file_item = form.get("file")
        if file_item is None:
            return JSONResponse({"error": "No file uploaded (use form key 'file')"}, status_code=400)
        filename = getattr(file_item, "filename", "workload.xlsx")
        content = await file_item.read()
        result = api.ingest_sheet(content, filename)
        return JSONResponse(result.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def intake_audio(request):
    try:
        form = await request.form()
        file_item = form.get("file")
        if file_item is None:
            return JSONResponse({"error": "No audio file uploaded"}, status_code=400)
        filename = getattr(file_item, "filename", "voice.wav")
        content = await file_item.read()
        rules = api.ingest_audio(content, filename)
        return JSONResponse({"rules": [r.model_dump() for r in rules]})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def intake_image(request):
    try:
        form = await request.form()
        file_item = form.get("file")
        if file_item is None:
            return JSONResponse({"error": "No image file uploaded"}, status_code=400)
        filename = getattr(file_item, "filename", "photo.png")
        content = await file_item.read()
        rules = api.ingest_image(content, filename)
        return JSONResponse({"rules": [r.model_dump() for r in rules]})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def post_solve(request):
    try:
        min_change = request.query_params.get("minimal_change", "true").lower() == "true"
        result = api.solve(minimal_change=min_change)
        return JSONResponse(result.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


async def get_schedule(request):
    sched = api.db.latest_schedule()
    if sched:
        return JSONResponse(sched.model_dump())
    return JSONResponse({"message": "No published schedule available yet"}, status_code=404)


async def explain_conflict(request):
    try:
        data = await request.json()
        conflict = Conflict.model_validate(data)
        explanation = api.explain_conflict(conflict)
        return JSONResponse(explanation.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def approve_option(request):
    option_id = request.path_params["id"]
    try:
        data = await request.json()
        as_user = data.get("as_user", "")
        result = api.approve_option(option_id, as_user=as_user)
        return JSONResponse(result.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def apply_option(request):
    option_id = request.path_params["id"]
    try:
        rule = api.apply_option(option_id)
        return JSONResponse(rule.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def get_why(request):
    session_id = request.path_params["session_id"]
    try:
        rules = api.why_cell(session_id)
        return JSONResponse({"session_id": session_id, "rules": [r.model_dump() for r in rules]})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


async def post_publish(request):
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


async def post_verify(request):
    try:
        body = await request.body()
        result = api.verify_file(body)
        return JSONResponse(result.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def get_events(request):
    try:
        return JSONResponse({"events": api.chain_events()})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


async def get_scoreboard(request):
    try:
        runs = int(request.query_params.get("runs", 3))
        res = api.run_scoreboard(runs)
        return JSONResponse(res.model_dump())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


async def post_seed(request):
    try:
        api.seed_demo()
        return JSONResponse({"status": "seeded", "ok": True})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


async def post_reset(request):
    try:
        api.reset_demo()
        return JSONResponse({"status": "reset", "ok": True})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


async def export_format(request):
    fmt = request.path_params.get("format", "json").lower()
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


async def get_upload(request):
    filename = request.path_params["filename"]
    data = api.get_upload(filename)
    if data is None:
        return JSONResponse({"error": "Upload not found"}, status_code=404)
    return Response(data, media_type="application/octet-stream")


routes = [
    Route("/", index, methods=["GET"]),
    Route("/health", get_health, methods=["GET"]),
    Route("/roster", get_roster, methods=["GET"]),
    Route("/rules", get_rules, methods=["GET"]),
    Route("/rules", post_rule, methods=["POST"]),
    Route("/rules/{id}", edit_rule, methods=["POST"]),
    Route("/rules/{id}/confirm", confirm_rule, methods=["POST"]),
    Route("/rules/{id}/reject", reject_rule, methods=["POST"]),
    Route("/intake/text", intake_text, methods=["POST"]),
    Route("/intake/sheet", intake_sheet, methods=["POST"]),
    Route("/intake/audio", intake_audio, methods=["POST"]),
    Route("/intake/image", intake_image, methods=["POST"]),
    Route("/schedule", get_schedule, methods=["GET"]),
    Route("/solve", post_solve, methods=["POST"]),
    Route("/conflicts/explain", explain_conflict, methods=["POST"]),
    Route("/options/{id}/approve", approve_option, methods=["POST"]),
    Route("/options/{id}/apply", apply_option, methods=["POST"]),
    Route("/why/{session_id}", get_why, methods=["GET"]),
    Route("/publish", post_publish, methods=["POST"]),
    Route("/verify", post_verify, methods=["POST"]),
    Route("/events", get_events, methods=["GET"]),
    Route("/audit", get_events, methods=["GET"]),
    Route("/scoreboard", get_scoreboard, methods=["GET"]),
    Route("/export/{format}", export_format, methods=["GET"]),
    Route("/uploads/{filename}", get_upload, methods=["GET"]),
    Route("/demo/seed", post_seed, methods=["POST"]),
    Route("/demo/reset", post_reset, methods=["POST"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
]

app = Starlette(routes=routes, middleware=middleware)


def run():
    import uvicorn
    uvicorn.run("backend.server:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
