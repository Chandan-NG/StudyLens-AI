# StudyLens AI 🎓
> **Turn YouTube educational lectures into structured notes, comprehension quizzes, and interactive AI study sessions.**

StudyLens AI is a lightweight, local-first, NotebookLM-inspired educational web application. It extracts transcripts from educational YouTube videos, analyzes them with a local LLM via [Ollama](https://ollama.com), and generates concise summaries, textbook-quality study notes, interactive self-assessment quizzes, and a transcript-grounded conversational tutor with optional DuckDuckGo web research capabilities.

**100% Free & Open-Source**: Built without paid APIs, without cloud API key requirements, without LangChain or LangGraph, and without complex vector database overhead for Version 1.

---

## Key Features

- 📺 **Intelligent YouTube Transcript Extraction**:
  - Automatically parses standard watch URLs, short URLs (`youtu.be`), mobile links (`m.youtube.com`), embeds, and shorts.
  - Multi-track language fallback to select the best available English or native caption track.
  - Zero video/audio downloads — caption text only for instant extraction.
  - Gracefully handles missing transcripts, disabled captions, or unavailable videos with user-friendly guidance.

- 📝 **Structured Executive Summaries**:
  - Synthesizes core concepts, primary arguments, and high-value takeaways grounded strictly in the transcript.
  - One-click Markdown export.

- 📚 **Comprehensive Study Notes**:
  - Generates textbook-quality notes structured across 6 academic sections:
    1. Introduction & Overview
    2. Core Concepts & Definitions
    3. Detailed Step-by-Step Explanations
    4. Examples & Demonstrations
    5. Important Terms & Glossary table
    6. Key Takeaways & Review Points
  - One-click Markdown download.

- 🧠 **Interactive Self-Quizzes**:
  - Generates 10 multiple-choice questions grounded in the lecture.
  - Pydantic schema validation ensuring reliable question structures, options, and explanations.
  - Interactive quiz UI: answers and explanations remain strictly hidden until submission.
  - Instant scoring, percentage calculation, performance feedback, and per-question explanations.

- 💬 **Transcript-Grounded AI Study Chat**:
  - Conversational tutor strictly anchored to the lecture transcript.
  - Smart keyword relevance chunking for large transcripts without needing a vector database.
  - **Dual Research Modes**:
    - **Video Only**: Answers strictly using the video transcript.
    - **Video + Web Research**: When transcript context is insufficient or when recent external information is needed, queries DuckDuckGo and synthesizes the answer with clickable source citations.

- 📜 **Local SQLite Study History**:
  - Lightweight persistence using SQLite (`data/studylens.db`).
  - Automatically saves processed videos, generated summaries, notes, and quizzes.
  - Reopen past study sessions in 1 click or remove them when done.

- 🎨 **Minimalist Ollama Design System**:
  - Paper-white canvas (`#ffffff`), soft secondary surfaces (`#fafafa`), and 1px hairline dividers (`#e5e5e5`).
  - Pure black pill buttons (`rounded.full`, 9999px) and clean typography (`Nunito`, `Inter`, `JetBrains Mono`).
  - Monospace terminal status cards with macOS traffic light dots.
  - Centered reading column with clean alignment and uncluttered navigation.

---

## Architecture & Workflow

```text
       YouTube Educational URL
                 │
                 ▼
       [services/youtube.py]
      (Extract & Clean Transcript)
                 │
                 ├───► [utils/text_cleaner.py] (Deterministic Normalization & Stats)
                 │
                 ▼
          Local Ollama LLM
         (e.g., qwen2:7b)
                 │
   ┌─────────────┼──────────────┬──────────────┐
   │             │              │              │
   ▼             ▼              ▼              ▼
Summary        Notes           Quiz           Chat
Generator    Generator      Generator      Assistant
(Markdown)   (6 Sections)    (JSON /       (Context
                             Pydantic)      Chunking)
                                               │
                                 [Optional Web Research]
                                    (DuckDuckGo / DDGS)
                                               │
                                               ▼
                                      Synthesized Answer
                                      + Web Citations
```

---

## Tech Stack

- **Frontend**: Modern, fast, responsive Single Page Application (SPA) built with [Bootstrap 5](https://getbootstrap.com/), [Bootstrap Icons 1.11](https://icons.getbootstrap.com/), and [Marked.js](https://marked.js.org/), strictly adhering to the Ollama minimalist design system. (Streamlit interface also preserved in `app.py`).
- **Backend API**: [FastAPI](https://fastapi.tiangolo.com/) with asynchronous endpoint handling and [Uvicorn](https://www.uvicorn.org/).
- **Local LLM Engine**: [Ollama](https://ollama.com/) (default: `qwen2:7b`, configurable to `qwen3:4b`, `llama3.2`, etc.)
- **YouTube Extraction**: [`youtube-transcript-api`](https://github.com/jdepoix/youtube-transcript-api)
- **Web Search**: [`ddgs`](https://github.com/deedy5/ddgs) / DuckDuckGo Search (free, no API keys) with dynamic fallback and query optimization.
- **Storage**: SQLite via Python's native `sqlite3` module (`data/studylens.db`)
- **Data Validation**: [Pydantic v2](https://docs.pydantic.dev/)
- **Testing**: [pytest](https://docs.pytest.org/)

---

## Project Structure

```text
StudyLensAI/
├── server.py                   # FastAPI backend server (port 8000)
├── static/                     # Modern Bootstrap 5 SPA Frontend
│   ├── index.html              # Clean single-page application
│   ├── styles.css              # Ollama-inspired minimalist CSS design system
│   └── app.js                  # Reactive state management & client logic
├── assets/
│   └── favicon.png             # Mortarboard logo icon
├── app.py                      # Streamlit alternate interface
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment configuration
├── .gitignore                  # Git ignore rules
├── LICENSE                     # MIT License
├── pytest.ini                  # Pytest configuration
├── README.md                   # Project documentation
├── .streamlit/
│   └── config.toml             # Streamlit light theme & server settings
├── data/
│   ├── .gitkeep
│   └── studylens.db            # Local SQLite database (auto-created)
├── services/
│   ├── __init__.py
│   ├── youtube.py              # URL extraction & transcript retrieval
│   ├── llm.py                  # Reusable Ollama client & model discovery
│   ├── summarizer.py           # Educational summary generator
│   ├── notes.py                # Structured academic study notes generator
│   ├── quiz.py                 # Quiz generator & Pydantic validation
│   ├── chat.py                 # Grounded chat service & context chunking
│   ├── search.py               # Free DuckDuckGo web search integration
│   └── database.py             # SQLite persistence & study history
├── utils/
│   ├── __init__.py
│   ├── text_cleaner.py         # Whitespace cleaning & reading stats
│   └── prompts.py              # Centralized prompt templates
└── tests/
    ├── test_server.py          # FastAPI REST endpoint & health tests
    ├── test_youtube.py         # YouTube URL & transcript tests
    ├── test_services.py        # LLM, summary, notes unit tests
    ├── test_quiz.py            # Quiz JSON parsing & validation tests
    ├── test_chat.py            # Keyword chunking & chat tests
    ├── test_search.py          # Search formatting & sufficiency tests
    ├── test_database.py        # SQLite persistence tests
    └── test_utils.py           # Text cleaner & formatting tests
```

---

## Prerequisites

1. **Python 3.11+** installed on your system.
2. **Ollama** installed and running locally:
   - Download from [https://ollama.com](https://ollama.com)
   - Pull the recommended model:
     ```bash
     ollama pull qwen2:7b
     ```
   - Start the Ollama background service:
     ```bash
     ollama serve
     ```

---

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/StudyLensAI.git
   cd StudyLensAI
   ```

2. **Create and activate a virtual environment**:
   - **Windows**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment (Optional)**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Default values:
   ```env
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=qwen2:7b
   ```

---

## Running the Application

### Option 1: FastAPI + Modern SPA Frontend (Recommended)

Start the high-performance FastAPI server:

```bash
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Open your browser at:
**[http://127.0.0.1:8000](http://127.0.0.1:8000)**

### Option 2: Streamlit Interface

Alternatively, run the Streamlit frontend:

```bash
streamlit run app.py
```

Open your browser at:
**[http://localhost:8501](http://localhost:8501)**

---

## How to Use

1. **Load a Video**:
   - Navigate to **Study Session** (`bi-tv`).
   - Paste any YouTube educational video URL that has captions available.
   - Click **Load Video**.
2. **Explore the Transcript**:
   - View the embedded video preview, word count, and reading time.
   - Use the **Transcript** tab (`bi-journal-text`) to toggle between continuous clean text or timestamped intervals, or search for key terms.
3. **Generate Summary & Study Notes**:
   - Click **Generate Summary** in the **Summary** tab (`bi-pencil-square`).
   - Click **Generate Notes** in the **Notes** tab (`bi-stickies`).
   - Copy the generated summary or notes directly to clipboard as **Markdown** or **Plain Text**.
4. **Take an Interactive Quiz**:
   - In the **Quiz** tab (`bi-ui-checks-grid`), click **Generate Quiz** to create 10 multiple-choice questions.
   - All options start unselected. Select your answers and click **Submit Quiz** to view your score, correct answers, and explanations.
5. **Chat with the Lecture**:
   - In the **Chat** tab (`bi-chat-dots`), ask questions about the video.
   - Toggle **Video Only** for strict transcript grounding, or **Video + Web Research** to supplement with live DuckDuckGo web results.
6. **Resume Previous Sessions**:
   - Click **Session History** (`bi-clock-history`) in the sidebar to view previously studied lectures and restore them in one click.

---

## Running Tests

Run the complete automated unit test suite with `pytest`:

```bash
pytest tests/ -v
```

All 46 unit tests validate URL extraction, text cleaning, Pydantic JSON schemas, context chunking, DuckDuckGo search, SQLite storage, and FastAPI REST endpoints.

---

## Limitations & Best Practices

- **Transcript Requirement**: The target YouTube video must have captions or an available transcript (automatic or creator-provided). If captions are disabled by the creator, StudyLens AI will notify you gracefully.
- **Local Hardware**: LLM generation speed depends on your local system specs (CPU/GPU) and the size of the model selected. Lightweight models such as `qwen2:7b`, `qwen3:4b`, or `llama3.2:3b` provide great speed-to-accuracy balance.
- **Web Search**: DuckDuckGo search results depend on internet connectivity and search terms.
- **Educational Disclaimer**: StudyLens AI is designed as a study aid to accelerate comprehension and review. It should be used alongside course materials and authoritative textbooks.

---

## License

MIT License — Free and open-source for personal and educational use.
