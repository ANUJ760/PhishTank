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
| 2 | **llama.cpp `llama-server`** (or vLLM) | Yes for real Gemma; No if `MOCK_LLM=1` | `llm/client.py` | release binary or build from the llama.cpp GitHub repo | `llama-server --version` | `MOCK_LLM=1` |
| 3 | **Gemma 4 weights**: E4B (GGUF + its multimodal projector file) and 12B (GGUF) | Yes for real Gemma | llama-server | Hugging Face (account and license acceptance may be needed). **Confirm exact repo and file names yourself.** | files exist on disk | `MOCK_LLM=1`, or use E4B for both tiers |
| 4 | NVIDIA GPU, 8 GB VRAM for one model, about 12 GB for both | Recommended | llama-server | driver | `nvidia-smi` | CPU works but is slow. With under 12 GB, run only E4B and set `REASON_URL=INTAKE_URL` |
| 5 | **Docker Engine** | Yes for sheet-parser sandbox | `intake/sandbox.py` | docs.docker.com | `docker run --rm hello-world` | `SANDBOX_MODE=local` (allowed only with `MOCK_LLM=1`) |
| 6 | **Foundry** (`forge`, `anvil`) | Yes for consent and verifier | `contracts/`, `chain/` | `curl -L https://foundry.paradigm.xyz \| bash` then `foundryup` | `anvil --version`, `forge --version` | **No fallback.** Install first. |
| 7 | Internet | Setup only | pip, Hugging Face, `docker build`, `foundryup`, forge's first solc download | n/a | n/a | Do all downloads before the event |
| 8 | Python packages | Yes | all | `pip install -r requirements.txt` | `python -c "import ortools, web3, streamlit"` | none |
| 9 | Chrome with mic permission | Only for live voice | frontend | n/a | open `http://localhost:8501` | use typed text or a pre-recorded WAV upload |
| 10 | ffmpeg | Optional | only if the model rejects the mic WAV | system package | `ffmpeg -version` | skip |

**Not needed:** Node.js, MetaMask, testnet ETH, any cloud API, Graphviz binary, Whisper or Tesseract, OpenZeppelin (the contract below does not use it).

**Honest note on wallets:** the demo uses Anvil's pre-unlocked accounts to stand in for each person's wallet. There is no browser wallet and no real signature prompt. Real wallet signing (EIP-712) is Future Scope. Say this plainly if asked.

### Where the external stack is touched

| Module | Touches | Fallback |
|---|---|---|
| `llm/client.py` | `[EXT: llama-server]` | `MOCK_LLM=1` fixtures |
| `intake/voice_photo.py` | `[EXT: llama-server]` with audio/vision model | `ingest_text`, fixtures |
| `intake/sheet_parser.py` | `[EXT: llama-server]` (first time per layout only) | fixture parser code |
| `intake/sandbox.py` | `[EXT: Docker]` | `SANDBOX_MODE=local` with `MOCK_LLM=1` |
| `chain/*`, `contracts/` | `[EXT: Foundry/Anvil]` | none |
| `solver/*`, `checker`, `hashing`, `registry` | `[PY]` only | n/a |

---

## 1. Setup (copy-paste, in order)

Run from the repo root.

**1. Python environment**
```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p data/uploads samples models
docker compose up -d postgres
```

`requirements.txt`
```
ortools>=9.11
pydantic>=2.7
web3>=7
streamlit>=1.40
pandas>=2.2
openpyxl>=3.1
openai>=1.40
python-dotenv>=1.0
psycopg[binary,pool]>=3.2
pytest>=8
```

PostgreSQL data persists in the `gecompose_postgres` Docker volume. The Compose service binds only to localhost. Override the development credentials with `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` before using this setup outside a local demo.

`.env.example`
```
MOCK_LLM=0
INTAKE_URL=http://127.0.0.1:8080/v1
INTAKE_MODEL=gemma-intake
REASON_URL=http://127.0.0.1:8081/v1
REASON_MODEL=gemma-reason
LLM_TIMEOUT_S=120
AUDIO_MODE=native          # native | transcript
SANDBOX_MODE=docker        # docker | local  (local only with MOCK_LLM=1)
SANDBOX_IMAGE=gecompose-sandbox
RPC_URL=http://127.0.0.1:8545
DATABASE_URL=postgresql://gecompose:gecompose_dev@127.0.0.1:5432/gecompose
UPLOAD_DIR=data/uploads
DAYS=5
SLOTS_PER_DAY=6
SOLVER_TIME_S=10
SOLVER_SEED=7
```

**2. Sandbox image `[EXT: Docker]`**

