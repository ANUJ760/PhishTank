"""SQLite registry with short-lived connections and parameterized queries."""
from __future__ import annotations
import json, re, sqlite3, time
from contextlib import contextmanager
from pathlib import Path
from backend import config
from backend.models import RelaxOption, Rule, Roster, Schedule

@contextmanager
def _connect():
    path = config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def init_db() -> None:
    with _connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS rules(id TEXT PRIMARY KEY,json TEXT NOT NULL,salt BLOB,rule_hash TEXT,status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS roster(id INTEGER PRIMARY KEY CHECK(id=1),json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS parsers(layout_signature TEXT PRIMARY KEY,code TEXT NOT NULL,created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS schedules(hash TEXT PRIMARY KEY,version INTEGER NOT NULL,json TEXT NOT NULL,tx_hash TEXT NOT NULL,created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS options(id TEXT PRIMARY KEY,json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS llm_calls(id INTEGER PRIMARY KEY AUTOINCREMENT,fn TEXT,model TEXT,tokens_in INT,tokens_out INT,ms INT,mock INT,ts REAL);
        """)

def reset_db(keep_parsers: bool = False) -> None:
    init_db()
    with _connect() as c:
        c.execute("DELETE FROM rules"); c.execute("DELETE FROM roster"); c.execute("DELETE FROM schedules"); c.execute("DELETE FROM options"); c.execute("DELETE FROM llm_calls")
        if not keep_parsers: c.execute("DELETE FROM parsers")

def save_roster(roster: Roster) -> None:
    with _connect() as c: c.execute("INSERT INTO roster(id,json) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET json=excluded.json", (roster.model_dump_json(),))
def get_roster() -> Roster:
    with _connect() as c: row = c.execute("SELECT json FROM roster WHERE id=1").fetchone()
    if row is None: raise LookupError("No roster is configured")
    return Roster.model_validate_json(row[0])
def next_rule_id() -> str:
    init_db()
    with _connect() as c: rows = c.execute("SELECT id FROM rules").fetchall()
    return f"R{max((int(m.group(1)) for r in rows if (m := re.fullmatch(r'R(\d+)', r[0]))), default=0)+1}"
def save_rule(rule: Rule, salt: bytes | None = None, rule_hash: str | None = None) -> None:
    with _connect() as c:
        c.execute("INSERT INTO rules(id,json,salt,rule_hash,status) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET json=excluded.json,salt=COALESCE(excluded.salt,rules.salt),rule_hash=COALESCE(excluded.rule_hash,rules.rule_hash),status=excluded.status", (rule.id,rule.model_dump_json(),salt,rule_hash,rule.status))
def get_rule(rule_id: str) -> Rule:
    with _connect() as c: row=c.execute("SELECT json FROM rules WHERE id=?",(rule_id,)).fetchone()
    if not row: raise LookupError(f"Rule {rule_id} was not found")
    return Rule.model_validate_json(row[0])
def list_rules(status: str | None = None) -> list[Rule]:
    with _connect() as c: rows=c.execute("SELECT json FROM rules WHERE status=? ORDER BY id",(status,)).fetchall() if status else c.execute("SELECT json FROM rules ORDER BY id").fetchall()
    return [Rule.model_validate_json(r[0]) for r in rows]
def get_salt(rule_id: str) -> bytes:
    with _connect() as c: row=c.execute("SELECT salt FROM rules WHERE id=?",(rule_id,)).fetchone()
    if not row or row[0] is None: raise LookupError(f"Rule {rule_id} has no registered salt")
    return bytes(row[0])
def get_rule_hash(rule_id: str) -> str:
    with _connect() as c: row=c.execute("SELECT rule_hash FROM rules WHERE id=?",(rule_id,)).fetchone()
    if not row or not row[0]: raise LookupError(f"Rule {rule_id} has no registered hash")
    return str(row[0])
def save_parser(sig: str, code: str) -> None:
    with _connect() as c: c.execute("INSERT INTO parsers VALUES(?,?,?) ON CONFLICT(layout_signature) DO UPDATE SET code=excluded.code,created_at=excluded.created_at",(sig,code,time.time()))
def get_parser(sig: str) -> str | None:
    with _connect() as c: row=c.execute("SELECT code FROM parsers WHERE layout_signature=?",(sig,)).fetchone()
    return row[0] if row else None
def delete_parser(sig: str) -> None:
    with _connect() as c: c.execute("DELETE FROM parsers WHERE layout_signature=?",(sig,))
def save_schedule(schedule: Schedule, hash_hex: str, tx_hash: str) -> None:
    with _connect() as c: c.execute("INSERT INTO schedules VALUES(?,?,?,?,?)",(hash_hex,schedule.version,schedule.model_dump_json(),tx_hash,time.time()))
def latest_schedule() -> Schedule | None:
    with _connect() as c: row=c.execute("SELECT json FROM schedules ORDER BY version DESC,created_at DESC LIMIT 1").fetchone()
    return Schedule.model_validate_json(row[0]) if row else None
def save_option(option: RelaxOption) -> None:
    with _connect() as c: c.execute("INSERT INTO options(id,json) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET json=excluded.json",(option.id,option.model_dump_json()))
def get_option(option_id: str) -> RelaxOption:
    with _connect() as c: row=c.execute("SELECT json FROM options WHERE id=?",(option_id,)).fetchone()
    if not row: raise LookupError(f"Option {option_id} was not found")
    return RelaxOption.model_validate_json(row[0])
def next_option_id() -> str:
    with _connect() as c: rows=c.execute("SELECT id FROM options").fetchall()
    return f"O{max((int(m.group(1)) for r in rows if (m:=re.fullmatch(r'O(\d+)',r[0]))),default=0)+1}"
def log_llm_call(fn: str, model: str, tokens_in: int, tokens_out: int, ms: int, mock: bool) -> None:
    with _connect() as c: c.execute("INSERT INTO llm_calls(fn,model,tokens_in,tokens_out,ms,mock,ts) VALUES(?,?,?,?,?,?,?)",(fn,model,tokens_in,tokens_out,ms,int(mock),time.time()))
def tokens_since(ts: float) -> int:
    with _connect() as c: row=c.execute("SELECT COALESCE(SUM(tokens_in+tokens_out),0) FROM llm_calls WHERE ts>=?",(ts,)).fetchone()
    return int(row[0])
def save_upload(filename: str, data: bytes) -> None:
    if not filename or Path(filename).name != filename or filename in {".",".."}: raise ValueError("invalid upload filename")
    folder=config.DB_PATH.parent / "uploads"; folder.mkdir(parents=True,exist_ok=True)
    target=folder / filename
    temp=target.with_name(target.name+".tmp")
    temp.write_bytes(data); temp.replace(target)
def get_upload(filename: str) -> bytes | None:
    if not filename or Path(filename).name != filename: return None
    path=config.DB_PATH.parent / "uploads" / filename
    return path.read_bytes() if path.is_file() else None

init_db()
