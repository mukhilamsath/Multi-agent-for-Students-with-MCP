"""
servers/study_mcp/server.py
═══════════════════════════════════════════════════════════════════════════════
Open-Source Study & Concept Explanation MCP Server.

A lightweight, dedicated Model Context Protocol (MCP) server providing
concept explanations, academic topic summaries, study tips, and quiz generation
for the Student Assistant Study Agent.

Protocol: Standard MCP 2.x JSON-RPC over stdio.
═══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import logging
import sys
import httpx
from typing import Any, Dict, List, Optional
from mcp.server.mcpserver import MCPServer

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("study-mcp-server")

server = MCPServer(
    name="study-concept-mcp",
    instructions=(
        "You are a study and academic concept explanation MCP server. "
        "Use `explain_concept` to retrieve structured academic explanations and definitions. "
        "Use `generate_study_quiz` to create practice quizzes for students. "
        "Use `get_concept_summary` for fast bulleted summaries and analogies. "
        "Use `get_study_tips` to get learning tips for difficult topics."
    ),
)

_HEADERS = {
    "User-Agent": "StudentAssistant-StudyMCP/2.0 (Academic Study Bot; mailto:student@assistant.local)",
    "Accept": "application/json",
}


def _fetch_wikipedia_summary(topic: str) -> Optional[str]:
    """Fetch encyclopedia summary from Wikipedia API with proper User-Agent."""
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + httpx.URL(topic).path
        with httpx.Client(timeout=8.0, headers=_HEADERS, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                extract = data.get("extract", "")
                if extract:
                    return extract
    except Exception as exc:
        logger.warning("Wikipedia API fetch notice for %r: %s", topic, exc)
    return None


@server.tool()
def explain_concept(concept: str, level: str = "beginner") -> Dict[str, Any]:
    """
    Explain an academic concept, scientific law, math topic, historical event, or programming idea.

    Args:
        concept: The subject or concept to explain (e.g. "Photosynthesis", "Newton's Laws", "Binary Search").
        level: Depth level - "beginner", "intermediate", or "advanced". Default is "beginner".

    Returns:
        Structured dictionary containing definition, explanation prompt, level, and background knowledge.
    """
    logger.info("explain_concept called | concept=%r level=%r", concept, level)
    clean_level = level.lower().strip()
    if clean_level not in {"beginner", "intermediate", "advanced"}:
        clean_level = "beginner"

    depth_instructions = {
        "beginner": "Use simple vocabulary, avoid unnecessary jargon, and provide a clear real-world analogy.",
        "intermediate": "Assume high-school knowledge. Use precise academic terminology and explain mechanism step-by-step.",
        "advanced": "Provide deep technical breakdown, mathematical or architectural formulation, and edge cases.",
    }

    # Fetch reference background if available
    wiki_summary = _fetch_wikipedia_summary(concept)

    return {
        "concept": concept,
        "level": clean_level,
        "depth_guideline": depth_instructions[clean_level],
        "reference_summary": wiki_summary or f"Core concept: {concept}",
        "structure": [
            "1. Clear, concise 1-2 sentence definition",
            "2. Core principles / how it works in bullet points",
            "3. Intuitive real-life example or analogy",
            "4. Why it matters in academic study",
        ],
    }


@server.tool()
def generate_study_quiz(topic: str, num_questions: int = 3, difficulty: str = "medium") -> Dict[str, Any]:
    """
    Generate multiple-choice practice quiz questions and test context for a student.

    Args:
        topic: The academic topic to create quiz questions for.
        num_questions: Number of questions (1 to 5). Default is 3.
        difficulty: "easy", "medium", or "hard". Default is "medium".

    Returns:
        Dictionary with quiz template, question specifications, and evaluation guidelines.
    """
    logger.info("generate_study_quiz called | topic=%r num_questions=%d", topic, num_questions)
    clamped_num = max(1, min(5, num_questions))

    return {
        "topic": topic,
        "num_questions": clamped_num,
        "difficulty": difficulty,
        "instructions": (
            f"Generate a {clamped_num}-question multiple choice quiz on '{topic}' at {difficulty} difficulty. "
            "For each question, include: Question prompt, 4 options labeled A) through D), the correct answer, "
            "and a 1-sentence explanation of why the correct option is right."
        ),
    }


@server.tool()
def get_concept_summary(concept: str) -> Dict[str, Any]:
    """
    Get a high-signal bulleted summary and key takeaways for quick revision.

    Args:
        concept: The topic to summarize.

    Returns:
        Structured summary framework with reference background.
    """
    logger.info("get_concept_summary called | concept=%r", concept)
    wiki_summary = _fetch_wikipedia_summary(concept)
    return {
        "concept": concept,
        "overview": wiki_summary or f"Academic overview for {concept}",
        "format": "Provide 3-5 bulleted core takeaways, key formulas/definitions, and a one-sentence summary.",
    }


@server.tool()
def get_study_tips(topic: str) -> Dict[str, Any]:
    """
    Get tailored study recommendations, mnemonics, and retention advice for a specific subject.

    Args:
        topic: The topic or field of study.

    Returns:
        Learning techniques and study tips.
    """
    logger.info("get_study_tips called | topic=%r", topic)
    return {
        "topic": topic,
        "recommended_techniques": [
            "Active Recall: Test yourself without looking at notes.",
            "Feynman Technique: Explain the concept in plain words as if teaching a beginner.",
            "Spaced Repetition: Revisit after 1 day, 3 days, and 7 days.",
        ],
    }


if __name__ == "__main__":
    server.run(transport="stdio")
