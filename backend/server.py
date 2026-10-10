"""HTTP REST API server exposing backend.api over HTTP using Starlette and Uvicorn."""
from __future__ import annotations
import json
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response, HTMLResponse
from starlette.routing import Route
from backend import api, config

async def index(request):
    h = api.health().items
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>GeCompose Backend API</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 900px; margin: 40px auto; line-height: 1.6; padding: 0 20px; color: #1e293b; }}
            h1 {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }}
            .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; margin: 16px 0; }}
            .pill-ok {{ background: #dcfce7; color: #15803d; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; }}
            .pill-fail {{ background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: left; }}
            th {{ background: #f1f5f9; }}
            a {{ color: #2563eb; text-decoration: none; font-weight: 500; }}
            a:hover {{ text-decoration: underline; }}
            code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <h1>GeCompose Backend Engine</h1>
        <p>Constraint-Satisfaction Timetable Scheduling with Multi-Party Consent & Blockchain Verification.</p>
        
        <div class="card">
            <h3>System Status</h3>
            <table>
                <tr><th>Component</th><th>Status</th><th>Details</th></tr>
                {''.join(f"<tr><td><b>{k}</b></td><td><span class='{'pill-ok' if v.get('ok') else 'pill-fail'}'>{'OK' if v.get('ok') else 'FAIL'}</span></td><td>{v.get('detail')}</td></tr>" for k, v in h.items())}
            </table>
        </div>

        <div class="card">
            <h3>Available Endpoints</h3>
            <ul>
                <li><a href="/health"><code>GET /health</code></a> - Health status of all services</li>
                <li><a href="/roster"><code>GET /roster</code></a> - Active university department roster</li>
                <li><a href="/rules"><code>GET /rules</code></a> - List active constraints and rules</li>
                <li><a href="/schedule"><code>GET /schedule</code></a> - Current solver-generated timetable schedule</li>
                <li><a href="/events"><code>GET /events</code></a> - Smart contract events on Anvil ledger</li>
                <li><a href="/scoreboard"><code>GET /scoreboard</code></a> - Constraint violation benchmarks</li>
                <li><code>POST /solve</code> - Trigger CP-SAT solver</li>
                <li><code>POST /publish</code> - Publish & anchor schedule on blockchain</li>
                <li><code>POST /demo/seed</code> - Seed initial demonstration rules and schedule</li>
                <li><code>POST /demo/reset</code> - Reset demo environment</li>
            </ul>
        </div>
    </body>
    </html>
    """)

async def get_health(request):
    return JSONResponse(api.health().model_dump())

async def get_roster(request):
    try:
        return JSONResponse(api.get_roster().model_dump())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=404)

async def get_rules(request):
    status = request.query_params.get("status")
    rules = [r.model_dump() for r in api.list_rules(status)]
    return JSONResponse({"rules": rules})

async def get_schedule(request):
    sched = api.db.latest_schedule()
    if sched:
        return JSONResponse(sched.model_dump())
    return JSONResponse({"message": "No published schedule available yet"}, status_code=404)

async def post_solve(request):
    min_change = request.query_params.get("minimal_change", "true").lower() == "true"
    result = api.solve(minimal_change=min_change)
    return JSONResponse(result.model_dump())

async def post_publish(request):
    try:
        pub = api.publish()
        return JSONResponse({
            "hash": pub.hash,
            "tx_hash": pub.tx_hash,
            "version": pub.version,
            "anchored": True
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

async def post_seed(request):
    try:
        api.seed_demo()
        return JSONResponse({"status": "seeded", "ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def post_reset(request):
    try:
        api.reset_demo()
        return JSONResponse({"status": "reset", "ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def get_events(request):
    try:
        return JSONResponse({"events": api.chain_events()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def get_scoreboard(request):
    runs = int(request.query_params.get("runs", 3))
    res = api.run_scoreboard(runs)
    return JSONResponse(res.model_dump())

routes = [
    Route("/", index, methods=["GET"]),
    Route("/health", get_health, methods=["GET"]),
    Route("/roster", get_roster, methods=["GET"]),
    Route("/rules", get_rules, methods=["GET"]),
    Route("/schedule", get_schedule, methods=["GET"]),
    Route("/solve", post_solve, methods=["POST"]),
    Route("/publish", post_publish, methods=["POST"]),
    Route("/demo/seed", post_seed, methods=["POST"]),
    Route("/demo/reset", post_reset, methods=["POST"]),
    Route("/events", get_events, methods=["GET"]),
    Route("/scoreboard", get_scoreboard, methods=["GET"]),
]

app = Starlette(routes=routes)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
