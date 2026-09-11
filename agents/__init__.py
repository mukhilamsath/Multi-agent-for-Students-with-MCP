"""
agents/__init__.py
═══════════════════════════════════════════════════════════════════════════════
Exports the specialist agent factories and metadata.
═══════════════════════════════════════════════════════════════════════════════
"""

from agents.study_agent import create_study_agent, AGENT_NAME as STUDY_AGENT_NAME
from agents.schedule_agent import create_schedule_agent, AGENT_NAME as SCHEDULE_AGENT_NAME
from agents.research_agent import create_research_agent, AGENT_NAME as RESEARCH_AGENT_NAME

__all__ = [
    "create_study_agent",
    "create_schedule_agent",
    "create_research_agent",
    "STUDY_AGENT_NAME",
    "SCHEDULE_AGENT_NAME",
    "RESEARCH_AGENT_NAME",
]
