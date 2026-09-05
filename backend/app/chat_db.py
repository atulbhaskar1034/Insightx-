"""
chat_db.py -- SQLite/PostgreSQL-backed chat session storage for InsightX.

Falls back to SQLite for local development. Uses psycopg2 with CONNECTION POOLING
for PostgreSQL if DATABASE_URL is present.

Performance improvement: Replaces per-request psycopg2.connect() (which opened a new
TCP+TLS connection every single call) with a persistent SimpleConnectionPool that
reuses connections across requests — eliminating ~150ms overhead per DB operation.
"""

import os
import json
import uuid
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    # Strip channel_binding if present to prevent libpq negotiation issues
    if "&channel_binding=require" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("&channel_binding=require", "")
    elif "?channel_binding=require&" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("channel_binding=require&", "")
    elif "?channel_binding=require" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("?channel_binding=require", "")

IS_POSTGRES = bool(DATABASE_URL and DATABASE_URL.startswith("postgresql://"))

if IS_POSTGRES:
    import psycopg2
    from psycopg2 import pool as pg_pool
    from psycopg2.extras import RealDictCursor

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "chat_history.db"

# ── Connection Pool (Postgres only) ───────────────────────────────────────────
# Instead of opening/closing a raw TCP connection for every single DB call,
# maintain a persistent pool of 1-5 connections that are reused across requests.

_pg_pool = None


def _get_pg_pool():
    """Lazily initialize and return the PostgreSQL connection pool."""
    global _pg_pool
    if _pg_pool is None or _pg_pool.closed:
        _pg_pool = pg_pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=DATABASE_URL,
        )
    return _pg_pool


class DBConn:
    """Context manager to abstract Postgres/SQLite differences.

    For Postgres: Gets a connection from the pool and returns it when done.
    For SQLite: Opens and closes a connection as before (SQLite is local, no TCP overhead).
    """
    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        if IS_POSTGRES:
            pool = _get_pg_pool()
            self.conn = pool.getconn()
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        else:
            DB_DIR.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(DB_PATH))
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
            self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.cursor.close()
            if IS_POSTGRES:
                # Return connection to pool instead of closing it
                pool = _get_pg_pool()
                pool.putconn(self.conn)
            else:
                self.conn.close()

    def execute(self, query, params=()):
        if IS_POSTGRES:
            query = query.replace("?", "%s")
            # SQLite AUTOINCREMENT is SERIAL in Postgres
            query = query.replace("AUTOINCREMENT", "")
            query = query.replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY")
        self.cursor.execute(query, params)
        return self.cursor

    def fetchall(self):
        return self.cursor.fetchall()
        
    @property
    def lastrowid(self):
        if IS_POSTGRES:
            # Requires RETURNING id on INSERT
            row = self.cursor.fetchone()
            return row["id"] if row else None
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount


def init_db() -> None:
    """Create tables if they don't exist."""
    with DBConn() as db:
        if IS_POSTGRES:
            db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id         TEXT PRIMARY KEY,
                    title      TEXT NOT NULL DEFAULT 'New chat',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id         SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    role       TEXT NOT NULL,
                    content    TEXT NOT NULL DEFAULT '',
                    sql_text   TEXT DEFAULT '',
                    data_json  TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            """)
        else:
            db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id         TEXT PRIMARY KEY,
                    title      TEXT NOT NULL DEFAULT 'New chat',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    role       TEXT NOT NULL,
                    content    TEXT NOT NULL DEFAULT '',
                    sql_text   TEXT DEFAULT '',
                    data_json  TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            """)


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(title: str = "New chat") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    sid = uuid.uuid4().hex[:12]
    with DBConn() as db:
        db.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (sid, title, now, now),
        )
    return {"id": sid, "title": title, "created_at": now, "updated_at": now}


def list_sessions(limit: int = 50) -> list[dict]:
    with DBConn() as db:
        db.execute(
            "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        rows = db.fetchall()
    return [dict(r) for r in rows]


def delete_session(session_id: str) -> bool:
    with DBConn() as db:
        db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return db.rowcount > 0


def update_session_title(session_id: str, title: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with DBConn() as db:
        db.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, session_id),
        )


def _touch_session(session_id: str) -> None:
    """Bump updated_at for a session."""
    now = datetime.now(timezone.utc).isoformat()
    with DBConn() as db:
        db.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )


# ── Messages ──────────────────────────────────────────────────────────────────

def add_message(
    session_id: str,
    role: str,
    content: str,
    sql_text: str = "",
    data_json: str = "{}",
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with DBConn() as db:
        if IS_POSTGRES:
            query = """INSERT INTO messages (session_id, role, content, sql_text, data_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?) RETURNING id"""
        else:
            query = """INSERT INTO messages (session_id, role, content, sql_text, data_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)"""
                       
        db.execute(
            query,
            (session_id, role, content, sql_text, data_json, now),
        )
        row_id = db.lastrowid
        
        # Bump session updated_at
        db.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
    return row_id  # type: ignore


def get_messages(session_id: str) -> list[dict]:
    with DBConn() as db:
        db.execute(
            """SELECT id, role, content, sql_text, data_json, created_at
               FROM messages WHERE session_id = ? ORDER BY id ASC""",
            (session_id,),
        )
        rows = db.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["data"] = json.loads(d.pop("data_json"))
        except (json.JSONDecodeError, KeyError):
            d["data"] = {}
            d.pop("data_json", None)
        result.append(d)
    return result


def auto_title(session_id: str, first_question: str) -> None:
    """Set session title from the first user question (truncated)."""
    title = first_question.strip()[:60]
    if len(first_question.strip()) > 60:
        title += "..."
    update_session_title(session_id, title)

