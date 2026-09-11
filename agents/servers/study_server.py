"""
agents/servers/study_server.py
═══════════════════════════════════════════════════════════════════════════════
A2A Server exposing the Study Agent via the standard A2A protocol.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from strands.multiagent.a2a import A2AServer
from agents.study_agent import create_study_agent

logger = logging.getLogger(__name__)

_study_server: A2AServer | None = None


def get_study_server() -> A2AServer:
    """Return a singleton A2AServer instance for the Study Agent."""
    global _study_server
    if _study_server is None:
        logger.info("Initializing Study Agent A2AServer")
        _study_server = A2AServer(
            agent_factory=create_study_agent,
            port=9001,
            enable_a2a_compliant_streaming=True,
        )
    return _study_server


def get_study_app():
    """Return the ASGI/Starlette application for the Study Agent A2A server."""
    return get_study_server().to_starlette_app()


if __name__ == "__main__":
    server = get_study_server()
    print("Starting Study Agent A2A server on port 9001...")
    server.serve(port=9001)
