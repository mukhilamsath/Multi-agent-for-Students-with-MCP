"""
tools/research_tools.py
═══════════════════════════════════════════════════════════════════════════════
Web research tools (Legacy reference).

NOTE:
As of the MCP migration, the Research Agent connects directly to the open-source
Model Context Protocol (MCP) server `duckduckgo-mcp-server` via `mcp.client`.
The MCP server exposes standard `search`, `fetch_content`, and `expand_link`
tools over MCP stdio transport.

These standalone Python functions are preserved for backwards compatibility and
testing fallbacks.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import re
from typing import Any
import httpx
from bs4 import BeautifulSoup
from strands import tool

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 StudentAssistant/2.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


@tool
def search_web(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Legacy local search tool (Replaced by MCP `search` tool).
    """
    logger.info("search_web called  |  query=%r  max_results=%d", query, max_results)
    max_results = max(1, min(10, max_results))

    results: list[dict[str, str]] = []

    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        raw_results = list(ddgs.text(query, max_results=max_results))
        for item in raw_results:
            results.append({
                "title": item.get("title", "No title"),
                "url": item.get("href") or item.get("link", ""),
                "snippet": item.get("body") or item.get("snippet", ""),
            })
    except Exception as exc:
        logger.warning("duckduckgo_search library encountered an issue (%s), attempting HTTP fallback", exc)

    if not results:
        try:
            with httpx.Client(timeout=10.0, headers=_DEFAULT_HEADERS, follow_redirects=True) as client:
                resp = client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    links = soup.select(".result__body")
                    for link in links[:max_results]:
                        title_elem = link.select_one(".result__title a")
                        snippet_elem = link.select_one(".result__snippet")
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            raw_href = title_elem.get("href", "")
                            match = re.search(r"uddg=([^&]+)", raw_href)
                            if match:
                                from urllib.parse import unquote
                                url = unquote(match.group(1))
                            else:
                                url = raw_href
                            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                            results.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet,
                            })
        except Exception as exc:
            logger.error("HTTP search fallback also failed: %s", exc)

    if not results:
        return {
            "query": query,
            "total_results": 0,
            "results": [],
            "status": "no_results_or_offline",
            "message": f"No web search results found for '{query}'.",
        }

    return {
        "query": query,
        "total_results": len(results),
        "results": results,
        "status": "success",
    }


@tool
def scrape_webpage(url: str) -> dict[str, Any]:
    """
    Legacy local scrape tool (Replaced by MCP `fetch_content` tool).
    """
    logger.info("scrape_webpage called  |  url=%r", url)

    if not (url.startswith("http://") or url.startswith("https://")):
        return {
            "url": url,
            "status": "error",
            "message": "Invalid URL: must start with http:// or https://",
        }

    try:
        with httpx.Client(timeout=12.0, headers=_DEFAULT_HEADERS, follow_redirects=True) as client:
            resp = client.get(url)
            status_code = resp.status_code
            content_type = resp.headers.get("content-type", "")

            if status_code != 200:
                return {
                    "url": url,
                    "status_code": status_code,
                    "status": "error",
                    "message": f"HTTP request returned status code {status_code}",
                }

            return {
                "url": url,
                "status_code": status_code,
                "content_type": content_type,
                "raw_text": resp.text[:3000],
                "status": "success",
            }
    except Exception as exc:
        logger.error("scrape_webpage failed for %r: %s", url, exc)
        return {
            "url": url,
            "status": "error",
            "message": f"Failed to scrape webpage: {str(exc)}",
        }


@tool
def extract_page_content(url: str, max_chars: int = 4000) -> dict[str, Any]:
    """
    Legacy local page extractor (Replaced by MCP `fetch_content` tool).
    """
    logger.info("extract_page_content called  |  url=%r  max_chars=%d", url, max_chars)
    max_chars = max(500, min(10000, max_chars))

    if not (url.startswith("http://") or url.startswith("https://")):
        return {
            "url": url,
            "status": "error",
            "message": "Invalid URL: must start with http:// or https://",
        }

    try:
        with httpx.Client(timeout=12.0, headers=_DEFAULT_HEADERS, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return {
                    "url": url,
                    "status_code": resp.status_code,
                    "status": "error",
                    "message": f"HTTP request returned status code {resp.status_code}",
                }

            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"

            for elem in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg"]):
                elem.decompose()

            body = soup.find("main") or soup.find("article") or soup.find("body") or soup
            lines = (line.strip() for line in body.get_text().splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = "\n".join(chunk for chunk in chunks if chunk)
            trimmed_text = clean_text[:max_chars]

            return {
                "url": url,
                "title": title,
                "text": trimmed_text,
                "char_count": len(trimmed_text),
                "status": "success",
            }
    except Exception as exc:
        logger.error("extract_page_content failed for %r: %s", url, exc)
        return {
            "url": url,
            "status": "error",
            "message": f"Failed to extract page content: {str(exc)}",
        }
