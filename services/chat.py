"""Chat service for StudyLens AI with context management, grounding, and web research."""

import re
from typing import Any, Dict, List, Optional
from services.llm import generate_completion
from services.search import format_search_results_for_llm, search_web
from utils.prompts import CHAT_SYSTEM_PROMPT, WEB_RESEARCH_PROMPT


COMMON_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
    "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more",
    "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
    "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they",
    "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who",
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves"
}

WEB_TRIGGER_TERMS = {
    "search", "web", "google", "internet", "online", "recent", "latest", "today",
    "current", "currently", "now", "outside", "beyond", "external", "externally",
    "news", "update", "updates", "who won", "2024", "2025", "2026",
    # Comparative & external scope queries
    "same year", "same decade", "same era", "same century", "same time", "same period",
    "other battle", "other battles", "other event", "other events", "other war", "other wars",
    "what else", "who else", "which other", "where else", "elsewhere",
    "around the same time", "during the same year", "during that time",
    "besides", "apart from", "other than", "outside the video", "not in the video",
    "world history", "in the world", "globally", "worldwide", "simultaneously",
    "concurrent", "contemporary"
}

INSUFFICIENT_ANSWER_PHRASES = [
    "does not provide information",
    "does not provide enough information",
    "does not contain information",
    "does not include information",
    "does not mention",
    "not mentioned in the video",
    "not mentioned in the transcript",
    "not covered in the transcript",
    "not covered in the video",
    "not discussed in the video",
    "not discussed in the transcript",
    "no information about",
    "no information provided",
    "transcript does not provide",
    "transcript does not mention",
    "transcript does not contain",
    "transcript does not include",
    "video does not provide",
    "video does not mention",
    "video does not contain",
    "video does not include",
    "cannot be answered from the transcript",
    "cannot be answered from the video",
    "does not list",
    "does not state",
]


def is_transcript_insufficient(answer_text: str) -> bool:
    """Check if the generated response indicates the transcript lacked sufficient information."""
    lower = answer_text.lower()
    return any(phrase in lower for phrase in INSUFFICIENT_ANSWER_PHRASES)


def extract_keywords(text: str) -> List[str]:
    """Extract informative lowercase keywords from text, removing punctuation and common stopwords."""
    words = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
    return [w for w in words if w not in COMMON_STOPWORDS]


def chunk_transcript(transcript: str, chunk_words: int = 350, overlap_words: int = 50) -> List[str]:
    """Split transcript text into overlapping chunks of words."""
    words = transcript.split()
    if len(words) <= chunk_words:
        return [transcript]

    chunks = []
    step = max(1, chunk_words - overlap_words)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_words])
        if chunk.strip():
            chunks.append(chunk.strip())
        if i + chunk_words >= len(words):
            break

    return chunks


def build_chat_context(transcript: str, query: str, max_words: int = 2500) -> str:
    """
    Select relevant sections from the transcript for the query.
    If the transcript fits within max_words, returns the entire transcript.
    Otherwise, chunks and ranks by keyword density.
    """
    words = transcript.split()
    if len(words) <= max_words:
        return transcript

    keywords = extract_keywords(query)
    chunks = chunk_transcript(transcript, chunk_words=350, overlap_words=50)

    if not keywords:
        selected = []
        count = 0
        for ch in chunks:
            ch_len = len(ch.split())
            if count + ch_len > max_words:
                break
            selected.append(ch)
            count += ch_len
        return "\n\n[...]\n\n".join(selected)

    # Score chunks by keyword frequency
    scored_chunks = []
    for idx, ch in enumerate(chunks):
        ch_lower = ch.lower()
        score = sum(ch_lower.count(k) for k in keywords)
        scored_chunks.append((score, idx, ch))

    scored_chunks.sort(key=lambda item: (-item[0], item[1]))

    selected_items = []
    current_word_count = 0
    for score, idx, ch in scored_chunks:
        ch_len = len(ch.split())
        if current_word_count + ch_len > max_words:
            if not selected_items:
                selected_items.append((idx, ch))
            break
        selected_items.append((idx, ch))
        current_word_count += ch_len

    selected_items.sort(key=lambda item: item[0])
    return "\n\n[...]\n\n".join([item[1] for item in selected_items])


