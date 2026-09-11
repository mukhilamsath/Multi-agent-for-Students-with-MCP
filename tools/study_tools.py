"""
tools/study_tools.py
═══════════════════════════════════════════════════════════════════════════════
Two study-focused tools that the Study Agent uses:

  explain_topic  — returns a structured explanation of any academic topic
  generate_quiz  — generates a short multiple-choice quiz on a topic

Both tools are pure Python functions decorated with @tool.
The Study Agent's LLM calls them; you never call them directly.

Why two tools instead of one?
    Explaining and quizzing are different cognitive tasks that benefit from
    different prompts and different return shapes.  Keeping them separate
    also lets the LLM choose the right one based on the student's request
    ("explain X" vs "quiz me on X").
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from strands import tool

logger = logging.getLogger(__name__)


@tool
def explain_topic(topic: str, level: str = "beginner") -> dict:
    """
    Return a structured explanation of an academic topic at the requested level.

    Use this tool when the student asks to understand, learn, summarise, or
    get an explanation of any subject — maths concept, historical event,
    scientific principle, programming idea, literary term, etc.

    Args:
        topic: The subject to explain, e.g. "photosynthesis", "quadratic
               equations", "World War 2 causes", "Python list comprehensions".
        level: The target depth of the explanation.
               Allowed values: "beginner", "intermediate", "advanced".
               Default is "beginner".

    Returns:
        A dict with keys:
          topic   — the subject as given
          level   — the depth level used
          prompt  — a ready-made instruction string the LLM should use to
                    compose the actual explanation
    """
    logger.info("explain_topic called  |  topic=%r  level=%r", topic, level)

    level = level.lower()
    if level not in {"beginner", "intermediate", "advanced"}:
        level = "beginner"

    # We return a prompt string rather than hard-coding the answer here.
    # The Study Agent's LLM reads this prompt and writes the real explanation,
    # which keeps the tool lightweight and the explanation high-quality.
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

    logger.info("explain_topic ready   |  prompt length=%d chars", len(prompt))
    return {"topic": topic, "level": level, "prompt": prompt}


@tool
def generate_quiz(topic: str, num_questions: int = 3) -> dict:
    """
    Generate a short multiple-choice quiz to test the student on a topic.

    Use this tool when the student asks to be tested, quizzed, or wants
    practice questions on any subject.

    Args:
        topic: The subject to create quiz questions about, e.g. "the French
               Revolution", "Newton's laws of motion", "Python dictionaries".
        num_questions: How many questions to include.
                       Must be between 1 and 5 (inclusive).
                       Default is 3.

    Returns:
        A dict with keys:
          topic         — the subject as given
          num_questions — the number of questions requested
          prompt        — a ready-made instruction string the LLM should use
                          to compose the actual quiz questions
    """
    logger.info("generate_quiz called  |  topic=%r  questions=%d", topic, num_questions)

    # Clamp to a sensible range so we never ask for 0 or 50 questions.
    num_questions = max(1, min(5, num_questions))

    prompt = (
        f"Create a {num_questions}-question multiple-choice quiz about '{topic}'. "
        f"For each question: write the question, provide 4 options labelled A–D, "
        f"and clearly mark the correct answer. "
        f"After all questions, add a brief 'Why it matters' sentence about the topic."
    )

    logger.info("generate_quiz ready   |  prompt length=%d chars", len(prompt))
    return {"topic": topic, "num_questions": num_questions, "prompt": prompt}
