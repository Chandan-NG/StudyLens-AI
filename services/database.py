"""SQLite database service for local persistence of study sessions."""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


DEFAULT_DB_PATH = os.path.join("data", "studylens.db")


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Ensure directory exists and return SQLite connection with Row factory."""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize SQLite database and create study_sessions table if it doesn't exist."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL UNIQUE,
                video_url TEXT NOT NULL,
                title TEXT,
                created_at TEXT NOT NULL,
                transcript TEXT,
                summary TEXT,
                notes TEXT,
                quiz_json TEXT
            );
            """
        )
        conn.commit()


def save_or_update_session(
    video_id: str,
    video_url: Optional[str] = None,
    title: Optional[str] = None,
    transcript: Optional[str] = None,
    summary: Optional[str] = None,
    notes: Optional[str] = None,
    quiz_data: Optional[Any] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> bool:
    """Insert or update a study session in the SQLite database."""
    if not video_id:
        return False

    init_db(db_path)
    quiz_json_str = None
    if quiz_data is not None:
        if isinstance(quiz_data, str):
            quiz_json_str = quiz_data
        else:
            try:
                quiz_json_str = json.dumps(quiz_data)
            except Exception:
                quiz_json_str = None

    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_title = title or f"YouTube Video ({video_id})"
    effective_url = video_url or f"https://www.youtube.com/watch?v={video_id}"

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO study_sessions (video_id, video_url, title, created_at, transcript, summary, notes, quiz_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                video_url=COALESCE(NULLIF(excluded.video_url, ''), study_sessions.video_url),
                title=COALESCE(excluded.title, study_sessions.title),
                transcript=COALESCE(excluded.transcript, study_sessions.transcript),
                summary=COALESCE(excluded.summary, study_sessions.summary),
                notes=COALESCE(excluded.notes, study_sessions.notes),
                quiz_json=COALESCE(excluded.quiz_json, study_sessions.quiz_json);
            """,
            (video_id, effective_url, clean_title, now_iso, transcript, summary, notes, quiz_json_str),
        )
        conn.commit()
        return True


def get_session_by_video_id(video_id: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve a single study session by its YouTube video ID."""
    if not video_id:
        return None

    init_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM study_sessions WHERE video_id = ? LIMIT 1;",
            (video_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        result = dict(row)
        if result.get("quiz_json"):
            try:
                result["quiz_data"] = json.loads(result["quiz_json"])
            except Exception:
                result["quiz_data"] = None
        else:
            result["quiz_data"] = None

        return result


def list_all_sessions(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """List all saved study sessions ordered by newest first."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, video_id, video_url, title, created_at, "
            "CASE WHEN summary IS NOT NULL AND length(summary) > 0 THEN 1 ELSE 0 END AS has_summary, "
            "CASE WHEN notes IS NOT NULL AND length(notes) > 0 THEN 1 ELSE 0 END AS has_notes, "
            "CASE WHEN quiz_json IS NOT NULL AND length(quiz_json) > 0 THEN 1 ELSE 0 END AS has_quiz "
            "FROM study_sessions ORDER BY id DESC;"
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def delete_session_by_video_id(video_id: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Delete a saved session by video ID."""
    if not video_id:
        return False

    init_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM study_sessions WHERE video_id = ?;", (video_id,))
        conn.commit()
        return cursor.rowcount > 0
