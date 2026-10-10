"""Environment-backed configuration for the local GeCompose demo."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv is optional for library consumers
    load_dotenv = None
if load_dotenv:
    load_dotenv()

def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc

def _float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value

MOCK_LLM = os.getenv("MOCK_LLM", "0") == "1"
INTAKE_URL = os.getenv("INTAKE_URL", "http://127.0.0.1:8080/v1")
INTAKE_MODEL = os.getenv("INTAKE_MODEL", "gemma-intake")
REASON_URL = os.getenv("REASON_URL", "http://127.0.0.1:8081/v1")
REASON_MODEL = os.getenv("REASON_MODEL", "gemma-reason")
LLM_TIMEOUT_S = _float("LLM_TIMEOUT_S", 120)
AUDIO_MODE = os.getenv("AUDIO_MODE", "native")
SANDBOX_MODE = os.getenv("SANDBOX_MODE", "docker")
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "gecompose-sandbox")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://gecompose:gecompose_dev@127.0.0.1:5432/gecompose",
)
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
DAYS = _int("DAYS", 5)
SLOTS_PER_DAY = _int("SLOTS_PER_DAY", 6)
SOLVER_TIME_S = _float("SOLVER_TIME_S", 10)
SOLVER_SEED = _int("SOLVER_SEED", 7)
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri"]
SLOT_TIMES = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00"]
WEEK_START_MONDAY = os.getenv("WEEK_START_MONDAY", "2026-10-12")
DEFAULT_OWNER = {"teacher_unavailable": None, "room_unavailable": "Coordinator", "pin_session": "Dept Head", "only_qualified": "Dean"}
if not 1 <= DAYS <= len(DAY_NAMES) or SLOTS_PER_DAY != len(SLOT_TIMES):
    raise RuntimeError("DAYS and SLOTS_PER_DAY must fit the configured week grid")
if AUDIO_MODE not in {"native", "transcript"}:
    raise RuntimeError("AUDIO_MODE must be native or transcript")
if SANDBOX_MODE not in {"docker", "local"}:
    raise RuntimeError("SANDBOX_MODE must be docker or local")
if SANDBOX_MODE == "local" and not MOCK_LLM:
    raise RuntimeError("SANDBOX_MODE=local is only allowed with MOCK_LLM=1")
