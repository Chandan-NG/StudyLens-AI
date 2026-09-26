"""Unit tests for SQLite persistence service."""

import os
import pytest
from services.database import (
    delete_session_by_video_id,
    get_session_by_video_id,
    init_db,
    list_all_sessions,
    save_or_update_session,
)


@pytest.fixture
def temp_db(tmp_path):
    """Fixture providing a clean temporary SQLite database path."""
    db_file = tmp_path / "test_studylens.db"
    return str(db_file)


def test_init_and_save_session(temp_db):
    init_db(temp_db)
    success = save_or_update_session(
        video_id="dQw4w9WgXcQ",
        video_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        title="Never Gonna Give You Up",
        transcript="We're no strangers to love...",
        summary="Classic music video summary.",
        notes="Music theory notes.",
        quiz_data=[{"question": "Who sings?", "options": ["A", "B"], "correct_answer": 0, "explanation": "Rick"}],
        db_path=temp_db,
    )
    assert success is True

    # Retrieve
    session = get_session_by_video_id("dQw4w9WgXcQ", db_path=temp_db)
    assert session is not None
    assert session["video_id"] == "dQw4w9WgXcQ"
    assert session["title"] == "Never Gonna Give You Up"
    assert session["summary"] == "Classic music video summary."
    assert session["quiz_data"] is not None
    assert len(session["quiz_data"]) == 1


def test_update_existing_session(temp_db):
    save_or_update_session(
        video_id="video12345",
        video_url="https://youtube.com/watch?v=video12345",
        transcript="Initial transcript",
        db_path=temp_db,
    )
    # Update notes later
    save_or_update_session(
        video_id="video12345",
        video_url="https://youtube.com/watch?v=video12345",
        notes="Newly generated notes.",
        db_path=temp_db,
    )
    session = get_session_by_video_id("video12345", db_path=temp_db)
    assert session["transcript"] == "Initial transcript"
    assert session["notes"] == "Newly generated notes."


def test_list_and_delete_sessions(temp_db):
    save_or_update_session("vid_1", "https://yt.com/1", title="Title 1", db_path=temp_db)
    save_or_update_session("vid_2", "https://yt.com/2", title="Title 2", db_path=temp_db)

    sessions = list_all_sessions(db_path=temp_db)
    assert len(sessions) == 2

    # Delete vid_1
    deleted = delete_session_by_video_id("vid_1", db_path=temp_db)
    assert deleted is True

    sessions_after = list_all_sessions(db_path=temp_db)
    assert len(sessions_after) == 1
    assert sessions_after[0]["video_id"] == "vid_2"
