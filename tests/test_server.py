"""Unit tests for FastAPI backend server endpoints."""

from fastapi.testclient import TestClient
from unittest.mock import patch
import pytest

from server import app

client = TestClient(app)


def test_root_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "StudyLens AI" in response.text
    # Verify required Bootstrap icons are present in the HTML template
    assert "bi-mortarboard-fill" in response.text
    assert "bi-journal-text" in response.text
    assert "bi-pencil-square" in response.text
    assert "bi-stickies" in response.text
    assert "bi-ui-checks-grid" in response.text
    assert "bi-chat-dots" in response.text
    assert "bi-clock-history" in response.text
    assert "bi-gear" in response.text
    assert "bi-tv" in response.text


def test_get_settings():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "ollama_host" in data
    assert "ollama_model" in data
    assert "web_research_enabled" in data


def test_update_settings():
    payload = {"model": "qwen2:7b", "web_research_enabled": True}
    response = client.post("/api/settings", json=payload)
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_load_video_empty():
    response = client.post("/api/video/load", json={"url": "   "})
    assert response.status_code == 400


@patch("server.get_video_transcript")
def test_load_video_success(mock_transcript):
    mock_transcript.return_value = {
        "success": True,
        "video_id": "test_123",
        "url": "https://www.youtube.com/watch?v=test_123",
        "clean_text": "This is a lecture transcript about physics and gravity.",
        "timestamped_text": "[00:00] Physics lecture begins.",
        "stats": {
            "word_count": 9,
            "char_count": 55,
            "reading_time_minutes": 1,
        }
    }

    response = client.post("/api/video/load", json={"url": "https://www.youtube.com/watch?v=test_123"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["video_id"] == "test_123"
    assert "clean_transcript" in data


def test_chat_empty_question():
    response = client.post("/api/chat", json={"question": "", "transcript": "some text"})
    assert response.status_code == 400


@patch("server.answer_question")
def test_chat_success(mock_answer):
    mock_answer.return_value = {
        "success": True,
        "answer": "Gravity is an attractive force between masses.",
        "source_type": "video",
        "source": "Current video transcript",
        "search_results": [],
        "model": "qwen2:7b",
        "error": None,
    }

    payload = {
        "question": "What is gravity?",
        "transcript": "Gravity pulls objects together.",
        "mode": "Video Only",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Gravity is an attractive force" in data["answer"]


def test_get_history():
    response = client.get("/api/history")
    assert response.status_code == 200
    assert "sessions" in response.json()
