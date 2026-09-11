"""
agents/servers/__init__.py
═══════════════════════════════════════════════════════════════════════════════
Exports A2A servers and ASGI applications for all specialist agents.
═══════════════════════════════════════════════════════════════════════════════
"""

from agents.servers.study_server import get_study_server, get_study_app
from agents.servers.schedule_server import get_schedule_server, get_schedule_app
from agents.servers.research_server import get_research_server, get_research_app

__all__ = [
    "get_study_server",
    "get_study_app",
    "get_schedule_server",
    "get_schedule_app",
    "get_research_server",
    "get_research_app",
]
