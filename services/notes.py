"""Study notes generation service for StudyLens AI."""

from typing import Any, Dict, Optional
from services.llm import generate_completion
from utils.prompts import NOTES_PROMPT, NOTES_SYSTEM_PROMPT


def generate_notes(
    transcript: str,
    topic: Optional[str] = None,
    model: Optional[str] = None,
    host: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate comprehensive, structured academic study notes from a video transcript using local Ollama.
    
    Returns:
        {
            "success": bool,
            "notes": str,
            "model": str,
            "error": str | None
        }
    """
    if not transcript or not transcript.strip():
        return {
            "success": False,
            "notes": "",
            "model": model or "",
            "error": "No transcript provided to generate notes.",
        }

    detected_topic = topic or "Lecture Overview"
    prompt = NOTES_PROMPT.format(topic=detected_topic, transcript=transcript)

    result = generate_completion(
        prompt=prompt,
        system_prompt=NOTES_SYSTEM_PROMPT,
        model=model,
        host=host,
        temperature=0.2,
    )

    if not result["success"]:
        return {
            "success": False,
            "notes": "",
            "model": result.get("model", ""),
            "error": result.get("error", "Failed to generate study notes."),
        }

    return {
        "success": True,
        "notes": result["content"],
        "model": result.get("model", ""),
        "error": None,
    }
