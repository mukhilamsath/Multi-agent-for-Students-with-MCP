"""
tools/study_tools.py
═══════════════════════════════════════════════════════════════════════════════
Study tools (Legacy reference).

NOTE:
As of the Study MCP migration, the Study Agent connects directly to the dedicated
Model Context Protocol (MCP) server `servers/study_mcp/server.py` via `mcp_client`.
The MCP server exposes standard `explain_concept`, `generate_study_quiz`,
`get_concept_summary`, and `get_study_tips` tools over MCP stdio transport.

These standalone Python functions are preserved for backwards compatibility and
testing fallbacks.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from strands import tool

logger = logging.getLogger(__name__)


@tool
def explain_topic(topic: str, level: str = "beginner") -> dict:
    """
    Legacy local study tool (Replaced by MCP `explain_concept` tool).
    """
    logger.info("explain_topic called  |  topic=%r  level=%r", topic, level)

    level = level.lower()
    if level not in {"beginner", "intermediate", "advanced"}:
        level = "beginner"

    depth_instructions = {
        "beginner":     "Use simple language, avoid jargon, and include a real-life analogy.",
        "intermediate": "Assume basic prior knowledge. Use correct terminology with brief definitions.",
        "advanced":     "Use technical language, include edge cases, and mention current research where relevant.",
    }

    prompt = (
        f"Please explain '{topic}' at a {level} level. "
        f"{depth_instructions[level]} "
        f"Structure your answer with: (1) a one-sentence definition, "
        f"(2) the key ideas in bullet points, "
        f"(3) a concrete example."
    )

    return {"topic": topic, "level": level, "prompt": prompt}


@tool
def generate_quiz(topic: str, num_questions: int = 3) -> dict:
    """
    Legacy local quiz tool (Replaced by MCP `generate_study_quiz` tool).
    """
    logger.info("generate_quiz called  |  topic=%r  questions=%d", topic, num_questions)
    num_questions = max(1, min(5, num_questions))

    prompt = (
        f"Create a {num_questions}-question multiple-choice quiz about '{topic}'. "
        f"For each question: write the question, provide 4 options labelled A–D, "
        f"and clearly mark the correct answer. "
        f"After all questions, add a brief 'Why it matters' sentence about the topic."
    )

    return {"topic": topic, "num_questions": num_questions, "prompt": prompt}
