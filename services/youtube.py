"""YouTube service for URL validation and transcript extraction."""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

try:
    from youtube_transcript_api import (
        CouldNotRetrieveTranscript,
        NoTranscriptFound,
        TranscriptsDisabled,
        YouTubeTranscriptApi,
    )
    # Check for VideoUnavailable which may reside in _errors
    try:
        from youtube_transcript_api._errors import VideoUnavailable
    except ImportError:
        VideoUnavailable = Exception
except ImportError:
    YouTubeTranscriptApi = None
    CouldNotRetrieveTranscript = Exception
    NoTranscriptFound = Exception
    TranscriptsDisabled = Exception
    VideoUnavailable = Exception

from utils.text_cleaner import (
    calculate_reading_stats,
    clean_whitespace,
    normalize_transcript,
)


YOUTUBE_REGEX = re.compile(
    r"(?:https?://)?"
    r"(?:www\.|m\.)?"
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|v/|shorts/)|youtu\.be/)"
    r"([a-zA-Z0-9_-]{11})"
)

ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def get_video_id(url: str) -> Optional[str]:
    """
    Extract the 11-character YouTube video ID from various URL formats.
    Returns None if the URL does not contain a valid ID.
    """
    if not url or not isinstance(url, str):
        return None

    cleaned_url = url.strip()

    # Check if raw 11-char ID was passed
    if ID_REGEX.match(cleaned_url):
        return cleaned_url

    # Check regex match across standard YouTube URL patterns
    match = YOUTUBE_REGEX.search(cleaned_url)
    if match:
        return match.group(1)

    # Fallback to query param parsing
    try:
        parsed = urlparse(cleaned_url)
        if "youtube.com" in parsed.netloc:
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                candidate = qs["v"][0]
                if ID_REGEX.match(candidate):
                    return candidate
    except Exception:
        pass

    return None


def clean_transcript(raw_entries: List[Any], include_timestamps: bool = False) -> str:
    """Clean and normalize transcript entries into continuous text or timestamped blocks."""
    return normalize_transcript(raw_entries, include_timestamps=include_timestamps)


def get_transcript(
    video_id: str,
    languages: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch the transcript entries for a given video ID using youtube-transcript-api.
    Returns a list of standardized dicts: {'text': str, 'start': float, 'duration': float}.
    Raises appropriate exceptions if unavailable.
    """
    if not video_id:
        raise ValueError("Video ID is required.")

    if YouTubeTranscriptApi is None:
        raise RuntimeError("youtube-transcript-api is not installed.")

    target_languages = languages or ["en", "en-US", "en-GB", "en-CA", "en-AU"]

    # Support both new (1.2+) instance-based API and legacy classmethod API
    raw_snippets = None
    try:
        api = YouTubeTranscriptApi()
        try:
            transcript_list = api.list(video_id)
            try:
                transcript_obj = transcript_list.find_transcript(target_languages)
            except Exception:
                # If target languages aren't found, fallback to first available transcript
                transcript_obj = next(iter(transcript_list))
            raw_snippets = transcript_obj.fetch()
        except AttributeError:
            # Legacy classmethod fallback
            raw_snippets = YouTubeTranscriptApi.get_transcript(
                video_id, languages=target_languages
            )
    except (AttributeError, TypeError):
        # Additional fallback
        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            raw_snippets = YouTubeTranscriptApi.get_transcript(
                video_id, languages=target_languages
            )
        else:
            raise

    # Standardize list of entries to dictionaries
    entries: List[Dict[str, Any]] = []
    for item in raw_snippets:
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            start = float(item.get("start", 0.0))
            duration = float(item.get("duration", 0.0))
        else:
            text = str(getattr(item, "text", "")).strip()
            start = float(getattr(item, "start", 0.0))
            duration = float(getattr(item, "duration", 0.0))

        if text:
            entries.append({"text": text, "start": start, "duration": duration})

    return entries


def get_video_transcript(url_or_id: str) -> Dict[str, Any]:
    """
    High-level function to extract transcript from a YouTube URL or video ID.
    Always returns a safe result dictionary without throwing unhandled exceptions.
    
    Returns:
        {
            "success": bool,
            "video_id": str | None,
            "url": str,
            "entries": list[dict],
            "clean_text": str,
            "timestamped_text": str,
            "stats": dict,
            "error": str | None
        }
    """
    video_id = get_video_id(url_or_id)
    if not video_id:
        return {
            "success": False,
            "video_id": None,
            "url": url_or_id,
            "entries": [],
            "clean_text": "",
            "timestamped_text": "",
            "stats": {"word_count": 0, "char_count": 0, "reading_time_minutes": 0},
            "error": "Invalid YouTube URL. Please provide a valid YouTube video link.",
        }

    canonical_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        entries = get_transcript(video_id)
        if not entries:
            return {
                "success": False,
                "video_id": video_id,
                "url": canonical_url,
                "entries": [],
                "clean_text": "",
                "timestamped_text": "",
                "stats": {"word_count": 0, "char_count": 0, "reading_time_minutes": 0},
                "error": "Transcript unavailable for this video. Please try another video with captions/transcript available.",
            }

        clean_text = clean_transcript(entries, include_timestamps=False)
        timestamped_text = clean_transcript(entries, include_timestamps=True)
        stats = calculate_reading_stats(clean_text)

        return {
            "success": True,
            "video_id": video_id,
            "url": canonical_url,
            "entries": entries,
            "clean_text": clean_text,
            "timestamped_text": timestamped_text,
            "stats": stats,
            "error": None,
        }

    except (TranscriptsDisabled, NoTranscriptFound):
        return {
            "success": False,
            "video_id": video_id,
            "url": canonical_url,
            "entries": [],
            "clean_text": "",
            "timestamped_text": "",
            "stats": {"word_count": 0, "char_count": 0, "reading_time_minutes": 0},
            "error": "Transcript unavailable for this video. Please try another video with captions/transcript available.",
        }
    except VideoUnavailable:
        return {
            "success": False,
            "video_id": video_id,
            "url": canonical_url,
            "entries": [],
            "clean_text": "",
            "timestamped_text": "",
            "stats": {"word_count": 0, "char_count": 0, "reading_time_minutes": 0},
            "error": "Video is unavailable or private. Please check the URL and try again.",
        }
    except Exception as exc:
        err_msg = str(exc).lower()
        if "transcript" in err_msg or "caption" in err_msg or "subtitles" in err_msg:
            friendly_err = "Transcript unavailable for this video. Please try another video with captions/transcript available."
        elif "connection" in err_msg or "network" in err_msg or "http" in err_msg:
            friendly_err = "Network error connecting to YouTube. Please check your internet connection."
        else:
            friendly_err = f"Could not retrieve transcript: {str(exc).splitlines()[0]}"

        return {
            "success": False,
            "video_id": video_id,
            "url": canonical_url,
            "entries": [],
            "clean_text": "",
            "timestamped_text": "",
            "stats": {"word_count": 0, "char_count": 0, "reading_time_minutes": 0},
            "error": friendly_err,
        }
