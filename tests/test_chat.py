"""Unit tests for Chat service and context selection."""

from unittest.mock import patch
import pytest
from services.chat import (
    answer_question,
    build_chat_context,
    chunk_transcript,
    extract_keywords,
)


def test_extract_keywords():
    query = "What is the primary function of DNA replication in biology?"
    keywords = extract_keywords(query)
    assert "primary" in keywords
    assert "function" in keywords
    assert "dna" in keywords
    assert "replication" in keywords
    assert "biology" in keywords
    # Common stopwords should be excluded
    assert "what" not in keywords
    assert "is" not in keywords
    assert "the" not in keywords
    assert "of" not in keywords
    assert "in" not in keywords


def test_chunk_transcript():
    text = " ".join([f"word{i}" for i in range(100)])
    # Single chunk if small
    chunks = chunk_transcript(text, chunk_words=150, overlap_words=20)
    assert len(chunks) == 1

    # Multiple chunks with overlap
    chunks_split = chunk_transcript(text, chunk_words=40, overlap_words=10)
    assert len(chunks_split) >= 3


def test_build_chat_context_small_transcript():
    short_transcript = "In this lecture, we introduce calculus and derivatives."
    context = build_chat_context(short_transcript, "What is calculus?", max_words=500)
    assert context == short_transcript


def test_build_chat_context_large_transcript():
    part1 = "First part discusses ancient history and Roman architecture. " * 30
    part2 = "Second part focuses strictly on machine learning, neural networks, and backpropagation. " * 30
    part3 = "Third part covers modern cooking techniques. " * 30
    long_transcript = f"{part1} {part2} {part3}"

    context = build_chat_context(long_transcript, "Explain backpropagation and neural networks", max_words=150)
    assert "neural networks" in context.lower()


def test_answer_question_validation():
    # Empty question
    res_empty_q = answer_question("", "Some transcript")
    assert res_empty_q["success"] is False
    assert "empty" in res_empty_q["error"].lower()

    # Empty transcript
    res_empty_t = answer_question("What is gravity?", "")
    assert res_empty_t["success"] is False
    assert "No video transcript" in res_empty_t["answer"]


@patch("services.chat.generate_completion")
def test_answer_question_success(mock_gen):
    mock_gen.return_value = {
        "success": True,
        "content": "According to the video, backpropagation computes the gradient of the loss function.\n\nSource: Current video transcript",
        "model": "qwen2:7b",
        "error": None,
    }

    transcript = "Backpropagation is an algorithm used to calculate gradients."
    res = answer_question("What is backpropagation?", transcript, model="qwen2:7b")
    assert res["success"] is True
    assert "backpropagation computes the gradient" in res["answer"]
    assert res["source"] == "Current video transcript"


def test_query_requires_web_research_comparative():
    from services.chat import query_requires_web_research, generate_search_queries
    q1 = "are there any battles which took place the same year in which the battle of plassey took place"
    assert query_requires_web_research(q1) is True

    q2 = "what else happened during the same era?"
    assert query_requires_web_research(q2) is True

    q3 = "what is the formula for area of circle"
    assert query_requires_web_research(q3) is False

    # Test query optimization
    transcript = "The Battle of Plassey took place on 23 June 1757 in Bengal."
    optimized = generate_search_queries(q1, transcript=transcript)
    assert any("1757" in q for q in optimized)
    assert any("battles" in q.lower() for q in optimized)


@patch("services.chat.search_web")
@patch("services.chat.generate_completion")
def test_answer_question_dynamic_web_fallback(mock_gen, mock_search):
    # Test that web search is dynamically triggered when transcript is insufficient
    mock_search.return_value = [
        {"title": "Battles of 1757", "url": "https://example.com/1757", "snippet": "Battle of Rossbach and Battle of Leuthen occurred in 1757."}
    ]
    mock_gen.return_value = {
        "success": True,
        "content": "In 1757, alongside the Battle of Plassey, other major battles included the Battle of Rossbach and the Battle of Leuthen.\n\nSources:\n- Battles of 1757 (https://example.com/1757)",
        "model": "qwen2:7b",
        "error": None,
    }

    transcript = "The Battle of Plassey was fought on June 23, 1757."
    res = answer_question(
        question="are there any battles which took place the same year in which the battle of plassey took place",
        transcript=transcript,
        mode="Video + Web Research",
    )

    assert res["success"] is True
    assert res["source_type"] == "web"
    assert "Battle of Rossbach" in res["answer"]
    assert len(res["search_results"]) == 1
    assert res["search_results"][0]["title"] == "Battles of 1757"
    assert mock_search.called


@patch("services.chat.search_web")
@patch("services.chat.generate_completion")
def test_answer_question_reactive_fallback(mock_gen, mock_search):
    # Test that even if a query looks like it is about the video, if the generated transcript
    # response states the video lacks information, it reactively triggers web search
    mock_search.return_value = [
        {"title": "Plassey Casualties", "url": "https://example.com/casualties", "snippet": "The British lost 22 soldiers while the Nawab lost around 500."}
    ]
    mock_gen.side_effect = [
        # Call 1: Video transcript cannot answer
        {
            "success": True,
            "content": "The video transcript does not provide information about the exact casualty numbers.",
            "model": "qwen2:7b",
            "error": None,
        },
        # Call 2: Web research fallback synthesis answer
        {
            "success": True,
            "content": "According to external records, the British lost approximately 22 men while the Nawab suffered around 500 casualties.\n\nSources:\n- Plassey Casualties (https://example.com/casualties)",
            "model": "qwen2:7b",
            "error": None,
        },
    ]

    # Transcript mentions battle, plassey, casualty, numbers so check_transcript_sufficiency passes
    transcript = "The Battle of Plassey battle casualty numbers were significant in Indian history."
    res = answer_question(
        question="What were the battle casualty numbers in Plassey?",
        transcript=transcript,
        mode="Video + Web Research",
    )

    assert res["success"] is True
    assert res["source_type"] == "web"
    assert "22 men" in res["answer"]
    assert mock_search.called
