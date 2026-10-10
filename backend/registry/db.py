"""PostgreSQL and SQLite dual-backend registry with short-lived, transaction-scoped connections."""
from __future__ import annotations

import atexit
import logging
from pathlib import Path
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Iterator

from backend import config
from backend.models import RelaxOption, Rule, Roster, Schedule

log = logging.getLogger(__name__)

_pool = None
_pool_lock = threading.Lock()
_sqlite_conn = None
_sqlite_lock = threading.RLock()
_engine_type: str | None = None
_db_initialized = False
_init_lock = threading.Lock()


class _SQLiteCursorAdapter:
    def __init__(self, cursor: sqlite3.Cursor):
        self._cursor = cursor

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __getattr__(self, name: str):
        return getattr(self._cursor, name)


class _SQLiteConnectionAdapter:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def execute(self, sql: str, params: tuple | list | None = None):
        adapted_sql = sql.replace("%s", "?")
        if " FOR UPDATE" in adapted_sql:
            adapted_sql = adapted_sql.replace(" FOR UPDATE", "")
        if params is None:
            cur = self._conn.execute(adapted_sql)
        else:
            cur = self._conn.execute(adapted_sql, tuple(params))
        return _SQLiteCursorAdapter(cur)

    def commit(self):
        self._conn.commit()


def _close_pool():
    global _pool, _sqlite_conn
    if _pool is not None:
        try:
            _pool.close()
        except Exception:
            pass
        _pool = None
    if _sqlite_conn is not None:
        try:
            _sqlite_conn.close()
        except Exception:
            pass
        _sqlite_conn = None


atexit.register(_close_pool)


def _get_sqlite_path() -> Path:
    db_url = config.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        path_str = db_url[len("sqlite:///"):]
    elif db_url.startswith("sqlite://"):
        path_str = db_url[len("sqlite://"):]
    elif db_url.startswith("sqlite:"):
        path_str = db_url[len("sqlite:"):]
    else:
        path_str = "data/gecompose.db"
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _get_sqlite_conn() -> sqlite3.Connection:
    global _sqlite_conn
    if _sqlite_conn is None:
        path = _get_sqlite_path()
        conn = sqlite3.connect(
            str(path),
            timeout=30.0,
            check_same_thread=False,
            isolation_level=None,  # autocommit mode; we manage transactions explicitly
        )
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        _sqlite_conn = conn
    return _sqlite_conn


def _get_pool():
    global _pool, _engine_type
    if _engine_type == "sqlite":
        return None
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _engine_type == "sqlite":
            return None
        if _pool is not None:
            return _pool

        # Check if SQLite is explicitly requested
        if config.DATABASE_URL.startswith("sqlite"):
            _engine_type = "sqlite"
            return None

        try:
            from psycopg_pool import ConnectionPool
            pool = ConnectionPool(
                conninfo=config.DATABASE_URL,
                min_size=1,
                max_size=10,
                timeout=1,
                kwargs={"connect_timeout": 1, "application_name": "gecompose-backend"},
                open=False,
            )
            pool.open(wait=True, timeout=1)
            _pool = pool
            _engine_type = "postgres"
            return _pool
        except Exception as exc:
            if config.DB_FALLBACK_SQLITE:
                log.warning(
                    "PostgreSQL connection failed (%s); falling back to local SQLite at %s",
                    exc,
                    _get_sqlite_path(),
                )
                _engine_type = "sqlite"
                return None
            raise RuntimeError(f"Cannot connect to PostgreSQL: {exc}") from exc


@contextmanager
def _connect() -> Iterator:
    global _db_initialized
    if not _db_initialized:
        with _init_lock:
            if not _db_initialized:
                _db_initialized = True
                init_db()

    pool = _get_pool()
    if pool is not None:
        try:
            with pool.connection() as connection:
                connection.autocommit = True
                yield connection
        except Exception as exc:
            raise RuntimeError(f"PostgreSQL connection error: {exc}") from exc
    else:
        # SQLite mode
        with _sqlite_lock:
            conn = _get_sqlite_conn()
            adapter = _SQLiteConnectionAdapter(conn)
            yield adapter


def get_engine_type() -> str:
    if _engine_type is None:
        _get_pool()
    return _engine_type or "sqlite"


