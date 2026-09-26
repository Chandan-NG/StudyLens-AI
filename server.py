"""
StudyLens AI — FastAPI Backend Server.
Provides robust REST endpoints for YouTube processing, notes, summaries, quizzes, grounded chat,
and SQLite session persistence. Serves the modern minimalist SPA frontend.
"""

import os
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests

from services.database import (
    delete_session_by_video_id,
    get_session_by_video_id,
    init_db,
    list_all_sessions,
    save_or_update_session,
)
from services.youtube import get_video_id, get_video_transcript
from services.llm import check_ollama_available
from services.summarizer import generate_summary
from services.notes import generate_notes
from services.quiz import generate_quiz
from services.chat import answer_question
from utils.text_cleaner import calculate_reading_stats

logger = logging.getLogger("studylens")

# Initialize database
init_db()

app = FastAPI(title="StudyLens AI API", version="1.0.0")

# Enable CORS for local dev / client flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=200,
        content={
            "success": False,
            "error": f"Server processing error: {str(exc) or 'An unexpected error occurred.'}"
        },
    )

# App State / Default Settings
APP_STATE = {
    "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "ollama_model": os.getenv("OLLAMA_MODEL", "qwen2:7b"),
    "web_research_enabled": True,
}


# --- Request & Response Models ---

class VideoLoadRequest(BaseModel):
    url: str

class SummaryRequest(BaseModel):
    video_id: str
    transcript: str
    model: Optional[str] = None
    host: Optional[str] = None

class NotesRequest(BaseModel):
    video_id: str
    transcript: str
    topic: Optional[str] = None
    model: Optional[str] = None
    host: Optional[str] = None

class QuizRequest(BaseModel):
    video_id: str
    transcript: str
    model: Optional[str] = None
    host: Optional[str] = None

class ChatRequest(BaseModel):
    question: str
    transcript: str
    chat_history: Optional[List[Dict[str, str]]] = []
    mode: Optional[str] = "Video + Web Research"
    model: Optional[str] = None
    host: Optional[str] = None

class SettingsUpdateRequest(BaseModel):
    model: Optional[str] = None
    host: Optional[str] = None
    web_research_enabled: Optional[bool] = None


# --- API Endpoints ---

@app.post("/api/video/load")
def load_video(req: VideoLoadRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please provide a valid YouTube link.")

    result = get_video_transcript(url)
    if not result["success"]:
        return {
            "success": False,
            "error": result.get("error", "Failed to retrieve transcript."),
        }

    vid = result["video_id"]
    clean_text = result["clean_text"]
    timestamped_text = result["timestamped_text"]
    stats = result["stats"]

    # Check if this video was previously saved in SQLite
    existing = get_session_by_video_id(vid)
    saved_summary = existing.get("summary") if existing else None
    saved_notes = existing.get("notes") if existing else None
    saved_quiz = existing.get("quiz_data") if existing else None

    # Persist or update session
    save_or_update_session(
        video_id=vid,
        video_url=result["url"],
        title=f"YouTube Video ({vid})",
        transcript=clean_text,
    )

    return {
        "success": True,
        "video_id": vid,
        "url": result["url"],
        "clean_transcript": clean_text,
        "timestamped_transcript": timestamped_text,
        "stats": stats,
        "summary": saved_summary,
        "notes": saved_notes,
        "quiz": saved_quiz,
    }


@app.post("/api/summary")
def get_summary(req: SummaryRequest):
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty.")

    model = req.model or APP_STATE["ollama_model"]
    host = req.host or APP_STATE["ollama_host"]

    res = generate_summary(transcript=req.transcript, model=model, host=host)
    if res["success"]:
        save_or_update_session(
            video_id=req.video_id,
            summary=res["summary"],
        )
    return res


@app.post("/api/notes")
def get_notes(req: NotesRequest):
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty.")

    model = req.model or APP_STATE["ollama_model"]
    host = req.host or APP_STATE["ollama_host"]
    topic = req.topic or f"Video {req.video_id}"

    res = generate_notes(transcript=req.transcript, topic=topic, model=model, host=host)
    if res["success"]:
        save_or_update_session(
            video_id=req.video_id,
            notes=res["notes"],
        )
    return res


@app.post("/api/quiz")
def get_quiz(req: QuizRequest):
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty.")

    model = req.model or APP_STATE["ollama_model"]
    host = req.host or APP_STATE["ollama_host"]

    res = generate_quiz(transcript=req.transcript, model=model, host=host)
    if res["success"]:
        save_or_update_session(
            video_id=req.video_id,
            quiz_data=res["questions"],
        )
    return res


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    model = req.model or APP_STATE["ollama_model"]
    host = req.host or APP_STATE["ollama_host"]
    mode = req.mode or ("Video + Web Research" if APP_STATE["web_research_enabled"] else "Video Only")

    res = answer_question(
        question=req.question,
        transcript=req.transcript,
        chat_history=req.chat_history,
        mode=mode,
        model=model,
        host=host,
    )
    return res


@app.get("/api/history")
def get_history():
    return {"sessions": list_all_sessions()}


@app.get("/api/history/{video_id}")
def get_session(video_id: str):
    sess = get_session_by_video_id(video_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    # Calculate stats if not present
    transcript = sess.get("transcript", "")
    stats = calculate_reading_stats(transcript)
    return {
        "success": True,
        "video_id": sess["video_id"],
        "url": sess["video_url"],
        "title": sess.get("title", ""),
        "clean_transcript": transcript,
        "timestamped_transcript": transcript,
        "stats": stats,
        "summary": sess.get("summary"),
        "notes": sess.get("notes"),
        "quiz": sess.get("quiz_data"),
    }


@app.delete("/api/history/{video_id}")
def delete_session(video_id: str):
    deleted = delete_session_by_video_id(video_id)
    return {"success": deleted}


@app.get("/api/settings")
def get_settings():
    host = APP_STATE["ollama_host"]
    online, models = check_ollama_available(host)

    return {
        "ollama_host": host,
        "ollama_model": APP_STATE["ollama_model"],
        "web_research_enabled": APP_STATE["web_research_enabled"],
        "ollama_online": online,
        "available_models": models,
    }


@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest):
    if req.model is not None:
        APP_STATE["ollama_model"] = req.model.strip()
    if req.host is not None:
        APP_STATE["ollama_host"] = req.host.strip()
    if req.web_research_enabled is not None:
        APP_STATE["web_research_enabled"] = req.web_research_enabled

    return {"success": True, "settings": APP_STATE}


# --- Static Files / Frontend Hosting ---

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Serve assets (e.g. favicon)
assets_dir = os.path.join(os.path.dirname(__file__), "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "StudyLens AI API is running. Frontend static/index.html not found."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
