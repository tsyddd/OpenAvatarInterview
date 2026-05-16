from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any


def search_duckduckgo(query: str, num_results: int = 5) -> list[dict[str, str]]:
    """Search using DuckDuckGo Instant Answer API (no API key needed)."""
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results: list[dict[str, str]] = []

        # Abstract
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", query),
                "url": data.get("AbstractURL", ""),
                "snippet": data["AbstractText"],
            })

        # Related topics
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:80],
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", ""),
                })

        return results[:num_results]
    except Exception:
        return []


def search(query: str, num_results: int = 5, provider: str = "duckduckgo", api_key: str | None = None) -> list[dict[str, str]]:
    """Search the web for interview-relevant information.

    Args:
        query: Search query string.
        num_results: Maximum number of results to return.
        provider: Search provider ("duckduckgo" or "tavily").
        api_key: API key for paid providers (optional).

    Returns:
        List of dicts with "title", "url", "snippet" keys.
    """
    if provider == "tavily" and api_key:
        return _search_tavily(query, num_results, api_key)
    return search_duckduckgo(query, num_results)


def _search_tavily(query: str, num_results: int, api_key: str) -> list[dict[str, str]]:
    """Search using Tavily API."""
    try:
        url = "https://api.tavily.com/search"
        payload = json.dumps({
            "query": query,
            "max_results": num_results,
            "api_key": api_key,
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")[:200],
            }
            for r in data.get("results", [])[:num_results]
        ]
    except Exception:
        return []