def init_db() -> None:
    engine = get_engine_type()
    if engine == "postgres":
        statements = (
            "CREATE TABLE IF NOT EXISTS rules(id TEXT PRIMARY KEY,json TEXT NOT NULL,salt BYTEA,rule_hash TEXT,status TEXT NOT NULL)",
            "CREATE INDEX IF NOT EXISTS rules_status_id_idx ON rules(status,id)",
            "CREATE TABLE IF NOT EXISTS roster(id SMALLINT PRIMARY KEY CHECK(id=1),json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS parsers(layout_signature TEXT PRIMARY KEY,code TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL)",
            "CREATE TABLE IF NOT EXISTS schedules(hash TEXT PRIMARY KEY,version INTEGER NOT NULL,json TEXT NOT NULL,tx_hash TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL)",
            "CREATE INDEX IF NOT EXISTS schedules_latest_idx ON schedules(version DESC,created_at DESC)",
            "CREATE TABLE IF NOT EXISTS options(id TEXT PRIMARY KEY,json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS llm_calls(id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,fn TEXT,model TEXT,tokens_in INTEGER,tokens_out INTEGER,ms INTEGER,mock BOOLEAN,ts DOUBLE PRECISION)",
            "CREATE INDEX IF NOT EXISTS llm_calls_timestamp_idx ON llm_calls(ts)",
            "CREATE TABLE IF NOT EXISTS id_sequences(name TEXT PRIMARY KEY,value BIGINT NOT NULL CHECK(value >= 0))",
            "CREATE TABLE IF NOT EXISTS audit_events(id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,event TEXT NOT NULL,entity_id TEXT NOT NULL,user_id TEXT NOT NULL,details TEXT NOT NULL,prev_hash TEXT NOT NULL DEFAULT '0000000000000000000000000000000000000000000000000000000000000000',entry_hash TEXT NOT NULL DEFAULT '',created_at DOUBLE PRECISION NOT NULL)",
            "CREATE INDEX IF NOT EXISTS audit_events_created_idx ON audit_events(created_at DESC)",
            "CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL)",
            "CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,created_at DOUBLE PRECISION NOT NULL,expires_at DOUBLE PRECISION NOT NULL)",
        )
    else:
        statements = (
            "CREATE TABLE IF NOT EXISTS rules(id TEXT PRIMARY KEY,json TEXT NOT NULL,salt BLOB,rule_hash TEXT,status TEXT NOT NULL)",
            "CREATE INDEX IF NOT EXISTS rules_status_id_idx ON rules(status,id)",
            "CREATE TABLE IF NOT EXISTS roster(id INTEGER PRIMARY KEY CHECK(id=1),json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS parsers(layout_signature TEXT PRIMARY KEY,code TEXT NOT NULL,created_at REAL NOT NULL)",
            "CREATE TABLE IF NOT EXISTS schedules(hash TEXT PRIMARY KEY,version INTEGER NOT NULL,json TEXT NOT NULL,tx_hash TEXT NOT NULL,created_at REAL NOT NULL)",
            "CREATE INDEX IF NOT EXISTS schedules_latest_idx ON schedules(version DESC,created_at DESC)",
            "CREATE TABLE IF NOT EXISTS options(id TEXT PRIMARY KEY,json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS llm_calls(id INTEGER PRIMARY KEY AUTOINCREMENT,fn TEXT,model TEXT,tokens_in INTEGER,tokens_out INTEGER,ms INTEGER,mock BOOLEAN,ts REAL)",
            "CREATE INDEX IF NOT EXISTS llm_calls_timestamp_idx ON llm_calls(ts)",
            "CREATE TABLE IF NOT EXISTS id_sequences(name TEXT PRIMARY KEY,value INTEGER NOT NULL CHECK(value >= 0))",
            "CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT NOT NULL,entity_id TEXT NOT NULL,user_id TEXT NOT NULL,details TEXT NOT NULL,prev_hash TEXT NOT NULL DEFAULT '0000000000000000000000000000000000000000000000000000000000000000',entry_hash TEXT NOT NULL DEFAULT '',created_at REAL NOT NULL)",
            "CREATE INDEX IF NOT EXISTS audit_events_created_idx ON audit_events(created_at DESC)",
            "CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL,created_at REAL NOT NULL)",
            "CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,created_at REAL NOT NULL,expires_at REAL NOT NULL)",
        )

    # Note: bypass _connect's auto-init check by executing directly
    pool = _get_pool()
    if pool is not None:
        with pool.connection() as connection:
            connection.autocommit = True
            for statement in statements:
                try:
                    connection.execute(statement)
                except Exception:
                    pass
            for col_stmt in (
                "ALTER TABLE audit_events ADD COLUMN prev_hash TEXT DEFAULT '0000000000000000000000000000000000000000000000000000000000000000'",
                "ALTER TABLE audit_events ADD COLUMN entry_hash TEXT DEFAULT ''",
            ):
                try:
                    connection.execute(col_stmt)
                except Exception:
                    pass
    else:
        with _sqlite_lock:
            conn = _get_sqlite_conn()
            conn.execute("BEGIN IMMEDIATE;")
            try:
                for statement in statements:
                    conn.execute(statement)
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise

            for col_stmt in (
                "ALTER TABLE audit_events ADD COLUMN prev_hash TEXT DEFAULT '0000000000000000000000000000000000000000000000000000000000000000'",
                "ALTER TABLE audit_events ADD COLUMN entry_hash TEXT DEFAULT ''",
            ):
                try:
                    conn.execute(col_stmt)
                    conn.commit()
                except Exception:
                    pass


