"""Unit tests for Quiz generator and validation service."""

from unittest.mock import patch
import pytest
from services.quiz import (
    QuizQuestion,
    generate_quiz,
    normalize_question_data,
    parse_json_from_llm,
    validate_and_parse_quiz,
)


def test_parse_json_from_llm():
    # Direct JSON
    raw = '{"key": "value"}'
    assert parse_json_from_llm(raw) == {"key": "value"}

    # Wrapped in markdown
    raw_md = "```json\n{\"test\": 123}\n```"
    assert parse_json_from_llm(raw_md) == {"test": 123}

    # Wrapped with commentary
    raw_commentary = "Here is your JSON:\n```json\n{\"a\": [1, 2]}\n```\nHope you like it!"
    assert parse_json_from_llm(raw_commentary) == {"a": [1, 2]}

    # Invalid JSON
    assert parse_json_from_llm("not valid json") is None
    assert parse_json_from_llm("") is None


def test_normalize_question_data():
    valid_raw = {
        "question": "What is 2+2?",
        "options": ["1", "2", "3", "4"],
        "correct_answer": 3,
        "explanation": "2+2 equals 4.",
    }
    normalized = normalize_question_data(valid_raw)
    assert normalized is not None
    assert normalized["correct_answer"] == 3

    # Letter answer
    letter_raw = {
        "question": "What is the capital of France?",
        "options": ["London", "Paris", "Berlin", "Madrid"],
        "correct_answer": "B",
        "explanation": "Paris is the capital.",
    }
    normalized_letter = normalize_question_data(letter_raw)
    assert normalized_letter is not None
    assert normalized_letter["correct_answer"] == 1

    # Insufficient options
    invalid_options = {
        "question": "Incomplete?",
        "options": ["Single option"],
        "correct_answer": 0,
    }
    assert normalize_question_data(invalid_options) is None


def test_validate_and_parse_quiz_valid():
    payload = """
    {
        "questions": [
            {
                "question": "Which particle has a negative charge?",
                "options": ["Proton", "Neutron", "Electron", "Photon"],
                "correct_answer": 2,
                "explanation": "Electrons have a negative charge."
            }
        ]
    }
    """
    questions = validate_and_parse_quiz(payload)
    assert len(questions) == 1
    assert questions[0]["question"] == "Which particle has a negative charge?"
    assert questions[0]["correct_answer"] == 2


def test_validate_and_parse_quiz_invalid():
    with pytest.raises(ValueError):
        validate_and_parse_quiz("{\"random\": 123}")

    with pytest.raises(ValueError):
        validate_and_parse_quiz("not json")


@patch("services.quiz.generate_completion")
def test_generate_quiz_success(mock_gen):
    mock_gen.return_value = {
        "success": True,
        "content": '{"questions": [{"question": "Q1", "options": ["A", "B", "C", "D"], "correct_answer": 0, "explanation": "Exp"}]}',
        "model": "qwen2:7b",
        "error": None,
    }
    res = generate_quiz("Lecture transcript...", model="qwen2:7b")
    assert res["success"] is True
    assert len(res["questions"]) == 1
    assert res["questions"][0]["question"] == "Q1"
