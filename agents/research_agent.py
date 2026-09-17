"""
agents/research_agent.py
═══════════════════════════════════════════════════════════════════════════════
The Research Specialist Agent.

Built with Strands Agents SDK and Amazon Bedrock Guardrails.
Communicates with the orchestrator exclusively via the A2A protocol.
Connects to external MCP tools as decorated Python functions (@mcp_tool)
without exposing raw URLs or connection endpoints directly.

MCP Tools connected:
    • search_web            — searches DuckDuckGo via MCP and returns relevant snippets & URLs
    • fetch_page_content    — fetches and extracts clean readable text from online pages via MCP
    • expand_shortened_link — resolves shortened link tokens to full URLs for citations via MCP

Responsibility:
    - Web research and information gathering
    - Finding recent articles, tutorials, documentation, and academic resources
    - Extracting clean content and providing source URLs
    - Summarizing findings clearly while distinguishing retrieved info from synthesis
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import Any, Dict, Optional

from strands import Agent
from mcp_client import mcp_tool
from guardrails import build_guarded_model
from session_manager import build_session_manager

logger = logging.getLogger(__name__)

AGENT_NAME = "Student Research Agent"
AGENT_DESCRIPTION = "Performs web research, searches the web, and extracts information from online sources via MCP tools."

# ── Decorated MCP Tool Functions (No raw URLs or transports exposed) ─────────

@mcp_tool(server_name="duckduckgo", tool_name="search")
def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the web using DuckDuckGo MCP tool for up-to-date information, articles, documentation, or tutorials.

    Args:
        query: The search query string.
        max_results: Maximum number of search results to return (1 to 10). Default is 5.
    """
    pass


@mcp_tool(server_name="duckduckgo", tool_name="fetch_content")
def fetch_page_content(url: str, max_length: int = 8000) -> Dict[str, Any]:
    """
    Fetch and extract clean, readable text content from a webpage URL using MCP.

    Args:
        url: The full webpage URL (starting with http:// or https://) or a result token.
        max_length: Maximum characters of extracted text to return. Default is 8000.
    """
    pass


@mcp_tool(server_name="duckduckgo", tool_name="expand_link")
def expand_shortened_link(token: str) -> Dict[str, Any]:
    """
    Expand a shortened link token from search results back into the full URL using MCP.

    Args:
        token: A link token exactly as it appeared in search results.
    """
    pass


_RESEARCH_SYSTEM_PROMPT = """
You are an expert academic research assistant helping a student gather information from the web.

You have access to three tools connected via the Model Context Protocol (MCP):
  • search_web            — search DuckDuckGo for relevant online resources, articles, docs, or tutorials.
  • fetch_page_content    — fetch and extract clean, readable text from a webpage URL or result token.
  • expand_shortened_link — resolve shortened link tokens back into full URLs for citing.

Workflow & Rules:
  1. For research or search queries, call `search_web` with a targeted query.
  2. If deep details or specific reading material is needed, call `fetch_page_content` on the most relevant URLs or tokens found.
  3. Synthesize the findings into a clear, student-friendly response.
  4. Always cite source URLs clearly (e.g., "[Source: https://...]").
  5. Distinguish facts found in web sources from your own synthesis.
  6. If the request is not research/web-related, reply:
     "NOT_RESEARCH: This request is outside my specialty."
  7. Keep your summary structured, accurate, and easy to read.
""".strip()


def create_research_agent(session_id: Optional[str] = None) -> Agent:
    """
    Factory function to build a Strands Research Agent powered by decorated MCP tool functions.

    Args:
        session_id: Unique identifier for the conversation session.
                    If provided, attaches session persistence for multi-turn history.

    Returns:
        Configured Strands Agent instance.
    """
    logger.info("Building Research Agent with decorated MCP tools | session_id=%r", session_id)

    model = build_guarded_model(temperature=0.2, streaming=False)

    agent_kwargs = dict(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        model=model,
        system_prompt=_RESEARCH_SYSTEM_PROMPT,
        tools=[search_web, fetch_page_content, expand_shortened_link],
        callback_handler=None,  # silent — output flows through A2A
    )

    if session_id and not session_id.startswith("__"):
        # Attach session manager for conversation memory across turns
        agent_kwargs["session_manager"] = build_session_manager(f"{session_id}_research")

    return Agent(**agent_kwargs)