def check_connection() -> None:
    with _connect() as connection:
        connection.execute("SELECT 1")


def reset_db(keep_parsers: bool = False) -> None:
    init_db()
    with _connect() as connection:
        for table in ("rules", "roster", "schedules", "options", "llm_calls", "id_sequences", "audit_events"):
            connection.execute(f"DELETE FROM {table}")
        if not keep_parsers:
            connection.execute("DELETE FROM parsers")


def save_roster(roster: Roster) -> None:
    with _connect() as connection:
        connection.execute(
            "INSERT INTO roster(id,json) VALUES(1,%s) ON CONFLICT(id) DO UPDATE SET json=EXCLUDED.json",
            (roster.model_dump_json(),),
        )


def get_roster() -> Roster:
    with _connect() as connection:
        row = connection.execute("SELECT json FROM roster WHERE id=1").fetchone()
    if row is None:
        raise LookupError("No roster is configured")
    return Roster.model_validate_json(row[0])


def _next_id(sequence: str, table: str, pattern: str, prefix: str) -> str:
    """Reserve an identifier atomically, accounting for fixed demo IDs."""
    with _connect() as connection:
        connection.execute(
            "INSERT INTO id_sequences(name,value) VALUES(%s,0) ON CONFLICT(name) DO NOTHING",
            (sequence,),
        )
        row = connection.execute(
            "SELECT value FROM id_sequences WHERE name=%s FOR UPDATE", (sequence,)
        ).fetchone()
        current = int(row[0])
        rows = connection.execute(f"SELECT id FROM {table}").fetchall()
        highest = max(
            (int(match.group(1)) for item in rows if (match := re.fullmatch(pattern, item[0]))),
            default=0,
        )
        value = max(current, highest) + 1
        connection.execute("UPDATE id_sequences SET value=%s WHERE name=%s", (value, sequence))
    return f"{prefix}{value}"


def next_rule_id() -> str:
    return _next_id("rules", "rules", r"R(\d+)", "R")


def save_rule(rule: Rule, salt: bytes | None = None, rule_hash: str | None = None) -> None:
    with _connect() as connection:
        connection.execute(
            """INSERT INTO rules(id,json,salt,rule_hash,status) VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT(id) DO UPDATE SET json=EXCLUDED.json,
            salt=COALESCE(EXCLUDED.salt,rules.salt),
            rule_hash=COALESCE(EXCLUDED.rule_hash,rules.rule_hash),status=EXCLUDED.status""",
            (rule.id, rule.model_dump_json(), salt, rule_hash, rule.status),
        )


def get_rule(rule_id: str) -> Rule:
    with _connect() as connection:
        row = connection.execute("SELECT json FROM rules WHERE id=%s", (rule_id,)).fetchone()
    if not row:
        raise LookupError(f"Rule {rule_id} was not found")
    return Rule.model_validate_json(row[0])


def list_rules(status: str | None = None) -> list[Rule]:
    with _connect() as connection:
        if status is None:
            rows = connection.execute("SELECT json FROM rules ORDER BY id").fetchall()
        else:
            rows = connection.execute("SELECT json FROM rules WHERE status=%s ORDER BY id", (status,)).fetchall()
    return [Rule.model_validate_json(row[0]) for row in rows]


def get_salt(rule_id: str) -> bytes:
    with _connect() as connection:
        row = connection.execute("SELECT salt FROM rules WHERE id=%s", (rule_id,)).fetchone()
    if not row or row[0] is None:
        raise LookupError(f"Rule {rule_id} has no registered salt")
    return bytes(row[0])


