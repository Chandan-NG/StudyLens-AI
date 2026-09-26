"""Local LLM service wrapper for Ollama."""

import os
from typing import Any, Dict, List, Optional, Tuple
import requests

try:
    import ollama
    from ollama import ResponseError
except ImportError:
    ollama = None
    ResponseError = Exception


DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2:7b")


def check_ollama_available(host: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    Check if the Ollama instance is reachable and return a list of installed models.
    """
    target_host = (host or DEFAULT_OLLAMA_HOST).rstrip("/")
    try:
        resp = requests.get(f"{target_host}/api/tags", timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
            models = [
                m.get("name") or m.get("model")
                for m in data.get("models", [])
                if m.get("name") or m.get("model")
            ]
            return True, models
    except Exception:
        pass
    return False, []


def generate_completion(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    host: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    response_format: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send prompt and system message to Ollama and return the generated content.
    
    Returns:
        {
            "success": bool,
            "content": str,
            "model": str,
            "error": str | None
        }
    """
    target_host = (host or DEFAULT_OLLAMA_HOST).rstrip("/")
    target_model = model or DEFAULT_OLLAMA_MODEL

    if not prompt or not prompt.strip():
        return {
            "success": False,
            "content": "",
            "model": target_model,
            "error": "Prompt cannot be empty.",
        }

    # Verify server availability first
    is_up, installed_models = check_ollama_available(target_host)
    if not is_up:
        return {
            "success": False,
            "content": "",
            "model": target_model,
            "error": (
                f"Cannot connect to Ollama at {target_host}. "
                "Please verify that Ollama is installed and running (`ollama serve`)."
            ),
        }

    # Build messages
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    options: Dict[str, Any] = {"temperature": temperature}
    if max_tokens:
        options["num_predict"] = max_tokens

    chat_kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": messages,
        "options": options,
    }
    if response_format:
        chat_kwargs["format"] = response_format

    try:
        client = ollama.Client(host=target_host)
        response = client.chat(**chat_kwargs)
        content = response.get("message", {}).get("content", "")
        return {
            "success": True,
            "content": content,
            "model": target_model,
            "error": None,
        }

    except ResponseError as resp_err:
        if getattr(resp_err, "status_code", 0) == 404 or "not found" in str(resp_err).lower():
            return {
                "success": False,
                "content": "",
                "model": target_model,
                "error": (
                    f"Model '{target_model}' not found in Ollama. "
                    f"Run `ollama pull {target_model}` in your terminal to download it."
                ),
            }
        return {
            "success": False,
            "content": "",
            "model": target_model,
            "error": f"Ollama error ({resp_err.status_code}): {str(resp_err)}",
        }

    except Exception as exc:
        err_msg = str(exc).lower()
        if "connect" in err_msg or "refused" in err_msg:
            friendly = f"Could not connect to Ollama at {target_host}. Ensure `ollama serve` is active."
        else:
            friendly = f"Failed to generate response: {str(exc).splitlines()[0]}"

        return {
            "success": False,
            "content": "",
            "model": target_model,
            "error": friendly,
        }
