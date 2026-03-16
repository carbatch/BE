import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "storage" / "carbatch.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL DEFAULT '새 채팅',
                created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS generations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id     INTEGER REFERENCES pages(id) ON DELETE CASCADE,
                prompt_id   TEXT    NOT NULL,
                prompt_text TEXT    NOT NULL,
                model       TEXT    NOT NULL,
                image_paths TEXT    NOT NULL DEFAULT '[]',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)
        # 마이그레이션: 기존 테이블에 없는 컬럼 추가
        for col_sql in [
            "ALTER TABLE generations ADD COLUMN page_id INTEGER REFERENCES pages(id) ON DELETE CASCADE",
            "ALTER TABLE generations ADD COLUMN status TEXT NOT NULL DEFAULT 'done'",
            "ALTER TABLE generations ADD COLUMN error_msg TEXT",
            "ALTER TABLE generations ADD COLUMN gen_count INTEGER NOT NULL DEFAULT 2",
            "ALTER TABLE pages ADD COLUMN user_id INTEGER REFERENCES users(id)",
        ]:
            try:
                conn.execute(col_sql)
            except Exception:
                pass
        # 서버 재시작 시 stuck 상태 초기화
        conn.execute(
            "UPDATE generations SET status='error', error_msg='서버 재시작으로 인해 중단됨' "
            "WHERE status IN ('pending', 'running')"
        )
        conn.commit()


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


# ── Users ──────────────────────────────────────────────────────────────────

def create_user(username: str, password_hash: str) -> dict:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        conn.commit()
        row = conn.execute("SELECT id, username, created_at FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


def get_user_by_username(username: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, created_at FROM users WHERE username = ?", (username,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


# ── Pages ──────────────────────────────────────────────────────────────────

def create_page(title: str = "새 채팅", user_id: int | None = None) -> dict:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO pages (title, user_id) VALUES (?, ?)", (title, user_id)
        )
        conn.commit()
        page_id = cur.lastrowid
        row = conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
        return dict(row)


def list_pages(user_id: int | None = None) -> list[dict]:
    with _conn() as conn:
        if user_id is not None:
            rows = conn.execute(
                "SELECT * FROM pages WHERE user_id = ? ORDER BY id DESC", (user_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM pages ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def get_page(page_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
    return dict(row) if row else None


def rename_page(page_id: int, title: str):
    with _conn() as conn:
        conn.execute("UPDATE pages SET title = ? WHERE id = ?", (title, page_id))
        conn.commit()


def delete_page(page_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM pages WHERE id = ?", (page_id,))
        conn.commit()


# ── Generations ────────────────────────────────────────────────────────────

def create_generation_pending(
    prompt_id: str,
    prompt_text: str,
    model: str,
    page_id: int | None,
    gen_count: int = 2,
) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO generations (page_id, prompt_id, prompt_text, model, image_paths, status, gen_count) "
            "VALUES (?, ?, ?, ?, '[]', 'pending', ?)",
            (page_id, prompt_id, prompt_text, model, gen_count),
        )
        conn.commit()
        return cur.lastrowid


def update_generation_running(prompt_id: str):
    with _conn() as conn:
        conn.execute("UPDATE generations SET status='running' WHERE prompt_id=?", (prompt_id,))
        conn.commit()


def update_generation_done(prompt_id: str, image_paths: list[str]):
    with _conn() as conn:
        conn.execute(
            "UPDATE generations SET status='done', image_paths=? WHERE prompt_id=?",
            (json.dumps(image_paths), prompt_id),
        )
        conn.commit()


def update_generation_error(prompt_id: str, error_msg: str):
    with _conn() as conn:
        conn.execute(
            "UPDATE generations SET status='error', error_msg=? WHERE prompt_id=?",
            (error_msg, prompt_id),
        )
        conn.commit()


def get_generation_by_prompt_id(prompt_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM generations WHERE prompt_id=? ORDER BY id DESC LIMIT 1",
            (prompt_id,),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["image_paths"] = json.loads(d["image_paths"])
    return d


def save_generation(
    prompt_id: str,
    prompt_text: str,
    model: str,
    image_paths: list[str],
    page_id: int | None = None,
) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO generations (page_id, prompt_id, prompt_text, model, image_paths, status) VALUES (?, ?, ?, ?, ?, 'done')",
            (page_id, prompt_id, prompt_text, model, json.dumps(image_paths)),
        )
        conn.commit()
        return cur.lastrowid


def get_page_generations(page_id: int) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM generations WHERE page_id = ? ORDER BY id ASC",
            (page_id,),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["image_paths"] = json.loads(d["image_paths"])
        result.append(d)
    return result


def get_generation(generation_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM generations WHERE id = ?", (generation_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["image_paths"] = json.loads(d["image_paths"])
    return d


def get_history(limit: int = 50, offset: int = 0) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM generations ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["image_paths"] = json.loads(d["image_paths"])
        result.append(d)
    return result
