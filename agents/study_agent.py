"""
agents/study_agent.py
═══════════════════════════════════════════════════════════════════════════════
The Study Specialist Agent.

Built with Strands Agents SDK and Amazon Bedrock Guardrails.
Communicates with the orchestrator exclusively via the A2A protocol.

Tools owned:
    • explain_topic  — structures a topic explanation at a chosen depth level
    • generate_quiz  — builds a multiple-choice quiz on any subject

Responsibility:
    - Explanations of concepts and academic topics
    - Academic question answering
    - Summaries of learning materials
    - Quiz generation and practice questions
    - Learning assistance
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import Optional

from strands import Agent
from tools.study_tools import explain_topic, generate_quiz
from guardrails import build_guarded_model
from session_manager import build_session_manager

logger = logging.getLogger(__name__)

AGENT_NAME = "Student Study Agent"
AGENT_DESCRIPTION = "Handles academic learning, topic explanations, summaries, and quizzes."

_STUDY_SYSTEM_PROMPT = """
You are an expert study tutor helping a student learn effectively.

You have two tools:
  • explain_topic  — call this when the student wants an explanation,
                     summary, or overview of any academic topic.
  • generate_quiz  — call this when the student wants to be tested,
                     quizzed, or wants practice questions.

Workflow:
  1. Call the appropriate tool with the topic extracted from the request.
     For explain_topic, also infer the level: "beginner" if unspecified.
     For generate_quiz, use 3 questions unless told otherwise.
  2. The tool returns a "prompt" field. Use that prompt as your instruction
     to write the actual explanation or quiz for the student.
  3. Present the result in a clear, encouraging, student-friendly tone.
  4. End every explanation with: "💡 Tip: ask me to quiz you on this topic!"
     End every quiz with: "✅ Done! Ask me to explain any topic you got wrong."
  5. If the request is not study-related, reply:
     "NOT_STUDY: This request is outside my specialty."
""".strip()


def create_study_agent(session_id: Optional[str] = None) -> Agent:
    """
    Factory function to build a Strands Study Agent.

    Args:
        session_id: Unique identifier for the conversation session.
                    If provided, attaches session persistence for multi-turn history.

    Returns:
        Configured Strands Agent instance.
    """
    logger.info("Building Study Agent  |  session_id=%r", session_id)

    model = build_guarded_model(temperature=0.4, streaming=False)

    agent_kwargs = dict(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        model=model,
        system_prompt=_STUDY_SYSTEM_PROMPT,
        tools=[explain_topic, generate_quiz],
        callback_handler=None,  # silent — output flows through A2A
    )

    if session_id and not session_id.startswith("__"):
        agent_kwargs["session_manager"] = build_session_manager(f"{session_id}_study")

    return Agent(**agent_kwargs)
