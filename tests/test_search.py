"""Unit tests for DuckDuckGo web search service."""

from unittest.mock import MagicMock, patch
import pytest
from services.search import format_search_results_for_llm, search_web
from services.chat import (
    answer_question,
    check_transcript_sufficiency,
    query_requires_web_research,
)


def test_search_web_empty_query():
    assert search_web("") == []
    assert search_web("   ") == []


def test_format_search_results_for_llm():
    sample_results = [
        {"title": "Python Docs", "url": "https://python.org", "snippet": "Official site"},
        {"title": "Tutorial", "url": "https://learnpython.org", "snippet": "Interactive courses"},
    ]
    formatted = format_search_results_for_llm(sample_results)
    assert "[1] Title: Python Docs" in formatted
    assert "https://python.org" in formatted
    assert "[2] Title: Tutorial" in formatted

    empty_formatted = format_search_results_for_llm([])
    assert "No external web search results found." in empty_formatted


def test_transcript_sufficiency():
    transcript = "In this lecture, we explore Newton's second law: Force equals mass times acceleration."
    # Covered
    assert check_transcript_sufficiency(transcript, "What is Newton's second law?") is True
    # Not covered
    assert check_transcript_sufficiency(transcript, "Who was the CEO of OpenAI in 2024?") is False


def test_query_requires_web_research():
    assert query_requires_web_research("Search the web for latest quantum computing papers") is True
    assert query_requires_web_research("What are the recent news about AI?") is True
    assert query_requires_web_research("Explain what the professor said about gravity") is False


@patch("services.chat.search_web")
@patch("services.chat.generate_completion")
def test_answer_question_web_research_mode(mock_gen, mock_search):
    mock_search.return_value = [
        {"title": "Latest Discovery", "url": "https://example.com/news", "snippet": "New astronomy discoveries."}
    ]
    mock_gen.return_value = {
        "success": True,
        "content": "**Answer**: New exoplanets were discovered.\n\n**Sources**:\n- Latest Discovery",
        "model": "qwen2:7b",
        "error": None,
    }

    transcript = "This video is about baking bread."
    question = "Search the web for latest astronomy news"
    res = answer_question(
        question=question,
        transcript=transcript,
        mode="Video + Web Research",
        model="qwen2:7b",
    )
    assert res["success"] is True
    assert res["source_type"] == "web"
    assert res["source"] == "Additional web research used"
    assert len(res["search_results"]) == 1