def get_rule_hash(rule_id: str) -> str:
    with _connect() as connection:
        row = connection.execute("SELECT rule_hash FROM rules WHERE id=%s", (rule_id,)).fetchone()
    if not row or not row[0]:
        raise LookupError(f"Rule {rule_id} has no registered hash")
    return str(row[0])


def save_parser(sig: str, code: str) -> None:
    with _connect() as connection:
        connection.execute(
            "INSERT INTO parsers(layout_signature,code,created_at) VALUES(%s,%s,%s) ON CONFLICT(layout_signature) DO UPDATE SET code=EXCLUDED.code,created_at=EXCLUDED.created_at",
            (sig, code, time.time()),
        )


def get_parser(sig: str) -> str | None:
    with _connect() as connection:
        row = connection.execute("SELECT code FROM parsers WHERE layout_signature=%s", (sig,)).fetchone()
    return row[0] if row else None


def delete_parser(sig: str) -> None:
    with _connect() as connection:
        connection.execute("DELETE FROM parsers WHERE layout_signature=%s", (sig,))


def save_schedule(schedule: Schedule, hash_hex: str, tx_hash: str = "") -> None:
    with _connect() as connection:
        connection.execute(
            "INSERT INTO schedules(hash,version,json,tx_hash,created_at) VALUES(%s,%s,%s,%s,%s) "
            "ON CONFLICT(hash) DO UPDATE SET version=EXCLUDED.version,json=EXCLUDED.json,tx_hash=EXCLUDED.tx_hash,created_at=EXCLUDED.created_at",
            (hash_hex, schedule.version, schedule.model_dump_json(), tx_hash, time.time()),
        )


def is_schedule_published(hash_hex: str) -> bool:
    with _connect() as connection:
        row = connection.execute("SELECT 1 FROM schedules WHERE hash=%s", (hash_hex,)).fetchone()
    return row is not None


def latest_schedule() -> Schedule | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT json FROM schedules ORDER BY version DESC,created_at DESC LIMIT 1"
        ).fetchone()
    return Schedule.model_validate_json(row[0]) if row else None


def save_option(option: RelaxOption) -> None:
    with _connect() as connection:
        connection.execute(
            "INSERT INTO options(id,json) VALUES(%s,%s) ON CONFLICT(id) DO UPDATE SET json=EXCLUDED.json",
            (option.id, option.model_dump_json()),
        )


def get_option(option_id: str) -> RelaxOption:
    with _connect() as connection:
        row = connection.execute("SELECT json FROM options WHERE id=%s", (option_id,)).fetchone()
    if not row:
        raise LookupError(f"Option {option_id} was not found")
    return RelaxOption.model_validate_json(row[0])


def next_option_id() -> str:
    return _next_id("options", "options", r"O(\d+)", "O")


def log_llm_call(fn: str, model: str, tokens_in: int, tokens_out: int, ms: int, mock: bool) -> None:
    with _connect() as connection:
        connection.execute(
            "INSERT INTO llm_calls(fn,model,tokens_in,tokens_out,ms,mock,ts) VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (fn, model, tokens_in, tokens_out, ms, mock, time.time()),
        )


def tokens_since(ts: float) -> int:
    with _connect() as connection:
        row = connection.execute(
            "SELECT COALESCE(SUM(tokens_in+tokens_out),0) FROM llm_calls WHERE ts>=%s", (ts,)
        ).fetchone()
    return int(row[0])


def save_upload(filename: str, data: bytes) -> None:
    if not filename or Path(filename).name != filename or filename in {".", ".."}:
        raise ValueError("invalid upload filename")
    folder = config.UPLOAD_DIR
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    temp = target.with_name(target.name + ".tmp")
    temp.write_bytes(data)
    temp.replace(target)


def get_upload(filename: str) -> bytes | None:
    if not filename or Path(filename).name != filename:
        return None
    path = config.UPLOAD_DIR / filename
    return path.read_bytes() if path.is_file() else None


def get_latest_audit_entry() -> dict | None:
    import json
    with _connect() as connection:
        try:
            row = connection.execute(
                "SELECT id,event,entity_id,user_id,details,prev_hash,entry_hash,created_at FROM audit_events ORDER BY id DESC LIMIT 1"
            ).fetchone()
        except Exception:
            return None
    if not row:
        return None
    return {
        "seq": row[0],
        "event": row[1],
        "entity_id": row[2],
        "actor": row[3],
        "details": json.loads(row[4]) if isinstance(row[4], str) else (row[4] or {}),
        "prev_hash": row[5] or ("0" * 64),
        "entry_hash": row[6] or "",
        "timestamp": row[7],
    }


