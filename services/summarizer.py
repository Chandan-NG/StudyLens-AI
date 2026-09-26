"""Summary generation service for StudyLens AI."""

from typing import Any, Dict, Optional
from services.llm import generate_completion
from utils.prompts import SUMMARY_PROMPT, SUMMARY_SYSTEM_PROMPT


def generate_summary(
    transcript: str,
    model: Optional[str] = None,
    host: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate an educational summary from a video transcript using local Ollama.
    
    Returns:
        {
            "success": bool,
            "summary": str,
            "model": str,
            "error": str | None
        }
    """
    if not transcript or not transcript.strip():
        return {
            "success": False,
            "summary": "",
            "model": model or "",
            "error": "No transcript provided to summarize.",
        }

    # Format the centralized prompt
    prompt = SUMMARY_PROMPT.format(transcript=transcript)

    result = generate_completion(
        prompt=prompt,
        system_prompt=SUMMARY_SYSTEM_PROMPT,
        model=model,
        host=host,
        temperature=0.2,
    )

    if not result["success"]:
        return {
            "success": False,
            "summary": "",
            "model": result.get("model", ""),
            "error": result.get("error", "Failed to generate summary."),
        }

    return {
        "success": True,
        "summary": result["content"],
        "model": result.get("model", ""),
        "error": None,
    }
