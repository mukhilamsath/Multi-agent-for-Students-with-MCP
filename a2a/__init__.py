"""
a2a/__init__.py
═══════════════════════════════════════════════════════════════════════════════
A2A protocol package for agent-to-agent communication.
Extends installed a2a-sdk namespace while providing project-level A2A client & cards.
═══════════════════════════════════════════════════════════════════════════════
"""

from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

from .cards import (
    STUDY_AGENT_CARD,
    SCHEDULE_AGENT_CARD,
    RESEARCH_AGENT_CARD,
    AGENT_CARDS,
)
from .client_manager import (
    A2AClientManager,
    send_a2a_message,
    send_a2a_message_sync,
)

__all__ = [
    "STUDY_AGENT_CARD",
    "SCHEDULE_AGENT_CARD",
    "RESEARCH_AGENT_CARD",
    "AGENT_CARDS",
    "A2AClientManager",
    "send_a2a_message",
    "send_a2a_message_sync",
]
