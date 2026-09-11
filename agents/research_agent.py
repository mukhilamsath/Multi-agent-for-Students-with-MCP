"""
agents/research_agent.py
═══════════════════════════════════════════════════════════════════════════════
The Research Specialist Agent.

Built with Strands Agents SDK and Amazon Bedrock Guardrails.
Communicates with the orchestrator exclusively via the A2A protocol.
Connects to external web tools via the Model Context Protocol (MCP).

MCP Tools consumed:
    • search        — searches DuckDuckGo and returns relevant snippets & URLs
    • fetch_content — fetches and extracts clean readable text from online pages
    • expand_link   — resolves shortened link tokens to full URLs for citations

Responsibility:
    - Web research and information gathering
    - Finding recent articles, tutorials, documentation, and academic resources
    - Extracting clean content and providing source URLs
    - Summarizing findings clearly while distinguishing retrieved info from synthesis
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import Optional

from strands import Agent
from mcp_client import create_research_mcp_client
from guardrails import build_guarded_model
from session_manager import build_session_manager

logger = logging.getLogger(__name__)

AGENT_NAME = "Student Research Agent"
AGENT_DESCRIPTION = "Performs web research, searches the web, and extracts information from online sources via MCP tools."

_RESEARCH_SYSTEM_PROMPT = """
You are an expert academic research assistant helping a student gather information from the web.

You have access to tools provided through the Model Context Protocol (MCP):
  • search          — search DuckDuckGo for relevant online resources, articles, docs, or tutorials.
  • fetch_content   — fetch and extract clean, readable text or main content from a webpage URL or result token.
  • expand_link     — resolve shortened link tokens back into full URLs for citing.

Workflow & Rules:
  1. For research or search queries, call `search` with a targeted query.
  2. If deep details or specific reading material is needed, call `fetch_content` on the most relevant URLs or tokens found.
  3. Synthesize the findings into a clear, student-friendly response.
  4. Always cite source URLs clearly (e.g., "[Source: https://...]").
  5. Distinguish facts found in web sources from your own synthesis.
  6. If the request is not research/web-related, reply:
     "NOT_RESEARCH: This request is outside my specialty."
  7. Keep your summary structured, accurate, and easy to read.
""".strip()


def create_research_agent(session_id: Optional[str] = None) -> Agent:
    """
    Factory function to build a Strands Research Agent powered by MCP tools.

    Args:
        session_id: Unique identifier for the conversation session.
                    If provided, attaches session persistence for multi-turn history.

    Returns:
        Configured Strands Agent instance connected to the DuckDuckGo MCP server.
    """
    logger.info("Building Research Agent with MCP tools  |  session_id=%r", session_id)

    model = build_guarded_model(temperature=0.2, streaming=False)

    # Initialize the MCP client for the DuckDuckGo MCP server
    mcp_client = create_research_mcp_client(continue_on_error=True)

    agent_kwargs = dict(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        model=model,
        system_prompt=_RESEARCH_SYSTEM_PROMPT,
        tools=[mcp_client],
        callback_handler=None,  # silent — output flows through A2A
    )

    if session_id and not session_id.startswith("__"):
        # Attach session manager for conversation memory across turns
        agent_kwargs["session_manager"] = build_session_manager(f"{session_id}_research")

    return Agent(**agent_kwargs)
