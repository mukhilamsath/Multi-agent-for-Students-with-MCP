"""
agents/servers/schedule_server.py
═══════════════════════════════════════════════════════════════════════════════
A2A Server exposing the Schedule Agent via the standard A2A protocol.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from strands.multiagent.a2a import A2AServer
from agents.schedule_agent import create_schedule_agent

logger = logging.getLogger(__name__)

_schedule_server: A2AServer | None = None


def get_schedule_server() -> A2AServer:
    """Return a singleton A2AServer instance for the Schedule Agent."""
    global _schedule_server
    if _schedule_server is None:
        logger.info("Initializing Schedule Agent A2AServer")
        _schedule_server = A2AServer(
            agent_factory=create_schedule_agent,
            port=9002,
            enable_a2a_compliant_streaming=True,
        )
    return _schedule_server


def get_schedule_app():
    """Return the ASGI/Starlette application for the Schedule Agent A2A server."""
    return get_schedule_server().to_starlette_app()


if __name__ == "__main__":
    server = get_schedule_server()
    print("Starting Schedule Agent A2A server on port 9002...")
    server.serve(port=9002)
