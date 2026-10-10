"""Human-readable and structured health checks for configured local services."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

# Ensure repository root is on sys.path for direct script execution
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend import config


def _command(command: list[str], timeout: int = 3) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return result.returncode == 0, (result.stdout or result.stderr).strip()[-500:]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)


def inspect() -> dict[str, dict]:
    items: dict[str, dict] = {
        "mock_llm": {
            "ok": True,
            "detail": "Fixture mode enabled" if config.MOCK_LLM else "Fixture mode disabled; live inference configured",
        }
    }

    # 1. Database Check (PostgreSQL or SQLite fallback)
    try:
        from backend.registry import db
        db.check_connection()
        engine = db.get_engine_type()
        if engine == "postgres":
            items["database"] = {"ok": True, "detail": f"PostgreSQL connection is healthy ({config.DATABASE_URL})"}
        else:
            items["database"] = {"ok": True, "detail": "SQLite local database is active and healthy (data/gecompose.db)"}
    except Exception as exc:
        items["database"] = {"ok": False, "detail": f"Database error: {exc}"}

    # 2. LLM / Ollama & Gemma Models Check
    if config.MOCK_LLM:
        items["intake_model"] = {"ok": True, "detail": f"Mock mode enabled; {config.INTAKE_MODEL} (4B) not required"}
        items["reason_model"] = {"ok": True, "detail": f"Mock mode enabled; {config.REASON_MODEL} (12B) not required"}
    elif config.LLM_PROVIDER == "ollama":
        from backend.llm.gemma import get_gemma_service
        gemma = get_gemma_service()
        health = gemma.check_health()
        if not health["connected"]:
            items["ollama"] = {
                "ok": False,
                "detail": f"Cannot reach Ollama at {gemma.base_url}. Start Ollama with 'ollama serve'.",
            }
            items["intake_model"] = {
                "ok": False,
                "detail": f"Ollama offline; required intake model: {config.INTAKE_MODEL}",
            }
            items["reason_model"] = {
                "ok": False,
                "detail": f"Ollama offline; required reasoning model: {config.REASON_MODEL}",
            }
        else:
            items["ollama"] = {
                "ok": True,
                "detail": f"Ollama is running at {gemma.base_url} ({len(health.get('installed_models', []))} models installed)",
            }
            intake_ok = health.get("intake_ready", False)
            items["intake_model"] = {
                "ok": intake_ok,
                "detail": (
                    f"Gemma 4B intake model '{config.INTAKE_MODEL}' is ready"
                    if intake_ok
                    else f"Model '{config.INTAKE_MODEL}' not found in Ollama. Run: 'ollama run {config.INTAKE_MODEL}'"
                ),
            }
            reason_ok = health.get("reason_ready", False)
            items["reason_model"] = {
                "ok": reason_ok,
                "detail": (
                    f"Gemma 12B reasoning model '{config.REASON_MODEL}' is ready"
                    if reason_ok
                    else f"Model '{config.REASON_MODEL}' not found in Ollama. Run: 'ollama run {config.REASON_MODEL}'"
                ),
            }
    else:
        # Generic OpenAI/llama-server
        for tier, url, model in (
            ("intake", config.INTAKE_URL, config.INTAKE_MODEL),
            ("reason", config.REASON_URL, config.REASON_MODEL),
        ):
            try:
                from openai import OpenAI
                models = OpenAI(base_url=url, api_key="local", timeout=3).models.list()
                names = [m.id for m in models.data]
                model_ok = model in names or not names
                items[f"{tier}_model"] = {
                    "ok": model_ok,
                    "detail": f"Connected to {url}; configured model: {model}",
                }
            except Exception as exc:
                items[f"{tier}_model"] = {"ok": False, "detail": str(exc)}

    # 3. Sandbox Check (Docker or Local)
    docker = shutil.which("docker")
    if config.SANDBOX_MODE == "local" or config.ALLOW_LOCAL_SANDBOX:
        items["sandbox"] = {
            "ok": True,
            "detail": f"Local subprocess sandbox enabled (SANDBOX_MODE={config.SANDBOX_MODE})",
        }
    elif not docker:
        items["sandbox"] = {
            "ok": False,
            "detail": "Docker executable not found and local sandbox is disabled",
        }
    else:
        ok, detail = _command([docker, "info"])
        image_ok, image_detail = _command([docker, "image", "inspect", config.SANDBOX_IMAGE])
        items["sandbox"] = {
            "ok": ok and image_ok,
            "detail": detail if not ok else image_detail if not image_ok else "Docker and sandbox image available",
        }

    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect health of GeCompose backend services.")
    parser.add_argument("--json", action="store_true", help="Output health status as JSON")
    parser.add_argument("--audio", help="Optional audio file path to verify audio intake pipeline")
    args = parser.parse_args()

    items = inspect()
    if args.json:
        print(json.dumps(items, indent=2))
    else:
        for name, item in items.items():
            status_text = "OK  " if item["ok"] else "FAIL"
            print(f"[{status_text}] {name:15}: {item['detail']}")

    if args.audio:
        try:
            from backend.intake.voice_photo import ingest_audio
            rules = ingest_audio(Path(args.audio).read_bytes(), Path(args.audio).name)
            print(json.dumps([r.model_dump() for r in rules], ensure_ascii=False, indent=2))
        except Exception as exc:
            print(f"FAIL audio: {exc}")
            return 1

    return 0 if all(item["ok"] for item in items.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
