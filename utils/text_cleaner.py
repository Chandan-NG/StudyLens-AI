"""Text cleaning and formatting utilities for StudyLens AI."""

import re
from typing import Any, Dict, List, Union


def remove_duplicate_spaces(text: str) -> str:
    """Replace consecutive whitespace characters with a single space."""
    if not text:
        return ""
    return re.sub(r"[ \t]+", " ", text)


def clean_whitespace(text: str) -> str:
    """Normalize whitespace and strip unnecessary leading/trailing spaces across lines."""
    if not text:
        return ""
    # Normalize newline characters
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Clean per line
    lines = [remove_duplicate_spaces(line).strip() for line in text.split("\n")]
    # Remove multiple consecutive blank lines
    cleaned = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def format_timestamp(seconds: float) -> str:
    """Convert seconds into HH:MM:SS or MM:SS format."""
    total_seconds = int(max(0, seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def normalize_transcript(
    entries: List[Union[Dict[str, Any], Any]],
    include_timestamps: bool = False,
    timestamp_interval_seconds: float = 30.0,
) -> str:
    """
    Convert raw transcript snippets into clean, human-readable continuous text.
    
    If include_timestamps is True, groups lines by timestamp intervals.
    """
    if not entries:
        return ""

    if not include_timestamps:
        text_parts = []
        for item in entries:
            # Handle both dataclass and dictionary objects
            text = item.get("text", "") if isinstance(item, dict) else getattr(item, "text", "")
            # Remove line breaks within individual subtitle snippets
            text = text.replace("\n", " ").strip()
            if text:
                text_parts.append(text)

        full_text = " ".join(text_parts)
        return clean_whitespace(full_text)

    # With timestamps: group into natural segments
    formatted_blocks = []
    current_block_texts: List[str] = []
    current_block_start: float = 0.0
    first_item = True

    for item in entries:
        text = item.get("text", "") if isinstance(item, dict) else getattr(item, "text", "")
        start = float(item.get("start", 0.0) if isinstance(item, dict) else getattr(item, "start", 0.0))
        text = text.replace("\n", " ").strip()
        if not text:
            continue

        if first_item:
            current_block_start = start
            first_item = False

        if start - current_block_start >= timestamp_interval_seconds and current_block_texts:
            timestamp_str = format_timestamp(current_block_start)
            block_content = remove_duplicate_spaces(" ".join(current_block_texts))
            formatted_blocks.append(f"[{timestamp_str}] {block_content}")
            current_block_texts = [text]
            current_block_start = start
        else:
            current_block_texts.append(text)

    if current_block_texts:
        timestamp_str = format_timestamp(current_block_start)
        block_content = remove_duplicate_spaces(" ".join(current_block_texts))
        formatted_blocks.append(f"[{timestamp_str}] {block_content}")

    return "\n\n".join(formatted_blocks)


def calculate_reading_stats(text: str) -> Dict[str, Any]:
    """Calculate word count, character count, and estimated reading time."""
    if not text:
        return {
            "word_count": 0,
            "char_count": 0,
            "reading_time_minutes": 0,
        }

    words = text.split()
    word_count = len(words)
    char_count = len(text)
    # Average reading speed: 200 words per minute
    reading_time = max(1, round(word_count / 200)) if word_count > 0 else 0

    return {
        "word_count": word_count,
        "char_count": char_count,
        "reading_time_minutes": reading_time,
    }
