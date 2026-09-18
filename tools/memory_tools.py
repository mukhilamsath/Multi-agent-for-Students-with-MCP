"""
tools/memory_tools.py
═══════════════════════════════════════════════════════════════════════════════
Native Python Tools for Long-Term Memory (LTM) interaction.
Equips Strands agents with tools to explicitly remember and recall student facts,
preferences, and learning history across sessions.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import Any, Dict

from strands import tool
from memory.long_term_memory import get_long_term_memory

logger = logging.getLogger(__name__)


@tool
def remember_student_preference(key: str, value: str) -> Dict[str, Any]:
    """
    Store or update a student's long-term learning preference (e.g., preferred difficulty, explanation style, target exam).

    Args:
        key: The preference category (e.g. 'explanation_style', 'difficulty', 'target_exam', 'favorite_subject').
        value: The value to store (e.g. 'concise with bullet points', 'beginner', 'May 2026 Finals').

    Returns:
        Status dictionary confirming the preference was saved.
    """
    logger.info("memory_tools | remember_student_preference: %r -> %r", key, value)
    ltm = get_long_term_memory()
    success = ltm.store_preference(key=key, value=value)
    return {
        "status": "success" if success else "failed",
        "message": f"Successfully remembered student preference: {key} = {value}",
    }


@tool
def remember_student_fact(fact: str, category: str = "general") -> Dict[str, Any]:
    """
    Remember an important fact, goal, or detail about the student that should persist across sessions.

    Args:
        fact: The statement or detail to remember (e.g. 'Student is preparing for AP Biology exam', 'Struggles with calculus integration').
        category: The category for this fact (e.g. 'goals', 'academic', 'general').

    Returns:
        Status dictionary confirming the fact was remembered.
    """
    logger.info("memory_tools | remember_student_fact: [%s] %r", category, fact)
    ltm = get_long_term_memory()
    success = ltm.remember_fact(fact=fact, category=category)
    return {
        "status": "success" if success else "failed",
        "message": f"Successfully saved to long-term memory: {fact}",
    }


@tool
def recall_student_memory(query: str) -> Dict[str, Any]:
    """
    Search and recall relevant facts, preferences, and past studied topics from long-term memory.

    Args:
        query: Search keywords or topic to look up in long-term memory.

    Returns:
        Dictionary containing matched memory items.
    """
    logger.info("memory_tools | recall_student_memory for query: %r", query)
    ltm = get_long_term_memory()
    results = ltm.search_memories(query=query, limit=5)
    return {
        "status": "success",
        "count": len(results),
        "results": results,
    }