def check_transcript_sufficiency(transcript: str, question: str) -> bool:
    """
    Check if the transcript contains relevant keywords for the question.
    Returns True if keywords appear in the transcript, False otherwise.
    """
    if query_requires_web_research(question):
        return False

    keywords = extract_keywords(question)
    if not keywords:
        return True
    transcript_lower = transcript.lower()
    matching_keywords = [kw for kw in keywords if kw in transcript_lower]
    return len(matching_keywords) >= max(1, len(keywords) // 2)


def query_requires_web_research(question: str) -> bool:
    """Check if the user explicitly asks for external web/recent information."""
    q_lower = question.lower()
    return any(term in q_lower for term in WEB_TRIGGER_TERMS)


def generate_search_queries(
    question: str,
    transcript: str = "",
    llm_answer: str = "",
) -> List[str]:
    """
    Generate targeted, high-precision search queries based on the question,
    transcript context, and any LLM preliminary response.
    """
    queries: List[str] = []
    q_clean = question.strip()
    q_lower = q_clean.lower()

    # Detect temporal or comparative questions
    temporal = any(
        term in q_lower
        for term in [
            "same year", "same decade", "same era", "same century", "same time", "same period",
            "other battle", "other battles", "other event", "other events", "other war", "other wars",
            "what else", "who else", "which other", "where else", "in history", "in the world", "globally"
        ]
    )

    # Extract 4-digit years from all sources
    years_q = re.findall(r"\b(1\d{3}|20\d{2})\b", q_clean)
    years_ans = re.findall(r"\b(1\d{3}|20\d{2})\b", llm_answer)
    years_t = re.findall(r"\b(1\d{3}|20\d{2})\b", transcript) if transcript else []
    unique_years = list(dict.fromkeys(years_q + years_ans + years_t))

    # Detect subject keywords
    subjects = [s for s in ["battles", "battle", "wars", "war", "treaties", "events", "leaders", "inventions", "revolutions"] if s in q_lower]
    primary_subject = subjects[0] if subjects else ("battles" if "battle" in q_lower else "historical events")

    # If asking about other events in the same year/era
    if temporal and unique_years:
        year = unique_years[0]
        queries.append(f"{primary_subject} in {year}")
        queries.append(f"major {primary_subject} fought in {year}")
        queries.append(f"events in {year} worldwide")

    # If asking about entity
    entity_match = re.search(r"(?:battle|war|treaty|event) of ([a-zA-Z\s]+)", q_clean, re.IGNORECASE)
    if entity_match and unique_years:
        queries.append(f"{primary_subject} same year as {entity_match.group(0).strip()}")

    # Condensed keyword query
    kw = extract_keywords(q_clean)
    if len(kw) >= 2:
        if unique_years and unique_years[0] not in kw:
            kw.append(unique_years[0])
        queries.append(" ".join(kw[:5]))

    # Original query
    queries.append(q_clean)

    # De-duplicate queries
    seen = set()
    deduped = []
    for q in queries:
        norm = q.strip().lower()
        if norm and norm not in seen:
            seen.add(norm)
            deduped.append(q.strip())
    return deduped


def execute_web_research(
    question: str,
    context: str,
    transcript: str = "",
    llm_prelim_answer: str = "",
    model: Optional[str] = None,
    host: Optional[str] = None,
    max_search_results: int = 5,
) -> Optional[Dict[str, Any]]:
    """Execute targeted DuckDuckGo searches and synthesize an educational answer."""
    queries = generate_search_queries(question, transcript=transcript, llm_answer=llm_prelim_answer)
    search_results = []
    for q in queries:
        res = search_web(q, max_results=max_search_results)
        if len(res) >= 2:
            search_results = res
            break
        elif res and not search_results:
            search_results = res

    if not search_results and queries:
        search_results = search_web(queries[-1], max_results=max_search_results)

    if not search_results:
        return None

    formatted_search = format_search_results_for_llm(search_results)
    research_prompt = WEB_RESEARCH_PROMPT.format(
        question=question,
        transcript_context=context,
        search_results=formatted_search,
    )

    result = generate_completion(
        prompt=research_prompt,
        system_prompt=(
            "You are StudyLens AI, an educational study assistant capable of synthesizing video content with external web research. "
            "Directly answer the question using the facts from both the search results and transcript. "
            "Clearly present the answer, relevant facts, and list the source URLs."
        ),
        model=model,
        host=host,
        temperature=0.2,
        max_tokens=None,
    )

    if result["success"]:
        return {
            "success": True,
            "answer": result["content"].strip(),
            "source_type": "web",
            "source": "Additional web research used",
            "search_results": search_results,
            "model": result.get("model", ""),
            "error": None,
        }
    return None


def answer_question(
    question: str,
    transcript: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    mode: str = "Video + Web Research",
    model: Optional[str] = None,
    host: Optional[str] = None,
    max_search_results: int = 5,
) -> Dict[str, Any]:
    """
    Generate an educational answer grounded in the transcript, with dynamic DuckDuckGo web research.
    
    Modes:
    - "Video Only": Answers strictly from the video transcript.
    - "Video + Web Research": Evaluates if video is sufficient; if insufficient or explicitly requested,
      queries DuckDuckGo, synthesizes answer, and formats web citations.
    """
    cleaned_q = question.strip() if question else ""
    if not cleaned_q:
        return {
            "success": False,
            "answer": "",
            "source_type": "video",
            "source": "",
            "search_results": [],
            "model": model or "",
            "error": "Question cannot be empty.",
        }

    if not transcript or not transcript.strip():
        return {
            "success": False,
            "answer": "No video transcript is currently loaded. Please load a video first.",
            "source_type": "video",
            "source": "",
            "search_results": [],
            "model": model or "",
            "error": "No transcript available.",
        }

    context = build_chat_context(transcript, cleaned_q)

    # Determine if web research should be invoked upfront
    should_search_upfront = False
    if mode == "Video + Web Research":
        if query_requires_web_research(cleaned_q) or not check_transcript_sufficiency(transcript, cleaned_q):
            should_search_upfront = True

    # Branch 1: Upfront Web Research when query requires external/comparative knowledge
    if should_search_upfront:
        web_res = execute_web_research(
            question=cleaned_q,
            context=context,
            transcript=transcript,
            model=model,
            host=host,
            max_search_results=max_search_results,
        )
        if web_res:
            return web_res

    # Branch 2: Standard Video-grounded answer
    history_str = ""
    if chat_history:
        recent_history = chat_history[-4:]
        lines = []
        for msg in recent_history:
            role_label = "Student" if msg.get("role") == "user" else "Assistant"
            lines.append(f"{role_label}: {msg.get('content', '')}")
        if lines:
            history_str = "PREVIOUS CONVERSATION:\n" + "\n".join(lines) + "\n\n"

    video_instruction = (
        "If the information is not present in the transcript context, explicitly state: "
        "'The video does not provide enough information to answer this question.'"
        if mode == "Video Only" else
        "Answer what is available in the transcript context. If details are missing, state what the video mentions."
    )

    user_prompt = f"""{history_str}VIDEO TRANSCRIPT CONTEXT:
{context}

---
STUDENT QUESTION: {cleaned_q}

Provide a clear, educational, and accurate explanation based strictly on the transcript context above.
{video_instruction}

Always conclude with:
Source: Current video transcript
"""

    result = generate_completion(
        prompt=user_prompt,
        system_prompt=CHAT_SYSTEM_PROMPT,
        model=model,
        host=host,
        temperature=0.2,
        max_tokens=None,
    )

    if not result["success"]:
        return {
            "success": False,
            "answer": "",
            "source_type": "video",
            "source": "Current video transcript",
            "search_results": [],
            "model": result.get("model", ""),
            "error": result.get("error", "Failed to generate answer."),
        }

    # Branch 3: Reactive Dynamic Fallback
    # If the transcript response indicates insufficiency and web research is enabled:
    if is_transcript_insufficient(result["content"]) and mode != "Video Only":
        web_res = execute_web_research(
            question=cleaned_q,
            context=context,
            transcript=transcript,
            llm_prelim_answer=result["content"],
            model=model,
            host=host,
            max_search_results=max_search_results,
        )
        if web_res:
            return web_res

    # If in web research mode and response still contains the refusal message, clean it up
    final_answer = result["content"].strip()
    if mode == "Video + Web Research" and "switch to 'Video + Web Research' mode" in final_answer:
        final_answer = final_answer.replace(
            "You may switch to 'Video + Web Research' mode for external knowledge.",
            "External web research did not return additional details for this specific inquiry."
        )

    return {
        "success": True,
        "answer": final_answer,
        "source_type": "video",
        "source": "Current video transcript",
        "search_results": [],
        "model": result.get("model", ""),
        "error": None,
    }
