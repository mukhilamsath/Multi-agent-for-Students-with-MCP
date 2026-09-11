"""
tools/__init__.py
═══════════════════════════════════════════════════════════════════════════════
Exports all tools used by the specialist agents.
═══════════════════════════════════════════════════════════════════════════════
"""

from tools.study_tools import explain_topic, generate_quiz
from tools.schedule_tools import add_task, view_schedule
from tools.research_tools import search_web, scrape_webpage, extract_page_content

__all__ = [
    "explain_topic",
    "generate_quiz",
    "add_task",
    "view_schedule",
    "search_web",
    "scrape_webpage",
    "extract_page_content",
]