def insert_ledger_entry(
    seq: int,
    event: str,
    entity_id: str,
    user_id: str,
    details: dict,
    prev_hash: str,
    entry_hash: str,
    created_at: float,
) -> None:
    import json
    with _connect() as connection:
        try:
            connection.execute(
                "INSERT INTO audit_events(id,event,entity_id,user_id,details,prev_hash,entry_hash,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (seq, event, entity_id, user_id, json.dumps(details or {}), prev_hash, entry_hash, created_at),
            )
        except Exception:
            connection.execute(
                "INSERT INTO audit_events(event,entity_id,user_id,details,prev_hash,entry_hash,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (event, entity_id, user_id, json.dumps(details or {}), prev_hash, entry_hash, created_at),
            )


def list_audit_events_extended(event_filter: str | None = None, limit: int = 200) -> list[dict]:
    import json
    with _connect() as connection:
        try:
            if event_filter and event_filter != "ALL":
                rows = connection.execute(
                    "SELECT id,event,entity_id,user_id,details,prev_hash,entry_hash,created_at FROM audit_events WHERE event=%s ORDER BY id DESC LIMIT %s",
                    (event_filter, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT id,event,entity_id,user_id,details,prev_hash,entry_hash,created_at FROM audit_events ORDER BY id DESC LIMIT %s",
                    (limit,),
                ).fetchall()
        except Exception:
            # Fallback if old schema
            rows = connection.execute(
                "SELECT id,event,entity_id,user_id,details,created_at FROM audit_events ORDER BY id DESC LIMIT %s",
                (limit,),
            ).fetchall()
            return [
                {
                    "seq": r[0],
                    "entry_id": f"LE-{r[0]:06d}",
                    "event": r[1],
                    "entity_id": r[2],
                    "actor": r[3],
                    "user": r[3],
                    "details": json.loads(r[4]) if isinstance(r[4], str) else (r[4] or {}),
                    "args": json.loads(r[4]) if isinstance(r[4], str) else (r[4] or {}),
                    "prev_hash": "0" * 64,
                    "entry_hash": "",
                    "timestamp": r[5],
                    "block": r[0],
                    "idx": 0,
                }
                for r in rows
            ]

    results = []
    for row in rows:
        details_dict = json.loads(row[4]) if isinstance(row[4], str) else (row[4] or {})
        prev_h = row[5] if len(row) > 6 and row[5] else ("0" * 64)
        entry_h = row[6] if len(row) > 6 and row[6] else ""
        results.append({
            "seq": row[0],
            "entry_id": f"LE-{row[0]:06d}",
            "event": row[1],
            "entity_id": row[2],
            "actor": row[3],
            "user": row[3],
            "details": details_dict,
            "args": details_dict,
            "prev_hash": prev_h,
            "entry_hash": entry_h,
            "timestamp": row[7] if len(row) > 7 else row[5],
            "block": row[0],
            "idx": 0,
        })
    return results


def list_all_ledger_entries() -> list[dict]:
    import json
    with _connect() as connection:
        try:
            rows = connection.execute(
                "SELECT id,event,entity_id,user_id,details,prev_hash,entry_hash,created_at FROM audit_events ORDER BY id ASC"
            ).fetchall()
        except Exception:
            rows = connection.execute(
                "SELECT id,event,entity_id,user_id,details,created_at FROM audit_events ORDER BY id ASC"
            ).fetchall()
            return [
                {
                    "seq": r[0],
                    "event": r[1],
                    "entity_id": r[2],
                    "actor": r[3],
                    "details": json.loads(r[4]) if isinstance(r[4], str) else (r[4] or {}),
                    "prev_hash": "0" * 64,
                    "entry_hash": "",
                    "timestamp": r[5],
                }
                for r in rows
            ]

    return [
        {
            "seq": row[0],
            "event": row[1],
            "entity_id": row[2],
            "actor": row[3],
            "details": json.loads(row[4]) if isinstance(row[4], str) else (row[4] or {}),
            "prev_hash": row[5] or ("0" * 64),
            "entry_hash": row[6] or "",
            "timestamp": row[7],
        }
        for row in rows
    ]


def log_audit_event(event: str, entity_id: str, user_id: str, details: dict | None = None) -> None:
    from backend.ledger import ledger
    ledger.append(event=event, entity_id=entity_id, actor=user_id, details=details or {})


def list_audit_events() -> list[dict]:
    return list_audit_events_extended()
