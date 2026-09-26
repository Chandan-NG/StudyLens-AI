"""Web search service for StudyLens AI using DuckDuckGo."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo and return a list of standardized results.
    
    Each result dictionary contains:
    - 'title': Title of the web page
    - 'url': Direct URL
    - 'snippet': Short informative snippet
    
    Handles failures gracefully without crashing.
    """
    cleaned_query = query.strip() if query else ""
    if not cleaned_query:
        return []

    if DDGS is None:
        logger.warning("Neither ddgs nor duckduckgo_search is installed.")
        return []

    results: List[Dict[str, str]] = []
    try:
        with DDGS(timeout=8) as ddgs:
            raw_results = ddgs.text(
                cleaned_query,
                max_results=max_results,
            )
            for item in raw_results:
                title = str(item.get("title", "")).strip()
                url = str(item.get("href") or item.get("link") or item.get("url", "")).strip()
                snippet = str(item.get("body") or item.get("snippet", "")).strip()

                if title and url:
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                    })

    except Exception as exc:
        logger.warning("DuckDuckGo search encountered an issue: %s", exc)

    return results


def format_search_results_for_llm(results: List[Dict[str, str]]) -> str:
    """Format structured web search results into clean markdown for the LLM prompt."""
    if not results:
        return "No external web search results found."

    formatted = []
    for idx, r in enumerate(results, start=1):
        formatted.append(
            f"[{idx}] Title: {r['title']}\n"
            f"    URL: {r['url']}\n"
            f"    Snippet: {r['snippet']}"
        )
    return "\n\n".join(formatted)