`Dockerfile.sandbox`
```dockerfile
FROM python:3.11-slim
RUN pip install --no-cache-dir pandas openpyxl
WORKDIR /work
```
```bash
docker build -f Dockerfile.sandbox -t gecompose-sandbox .
```
Build this now while you have internet. The sandbox runs with no network.

**3. Foundry project `[EXT: Foundry]`**
```bash
forge init contracts --no-git
rm contracts/src/Counter.sol contracts/test/Counter.t.sol contracts/script/Counter.s.sol
# put ConsentLedger.sol in contracts/src/ and ConsentLedger.t.sol in contracts/test/ (Section 7.4)
# in contracts/foundry.toml under [profile.default] add: solc = "0.8.24"
cd contracts && forge build && forge test -vv && cd ..
```
ABI file produced: `contracts/out/ConsentLedger.sol/ConsentLedger.json`.

**4. Start the local chain `[EXT: Anvil]` (own terminal, leave running)**
```bash
anvil --port 8545
```
**5. Deploy**
```bash
python -m backend.chain.deploy      # writes data/deployment.json
```
If you restart Anvil, the chain is wiped. Redeploy and run `python -m backend.reset_demo`.

**6. Start Gemma servers `[EXT: llama-server]` (two terminals; skip if `MOCK_LLM=1`)**

File names below are placeholders. Use the real names you downloaded.
```bash
# Intake tier: audio + images + text
llama-server -m models/<gemma4-e4b>.gguf --mmproj models/<gemma4-e4b-mmproj>.gguf \
  --host 127.0.0.1 --port 8080 -ngl 99 -c 8192 --alias gemma-intake

# Reasoning tier: parser codegen + conflict explanation
llama-server -m models/<gemma4-12b>.gguf \
  --host 127.0.0.1 --port 8081 -ngl 99 -c 8192 --alias gemma-reason
```
**Verify audio works on your exact runtime and model before building voice features:**
```bash
python -m backend.healthcheck --audio samples/rao_hindi.wav
```
If audio is rejected, set `AUDIO_MODE=transcript` (the UI then asks for typed text). Do not add a separate speech model unless you accept losing the "one model" claim.

**7. Health check**
```bash
python -m backend.healthcheck       # prints OK/FAIL per external item
```

