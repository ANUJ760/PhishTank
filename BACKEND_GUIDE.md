# GeCompose Backend: AI Build Guide (v2)

Audience: an AI coding assistant and the team. Read fully before writing code.

- Reference code below is **untested**. Run the tests in Section 12 before trusting it.
- Tags: **`[EXT: x]`** = needs something installed or running outside Python code. **`[PY]`** = pure Python, no outside service.
- Frontend setup: see [`FRONTEND_SETUP.md`](FRONTEND_SETUP.md). Usage and demo flow: see [`WORKFLOW_AND_USAGE.md`](WORKFLOW_AND_USAGE.md).

---

## 0. External Stack (what must exist outside the Python code)

| # | Item | Required? | Used by | Install | Verify | If missing |
|---|---|---|---|---|---|---|
| 1 | Python 3.11+ | Yes | everything | system / pyenv | `python --version` | none |
| 2 | **Ollama** (or llama.cpp / vLLM) | Recommended for real Gemma; No if `MOCK_LLM=1` | `llm/gemma.py`, `llm/client.py` | `curl -fsSL https://ollama.com/install.sh \| sh` | `ollama --version` | `MOCK_LLM=1` |
| 3 | **Gemma models**: 4B (intake: audio/vision/text) and 12B (reasoning: parser/conflict) | Yes for live Gemma | Ollama | `ollama run gemma:4b` and `ollama run gemma:12b` | `ollama list` | `MOCK_LLM=1`, or configure smaller tag |
| 4 | NVIDIA GPU or fast CPU | Recommended | Ollama | driver | `nvidia-smi` | CPU works with 4-bit quantization |
| 5 | **Docker Engine** (or local sandbox) | Optional for parser sandbox | `intake/sandbox.py` | docs.docker.com | `docker run --rm hello-world` | `SANDBOX_MODE=local` with `ALLOW_LOCAL_SANDBOX=1` |
| 6 | **Database** (SQLite / PostgreSQL) | Yes (built-in SQLite zero-setup) | `registry/db.py` | Python built-in `sqlite3` or Docker PostgreSQL | `python -m backend.healthcheck` | automatically falls back to SQLite |
| 7 | Python packages | Yes | all | `pip install -r requirements.txt` | `python -c "import ortools, streamlit"` | none |
| 8 | Chrome with mic permission | Only for live voice | frontend | n/a | open `http://localhost:8501` | use typed text or pre-recorded WAV |

**Not needed:** Web3, Foundry, Anvil, Smart contracts, MetaMask, testnet ETH, any cloud API, Graphviz binary, Whisper or Tesseract.

### Where the external stack is touched

| Module | Touches | Fallback |
|---|---|---|
| `llm/gemma.py`, `llm/client.py` | `[EXT: Ollama (gemma:4b, gemma:12b)]` | `MOCK_LLM=1` or `LLM_FALLBACK_TO_MOCK=1` fixtures |
| `intake/voice_photo.py` | `[EXT: Ollama]` with multimodal Gemma 4B | `ingest_text`, fixtures |
| `intake/sheet_parser.py` | `[EXT: Ollama]` (first time per layout only) | fixture parser code |
| `intake/sandbox.py` | `[EXT: Docker]` | `SANDBOX_MODE=local` |
| `registry/db.py` | `[EXT: PostgreSQL]` | Built-in SQLite (`data/gecompose.db`) |
| `solver/*`, `checker`, `hashing` | `[PY]` only | n/a |

---

## 1. Setup (copy-paste, in order)

Run from the repo root.

**1. Python environment**
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p data/uploads samples models
```

**2. Database (Zero-Setup SQLite or Docker PostgreSQL)**
- For frictionless local development, the default database is SQLite at `data/gecompose.db` (zero setup required).
- For production Docker PostgreSQL:
```bash
docker compose up -d postgres
```

**3. Start Ollama and pull Gemma models (Skip if `MOCK_LLM=1`)**
```bash
# Start the Ollama background daemon
ollama serve

