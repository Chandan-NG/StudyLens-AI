"""Quiz generation and validation service for StudyLens AI."""

import json
import re
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ValidationError

from services.llm import generate_completion
from utils.prompts import QUIZ_PROMPT, QUIZ_SYSTEM_PROMPT


class QuizQuestion(BaseModel):
    """Schema for an individual multiple-choice question."""
    question: str
    options: List[str] = Field(..., min_length=2, max_length=6)
    correct_answer: int = Field(..., ge=0, le=5)
    explanation: str


class QuizPayload(BaseModel):
    """Schema for the full quiz payload."""
    questions: List[QuizQuestion] = Field(..., min_length=1)


def parse_json_from_llm(raw_text: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """
    Extract and parse a JSON object or array from LLM response text,
    stripping markdown fences or surrounding chatter.
    """
    if not raw_text or not raw_text.strip():
        return None

    cleaned = raw_text.strip()

    # Remove markdown code blocks if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try regex search for outermost { ... }
    brace_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try regex search for outermost [ ... ]
    bracket_match = re.search(r"(\[.*\])", cleaned, re.DOTALL)
    if bracket_match:
        try:
            return json.loads(bracket_match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def normalize_question_data(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Sanitize and normalize a raw question dictionary."""
    question_text = str(item.get("question", "")).strip()
    raw_options = item.get("options", [])
    raw_answer = item.get("correct_answer", 0)
    explanation = str(item.get("explanation", "")).strip()

    if not question_text or not isinstance(raw_options, (list, tuple)) or len(raw_options) < 2:
        return None

    options = [str(opt).strip() for opt in raw_options if str(opt).strip()]
    if len(options) < 2:
        return None

    # Handle letter answers like 'A', 'B', 'C', 'D'
    correct_idx = 0
    if isinstance(raw_answer, str):
        cleaned_ans = raw_answer.strip().upper()
        if cleaned_ans in ("A", "0"):
            correct_idx = 0
        elif cleaned_ans in ("B", "1"):
            correct_idx = 1
        elif cleaned_ans in ("C", "2"):
            correct_idx = 2
        elif cleaned_ans in ("D", "3"):
            correct_idx = 3
        else:
            try:
                correct_idx = int(cleaned_ans)
            except ValueError:
                correct_idx = 0
    elif isinstance(raw_answer, (int, float)):
        correct_idx = int(raw_answer)

    # Bound check correct_idx
    if correct_idx < 0 or correct_idx >= len(options):
        correct_idx = 0

    return {
        "question": question_text,
        "options": options,
        "correct_answer": correct_idx,
        "explanation": explanation or "Grounded in the video transcript discussion.",
    }


def validate_and_parse_quiz(raw_text: str) -> List[Dict[str, Any]]:
    """
    Parse and validate quiz questions from LLM text into standardized dictionary format.
    Raises ValueError if no valid questions could be extracted.
    """
    parsed_json = parse_json_from_llm(raw_text)
    if parsed_json is None:
        raise ValueError("Could not parse valid JSON from the model response.")

    raw_items = []
    if isinstance(parsed_json, dict):
        if "questions" in parsed_json and isinstance(parsed_json["questions"], list):
            raw_items = parsed_json["questions"]
        elif "quiz" in parsed_json and isinstance(parsed_json["quiz"], list):
            raw_items = parsed_json["quiz"]
        else:
            # Check if dict values contain a list of questions
            for val in parsed_json.values():
                if isinstance(val, list) and val and isinstance(val[0], dict):
                    raw_items = val
                    break
    elif isinstance(parsed_json, list):
        raw_items = parsed_json

    if not raw_items:
        raise ValueError("No quiz questions found in the JSON output.")

    validated_questions: List[Dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        normalized = normalize_question_data(item)
        if normalized:
            try:
                # Pydantic validation
                q_model = QuizQuestion(**normalized)
                validated_questions.append(q_model.model_dump())
            except ValidationError:
                continue

    if not validated_questions:
        raise ValueError("Failed to validate quiz schema with Pydantic.")

    return validated_questions


def generate_quiz(
    transcript: str,
    num_questions: int = 10,
    model: Optional[str] = None,
    host: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate multiple-choice quiz questions from a video transcript using local Ollama.
    
    Returns:
        {
            "success": bool,
            "questions": list[dict],
            "model": str,
            "error": str | None
        }
    """
    if not transcript or not transcript.strip():
        return {
            "success": False,
            "questions": [],
            "model": model or "",
            "error": "No transcript provided to generate a quiz.",
        }

    # Format the prompt
    prompt = QUIZ_PROMPT.format(transcript=transcript)

    result = generate_completion(
        prompt=prompt,
        system_prompt=QUIZ_SYSTEM_PROMPT,
        model=model,
        host=host,
        temperature=0.2,
        response_format="json",
    )

    if not result["success"]:
        return {
            "success": False,
            "questions": [],
            "model": result.get("model", ""),
            "error": result.get("error", "Failed to generate quiz."),
        }

    try:
        questions = validate_and_parse_quiz(result["content"])
        return {
            "success": True,
            "questions": questions,
            "model": result.get("model", ""),
            "error": None,
        }
    except Exception as exc:
        return {
            "success": False,
            "questions": [],
            "model": result.get("model", ""),
            "error": f"Failed to validate quiz structure: {str(exc)}",
        }