**8. Run frontend:** see `FRONTEND_SETUP.md`.

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
  config.py  models.py  api.py  healthcheck.py  reset_demo.py  scoreboard.py
  registry/db.py
  llm/client.py  llm/prompts.py  llm/fixtures/*.json
  intake/voice_photo.py  intake/sheet_parser.py  intake/sandbox.py
  solver/model.py  solver/conflicts.py  solver/checker.py  solver/trace.py
  chain/hashing.py  chain/client.py  chain/deploy.py
  export.py
contracts/            # Foundry project
frontend/             # see FRONTEND_SETUP.md
samples/              # roster.json, base_rules.json, workload.xlsx, workload2.xlsx, rao_hindi.wav, board.png
tests/
data/                 # created at runtime: gecompose.db, deployment.json, uploads/
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
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://gecompose:gecompose_dev@127.0.0.1:5432/gecompose")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
DAYS = int(os.getenv("DAYS", "5"))
SLOTS_PER_DAY = int(os.getenv("SLOTS_PER_DAY", "6"))
SOLVER_TIME_S = float(os.getenv("SOLVER_TIME_S", "10"))
SOLVER_SEED = int(os.getenv("SOLVER_SEED", "7"))

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri"]
SLOT_TIMES = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00"]  # 1 hour each
WEEK_START_MONDAY = "2026-10-12"                                      # for .ics export

# Anvil account index per person. Anvil's accounts are pre-unlocked, so no keys are needed.
ACCOUNT_INDEX = {"Coordinator": 0, "Prof. Rao": 1, "Prof. Mehta": 2,
                 "Dept Head": 3, "Dean": 4, "Prof. Iyer": 5}
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

## 10. Chain `[EXT: Foundry/Anvil]`

### 10.1 `contracts/src/ConsentLedger.sol`
```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

contract ConsentLedger {
    address public coordinator;
    mapping(bytes32 => address) public ruleOwner;                 // ruleHash => owner
    mapping(bytes32 => mapping(bytes32 => bool)) public approved; // ruleHash => optionHash => approved
    mapping(bytes32 => bool) public anchored;                     // scheduleHash => exists

    event RuleRegistered(bytes32 indexed ruleHash, address indexed owner);
    event RelaxationApproved(bytes32 indexed ruleHash, bytes32 indexed optionHash, address indexed owner);
    event ScheduleAnchored(bytes32 indexed scheduleHash, uint256 version, address indexed by);

    constructor() { coordinator = msg.sender; }

    function registerRule(bytes32 ruleHash, address owner) external {
        require(msg.sender == coordinator, "only coordinator");
        require(owner != address(0), "zero owner");
        require(ruleOwner[ruleHash] == address(0), "already registered");
        ruleOwner[ruleHash] = owner;
        emit RuleRegistered(ruleHash, owner);
    }

    function approveRelaxation(bytes32 ruleHash, bytes32 optionHash) external {
        require(ruleOwner[ruleHash] == msg.sender, "not rule owner");
        approved[ruleHash][optionHash] = true;
        emit RelaxationApproved(ruleHash, optionHash, msg.sender);
    }

    function anchorSchedule(bytes32 scheduleHash, uint256 version) external {
        require(msg.sender == coordinator, "only coordinator");
        require(!anchored[scheduleHash], "already anchored");
        anchored[scheduleHash] = true;
        emit ScheduleAnchored(scheduleHash, version, msg.sender);
    }
}
```

### 10.2 `contracts/test/ConsentLedger.t.sol`
```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import "forge-std/Test.sol";
import "../src/ConsentLedger.sol";

contract ConsentLedgerTest is Test {
    ConsentLedger l;
    address rao = address(0xA1);
    address eve = address(0xB2);
    bytes32 rh = keccak256("rule1");
    bytes32 oh = keccak256("opt1");

    function setUp() public { l = new ConsentLedger(); }

    function test_ownerCanApprove() public {
        l.registerRule(rh, rao);
        vm.prank(rao);
        l.approveRelaxation(rh, oh);
        assertTrue(l.approved(rh, oh));
    }
    function test_nonOwnerReverts() public {
        l.registerRule(rh, rao);
        vm.prank(eve);
        vm.expectRevert(bytes("not rule owner"));
        l.approveRelaxation(rh, oh);
    }
    function test_onlyCoordinatorRegisters() public {
        vm.prank(eve);
        vm.expectRevert(bytes("only coordinator"));
        l.registerRule(rh, rao);
    }
    function test_doubleRegisterReverts() public {
        l.registerRule(rh, rao);
        vm.expectRevert(bytes("already registered"));
        l.registerRule(rh, rao);
    }
    function test_anchorOnce() public {
        l.anchorSchedule(rh, 1);
        assertTrue(l.anchored(rh));
        vm.expectRevert(bytes("already anchored"));
        l.anchorSchedule(rh, 1);
    }
}
```

### 10.3 `backend/chain/hashing.py` `[PY]`
```python
import json, os
from web3 import Web3
from backend.models import Schedule

def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def schedule_obj(s: Schedule) -> dict:
    return {"version": s.version,
            "placements": sorted((p.model_dump() for p in s.placements), key=lambda p: p["session_id"])}

def schedule_hash(s: Schedule) -> bytes:
    return Web3.keccak(canonical(schedule_obj(s)).encode())

def new_salt() -> bytes: return os.urandom(16)

def rule_hash(rule_id: str, rtype: str, owner: str, salt: bytes) -> bytes:
    # identity of the rule; does NOT commit to params (params can be relaxed later)
    return Web3.keccak(salt + canonical({"id": rule_id, "type": rtype, "owner": owner}).encode())

def option_hash(rule_id: str, new_params: dict) -> bytes:
    # commits to the exact change the owner approves
    return Web3.keccak(canonical({"rule_id": rule_id, "new_params": new_params}).encode())

hexs = Web3.to_hex   # bytes -> "0x..." (always with prefix)
```

### 10.4 `backend/chain/client.py`
```python
import json
from pathlib import Path
from web3 import Web3
from web3.exceptions import ContractLogicError
from backend import config

ABI_PATH = Path("contracts/out/ConsentLedger.sol/ConsentLedger.json")
DEPLOY_PATH = Path("data/deployment.json")
class ChainError(Exception): ...

class Chain:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(config.RPC_URL))              # [EXT: Anvil]
        abi = json.loads(ABI_PATH.read_text())["abi"]
        addr = json.loads(DEPLOY_PATH.read_text())["address"]
        self.c = self.w3.eth.contract(address=addr, abi=abi)
        self.accounts = self.w3.eth.accounts

    def addr(self, name: str) -> str:
        if name not in config.ACCOUNT_INDEX: raise ChainError(f"no wallet configured for {name}")
        return self.accounts[config.ACCOUNT_INDEX[name]]

    def _send(self, fn, sender: str) -> str:
        try:
            h = fn.transact({"from": self.addr(sender)})
            self.w3.eth.wait_for_transaction_receipt(h)
            return Web3.to_hex(h)
        except ContractLogicError as e:
            raise ChainError(str(e))          # e.g. "execution reverted: not rule owner"

    def register_rule(self, rule_hash: bytes, owner: str) -> str:
        return self._send(self.c.functions.registerRule(rule_hash, self.addr(owner)), "Coordinator")
    def approve(self, rule_hash: bytes, option_hash: bytes, as_user: str) -> str:
        return self._send(self.c.functions.approveRelaxation(rule_hash, option_hash), as_user)
    def is_approved(self, rule_hash: bytes, option_hash: bytes) -> bool:
        return self.c.functions.approved(rule_hash, option_hash).call()
    def anchor(self, sched_hash: bytes, version: int) -> str:
        return self._send(self.c.functions.anchorSchedule(sched_hash, version), "Coordinator")
    def is_anchored(self, sched_hash: bytes) -> bool:
        return self.c.functions.anchored(sched_hash).call()
    def events(self) -> list[dict]:
        out = []
        for name in ("RuleRegistered", "RelaxationApproved", "ScheduleAnchored"):
            for e in getattr(self.c.events, name)().get_logs(from_block=0):
                out.append({"event": name, "block": e["blockNumber"], "idx": e["logIndex"],
                            "args": {k: (Web3.to_hex(v) if isinstance(v, (bytes, bytearray)) else v)
                                     for k, v in e["args"].items()}})
        return sorted(out, key=lambda r: (r["block"], r["idx"]))
```
A non-owner calling `approve` raises `ChainError("... not rule owner")`. The UI shows this message (it is the demo of "nobody can approve for someone else").

### 10.5 `backend/chain/deploy.py`
```python
import json
from pathlib import Path
from web3 import Web3
from backend import config
from backend.chain.client import ABI_PATH, DEPLOY_PATH

def deploy():
    w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
    art = json.loads(ABI_PATH.read_text())
    C = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"]["object"])
    h = C.constructor().transact({"from": w3.eth.accounts[0]})   # account 0 = Coordinator
    addr = w3.eth.wait_for_transaction_receipt(h).contractAddress
    DEPLOY_PATH.parent.mkdir(exist_ok=True)
    DEPLOY_PATH.write_text(json.dumps({"address": addr}))
    print("deployed", addr)

if __name__ == "__main__": deploy()
```

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

def health() -> Health                                   # intake, reason, docker, anvil, contract, mock flags
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
Prints OK/FAIL with detail for: intake model (`client.models.list()` with a 3 s timeout), reason model, Docker (`docker info`, and `docker image inspect gecompose-sandbox`), Anvil (`w3.is_connected()`), contract (code at the saved address is not empty; empty means Anvil was restarted), `MOCK_LLM`. `--audio file.wav` sends the clip to the intake model and prints the rules or the error.

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
| Foundry `forge test` | owner approves; non-owner reverts; non-coordinator reverts; double register and double anchor revert |
| `test_chain_integration` (needs Anvil) | register, approve, anchor, `is_anchored`; non-owner approve raises `ChainError` |
| `test_sheet_cache` (MOCK + `SANDBOX_MODE=local`) | first sheet `cache_hit=False`; second sheet same layout `cache_hit=True`, `tokens_used=0` |

---

## 13. Build Order (about 4 to 5 hours of focused work; stop early if needed)

| Step | Work | Needs external stack? |
|---|---|---|
| 1 | `config`, `models`, `registry/db` | no |
| 2 | solver, checker, tests 1 to 5 and 7 | no |
| 3 | conflicts, options, minimal change | no |
| 4 | contract, `forge test`, `deploy`, `chain/client`, hashing, chain tests | Foundry, Anvil |
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
| Anvil restarted | `python -m backend.chain.deploy` then `python -m backend.reset_demo`, then `seed_demo` |
| Solver slow | lower `SOLVER_TIME_S`; the demo roster is tiny so this should not happen |

---

## 15. Definition of Done

- [ ] `python -m backend.healthcheck` shows OK for every item you are using.
- [ ] Clash scenario runs end to end in `MOCK_LLM=1` and with the real model.
- [ ] Checker returns no violations on every published schedule.
- [ ] Non-owner approval reverts on-chain (Foundry test and shown in the UI).
- [ ] Tampered schedule shows a mismatch in the verifier.
- [ ] Second sheet with the same layout runs with `tokens_used=0`.
- [ ] Scoreboard shows measured numbers.
- [ ] README claims match what you actually measured.
