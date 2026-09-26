"""Unit tests for utility functions."""

import pytest
from utils.text_cleaner import (
    calculate_reading_stats,
    clean_whitespace,
    format_timestamp,
    normalize_transcript,
    remove_duplicate_spaces,
)


def test_remove_duplicate_spaces():
    assert remove_duplicate_spaces("hello    world") == "hello world"
    assert remove_duplicate_spaces("   a   b   c   ") == " a b c "
    assert remove_duplicate_spaces("") == ""


def test_clean_whitespace():
    raw = "  Line 1   \n\n\n\n   Line 2  with   extra   spaces\n\n\n"
    cleaned = clean_whitespace(raw)
    assert cleaned == "Line 1\n\nLine 2 with extra spaces"
    assert clean_whitespace("") == ""


def test_format_timestamp():
    assert format_timestamp(0) == "00:00"
    assert format_timestamp(45) == "00:45"
    assert format_timestamp(65) == "01:05"
    assert format_timestamp(3665) == "01:01:05"


def test_normalize_transcript_continuous():
    entries = [
        {"text": "Hello world.", "start": 0.0, "duration": 2.0},
        {"text": "Welcome to the lecture.", "start": 2.5, "duration": 3.0},
    ]
    text = normalize_transcript(entries, include_timestamps=False)
    assert text == "Hello world. Welcome to the lecture."


def test_normalize_transcript_timestamped():
    entries = [
        {"text": "First segment.", "start": 0.0, "duration": 5.0},
        {"text": "Second segment.", "start": 35.0, "duration": 5.0},
    ]
    text = normalize_transcript(entries, include_timestamps=True, timestamp_interval_seconds=30.0)
    assert "[00:00] First segment." in text
    assert "[00:35] Second segment." in text


def test_calculate_reading_stats():
    text = "word " * 400
    stats = calculate_reading_stats(text)
    assert stats["word_count"] == 400
    assert stats["reading_time_minutes"] == 2

    empty_stats = calculate_reading_stats("")
    assert empty_stats["word_count"] == 0
    assert empty_stats["reading_time_minutes"] == 0
