"""Unit tests for YouTube service."""

import pytest
from services.youtube import get_video_id, get_video_transcript


def test_get_video_id_valid_formats():
    urls = {
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "http://www.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://www.youtube.com/watch?feature=share&v=dQw4w9WgXcQ&t=12s": "dQw4w9WgXcQ",
        "dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "  https://youtu.be/dQw4w9WgXcQ  ": "dQw4w9WgXcQ",
    }
    for url, expected_id in urls.items():
        assert get_video_id(url) == expected_id, f"Failed for {url}"


def test_get_video_id_invalid_formats():
    invalid_inputs = [
        "",
        None,
        "https://example.com/not-youtube",
        "https://youtube.com/watch",
        "https://youtu.be/",
        "short",
        "1234567890",  # 10 chars, not 11
        "https://youtube.com/watch?v=short",
    ]
    for inp in invalid_inputs:
        assert get_video_id(inp) is None, f"Expected None for {inp}"


def test_get_video_transcript_invalid_url():
    result = get_video_transcript("https://invalid.com/test")
    assert result["success"] is False
    assert result["video_id"] is None
    assert "Invalid YouTube URL" in result["error"]


def test_get_video_transcript_nonexistent_video():
    # Non-existent 11-char ID
    result = get_video_transcript("https://www.youtube.com/watch?v=00000000000")
    assert result["success"] is False
    assert result["video_id"] == "00000000000"
    assert result["error"] is not None
