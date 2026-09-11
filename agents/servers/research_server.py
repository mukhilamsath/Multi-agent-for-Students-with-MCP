"""
agents/servers/research_server.py
═══════════════════════════════════════════════════════════════════════════════
A2A Server exposing the Research Agent via the standard A2A protocol.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from strands.multiagent.a2a import A2AServer
from agents.research_agent import create_research_agent

logger = logging.getLogger(__name__)

_research_server: A2AServer | None = None


def get_research_server() -> A2AServer:
    """Return a singleton A2AServer instance for the Research Agent."""
    global _research_server
    if _research_server is None:
        logger.info("Initializing Research Agent A2AServer")
        _research_server = A2AServer(
            agent_factory=create_research_agent,
            port=9003,
            enable_a2a_compliant_streaming=True,
        )
    return _research_server


def get_research_app():
    """Return the ASGI/Starlette application for the Research Agent A2A server."""
    return get_research_server().to_starlette_app()


if __name__ == "__main__":
    server = get_research_server()
    print("Starting Research Agent A2A server on port 9003...")
    server.serve(port=9003)
