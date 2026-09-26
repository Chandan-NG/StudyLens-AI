"""Unit tests for LLM, Summarizer, and Notes services."""

from unittest.mock import MagicMock, patch
import pytest
from services.llm import generate_completion, check_ollama_available
from services.summarizer import generate_summary
from services.notes import generate_notes
from utils.prompts import SUMMARY_PROMPT, NOTES_PROMPT


def test_prompts_formatting():
    s_prompt = SUMMARY_PROMPT.format(transcript="Sample transcript text")
    assert "Sample transcript text" in s_prompt
    assert "# Executive Summary" in s_prompt

    n_prompt = NOTES_PROMPT.format(topic="Quantum Physics", transcript="Sample transcript text")
    assert "Quantum Physics" in n_prompt
    assert "Sample transcript text" in n_prompt
    assert "## 1. Introduction" in n_prompt


def test_empty_inputs():
    # LLM service with empty prompt
    res = generate_completion("")
    assert res["success"] is False
    assert "empty" in res["error"].lower()

    # Summarizer with empty transcript
    s_res = generate_summary("")
    assert s_res["success"] is False
    assert "No transcript" in s_res["error"]

    # Notes with empty transcript
    n_res = generate_notes("")
    assert n_res["success"] is False
    assert "No transcript" in n_res["error"]


@patch("services.llm.check_ollama_available")
@patch("ollama.Client")
def test_generate_completion_success(mock_client_cls, mock_check):
    mock_check.return_value = (True, ["qwen2:7b"])
    mock_instance = MagicMock()
    mock_instance.chat.return_value = {
        "message": {"content": "This is a test response from LLM."}
    }
    mock_client_cls.return_value = mock_instance

    res = generate_completion("Test prompt", model="qwen2:7b")
    assert res["success"] is True
    assert res["content"] == "This is a test response from LLM."
    assert res["model"] == "qwen2:7b"
    assert res["error"] is None


@patch("services.llm.check_ollama_available")
def test_generate_completion_server_offline(mock_check):
    mock_check.return_value = (False, [])
    res = generate_completion("Test prompt", model="qwen2:7b")
    assert res["success"] is False
    assert "Cannot connect to Ollama" in res["error"]


@patch("services.summarizer.generate_completion")
def test_generate_summary_success(mock_gen):
    mock_gen.return_value = {
        "success": True,
        "content": "# Executive Summary\nLecture summary content.",
        "model": "qwen2:7b",
        "error": None,
    }
    res = generate_summary("Valid lecture transcript text.", model="qwen2:7b")
    assert res["success"] is True
    assert "# Executive Summary" in res["summary"]


@patch("services.notes.generate_completion")
def test_generate_notes_success(mock_gen):
    mock_gen.return_value = {
        "success": True,
        "content": "# Study Notes: Python Decorators\nDetailed notes content.",
        "model": "qwen2:7b",
        "error": None,
    }
    res = generate_notes("Valid lecture transcript text.", topic="Python Decorators", model="qwen2:7b")
    assert res["success"] is True
    assert "Study Notes: Python Decorators" in res["notes"]