# Pull or run the Gemma models (in another terminal or background)
ollama pull gemma:4b       # Multimodal intake tier (text, audio, photos)
ollama pull gemma:12b      # Reasoning tier (conflict diagnosis, parser coding)
```

**4. Run Health Check**
```bash
python -m backend.healthcheck
```
Verify that database, Ollama, Gemma 4B, and Gemma 12B report `[OK]`.

**5. Run the Backend REST API Server**
```bash
python -m backend.server
# Server starts at http://127.0.0.1:8000
```

**6. Run Frontend & Verification Portal**
```bash
streamlit run frontend/app.py
```

---

## 2. Golden Rules

1. Gemma never assigns slots. Only CP-SAT produces schedules.
2. Gemma never approves, signs, or sees keys. Gemma does not decide who owns a rule.
3. Gemma output is a draft until a human confirms it.
4. A schedule is published only if `checker.check()` returns no violations.
5. Only hashes go on-chain. No names, audio, photos, or availability.
6. Generated parser code runs only in the Docker sandbox. `SANDBOX_MODE=local` is allowed only when `MOCK_LLM=1` (trusted fixture code).
7. Every Gemma call has a fixture fallback (`MOCK_LLM=1`).
8. **v1 scope limits:** every session is exactly 1 slot; 4 rule types; one project; one coordinator. Do not build beyond this.

---

## 3. Repo Layout (exact)

```
.env.example  requirements.txt  Dockerfile.sandbox
backend/
  __init__.py
  config.py  models.py  hashing.py  api.py  healthcheck.py  reset_demo.py  scoreboard.py
  registry/db.py
  llm/client.py  llm/prompts.py  llm/fixtures/*.json
  intake/voice_photo.py  intake/sheet_parser.py  intake/sandbox.py
  solver/model.py  solver/conflicts.py  solver/checker.py  solver/trace.py
  export.py
frontend/             # see FRONTEND_SETUP.md
samples/              # roster.json, base_rules.json, workload.xlsx, workload2.xlsx, rao_hindi.wav, board.png
tests/
data/                 # created at runtime: gecompose.db, uploads/
```

---

## 4. Config and Schemas

### 4.1 `backend/config.py` `[PY]`
```python
import os
from dotenv import load_dotenv
load_dotenv()

def _flag(k: str) -> bool: return os.getenv(k, "0") == "1"

MOCK_LLM = _flag("MOCK_LLM")
INTAKE_URL = os.getenv("INTAKE_URL", "http://127.0.0.1:8080/v1")
INTAKE_MODEL = os.getenv("INTAKE_MODEL", "gemma-intake")
REASON_URL = os.getenv("REASON_URL", "http://127.0.0.1:8081/v1")
REASON_MODEL = os.getenv("REASON_MODEL", "gemma-reason")
LLM_TIMEOUT_S = int(os.getenv("LLM_TIMEOUT_S", "120"))
AUDIO_MODE = os.getenv("AUDIO_MODE", "native")
SANDBOX_MODE = os.getenv("SANDBOX_MODE", "docker")
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "gecompose-sandbox")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://gecompose:gecompose_dev@127.0.0.1:5432/gecompose")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
DAYS = int(os.getenv("DAYS", "5"))
SLOTS_PER_DAY = int(os.getenv("SLOTS_PER_DAY", "6"))
SOLVER_TIME_S = float(os.getenv("SOLVER_TIME_S", "10"))
SOLVER_SEED = int(os.getenv("SOLVER_SEED", "7"))

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri"]
SLOTS_TIMES = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00"]  # 1 hour each
WEEK_START_MONDAY = "2026-10-12"                                      # for .ics export

# Default approver per rule type (Gemma never decides this; editable in the review screen)
DEFAULT_OWNER = {"teacher_unavailable": None,   # None = the teacher named in params
                 "room_unavailable": "Coordinator",
                 "pin_session": "Dept Head",
                 "only_qualified": "Dean"}

if SANDBOX_MODE == "local" and not MOCK_LLM:
    raise RuntimeError("SANDBOX_MODE=local is only allowed with MOCK_LLM=1")
```

### 4.2 `backend/models.py` `[PY]`
```python
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict
from backend import config

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

RuleType = Literal["teacher_unavailable", "room_unavailable", "pin_session", "only_qualified"]

class Evidence(Strict):
    kind: Literal["audio", "image", "sheet", "text"]
    ref: str          # "<filename>@<locator>" e.g. "voice.wav@00:03-00:07", "workload.xlsx!B7", "board.png@10,20,300,80"

class Rule(Strict):
    id: str           # "R1", "R2", ...
    type: RuleType
    owner: str        # person who must approve any change to this rule
    params: dict
    evidence: list[Evidence] = []
    status: Literal["draft", "confirmed", "rejected"] = "draft"

class Room(Strict):
    name: str
    capacity: int

class Session(Strict):
    id: str
    course: str
    teachers: list[str]   # candidate teachers (roster level). Rules restrict further.
    size: int = 30

class Roster(Strict):
    teachers: list[str]
    rooms: list[Room]
    sessions: list[Session]

class Placement(Strict):
    session_id: str
    teacher: str
    room: str
    day: int
    slot: int

class Schedule(Strict):
    placements: list[Placement]
    version: int = 1

class Conflict(Strict):
    rule_ids: list[str]
    owners: list[str]

class RelaxOption(Strict):
    id: str                 # "O1", ...
    rule_id: str
    new_params: dict
    description: str
    approver: str           # = rule.owner, set by backend, never by Gemma
    verified: bool = False  # True only if re-solve with this change is feasible
    option_hash: str = ""   # hex, set by backend

class Explanation(Strict):
    summary: str
    options: list[RelaxOption]

# ---- LLM output schemas (what Gemma is allowed to return) ----
class DraftRule(Strict):
    type: RuleType
    params: dict
    evidence_ref: str = ""

class DraftRulesOut(Strict):
    rules: list[DraftRule]

class ParserOut(Strict):
    code: str

class ExplainOptionOut(Strict):
    rule_id: str
    new_params: dict
    description: str

class ExplainOut(Strict):
    summary: str
    options: list[ExplainOptionOut]

# ---- param validation (call on every rule from Gemma, sheets, or the UI) ----
def validate_params(rtype: str, p: dict, roster: Roster) -> None:
    teachers = set(roster.teachers)
    rooms = {r.name for r in roster.rooms}
    sessions = {s.id for s in roster.sessions}

    def check_day_slots():
        if not isinstance(p.get("day"), int) or not 0 <= p["day"] < config.DAYS:
            raise ValueError("bad day")
        sl = p.get("slots")
        if (not isinstance(sl, list) or not sl or
                any(not isinstance(t, int) or not 0 <= t < config.SLOTS_PER_DAY for t in sl)):
            raise ValueError("bad slots")

    if rtype == "teacher_unavailable":
        if set(p) != {"teacher", "day", "slots"} or p["teacher"] not in teachers: raise ValueError("teacher_unavailable params")
        check_day_slots()
    elif rtype == "room_unavailable":
        if set(p) != {"room", "day", "slots"} or p["room"] not in rooms: raise ValueError("room_unavailable params")
        check_day_slots()
    elif rtype == "pin_session":
        if set(p) != {"session_id", "day", "slots"} or p["session_id"] not in sessions: raise ValueError("pin_session params")
        check_day_slots()
    elif rtype == "only_qualified":
        if set(p) != {"session_id", "teachers"} or p["session_id"] not in sessions: raise ValueError("only_qualified params")
        if not p["teachers"] or any(t not in teachers for t in p["teachers"]): raise ValueError("unknown teacher")
    else:
        raise ValueError("unknown rule type")
```

Rule params (exact):

| type | params | meaning |
|---|---|---|
| `teacher_unavailable` | `{"teacher": str, "day": int, "slots": [int]}` | teacher cannot teach in these slots |
| `room_unavailable` | `{"room": str, "day": int, "slots": [int]}` | room closed in these slots |
| `pin_session` | `{"session_id": str, "day": int, "slots": [int]}` | session must be in one of these slots that day |
| `only_qualified` | `{"session_id": str, "teachers": [str]}` | only these teachers may take the session |

Day 0 = Monday. Slots 0 to 2 are morning, 3 to 5 afternoon.

---

## 5. Registry `[PY]` (`backend/registry/db.py`, PostgreSQL)

Tables:
- `rules(id TEXT PRIMARY KEY, json TEXT, salt BLOB, rule_hash TEXT, status TEXT)`
- `roster(id INTEGER PRIMARY KEY CHECK (id=1), json TEXT)`
- `parsers(layout_signature TEXT PRIMARY KEY, code TEXT, created_at REAL)`
- `schedules(hash TEXT PRIMARY KEY, version INTEGER, json TEXT, tx_hash TEXT, created_at REAL)`
- `options(id TEXT PRIMARY KEY, json TEXT)`
- `llm_calls(id INTEGER PRIMARY KEY AUTOINCREMENT, fn TEXT, model TEXT, tokens_in INT, tokens_out INT, ms INT, mock INT, ts REAL)`

Functions (all required):
```
init_db(); reset_db()
save_roster(Roster); get_roster() -> Roster
next_rule_id() -> "R{n}"
save_rule(Rule, salt: bytes | None = None, rule_hash: str | None = None); get_rule(id) -> Rule
list_rules(status: str | None = None) -> list[Rule]; get_salt(rule_id) -> bytes; get_rule_hash(rule_id) -> str
save_parser(sig, code); get_parser(sig) -> str | None; delete_parser(sig)
save_schedule(Schedule, hash_hex, tx_hash); latest_schedule() -> Schedule | None
save_option(RelaxOption); get_option(id) -> RelaxOption; next_option_id() -> "O{n}"
log_llm_call(fn, model, tokens_in, tokens_out, ms, mock); tokens_since(ts: float) -> int
save_upload(filename, data: bytes); get_upload(filename) -> bytes | None     # files in data/uploads/
```

---

## 6. Gemma Layer `[EXT: llama-server]`

### 6.1 `backend/llm/client.py`
```python
import json, time
from pathlib import Path
from openai import OpenAI
from pydantic import BaseModel, ValidationError
from backend import config
from backend.registry import db

FIXTURES = Path(__file__).parent / "fixtures"
class LLMError(Exception): ...

_clients: dict[str, OpenAI] = {}
def _cfg(tier: str):
    return (config.INTAKE_URL, config.INTAKE_MODEL) if tier == "intake" else (config.REASON_URL, config.REASON_MODEL)

def call_json(fn: str, tier: str, messages: list[dict], schema: type[BaseModel], retries: int = 2) -> BaseModel:
    if config.MOCK_LLM:                                   # [PY] fixture path
        data = json.loads((FIXTURES / f"{fn}.json").read_text())
        db.log_llm_call(fn, "mock", 0, 0, 0, True)
        return schema.model_validate(data)
    url, model = _cfg(tier)
    client = _clients.setdefault(url, OpenAI(base_url=url, api_key="none"))   # [EXT: llama-server]
    last = None
    for _ in range(retries + 1):
        t0 = time.time()
        resp = client.chat.completions.create(
            model=model, messages=messages, temperature=0,
            response_format={"type": "json_object"}, timeout=config.LLM_TIMEOUT_S)
        text = resp.choices[0].message.content or ""
        u = resp.usage
        db.log_llm_call(fn, model, getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0),
                        int((time.time() - t0) * 1000), False)
        try:
            return schema.model_validate_json(text)
        except ValidationError as e:
            last = e
            messages = messages + [{"role": "assistant", "content": text},
                                   {"role": "user", "content": f"Invalid JSON for the schema: {e}. Return corrected JSON only."}]
    raise LLMError(f"{fn} failed after retries: {last}")
```
If `response_format` is rejected by your llama-server build, remove it. The prompts already say JSON only.

### 6.2 `backend/llm/prompts.py` (exact prompt text)

`extract_rules(roster)` (system prompt for audio, image, and text intake):
```
You extract scheduling rules for a college timetable from the coordinator's input.
The input may be Hindi, Marathi or English (speech, a photo, or typed text).
Allowed rule types and EXACT params:
- teacher_unavailable: {"teacher": <name>, "day": <0-4>, "slots": [<0-5>, ...]}
- room_unavailable:    {"room": <name>, "day": <0-4>, "slots": [<0-5>, ...]}
- pin_session:         {"session_id": <id>, "day": <0-4>, "slots": [<0-5>, ...]}
- only_qualified:      {"session_id": <id>, "teachers": [<name>, ...]}
Day 0=Monday ... 4=Friday. Slots 0-2 are morning, 3-5 afternoon.
Known teachers: {teachers}
Known rooms: {rooms}
Known sessions (id: course): {sessions}
Return JSON only: {"rules":[{"type": ..., "params": {...}, "evidence_ref": "<audio time range like 00:03-00:07, or image box x,y,w,h>"}]}
Use only names and ids from the known lists. If unsure, omit the rule. Never invent anything.
```

`gen_sheet_parser(sample_rows_text, last_error)` (reasoning tier):
```
Write a Python function `parse(path: str) -> list[dict]` that reads the Excel file at `path`
using only pandas and openpyxl, and returns one dict per data row:
{"course": <str>, "teachers": [<str>, ...], "source_cell": <str like "B7">}
"teachers" is the list of qualified faculty for that course. Split comma/semicolon-separated names. Trim spaces.
Do not use the network, do not write files, do not import other libraries.
First rows of the sheet (row number, then cell values):
{sample_rows_text}
{last_error_block}
Return JSON only: {"code": "<the full python source>"}
```

`explain_conflict(rules_text)` (reasoning tier; thinking mode on if your server supports it):
```
A timetable solver proved these rules cannot all hold at the same time:
{rules_text}   # one line each: "R7 [teacher_unavailable] owner=Prof. Rao params={...}"
Write: (1) a 2-3 sentence plain-English explanation naming the people and rules.
(2) up to 3 options. Each option changes the params of exactly ONE listed rule, keeping the same params shape.
Return JSON only: {"summary": str, "options": [{"rule_id": str, "new_params": {...}, "description": str}]}
Do not change rules that are not listed. Do not claim an option works; the solver will check it.
```

### 6.3 Fixtures for `MOCK_LLM=1` (`backend/llm/fixtures/`)

- `extract_rules_audio.json`
```json
{"rules":[{"type":"teacher_unavailable","params":{"teacher":"Prof. Rao","day":0,"slots":[0,1,2]},"evidence_ref":"00:03-00:07"}]}
```
- `extract_rules_text.json`
```json
{"rules":[{"type":"pin_session","params":{"session_id":"DB_LAB","day":0,"slots":[0,1,2]},"evidence_ref":"text"}]}
```
- `extract_rules_image.json`: same shape; one rule with `evidence_ref` `"10,20,300,80"`.
- `explain_conflict.json`
```json
{"summary":"Database Lab is pinned to Monday morning and only Prof. Rao may teach it, but Prof. Rao is unavailable on Monday morning.",
 "options":[
  {"rule_id":"<id of the pin rule>","new_params":{"session_id":"DB_LAB","day":1,"slots":[1]},"description":"Move Database Lab to Tuesday 10:00."},
  {"rule_id":"<id of only_qualified DB_LAB>","new_params":{"session_id":"DB_LAB","teachers":["Prof. Rao","Prof. Mehta"]},"description":"Allow Prof. Mehta to co-teach Database Lab."}]}
```
Rule ids in the fixture must match the ids created in your demo run. Easiest: seed data (Section 9) creates fixed ids and the fixture uses them.
- `gen_sheet_parser.json`: `{"code": "<source of the function below, JSON-escaped>"}` (create with `json.dumps`)
```python
import pandas as pd
def parse(path):
    df = pd.read_excel(path, header=0)
    out = []
    for i, row in df.iterrows():
        names = [t.strip() for t in str(row.iloc[1]).replace(";", ",").split(",") if t.strip()]
        out.append({"course": str(row.iloc[0]).strip(), "teachers": names, "source_cell": f"B{i + 2}"})
    return out
```

---

## 7. Intake

### 7.1 `intake/voice_photo.py` `[EXT: llama-server]`
Functions:
```
ingest_audio(wav: bytes, filename: str) -> list[Rule]     # AUDIO_MODE=native only
ingest_image(img: bytes, filename: str) -> list[Rule]
ingest_text(text: str) -> list[Rule]                      # fallback + typed rules
```
Message formats sent to llama-server (OpenAI-compatible):
```python
# audio
{"role":"user","content":[{"type":"input_audio","input_audio":{"data": b64_wav, "format":"wav"}},
                          {"type":"text","text":"Extract the rules."}]}
# image
{"role":"user","content":[{"type":"image_url","image_url":{"url": f"data:image/png;base64,{b64}"}},
                          {"type":"text","text":"Extract the rules."}]}
```
Shared post-processing `_to_rules(out: DraftRulesOut, kind, filename)`:
1. For each draft: `validate_params(...)`. On error, **skip it** (log; never raise).
2. `id = db.next_rule_id()`.
3. `owner` = `DEFAULT_OWNER[type]`, or `params["teacher"]` when that is `None`.
4. `evidence = [Evidence(kind=kind, ref=f"{filename}@{draft.evidence_ref}")]`.
5. `status="draft"`. `db.save_upload(filename, bytes)`. `db.save_rule(rule)`. Return the list.

Audio is not guaranteed on every runtime. Run the audio health check (Section 1, step 6) first.

### 7.2 `intake/sandbox.py` `[EXT: Docker]`
```python
import json, subprocess, shutil, sys, tempfile, uuid
from pathlib import Path
from backend import config

class SandboxError(Exception): ...

RUNNER = '''
import sys, json, importlib.util
d = sys.argv[1]
spec = importlib.util.spec_from_file_location("parser", f"{d}/parser.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(json.dumps(m.parse(f"{d}/input.xlsx")))
'''

def run_parser(code: str, xlsx: Path, timeout_s: int = 15) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "parser.py").write_text(code)
        (d / "runner.py").write_text(RUNNER)
        shutil.copy(xlsx, d / "input.xlsx")
        name = f"gc-{uuid.uuid4().hex[:8]}"
        if config.SANDBOX_MODE == "docker":
            cmd = ["docker", "run", "--rm", "--name", name, "--network", "none", "--read-only",
                   "--tmpfs", "/tmp", "--memory", "256m", "--cpus", "1", "--pids-limit", "64",
                   "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                   "-v", f"{d}:/work:ro", config.SANDBOX_IMAGE, "python", "/work/runner.py", "/work"]
        else:   # local: MOCK_LLM only, trusted fixture code
            cmd = [sys.executable, str(d / "runner.py"), str(d)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True)
            raise SandboxError("parser timed out")
        if r.returncode != 0:
            raise SandboxError(r.stderr[-2000:])
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            raise SandboxError("parser did not print valid JSON")
```
Docker Desktop on Mac or Windows must have the temp directory shared. On SELinux Linux hosts add `:z` to the volume flag.

### 7.3 `intake/sheet_parser.py` `[EXT: llama-server]` (first time per layout), `[EXT: Docker]` (always)
```
layout_signature(path) -> str
  sha256 (first 16 hex) of JSON of [[sheet_title, [lowercased non-empty header cells]] for each sheet]
ingest_sheet(path: Path, filename: str) -> IngestSheetResult
```
Algorithm:
1. `sig = layout_signature(path)`; `t0 = time.time()`.
2. `code = db.get_parser(sig)`. If found: `cache_hit=True`, `attempts=0`, run it with `sandbox.run_parser`.
3. If the cached run fails validation for more than 5% of rows, `db.delete_parser(sig)` and continue as if not cached.
4. If not found: up to 3 attempts. Each attempt: send `gen_sheet_parser` (first 10 rows as text, plus the last error), run in sandbox, validate. On success `db.save_parser(sig, code)`.
5. Row validation: `course` matches a roster course (case-insensitive) to a session id; every teacher is in the roster; `source_cell` is a string. Invalid rows count as failures. Raise `ParseError` if no valid rows, or failures exceed 5%.
6. Each valid row becomes `Rule(type="only_qualified", params={"session_id", "teachers"}, owner="Dean", evidence=[Evidence(kind="sheet", ref=f"{filename}!{source_cell}")])`, status `draft`.
7. Return `IngestSheetResult(rules, cache_hit, attempts, tokens_used=db.tokens_since(t0), seconds=...)`.

**Demo proof of "zero tokens":** first sheet shows `cache_hit=False, tokens_used>0`. Second sheet with the same header layout shows `cache_hit=True, tokens_used=0`.

Sample sheets (create with openpyxl): `samples/workload.xlsx` and `samples/workload2.xlsx` both with sheet `Workload`, header row `Course | Qualified Faculty | Hours/Week`, same header, different rows. Rows for `workload.xlsx`:
```
Database Lab        | Prof. Rao                            | 3
Operating Systems   | Prof. Rao, Prof. Mehta, Prof. Iyer   | 3
Computer Networks   | Prof. Mehta, Prof. Iyer              | 3
Artificial Intel.   | Prof. Iyer, Prof. Rao                | 3
Machine Learning Lab| Prof. Mehta, Prof. Iyer              | 3
Software Eng.       | Prof. Iyer                           | 3
```
Course text must match `Session.course` in the roster (case-insensitive).

---

## 8. Solver `[PY]` (OR-Tools)

OR-Tools names below are snake_case (version 9.11 or newer). If you get `AttributeError`, use the CamelCase equivalents (`NewBoolVar`, `AddExactlyOne`, `OnlyEnforceIf`, `AddAssumptions`, `SufficientAssumptionsForInfeasibility`).

### 8.1 `solver/model.py`
```python
from collections import defaultdict
from ortools.sat.python import cp_model
from backend import config
from backend.models import Roster, Rule, Schedule, Placement

def build(roster: Roster, rules: list[Rule], prev: Schedule | None = None):
    m = cp_model.CpModel()
    x = {}                                    # (sid, teacher, room, day, slot) -> BoolVar
    by_session, by_room_slot, by_teacher_slot = defaultdict(list), defaultdict(list), defaultdict(list)
    for s in roster.sessions:
        for p in s.teachers:
            for r in roster.rooms:
                if r.capacity < s.size:       # built-in capacity rule: variable never exists
                    continue
                for d in range(config.DAYS):
                    for t in range(config.SLOTS_PER_DAY):
                        v = m.new_bool_var(f"x_{s.id}_{p}_{r.name}_{d}_{t}")
                        x[(s.id, p, r.name, d, t)] = v
                        by_session[s.id].append(v)
                        by_room_slot[(r.name, d, t)].append(v)
                        by_teacher_slot[(p, d, t)].append(v)
    for s in roster.sessions:
        m.add_exactly_one(by_session[s.id])   # every session placed exactly once
    for vs in by_room_slot.values():  m.add_at_most_one(vs)     # no room double-booking
    for vs in by_teacher_slot.values(): m.add_at_most_one(vs)   # no teacher double-booking

    lits = {}                                 # rule_id -> assumption literal (one per CONFIRMED rule)
    for rule in rules:
        if rule.status != "confirmed":
            continue
        lit = m.new_bool_var(f"rule_{rule.id}")
        lits[rule.id] = lit
        p = rule.params
        for (sid, teacher, room, d, t), v in x.items():
            bad = False
            if rule.type == "teacher_unavailable":
                bad = teacher == p["teacher"] and d == p["day"] and t in p["slots"]
            elif rule.type == "room_unavailable":
                bad = room == p["room"] and d == p["day"] and t in p["slots"]
            elif rule.type == "pin_session":
                bad = sid == p["session_id"] and not (d == p["day"] and t in p["slots"])
            elif rule.type == "only_qualified":
                bad = sid == p["session_id"] and teacher not in p["teachers"]
            if bad:
                m.add(v == 0).only_enforce_if(lit)
    m.add_assumptions(list(lits.values()))    # built-in constraints above are NOT assumptions

    if prev is not None:                      # minimal-change objective
        terms = []
        for pl in prev.placements:
            v = x.get((pl.session_id, pl.teacher, pl.room, pl.day, pl.slot))
            terms.append(1 - v if v is not None else 1)
        m.minimize(sum(terms))
    return m, x, lits

def solve(roster, rules, prev=None):
    """returns (status, Schedule|None, core_rule_ids|None); status in feasible|infeasible|unknown"""
    m, x, lits = build(roster, rules, prev)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = config.SOLVER_TIME_S
    s.parameters.random_seed = config.SOLVER_SEED
    st = s.solve(m)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        pls = [Placement(session_id=k[0], teacher=k[1], room=k[2], day=k[3], slot=k[4])
               for k, v in x.items() if s.value(v)]
        pls.sort(key=lambda p: p.session_id)
        return "feasible", Schedule(placements=pls), None
    if st == cp_model.INFEASIBLE:
        by_index = {lit.index: rid for rid, lit in lits.items()}
        core = [by_index[i] for i in s.sufficient_assumptions_for_infeasibility() if i in by_index]
        return "infeasible", None, core       # empty core = built-in capacity conflict
    return "unknown", None, None
```
Version of a new schedule = previous `version + 1` (set in `api.solve`).

If the core looks wrong or empty, try `s.parameters.num_workers = 1` and `s.parameters.cp_model_presolve = False` while extracting the core.

### 8.2 `solver/conflicts.py`
```python
def shrink_core(roster, rules, core) -> list[str]:
    by_id = {r.id: r for r in rules}
    core = list(core)
    for rid in list(core):
        trial = [c for c in core if c != rid]
        status, _, _ = solve(roster, [by_id[c] for c in trial])
        if status == "infeasible":
            core = trial
    return core                                # minimal: dropping any rule makes it feasible

def verify_option(roster, rules, rule_id, new_params) -> bool:
    patched = [r.model_copy(update={"params": new_params}) if r.id == rule_id else r for r in rules]
    return solve(roster, patched)[0] == "feasible"
```
Option pipeline in `api.explain_conflict`:
1. Build text for the core rules, call Gemma (`explain_conflict`).
2. For each option: skip if `rule_id` not in the core; skip if `validate_params` fails; skip if `verify_option` is False.
3. Keep verified ones as `RelaxOption(id=db.next_option_id(), approver=rule.owner, verified=True, option_hash=...)`. Save with `db.save_option`.
4. If no option survives, return the summary with an empty options list. The UI tells the coordinator to edit a rule by hand.
5. Max 3 relaxation cycles per session. Track in the API layer; on the 4th, return an error.

### 8.3 `solver/checker.py` (independent, no OR-Tools import)
```python
from collections import Counter
from backend import config
from backend.models import Schedule, Roster, Rule

def check(schedule: Schedule, roster: Roster, rules: list[Rule]) -> list[str]:
    v = []
    sess = {s.id: s for s in roster.sessions}
    rooms = {r.name: r for r in roster.rooms}
    count = Counter(p.session_id for p in schedule.placements)
    for sid in sess:
        if count[sid] != 1: v.append(f"Session {sid} is placed {count[sid]} times (must be 1)")
    for p in schedule.placements:
        s = sess.get(p.session_id)
        if s is None: v.append(f"Unknown session {p.session_id}"); continue
        if p.teacher not in s.teachers: v.append(f"{p.teacher} cannot teach {p.session_id}")
        r = rooms.get(p.room)
        if r is None: v.append(f"Unknown room {p.room}")
        elif r.capacity < s.size: v.append(f"Room {p.room} too small for {p.session_id}")
        if not (0 <= p.day < config.DAYS and 0 <= p.slot < config.SLOTS_PER_DAY):
            v.append(f"{p.session_id} outside the week grid")
    for key, label in (("room", "Room"), ("teacher", "Teacher")):
        c = Counter((getattr(p, key), p.day, p.slot) for p in schedule.placements)
        for (who, d, t), n in c.items():
            if n > 1: v.append(f"{label} clash: {who} has {n} sessions on {config.DAY_NAMES[d]} slot {t}")
    for rule in rules:
        if rule.status != "confirmed": continue
        q = rule.params
        for p in schedule.placements:
            if rule.type == "teacher_unavailable" and p.teacher == q["teacher"] and p.day == q["day"] and p.slot in q["slots"]:
                v.append(f"{rule.id}: {p.teacher} teaches {p.session_id} while unavailable")
            if rule.type == "room_unavailable" and p.room == q["room"] and p.day == q["day"] and p.slot in q["slots"]:
                v.append(f"{rule.id}: room {p.room} used while closed")
            if rule.type == "pin_session" and p.session_id == q["session_id"] and not (p.day == q["day"] and p.slot in q["slots"]):
                v.append(f"{rule.id}: {p.session_id} is not in its pinned slot")
            if rule.type == "only_qualified" and p.session_id == q["session_id"] and p.teacher not in q["teachers"]:
                v.append(f"{rule.id}: {p.teacher} is not qualified for {p.session_id}")
    return v
```

### 8.4 `solver/trace.py` ("Why is this class here?")
`why(session_id, schedule, rules) -> list[Rule]`: return confirmed rules whose params mention that session id, its placed teacher, its placed room, or its placed day and slot. Plain lookup. No second solve.

---

## 9. Demo Seed Data (`samples/`)

`samples/roster.json`
```json
{"teachers":["Prof. Rao","Prof. Mehta","Prof. Iyer"],
 "rooms":[{"name":"Lab-1","capacity":40},{"name":"Room-101","capacity":60},{"name":"Room-102","capacity":60}],
 "sessions":[
  {"id":"DB_LAB","course":"Database Lab","teachers":["Prof. Rao","Prof. Mehta"],"size":30},
  {"id":"OS_LEC","course":"Operating Systems","teachers":["Prof. Rao","Prof. Mehta","Prof. Iyer"],"size":30},
  {"id":"CN_LEC","course":"Computer Networks","teachers":["Prof. Mehta","Prof. Iyer"],"size":30},
  {"id":"AI_LEC","course":"Artificial Intel.","teachers":["Prof. Iyer","Prof. Rao"],"size":30},
  {"id":"ML_LAB","course":"Machine Learning Lab","teachers":["Prof. Mehta","Prof. Iyer"],"size":30},
  {"id":"SE_LEC","course":"Software Eng.","teachers":["Prof. Iyer"],"size":30}]}
```
Note `DB_LAB` lists Mehta as a candidate. The rule `only_qualified [Prof. Rao]` restricts it, and the Option B relaxation re-allows Mehta.

`seed_demo()` (in `api.py`) does:
1. `db.reset_db()`, load roster.
2. Confirm and register (on-chain) two base rules with **fixed ids**: `R1` = `pin_session` DB_LAB Monday slots [0,1,2], owner Dept Head; `R2` = `only_qualified` DB_LAB [Prof. Rao], owner Dean.
3. Solve and publish **v1** (anchored). DB_LAB lands Monday morning with Prof. Rao.
4. Leave later rules (the Hindi voice rule "Prof. Rao cannot do Monday morning") to be added live. It will get id `R3`.
The fixture `explain_conflict.json` then uses `R1` (pin) and `R2` (only_qualified).

---

## 10. Consent Ledger & Cryptographic Hashing `[PY]`

### 10.1 `backend/hashing.py` `[PY]`
```python
import hashlib, json, os
from backend.models import Schedule

def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def schedule_obj(s: Schedule) -> dict:
    return {"version": s.version,
            "placements": sorted((p.model_dump() for p in s.placements), key=lambda p: p["session_id"])}

def _hash(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def schedule_hash(s: Schedule) -> bytes:
    return _hash(canonical(schedule_obj(s)).encode("utf-8"))

def new_salt() -> bytes: return os.urandom(16)

def rule_hash(rule_id: str, rtype: str, owner: str, salt: bytes) -> bytes:
    return _hash(salt + canonical({"id": rule_id, "type": rtype, "owner": owner}).encode("utf-8"))

def option_hash(rule_id: str, new_params: dict) -> bytes:
    return _hash(canonical({"rule_id": rule_id, "new_params": new_params}).encode("utf-8"))

def hexs(value: bytes) -> str:
    return "0x" + value.hex()
```

### 10.2 Consent Ledger Protocol
Consent is managed directly by the application backend and PostgreSQL registry:
- **Rule Registration:** When a rule is confirmed, a cryptographic salt and canonical SHA-256 hash are recorded, and an audit event (`RuleConfirmed`) is logged.
- **Conflict Relaxation:** When an infeasible schedule causes conflicts, proposed relaxation options require explicit approval from the rule owner (`opt.approver`).
- **Authorization Enforcement:** A user cannot approve a change to someone else's rule (`as_user != option.approver` rejects with authorization failure).
- **Audit Log:** Every confirmation, approval, and publication writes to the `audit_events` ledger for an immutable verification trace.

---

## 11. Facade for the Frontend (`backend/api.py`)

This is the **only** module the frontend imports. All return types are Pydantic models from `models.py` or the models below. Keep signatures exactly.

```python
class IngestSheetResult(BaseModel): rules: list[Rule]; cache_hit: bool; attempts: int; tokens_used: int; seconds: float
class SolveResult(BaseModel): status: Literal["feasible","infeasible","unknown","error"]; schedule: Schedule | None; conflict: Conflict | None; moved: list[str]; solve_ms: int; message: str = ""
class ApprovalResult(BaseModel): ok: bool; tx_hash: str | None; error: str | None
class PublishResult(BaseModel): hash: str; tx_hash: str; version: int; json_bytes: bytes; csv_bytes: bytes; ics_bytes: bytes
class VerifyResult(BaseModel): match: bool; recomputed_hash: str; anchored: bool; error: str | None
class ScoreboardRow(BaseModel): run: int; baseline_violations: int; baseline_details: list[str]; gecompose_violations: int
class ScoreboardResult(BaseModel): rows: list[ScoreboardRow]
class Health(BaseModel): items: dict[str, dict]   # name -> {"ok": bool, "detail": str}

def health() -> Health                                   # intake, reason, docker, mock flags
def seed_demo() -> None;  def reset_demo() -> None
def get_roster() -> Roster
def ingest_audio(wav: bytes, filename: str) -> list[Rule]
def ingest_image(img: bytes, filename: str) -> list[Rule]
def ingest_text(text: str) -> list[Rule]
def ingest_sheet(xlsx: bytes, filename: str) -> IngestSheetResult
def list_rules(status: str | None = None) -> list[Rule]
def edit_rule(rule_id: str, params: dict | None = None, owner: str | None = None) -> Rule   # validates params
def confirm_rule(rule_id: str) -> Rule        # status=confirmed; creates salt+rule_hash; registers rule on-chain
def reject_rule(rule_id: str) -> Rule
def get_upload(filename: str) -> bytes | None
def solve(minimal_change: bool = True) -> SolveResult
    # confirmed rules + roster; prev = latest published schedule if minimal_change
    # on infeasible: shrink_core, return Conflict(rule_ids, owners)
    # on feasible: run checker; if violations -> status "error" with message (never return an invalid schedule)
    # new schedule.version = latest.version + 1 (or 1); `moved` = session ids whose placement differs from prev
    # the last feasible schedule is kept in memory as "pending" for publish()
def explain_conflict(conflict: Conflict) -> Explanation
def approve_option(option_id: str, as_user: str) -> ApprovalResult      # chain.approve; catches ChainError
def apply_option(option_id: str) -> Rule      # requires chain.is_approved(...) True; updates rule params in DB
def why_cell(session_id: str) -> list[Rule]
def publish() -> PublishResult                # checker must be clean; anchor on chain; save; build exports
def verify_file(data: bytes) -> VerifyResult  # parse JSON -> Schedule -> hash -> chain.is_anchored
def run_scoreboard(runs: int = 5) -> ScoreboardResult
def chain_events() -> list[dict]
```
`api.py` must catch every backend exception and convert it to a friendly message in the return value (`message` or `error`) so Streamlit never shows a stack trace.

### 11.1 `export.py` `[PY]`
- JSON: `canonical(schedule_obj(s))` (this exact text is what is hashed; the verifier re-parses it).
- CSV: header `session_id,teacher,room,day,time` (day name and `SLOT_TIMES[slot]`).
- ICS: `BEGIN:VCALENDAR / VERSION:2.0 / PRODID:-//GeCompose//EN`; one `VEVENT` per placement with `UID`, `DTSTAMP`, `SUMMARY:<session_id> (<teacher>)`, `LOCATION:<room>`, floating `DTSTART:YYYYMMDDTHHMMSS` and `DTEND` one hour later, starting from `WEEK_START_MONDAY + day`; lines end with `\r\n`.

### 11.2 `scoreboard.py` `[EXT: llama-server]` for the baseline
For each run: send the roster plus confirmed rules to the reasoning model with "produce a full timetable as JSON in this schema" (Placement list). Validate with `Schedule`. Invalid JSON counts as 1 violation ("invalid output"). Run `checker.check` on it. GeCompose side: run `solver.solve` then `checker.check` (expect 0). Report real numbers from all runs. If the baseline happens to be clean on a run, show it as 0. In `MOCK_LLM=1`, load a recorded baseline from `fixtures/baseline_runs.json` and label it "recorded".

### 11.3 `backend/healthcheck.py`
Prints OK/FAIL with detail for: intake model (`client.models.list()` with a 3 s timeout), reason model, Docker (`docker info`, and `docker image inspect gecompose-sandbox`), `MOCK_LLM`. `--audio file.wav` sends the clip to the intake model and prints the rules or the error.

### 11.4 `backend/reset_demo.py`
Calls `api.reset_demo()`: clears DB tables and `data/uploads/`, keeps parser cache **only if** `--keep-parsers` is passed. (For the zero-token demo you want the parser cache empty before the first sheet.)

---

## 12. Tests (`pytest -q`)

| Test | Checks |
|---|---|
| `test_solver_feasible` | seed roster + base rules R1, R2 give a feasible schedule; `checker.check` returns `[]` |
| `test_core_exact` | add R3 (Rao unavailable Mon 0-2): status infeasible; `shrink_core` returns exactly `{R1, R2, R3}` |
| `test_options_verified` | Option A (pin to Tue slot 1) and Option B (add Mehta) both verify feasible; a bogus option does not |
| `test_min_change` | after Option A with `prev=v1`, only `DB_LAB` (and at most direct clashes) moved |
| `test_checker_catches` | hand-made schedule with a double-booked room reports a room clash; one with an unavailable teacher reports it |
| `test_hash_stable` | same schedule hashes identically across runs; changing one placement changes the hash |
| `test_validate_params` | unknown teacher, bad day, extra keys all raise |
| `test_consent_approval` | rule confirmation, relaxation approval authorization, non-owner reject, and apply restriction |
| `test_publish_and_verify` | publish schedule, verify against registry returns True, tampered schedule returns False |
| `test_sheet_cache` (MOCK + `SANDBOX_MODE=local`) | first sheet `cache_hit=False`; second sheet same layout `cache_hit=True`, `tokens_used=0` |

---

## 13. Build Order (about 4 to 5 hours of focused work; stop early if needed)

| Step | Work | Needs external stack? |
|---|---|---|
| 1 | `config`, `models`, `registry/db` | no |
| 2 | solver, checker, tests 1 to 5 and 7 | no |
| 3 | conflicts, options, minimal change | no |
| 4 | consent ledger, hashing, consent tests | no |
| 5 | `llm/client` + fixtures, `explain_conflict`, `api.py` with `MOCK_LLM=1` | no |
| 6 | frontend skeleton running on mock data | no |
| 7 | real Gemma: text intake, then audio, then image | llama-server |
| 8 | sandbox + sheet parser + cache | Docker (+ llama-server) |
| 9 | verifier + tamper button, scoreboard | llama-server for the baseline |

**Decision rule:** if steps 1 to 6 are not working by the time you have 90 minutes left, stop adding features and rehearse the mock-mode demo.

---

## 14. Fallback Matrix (live demo)

| Failure | Do this |
|---|---|
| Gemma server down or slow | `MOCK_LLM=1`, restart Streamlit |
| Audio not accepted | `AUDIO_MODE=transcript`, type the rule, or upload the pre-tested `rao_hindi.wav` |
| Docker not running | `SANDBOX_MODE=local` with `MOCK_LLM=1` (fixture parser only) |
| Database reset needed | `python -m backend.reset_demo`, then `seed_demo` |
| Solver slow | lower `SOLVER_TIME_S`; the demo roster is tiny so this should not happen |

---

## 15. Definition of Done

- [ ] `python -m backend.healthcheck` shows OK for every item you are using.
- [ ] Clash scenario runs end to end in `MOCK_LLM=1` and with the real model.
- [ ] Checker returns no violations on every published schedule.
- [ ] Non-owner approval is rejected by consent authorization (shown in the UI).
- [ ] Tampered schedule shows a mismatch in the verifier.
- [ ] Second sheet with the same layout runs with `tokens_used=0`.
- [ ] Scoreboard shows measured numbers.
- [ ] README claims match what you actually measured.
