"""
agents/study_agent.py
═══════════════════════════════════════════════════════════════════════════════
The Study Specialist Agent.

Built with Strands Agents SDK and Amazon Bedrock Guardrails.
Powered by Amazon Nova (amazon.nova-micro-v1:0).
Communicates with the orchestrator exclusively via the A2A protocol.
Connects to academic study tools as decorated Python functions (@mcp_tool)
without exposing raw URLs or connection endpoints directly.

MCP Tools connected:
    • explain_concept      — retrieves structured academic explanations & reference summaries via MCP
    • generate_study_quiz  — generates practice multiple-choice quizzes via MCP
    • get_concept_summary  — provides bulleted core takeaways and analogies via MCP
    • get_study_tips       — provides subject-specific study advice and memory techniques via MCP

Responsibility:
    - Explaining concepts, scientific principles, math topics, and academic subjects
    - Academic question answering and tutoring
    - Generating practice quizzes and test preparation
    - Providing study summaries and retention techniques
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import Any, Dict, Optional

from strands import Agent
from mcp_client import mcp_tool
from guardrails import build_guarded_model
from session_manager import build_session_manager

logger = logging.getLogger(__name__)

AGENT_NAME = "Student Study Agent"
AGENT_DESCRIPTION = "Handles academic learning, topic explanations, concept summaries, and practice quizzes via MCP tools."

# ── Decorated MCP Tool Functions (No raw URLs or transports exposed) ─────────

@mcp_tool(server_name="study", tool_name="explain_concept")
def explain_concept(concept: str, level: str = "beginner") -> Dict[str, Any]:
    """
    Explain an academic concept, scientific law, math topic, historical event, or theory using Study MCP.

    Args:
        concept: The subject or concept to explain (e.g. "Photosynthesis", "Newton's Laws", "Binary Search").
        level: Depth level - "beginner", "intermediate", or "advanced". Default is "beginner".
    """
    pass


@mcp_tool(server_name="study", tool_name="generate_study_quiz")
def generate_study_quiz(topic: str, num_questions: int = 3, difficulty: str = "medium") -> Dict[str, Any]:
    """
    Generate multiple-choice practice quiz questions and test context for a student using Study MCP.

    Args:
        topic: The academic topic to create quiz questions for.
        num_questions: Number of questions (1 to 5). Default is 3.
        difficulty: "easy", "medium", or "hard". Default is "medium".
    """
    pass


@mcp_tool(server_name="study", tool_name="get_concept_summary")
def get_concept_summary(concept: str) -> Dict[str, Any]:
    """
    Get a high-signal bulleted summary and key takeaways for quick revision using Study MCP.

    Args:
        concept: The topic to summarize.
    """
    pass


@mcp_tool(server_name="study", tool_name="get_study_tips")
def get_study_tips(topic: str) -> Dict[str, Any]:
    """
    Get tailored study recommendations, mnemonics, and retention advice for a specific subject using Study MCP.

    Args:
        topic: The topic or field of study.
    """
    pass


_STUDY_SYSTEM_PROMPT = """
You are an expert academic tutor helping a student learn effectively and master academic concepts.

You have access to tools connected via the Model Context Protocol (MCP):
  • explain_concept      — call this when the student wants an explanation, definition,
                           or deep dive into any academic topic, concept, or theory.
  • generate_study_quiz  — call this when the student wants to be tested, quizzed,
                           or wants practice questions on any topic.
  • get_concept_summary  — call this when the student wants quick bullet points,
                           formulas, or a fast revision summary.
  • get_study_tips       — call this when the student asks for study advice, memory
                           techniques, or tips on mastering difficult material.

Workflow & Rules:
  1. For explanations, call `explain_concept` with the subject and inferred level ("beginner", "intermediate", or "advanced").
  2. For quiz requests, call `generate_study_quiz` with the topic and requested number of questions (default 3).
  3. Synthesize the tool result into a clear, student-friendly, and encouraging explanation or quiz.
  4. Always present explanations with:
     - Clear, intuitive definition
     - Core concepts / bullet points
     - Concrete real-world example or analogy
  5. End every explanation with: "💡 Tip: ask me to quiz you on this topic!"
     End every quiz with: "✅ Done! Ask me to explain any question you got wrong."
  6. If the request is not academic/study-related, reply:
     "NOT_STUDY: This request is outside my specialty."
""".strip()


def create_study_agent(session_id: Optional[str] = None) -> Agent:
    """
    Factory function to build a Strands Study Agent powered by decorated MCP tool functions.

    Args:
        session_id: Unique identifier for the conversation session.
                    If provided, attaches session persistence for multi-turn history.

    Returns:
        Configured Strands Agent instance.
    """
    logger.info("Building Study Agent with decorated MCP tools | session_id=%r", session_id)

    model = build_guarded_model(temperature=0.3, streaming=False)

    agent_kwargs = dict(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        model=model,
        system_prompt=_STUDY_SYSTEM_PROMPT,
        tools=[explain_concept, generate_study_quiz, get_concept_summary, get_study_tips],
        callback_handler=None,  # silent — output flows through A2A
    )

    if session_id and not session_id.startswith("__"):
        # Attach session manager for conversation memory across turns
        agent_kwargs["session_manager"] = build_session_manager(f"{session_id}_study")

    return Agent(**agent_kwargs)
