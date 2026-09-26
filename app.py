"""
StudyLens AI — AI-Powered YouTube Study Assistant.
Minimalist, local-first educational assistant designed with Ollama-inspired design principles.
"""

import os
import requests
import streamlit as st

from services.youtube import get_video_id, get_video_transcript
from services.llm import check_ollama_available
from services.summarizer import generate_summary
from services.notes import generate_notes
from services.quiz import generate_quiz
from services.chat import answer_question
from services.database import (
    delete_session_by_video_id,
    get_session_by_video_id,
    init_db,
    list_all_sessions,
    save_or_update_session,
)
from utils.text_cleaner import calculate_reading_stats, clean_whitespace

# Page configuration with mortarboard icon
icon_path = os.path.join("assets", "favicon.png")
st.set_page_config(
    page_title="StudyLens AI",
    page_icon=icon_path if os.path.exists(icon_path) else "🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize SQLite database on startup
init_db()

# Ollama-inspired Design System CSS with Bootstrap Icons, Unified Capsule Input, & Clean Nav Pills
st.html(
    r"""
    <style>
    @import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Nunito:wght@500;600;700&display=swap');

    /* Local and CDN @font-face fallback for Bootstrap Icons */
    @font-face {
        font-family: 'bootstrap-icons';
        src: url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff2') format('woff2'),
             url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff') format('woff');
        font-weight: normal;
        font-style: normal;
        font-display: block;
    }

    .bi::before, [class^="bi-"]::before, [class*=" bi-"]::before {
        display: inline-block;
        font-family: 'bootstrap-icons' !important;
        font-style: normal;
        font-weight: normal !important;
        font-variant: normal;
        text-transform: none;
        line-height: 1;
        vertical-align: -0.125em;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    .bi-mortarboard-fill::before { content: "\f473"; }
    .bi-journal-text::before { content: "\f44c"; }
    .bi-pencil-square::before { content: "\f4cb"; }
    .bi-ui-checks-grid::before { content: "\f5e3"; }
    .bi-chat-dots::before { content: "\f257"; }
    .bi-stickies::before { content: "\f593"; }
    .bi-clock-history::before { content: "\f293"; }
    .bi-gear::before { content: "\f3e5"; }
    .bi-tv::before { content: "\f5df"; }

    /* Global canvas & typography */
    html, body, .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #000000;
        background-color: #ffffff;
    }

    /* Headings */
    h1, h2, h3, h4 {
        font-family: 'Nunito', 'Inter', -apple-system, sans-serif;
        font-weight: 600;
        letter-spacing: -0.02em;
        color: #000000;
    }

    /* Main container constraint for reading column alignment */
    .main .block-container {
        max-width: 900px !important;
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
        margin: 0 auto !important;
    }

    /* Default buttons */
    .stButton > button {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-radius: 9999px !important;
        border: 1px solid #000000 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        padding: 8px 24px !important;
        height: 42px !important;
        box-shadow: none !important;
        transition: background-color 0.15s ease;
    }
    .stButton > button:hover {
        background-color: #171717 !important;
        color: #ffffff !important;
        border-color: #171717 !important;
    }
    .stButton > button:active {
        background-color: #090909 !important;
    }

    /* Unified Capsule Input Bar (Ollama search aesthetics) */
    div[data-testid="stForm"] {
        border: 1px solid #e5e5e5 !important;
        background-color: #fafafa !important;
        border-radius: 9999px !important;
        padding: 4px 6px 4px 20px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.15s ease !important;
    }
    div[data-testid="stForm"]:focus-within {
        border-color: #000000 !important;
        background-color: #ffffff !important;
        box-shadow: 0 0 0 1px #000000, 0 2px 6px rgba(0, 0, 0, 0.05) !important;
    }
    div[data-testid="stForm"] .stTextInput {
        padding: 0 !important;
        margin: 0 !important;
    }
    div[data-testid="stForm"] .stTextInput > div,
    div[data-testid="stForm"] .stTextInput > div > div {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
    }
    div[data-testid="stForm"] .stTextInput > div > div > input {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        font-size: 14px !important;
        height: 42px !important;
        color: #000000 !important;
        padding-left: 0 !important;
    }
    div[data-testid="stForm"] .stTextInput > div > div > input:focus {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        outline: none !important;
    }
    div[data-testid="stForm"] .stTextInput > div > div > input::placeholder {
        color: #a3a3a3 !important;
        font-weight: 400 !important;
    }
    div[data-testid="stForm"] .stFormSubmitButton {
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stForm"] .stFormSubmitButton > button {
        height: 40px !important;
        padding: 0 24px !important;
        border-radius: 9999px !important;
        background-color: #000000 !important;
        color: #ffffff !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        border: 1px solid #000000 !important;
        box-shadow: none !important;
        transition: background-color 0.15s ease !important;
    }
    div[data-testid="stForm"] .stFormSubmitButton > button:hover {
        background-color: #262626 !important;
        border-color: #262626 !important;
    }

    /* Remove "Press Enter to submit form" instructions from input box display */
    [data-testid="InputInstructions"],
    div[data-testid="InputInstructions"],
    .stTextInput [data-testid="InputInstructions"],
    div[data-testid="stForm"] [data-testid="InputInstructions"],
    [class*="InputInstructions"],
    [class*="instructions"],
    .stTextInput small,
    div[data-testid="stForm"] small {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        max-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* Secondary / outline buttons */
    .stDownloadButton > button {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-radius: 9999px !important;
        border: 1px solid #d4d4d4 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 6px 18px !important;
        height: 38px !important;
        box-shadow: none !important;
    }
    .stDownloadButton > button:hover {
        background-color: #fafafa !important;
        border-color: #000000 !important;
    }

    /* Metric cards: 1px hairline border with rounded.lg */
    div[data-testid="stMetric"] {
        background-color: #fafafa;
        border: 1px solid #e5e5e5;
        border-radius: 12px;
        padding: 14px 18px;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 11px;
        color: #737373;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetricValue"] {
        font-size: 20px;
        font-weight: 600;
        color: #000000;
    }

    /* Workspace Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #e5e5e5;
        margin-bottom: 20px;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 9999px;
        padding: 8px 20px;
        font-size: 14px;
        font-weight: 500;
        color: #737373;
        background-color: transparent;
        border: 1px solid transparent;
        transition: all 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #000000;
        background-color: #fafafa;
    }
    .stTabs [aria-selected="true"] {
        color: #000000 !important;
        background-color: #fafafa !important;
        font-weight: 600 !important;
        border: 1px solid #e5e5e5 !important;
    }

    /* Bootstrap icons prefix for tabs */
    .stTabs [data-baseweb="tab"]:nth-child(1) [data-testid="stMarkdownContainer"] p::before,
    .stTabs [data-baseweb="tab"]:nth-child(1) p::before {
        font-family: 'bootstrap-icons' !important;
        content: "\f44c\a0\a0"; /* bi-journal-text */
        font-size: 14px;
        vertical-align: middle;
    }
    .stTabs [data-baseweb="tab"]:nth-child(2) [data-testid="stMarkdownContainer"] p::before,
    .stTabs [data-baseweb="tab"]:nth-child(2) p::before {
        font-family: 'bootstrap-icons' !important;
        content: "\f4cb\a0\a0"; /* bi-pencil-square */
        font-size: 14px;
        vertical-align: middle;
    }
    .stTabs [data-baseweb="tab"]:nth-child(3) [data-testid="stMarkdownContainer"] p::before,
    .stTabs [data-baseweb="tab"]:nth-child(3) p::before {
        font-family: 'bootstrap-icons' !important;
        content: "\f593\a0\a0"; /* bi-stickies */
        font-size: 14px;
        vertical-align: middle;
    }
    .stTabs [data-baseweb="tab"]:nth-child(4) [data-testid="stMarkdownContainer"] p::before,
    .stTabs [data-baseweb="tab"]:nth-child(4) p::before {
        font-family: 'bootstrap-icons' !important;
        content: "\f5e3\a0\a0"; /* bi-ui-checks-grid */
        font-size: 14px;
        vertical-align: middle;
    }
    .stTabs [data-baseweb="tab"]:nth-child(5) [data-testid="stMarkdownContainer"] p::before,
    .stTabs [data-baseweb="tab"]:nth-child(5) p::before {
        font-family: 'bootstrap-icons' !important;
        content: "\f257\a0\a0"; /* bi-chat-dots */
        font-size: 14px;
        vertical-align: middle;
    }

    /* Sidebar clean minimal styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e5e5e5;
        padding-top: 1.5rem;
    }

    /* Sidebar navigation pill buttons */
    .stSidebar div.stButton button {
        width: 100% !important;
        justify-content: flex-start !important;
        text-align: left !important;
        padding: 10px 18px !important;
        height: 42px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        border-radius: 9999px !important;
        margin-bottom: 4px !important;
        box-shadow: none !important;
        transition: all 0.15s ease !important;
    }
    /* Inactive sidebar buttons */
    .stSidebar div.stButton button[data-testid="baseButton-secondary"] {
        background-color: transparent !important;
        color: #525252 !important;
        border: 1px solid transparent !important;
    }
    .stSidebar div.stButton button[data-testid="baseButton-secondary"]:hover {
        background-color: #fafafa !important;
        border-color: #e5e5e5 !important;
        color: #000000 !important;
    }
    /* Active sidebar button: pure black pill */
    .stSidebar div.stButton button[data-testid="baseButton-primary"] {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #000000 !important;
        font-weight: 600 !important;
    }
    .stSidebar div.stButton button[data-testid="baseButton-primary"]:hover {
        background-color: #171717 !important;
        border-color: #171717 !important;
        color: #ffffff !important;
    }

    /* Sidebar navigation button icon prefixes */
    .stSidebar div.stButton:nth-of-type(1) button p::before {
        font-family: 'bootstrap-icons' !important;
        content: "\f5df\a0\a0"; /* bi-tv */
        font-size: 15px;
        vertical-align: middle;
    }
    .stSidebar div.stButton:nth-of-type(2) button p::before {
        font-family: 'bootstrap-icons' !important;
        content: "\f293\a0\a0"; /* bi-clock-history */
        font-size: 15px;
        vertical-align: middle;
    }
    .stSidebar div.stButton:nth-of-type(3) button p::before {
        font-family: 'bootstrap-icons' !important;
        content: "\f3e5\a0\a0"; /* bi-gear */
        font-size: 15px;
        vertical-align: middle;
    }

    /* Dividers */
    hr {
        border-top: 1px solid #e5e5e5 !important;
        margin: 20px 0 !important;
    }
    </style>
    """
)


def init_session_state():
    """Initialize persistent session state variables."""
    default_state = {
        "current_url": "",
        "video_id": None,
        "transcript_entries": [],
        "clean_transcript": "",
        "timestamped_transcript": "",
        "transcript_stats": {"word_count": 0, "char_count": 0, "reading_time_minutes": 0},
        "summary": None,
        "notes": None,
        "quiz": None,
        "quiz_submitted": False,
        "quiz_score": 0,
        "user_answers": {},
        "chat_history": [],
        "search_history": [],
        "ollama_model": os.getenv("OLLAMA_MODEL", "qwen2:7b"),
        "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "web_research_enabled": True,
        "active_nav": "Study Session",
    }
    for key, val in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()

# Query local Ollama connectivity
ollama_online, available_models = check_ollama_available(st.session_state.ollama_host)


# ----------------- SIDEBAR: CLEAN & UNCLUTTERED -----------------
with st.sidebar:
    st.markdown(
        """
        <div style="font-size: 20px; font-weight: 700; letter-spacing: -0.02em; display: flex; align-items: center; gap: 8px;">
            <i class="bi bi-mortarboard-fill"></i> StudyLens AI
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Turn YouTube lectures into notes, quizzes, and study sessions.")
    st.markdown("<hr style='margin: 14px 0;'>", unsafe_allow_html=True)

    # Clean pill navigation buttons (strictly no checkboxes or radio bullets)
    if st.button(
        "Study Session",
        key="nav_btn_session",
        type="primary" if st.session_state.active_nav == "Study Session" else "secondary",
        use_container_width=True,
    ):
        if st.session_state.active_nav != "Study Session":
            st.session_state.active_nav = "Study Session"
            st.rerun()

    if st.button(
        "Study History",
        key="nav_btn_history",
        type="primary" if st.session_state.active_nav == "Study History" else "secondary",
        use_container_width=True,
    ):
        if st.session_state.active_nav != "Study History":
            st.session_state.active_nav = "Study History"
            st.rerun()

    if st.button(
        "Settings",
        key="nav_btn_settings",
        type="primary" if st.session_state.active_nav == "Settings" else "secondary",
        use_container_width=True,
    ):
        if st.session_state.active_nav != "Settings":
            st.session_state.active_nav = "Settings"
            st.rerun()

    selected_nav = st.session_state.active_nav




# ----------------- REUSABLE COMPONENTS -----------------

def render_quiz_component(key_prefix: str = "main"):
    """Render interactive quiz taking, scoring, and explanations without pre-selecting answers."""
    if not st.session_state.quiz:
        st.markdown(
            """
            <div style="background-color: #fafafa; border: 1px solid #e5e5e5; border-radius: 12px; padding: 28px; text-align: center; margin: 16px 0;">
                <h4 style="margin-bottom: 8px;"><i class="bi bi-ui-checks-grid"></i> Test Your Comprehension</h4>
                <p style="color: #737373; font-size: 14px; max-width: 460px; margin: 0 auto 16px auto;">
                    Generate 10 multiple-choice questions to test your understanding of this lecture.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_btn, _ = st.columns([2, 5])
        with col_btn:
            if st.button("Generate Quiz", key=f"{key_prefix}_btn_gen_quiz"):
                with st.spinner("Generating quiz..."):
                    res = generate_quiz(
                        transcript=st.session_state.clean_transcript,
                        model=st.session_state.ollama_model,
                        host=st.session_state.ollama_host,
                    )
                    if res["success"]:
                        st.session_state.quiz = res["questions"]
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_score = 0
                        st.session_state.user_answers = {}
                        save_or_update_session(
                            video_id=st.session_state.video_id,
                            video_url=st.session_state.current_url,
                            quiz_data=st.session_state.quiz,
                        )
                        st.rerun()
                    else:
                        st.error(res["error"])
        return

    total_q = len(st.session_state.quiz)

    # Score summary banner if submitted
    if st.session_state.quiz_submitted:
        score = st.session_state.quiz_score
        percentage = round((score / total_q) * 100) if total_q > 0 else 0

        if percentage >= 80:
            badge_icon, badge_msg = "🎉", "Outstanding mastery! You have grasped the key concepts thoroughly."
        elif percentage >= 50:
            badge_icon, badge_msg = "👍", "Good effort! Review the explanations below to solidify your understanding."
        else:
            badge_icon, badge_msg = "📚", "Consider reviewing the study notes and retaking the quiz to strengthen your knowledge."

        col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
        with col_s1:
            st.metric("Score", f"{score} / {total_q}")
        with col_s2:
            st.metric("Percentage", f"{percentage}%")
        with col_s3:
            st.markdown(
                f"""
                <div style="background-color: #fafafa; border: 1px solid #e5e5e5; border-radius: 12px; padding: 12px 16px; margin-top: 4px;">
                    <div style="font-size: 13px; font-weight: 500;">{badge_icon} {badge_msg}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        col_r1, col_r2, _ = st.columns([2, 2, 4])
        with col_r1:
            if st.button("Retake Quiz", key=f"{key_prefix}_retake_btn"):
                st.session_state.quiz_submitted = False
                st.session_state.user_answers = {}
                st.session_state.quiz_score = 0
                st.rerun()
        with col_r2:
            if st.button("Regenerate New Quiz", key=f"{key_prefix}_regen_btn"):
                with st.spinner("Generating new quiz..."):
                    res = generate_quiz(
                        transcript=st.session_state.clean_transcript,
                        model=st.session_state.ollama_model,
                        host=st.session_state.ollama_host,
                    )
                    if res["success"]:
                        st.session_state.quiz = res["questions"]
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_score = 0
                        st.session_state.user_answers = {}
                        save_or_update_session(
                            video_id=st.session_state.video_id,
                            video_url=st.session_state.current_url,
                            quiz_data=st.session_state.quiz,
                        )
                        st.rerun()
                    else:
                        st.error(res["error"])
    else:
        col_hdr, col_reg = st.columns([5, 2])
        with col_hdr:
            st.caption("Select your answers below and submit to view your score and explanations.")
        with col_reg:
            if st.button("Regenerate Questions", key=f"{key_prefix}_regen_btn_unsub"):
                with st.spinner("Generating new questions..."):
                    res = generate_quiz(
                        transcript=st.session_state.clean_transcript,
                        model=st.session_state.ollama_model,
                        host=st.session_state.ollama_host,
                    )
                    if res["success"]:
                        st.session_state.quiz = res["questions"]
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_score = 0
                        st.session_state.user_answers = {}
                        save_or_update_session(
                            video_id=st.session_state.video_id,
                            video_url=st.session_state.current_url,
                            quiz_data=st.session_state.quiz,
                        )
                        st.rerun()
                    else:
                        st.error(res["error"])

    st.markdown("<hr style='margin: 16px 0;'>", unsafe_allow_html=True)

    # Render each question card with no answer marked by default (index=None)
    letters = ["A", "B", "C", "D", "E", "F"]
    for idx, q in enumerate(st.session_state.quiz):
        with st.container(border=True):
            st.markdown(f"**Question {idx + 1} of {total_q}**")
            st.markdown(f"#### {q['question']}")

            options_formatted = [
                f"{letters[i]}. {opt}" for i, opt in enumerate(q["options"])
            ]

            if not st.session_state.quiz_submitted:
                prev_selected = st.session_state.user_answers.get(idx, None)
                selected_idx = st.radio(
                    f"Options for Q{idx+1}",
                    options=list(range(len(q["options"]))),
                    format_func=lambda i: options_formatted[i],
                    index=prev_selected,  # Starts as None (completely empty, no default marked)
                    key=f"{key_prefix}_radio_q_{idx}",
                    label_visibility="collapsed",
                )
                if selected_idx is not None:
                    st.session_state.user_answers[idx] = selected_idx
            else:
                user_ans = st.session_state.user_answers.get(idx, None)
                correct_ans = q["correct_answer"]

                for opt_idx, opt_text in enumerate(q["options"]):
                    label = f"{letters[opt_idx]}. {opt_text}"
                    if opt_idx == correct_ans:
                        st.markdown(
                            f"<div style='padding: 8px 14px; background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #166534;'>✓ {label} <i>(Correct Answer)</i></div>",
                            unsafe_allow_html=True,
                        )
                    elif user_ans is not None and opt_idx == user_ans and user_ans != correct_ans:
                        st.markdown(
                            f"<div style='padding: 8px 14px; background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; margin-bottom: 6px; font-size: 14px; color: #991b1b;'>✗ {label} <i>(Your Selection)</i></div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<div style='padding: 8px 14px; background-color: #fafafa; border: 1px solid #e5e5e5; border-radius: 8px; margin-bottom: 6px; font-size: 14px; color: #737373;'>{label}</div>",
                            unsafe_allow_html=True,
                        )

                if user_ans is None:
                    st.markdown("<div style='font-size: 12px; color: #a3a3a3; margin-top: 4px;'><i>(Question was left unanswered)</i></div>", unsafe_allow_html=True)

                st.markdown(
                    f"""
                    <div style="font-size: 13px; color: #525252; background: #ffffff; padding: 12px 16px; border-radius: 8px; border: 1px solid #e5e5e5; margin-top: 10px;">
                        💡 <b>Explanation:</b> {q['explanation']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    if not st.session_state.quiz_submitted:
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        col_sub, _ = st.columns([2, 5])
        with col_sub:
            if st.button("Submit Quiz", key=f"{key_prefix}_btn_submit_quiz"):
                unanswered = [i + 1 for i in range(total_q) if st.session_state.user_answers.get(i) is None]
                if unanswered and len(unanswered) == total_q:
                    st.warning("Please answer at least one question before submitting.")
                else:
                    score = sum(
                        1
                        for i, q in enumerate(st.session_state.quiz)
                        if st.session_state.user_answers.get(i) == q["correct_answer"]
                    )
                    st.session_state.quiz_score = score
                    st.session_state.quiz_submitted = True
                    st.rerun()


def render_chat_component(key_prefix: str = "main"):
    """Render educational chat grounded in the video transcript with optional web research."""
    if not st.session_state.video_id:
        st.info("Please load a video in Study Session first to chat with its content.")
        return

    # Header with mode selector and Clear Chat action
    col_mode, col_clr = st.columns([5, 1])
    with col_mode:
        chat_mode = st.radio(
            "Research Mode",
            options=["Video + Web Research", "Video Only"],
            index=0 if st.session_state.web_research_enabled else 1,
            horizontal=True,
            key=f"{key_prefix}_mode_radio",
            label_visibility="collapsed",
        )
    with col_clr:
        if st.session_state.chat_history:
            if st.button("Clear Chat", key=f"{key_prefix}_clear_chat"):
                st.session_state.chat_history = []
                st.rerun()

    if chat_mode == "Video + Web Research":
        st.caption("<i class='bi bi-journal-text'></i> <b>Dynamic Research Active</b>: Answers from video transcript with automatic web search fallback when needed.", unsafe_allow_html=True)
    else:
        st.caption("<i class='bi bi-journal-text'></i> <b>Video Grounding Active</b>: Answers strictly from the video transcript.", unsafe_allow_html=True)

    st.markdown("<hr style='margin: 8px 0 16px 0;'>", unsafe_allow_html=True)

    # Prompt suggestions if chat is empty
    if not st.session_state.chat_history:
        st.markdown(
            """
            <div style="background-color: #fafafa; border: 1px solid #e5e5e5; border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;">
                <div style="font-size: 14px; font-weight: 600; margin-bottom: 8px;">Suggested Questions to Ask:</div>
                <div style="font-size: 13px; color: #525252; line-height: 1.6;">
                    • <i>What are the main concepts covered in this video?</i><br>
                    • <i>Can you explain the key theory or technique mentioned?</i><br>
                    • <i>What real-world examples were discussed?</i><br>
                    • <i>What are recent developments related to this topic?</i>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Render message history
    for msg in st.session_state.chat_history:
        role = msg.get("role", "user")
        with st.chat_message(role):
            st.markdown(msg.get("content", ""))
            if role == "assistant":
                source_type = msg.get("source_type", "video")
                if source_type == "web":
                    st.markdown(
                        """
                        <div style="font-size: 12px; font-weight: 500; color: #000000; margin-top: 8px;">
                            <b>Web research referenced</b>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    search_results = msg.get("search_results", [])
                    if search_results:
                        with st.expander("View Web Sources & Citations", expanded=False):
                            for src in search_results:
                                st.markdown(f"• **[{src['title']}]({src['url']})**")
                                if src.get("snippet"):
                                    st.caption(src["snippet"])
                else:
                    st.caption("<i class='bi bi-journal-text'></i> Video Transcript Grounding", unsafe_allow_html=True)

    # Chat input
    user_query = st.chat_input("Ask a question about this video...", key=f"{key_prefix}_chat_input")
    if user_query and user_query.strip():
        q_text = user_query.strip()
        st.session_state.chat_history.append({"role": "user", "content": q_text})
        with st.chat_message("user"):
            st.markdown(q_text)

        with st.chat_message("assistant"):
            spinner_msg = (
                "Searching and answering..."
                if chat_mode == "Video + Web Research"
                else "Thinking..."
            )
            with st.spinner(spinner_msg):
                res = answer_question(
                    question=q_text,
                    transcript=st.session_state.clean_transcript,
                    chat_history=st.session_state.chat_history[:-1],
                    mode=chat_mode,
                    model=st.session_state.ollama_model,
                    host=st.session_state.ollama_host,
                )
                if res["success"]:
                    st.markdown(res["answer"])
                    if res.get("source_type") == "web":
                        st.markdown(
                            """
                            <div style="font-size: 12px; font-weight: 500; color: #000000; margin-top: 8px;">
                                <b>Additional web research used</b>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if res.get("search_results"):
                            with st.expander("View Web Sources & Citations", expanded=True):
                                for src in res["search_results"]:
                                    st.markdown(f"• **[{src['title']}]({src['url']})**")
                                    if src.get("snippet"):
                                        st.caption(src["snippet"])
                    else:
                        st.caption(f"<i class='bi bi-journal-text'></i> Source: {res['source']}", unsafe_allow_html=True)

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": res["answer"],
                        "source_type": res.get("source_type", "video"),
                        "source": res["source"],
                        "search_results": res.get("search_results", []),
                    })
                else:
                    err_msg = res.get("error", "Failed to generate answer.")
                    st.error(err_msg)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"⚠️ {err_msg}",
                        "source_type": "error",
                        "source": "System Error",
                        "search_results": [],
                    })
        st.rerun()


# ----------------- MAIN VIEW LOGIC -----------------

if selected_nav == "Study Session":
    # Centered Header with Mortarboard Icon
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 28px;">
            <div style="font-size: 42px; margin-bottom: 4px; color: #000000;">
                <i class="bi bi-mortarboard-fill"></i>
            </div>
            <h1 style="font-size: 34px; font-weight: 700; margin-bottom: 8px; letter-spacing: -0.03em;">
                StudyLens AI
            </h1>
            <p style="font-size: 16px; color: #737373; line-height: 1.5; margin-bottom: 0px;">
                Turn YouTube educational lectures into structured notes, quizzes, and interactive AI study sessions.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Aesthetic YouTube URL input form (Unified Capsule Pill)
    with st.form(key="video_search_form", clear_on_submit=False):
        col_input, col_action = st.columns([5, 1], vertical_alignment="center")
        with col_input:
            video_url = st.text_input(
                "YouTube Video URL",
                value=st.session_state.current_url,
                placeholder="Paste YouTube link...",
                label_visibility="collapsed",
                key="study_url_input",
            )
        with col_action:
            load_video_btn = st.form_submit_button("Study →", use_container_width=True)

    if load_video_btn:
        cleaned_url = video_url.strip()
        if not cleaned_url:
            st.error("Please enter a valid YouTube URL.")
        else:
            with st.spinner("Loading video transcript..."):
                res = get_video_transcript(cleaned_url)
                if res["success"]:
                    st.session_state.current_url = res["url"]
                    st.session_state.video_id = res["video_id"]
                    st.session_state.transcript_entries = res["entries"]
                    st.session_state.clean_transcript = res["clean_text"]
                    st.session_state.timestamped_transcript = res["timestamped_text"]
                    st.session_state.transcript_stats = res["stats"]
                    # Reset generation artifacts on new video
                    st.session_state.summary = None
                    st.session_state.notes = None
                    st.session_state.quiz = None
                    st.session_state.quiz_submitted = False
                    st.session_state.quiz_score = 0
                    st.session_state.user_answers = {}
                    st.session_state.chat_history = []

                    # Automatically persist newly loaded session in SQLite
                    save_or_update_session(
                        video_id=res["video_id"],
                        video_url=res["url"],
                        title=f"YouTube Video ({res['video_id']})",
                        transcript=res["clean_text"],
                    )
                    st.rerun()
                else:
                    st.error(res["error"])

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # Active Lecture status banner when video is loaded
    if st.session_state.video_id:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 20px; background-color: #fafafa; border: 1px solid #e5e5e5; border-radius: 9999px; margin-bottom: 20px; font-size: 13px; color: #525252;">
                <span style="font-weight: 500; color: #000000;"><i class="bi bi-tv" style="margin-right: 6px;"></i> Active Lecture Loaded</span>
                <span><i class="bi bi-journal-text" style="margin-right: 4px;"></i> {st.session_state.transcript_stats['word_count']:,} words &nbsp;·&nbsp; <i class="bi bi-clock-history" style="margin-right: 4px;"></i> ~{st.session_state.transcript_stats['reading_time_minutes']} min read</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 5 Workspace Tabs (Always visible immediately upon opening Study Session)
    tab_info, tab_summary, tab_notes, tab_quiz, tab_chat = st.tabs(
        ["Transcript", "Summary", "Notes", "Quiz", "Chat"]
    )

    # Tab 1: Video Info & Transcript Explorer
    with tab_info:
        if st.session_state.video_id:
            col_v1, col_v2 = st.columns([1, 1], gap="medium")
            with col_v1:
                st.markdown("#### <i class='bi bi-tv'></i> Video Preview", unsafe_allow_html=True)
                st.video(f"https://www.youtube.com/watch?v={st.session_state.video_id}")
                st.caption(f"Source: `{st.session_state.current_url}`")

            with col_v2:
                st.markdown("#### <i class='bi bi-journal-text'></i> Transcript Explorer", unsafe_allow_html=True)
                t_mode = st.radio(
                    "Transcript View Mode",
                    options=["Continuous Clean Text", "Timestamped Segments"],
                    horizontal=True,
                    label_visibility="collapsed",
                )

                search_query = st.text_input(
                    "Search transcript text",
                    placeholder="Search keywords...",
                    key="transcript_search",
                )

                if t_mode == "Continuous Clean Text":
                    display_text = st.session_state.clean_transcript
                else:
                    display_text = st.session_state.timestamped_transcript

                if search_query.strip():
                    query = search_query.strip().lower()
                    filtered_lines = [
                        line for line in display_text.splitlines() if query in line.lower()
                    ]
                    if filtered_lines:
                        st.info(f"Found {len(filtered_lines)} matching segment(s):")
                        st.text_area(
                            "Filtered Matches",
                            value="\n\n".join(filtered_lines),
                            height=280,
                            label_visibility="collapsed",
                        )
                    else:
                        st.warning(f"No occurrences of '{search_query}' found.")
                else:
                    st.text_area(
                        "Full Transcript",
                        value=display_text,
                        height=280,
                        label_visibility="collapsed",
                    )
        else:
            st.markdown(
                """
                <div style="background-color: #fafafa; border: 1px solid #e5e5e5; border-radius: 14px; padding: 40px 24px; text-align: center; margin: 16px 0;">
                    <div style="font-size: 32px; margin-bottom: 8px; color: #000000;"><i class="bi bi-journal-text"></i></div>
                    <h4 style="margin-bottom: 6px; font-weight: 600;">Transcript Explorer</h4>
                    <p style="color: #737373; font-size: 14px; max-width: 480px; margin: 0 auto;">
                        Paste a YouTube video link above and click <strong>Study →</strong> to view synchronized lecture transcripts, timestamps, and search across spoken text.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Tab 2: Summary
    with tab_summary:
        st.markdown("#### <i class='bi bi-pencil-square'></i> Lecture Summary", unsafe_allow_html=True)
        st.caption("AI-generated core concepts, key points, and takeaways grounded strictly in the transcript.")

        if st.session_state.video_id:
            if not st.session_state.summary:
                st.markdown(
                    """
                    <div style="background-color: #fafafa; border: 1px solid #e5e5e5; border-radius: 12px; padding: 28px; text-align: center; margin: 16px 0;">
                        <h4 style="margin-bottom: 8px;">No Summary Generated Yet</h4>
                        <p style="color: #737373; font-size: 14px; max-width: 460px; margin: 0 auto 16px auto;">
                            Extract key takeaways, core concepts, and main arguments from this video.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                col_btn, _ = st.columns([2, 5])
                with col_btn:
                    if st.button("Generate Summary", key="btn_gen_summary"):
                        with st.spinner("Generating summary..."):
                            res = generate_summary(
                                transcript=st.session_state.clean_transcript,
                                model=st.session_state.ollama_model,
                                host=st.session_state.ollama_host,
                            )
                            if res["success"]:
                                st.session_state.summary = res["summary"]
                                save_or_update_session(
                                    video_id=st.session_state.video_id,
                                    video_url=st.session_state.current_url,
                                    summary=res["summary"],
                                )
                                st.rerun()
                            else:
                                st.error(res["error"])
            else:
                col_act1, col_act2, _ = st.columns([2, 2, 4])
                with col_act1:
                    if st.button("Regenerate Summary", key="btn_regen_summary"):
                        with st.spinner("Generating summary..."):
                            res = generate_summary(
                                transcript=st.session_state.clean_transcript,
                                model=st.session_state.ollama_model,
                                host=st.session_state.ollama_host,
                            )
                            if res["success"]:
                                st.session_state.summary = res["summary"]
                                save_or_update_session(
                                    video_id=st.session_state.video_id,
                                    video_url=st.session_state.current_url,
                                    summary=res["summary"],
                                )
                                st.rerun()
                            else:
                                st.error(res["error"])
                with col_act2:
                    st.download_button(
                        label="Download Summary (MD)",
                        data=st.session_state.summary,
                        file_name=f"summary_{st.session_state.video_id}.md",
                        mime="text/markdown",
                    )

                with st.container(border=True):
                    st.markdown(st.session_state.summary)
        else:
            st.markdown(
                """
                <div style="background-color: #fafafa; border: 1px solid #e5e5e5; border-radius: 14px; padding: 40px 24px; text-align: center; margin: 16px 0;">
                    <div style="font-size: 32px; margin-bottom: 8px; color: #000000;"><i class="bi bi-pencil-square"></i></div>
                    <h4 style="margin-bottom: 6px; font-weight: 600;">Executive Summary</h4>
                    <p style="color: #737373; font-size: 14px; max-width: 480px; margin: 0 auto;">
                        Paste a YouTube video link above to generate comprehensive key takeaways, core concepts, and main arguments.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Tab 3: Notes
    with tab_notes:
        st.markdown("#### <i class='bi bi-stickies'></i> Structured Study Notes", unsafe_allow_html=True)
        st.caption("Comprehensive academic study notes with definitions, explanations, and key takeaways.")

        if st.session_state.video_id:
            if not st.session_state.notes:
                st.markdown(
                    """
                    <div style="background-color: #fafafa; border: 1px solid #e5e5e5; border-radius: 12px; padding: 28px; text-align: center; margin: 16px 0;">
                        <h4 style="margin-bottom: 8px;">No Study Notes Generated Yet</h4>
                        <p style="color: #737373; font-size: 14px; max-width: 460px; margin: 0 auto 16px auto;">
                            Generate structured notes with key concepts, detailed explanations, and a glossary.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                col_btn, _ = st.columns([2, 5])
                with col_btn:
                    if st.button("Generate Notes", key="btn_gen_notes"):
                        with st.spinner("Generating notes..."):
                            res = generate_notes(
                                transcript=st.session_state.clean_transcript,
                                topic=f"Video {st.session_state.video_id}",
                                model=st.session_state.ollama_model,
                                host=st.session_state.ollama_host,
                            )
                            if res["success"]:
                                st.session_state.notes = res["notes"]
                                save_or_update_session(
                                    video_id=st.session_state.video_id,
                                    video_url=st.session_state.current_url,
                                    notes=res["notes"],
                                )
                                st.rerun()
                            else:
                                st.error(res["error"])
            else:
                col_act1, col_act2, _ = st.columns([2, 2, 4])
                with col_act1:
                    if st.button("Regenerate Notes", key="btn_regen_notes"):
                        with st.spinner("Generating notes..."):
                            res = generate_notes(
                                transcript=st.session_state.clean_transcript,
                                topic=f"Video {st.session_state.video_id}",
                                model=st.session_state.ollama_model,
                                host=st.session_state.ollama_host,
                            )
                            if res["success"]:
                                st.session_state.notes = res["notes"]
                                save_or_update_session(
                                    video_id=st.session_state.video_id,
                                    video_url=st.session_state.current_url,
                                    notes=res["notes"],
                                )
                                st.rerun()
                            else:
                                st.error(res["error"])
                with col_act2:
                    st.download_button(
                        label="Download Notes (MD)",
                        data=st.session_state.notes,
                        file_name=f"notes_{st.session_state.video_id}.md",
                        mime="text/markdown",
                    )

                with st.container(border=True):
                    st.markdown(st.session_state.notes)
        else:
            st.markdown(
                """
                <div style="background-color: #fafafa; border: 1px solid #e5e5e5; border-radius: 14px; padding: 40px 24px; text-align: center; margin: 16px 0;">
                    <div style="font-size: 32px; margin-bottom: 8px; color: #000000;"><i class="bi bi-stickies"></i></div>
                    <h4 style="margin-bottom: 6px; font-weight: 600;">Structured Study Notes</h4>
                    <p style="color: #737373; font-size: 14px; max-width: 480px; margin: 0 auto;">
                        Paste a YouTube video link above to generate structured lecture notes, definitions, key takeaways, and flashcards.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Tab 4: Interactive Quiz
    with tab_quiz:
        st.markdown("#### <i class='bi bi-ui-checks-grid'></i> Interactive Quiz", unsafe_allow_html=True)
        st.caption("Test your comprehension with 10 questions extracted strictly from the video transcript.")
        if st.session_state.video_id:
            render_quiz_component(key_prefix="tab_quiz")
        else:
            st.markdown(
                """
                <div style="background-color: #fafafa; border: 1px solid #e5e5e5; border-radius: 14px; padding: 40px 24px; text-align: center; margin: 16px 0;">
                    <div style="font-size: 32px; margin-bottom: 8px; color: #000000;"><i class="bi bi-ui-checks-grid"></i></div>
                    <h4 style="margin-bottom: 6px; font-weight: 600;">Comprehension Quiz</h4>
                    <p style="color: #737373; font-size: 14px; max-width: 480px; margin: 0 auto;">
                        Paste a YouTube video link above to generate an interactive 10-question multiple-choice quiz with instant scoring and explanations.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Tab 5: Chat
    with tab_chat:
        st.markdown("#### <i class='bi bi-chat-dots'></i> Chat with Video", unsafe_allow_html=True)
        st.caption("Interactive Q&A powered by the video transcript and optional DuckDuckGo web research.")
        if st.session_state.video_id:
            render_chat_component(key_prefix="tab_chat")
        else:
            st.markdown(
                """
                <div style="background-color: #fafafa; border: 1px solid #e5e5e5; border-radius: 14px; padding: 40px 24px; text-align: center; margin: 16px 0;">
                    <div style="font-size: 32px; margin-bottom: 8px; color: #000000;"><i class="bi bi-chat-dots"></i></div>
                    <h4 style="margin-bottom: 6px; font-weight: 600;">Interactive Lecture Chat</h4>
                    <p style="color: #737373; font-size: 14px; max-width: 480px; margin: 0 auto;">
                        Paste a YouTube video link above to ask questions and receive answers grounded strictly in the lecture transcript.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )


elif selected_nav == "Study History":
    st.markdown("## <i class='bi bi-clock-history'></i> Study History", unsafe_allow_html=True)
    st.caption("Your saved study sessions.")
    st.markdown("<hr style='margin: 14px 0 20px 0;'>", unsafe_allow_html=True)

    sessions = list_all_sessions()
    if not sessions:
        st.markdown(
            """
            <div style="background-color: #fafafa; border: 1px dashed #e5e5e5; border-radius: 12px; padding: 40px; text-align: center;">
                <p style="color: #737373; font-size: 14px; margin: 0;">
                    No past study sessions found. Process a video in <b>Study Session</b> to start your history.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for s in sessions:
            with st.container(border=True):
                col_info, col_btn, col_del = st.columns([5, 2, 1])
                with col_info:
                    st.markdown(f"**{s.get('title', 'Video')}**")
                    badges = []
                    if s.get("has_summary"):
                        badges.append("<i class='bi bi-pencil-square'></i> Summary")
                    if s.get("has_notes"):
                        badges.append("<i class='bi bi-stickies'></i> Notes")
                    if s.get("has_quiz"):
                        badges.append("<i class='bi bi-ui-checks-grid'></i> Quiz")
                    badge_str = " · ".join(badges) if badges else "Transcript"

                    st.markdown(
                        f"""
                        <div style="font-size: 13px; color: #737373;">
                            Saved: {s['created_at'][:10]} · {badge_str}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with col_btn:
                    if st.button("Open Session →", key=f"open_session_{s['video_id']}"):
                        session_data = get_session_by_video_id(s["video_id"])
                        if session_data:
                            st.session_state.current_url = session_data["video_url"]
                            st.session_state.video_id = session_data["video_id"]
                            st.session_state.clean_transcript = session_data.get("transcript", "")
                            st.session_state.timestamped_transcript = session_data.get("transcript", "")
                            st.session_state.transcript_stats = calculate_reading_stats(st.session_state.clean_transcript)
                            st.session_state.summary = session_data.get("summary")
                            st.session_state.notes = session_data.get("notes")
                            st.session_state.quiz = session_data.get("quiz_data")
                            st.session_state.quiz_submitted = False
                            st.session_state.quiz_score = 0
                            st.session_state.user_answers = {}
                            st.session_state.chat_history = []
                            st.session_state.active_nav = "Study Session"
                            st.rerun()

                with col_del:
                    if st.button("Delete", key=f"del_session_{s['video_id']}"):
                        delete_session_by_video_id(s["video_id"])
                        st.rerun()


elif selected_nav == "Settings":
    st.markdown("## <i class='bi bi-gear'></i> Settings", unsafe_allow_html=True)
    st.caption("Manage AI model and search preferences.")
    st.markdown("<hr style='margin: 14px 0 24px 0;'>", unsafe_allow_html=True)

    col_s1, col_s2 = st.columns([1, 1], gap="large")

    with col_s1:
        st.markdown("#### <i class='bi bi-gear'></i> AI Model", unsafe_allow_html=True)
        if available_models:
            current_model_idx = (
                available_models.index(st.session_state.ollama_model)
                if st.session_state.ollama_model in available_models
                else 0
            )
            selected_model = st.selectbox(
                "Model",
                options=available_models,
                index=current_model_idx,
            )
            st.session_state.ollama_model = selected_model
        else:
            model_text = st.text_input(
                "Model Name",
                value=st.session_state.ollama_model,
                help="Example: qwen2:7b",
            )
            st.session_state.ollama_model = model_text.strip()

        host_input = st.text_input(
            "Service Host",
            value=st.session_state.ollama_host,
            help="Default: http://localhost:11434",
        )
        st.session_state.ollama_host = host_input.strip()

        if ollama_online:
            st.success(f"✓ Connected ({st.session_state.ollama_host})")
        else:
            st.error("✗ Service unavailable")
            st.markdown(
                """
                **How to start Ollama:**
                1. Download: [https://ollama.com](https://ollama.com)
                2. Pull model: `ollama pull qwen2:7b`
                3. Run: `ollama serve`
                """
            )

    with col_s2:
        st.markdown("#### Web Research", unsafe_allow_html=True)
        web_search = st.toggle(
            "Enable Web Research by Default",
            value=st.session_state.web_research_enabled,
            help="Augment Q&A with web search when video info is insufficient.",
        )
        st.session_state.web_research_enabled = web_search

        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
        st.markdown("#### <i class='bi bi-mortarboard-fill'></i> About StudyLens AI", unsafe_allow_html=True)
        st.caption("StudyLens AI — Minimalist, private study companion. Open source & free.")
