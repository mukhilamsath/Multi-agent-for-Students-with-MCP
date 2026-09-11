"""
agents/schedule_agent.py
═══════════════════════════════════════════════════════════════════════════════
The Schedule Specialist Agent.

Built with Strands Agents SDK and Amazon Bedrock Guardrails.
Communicates with the orchestrator exclusively via the A2A protocol.

Tools owned:
    • add_task       — stores a new task in the in-memory schedule
    • view_schedule  — retrieves tasks, optionally filtered by subject

Responsibility:
    - Managing study tasks, assignments, and deadlines
    - Scheduling revision sessions and study plans
    - Viewing and filtering scheduled tasks
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import Optional

from strands import Agent
from tools.schedule_tools import add_task, view_schedule
from guardrails import build_guarded_model
from session_manager import build_session_manager

logger = logging.getLogger(__name__)

AGENT_NAME = "Student Schedule Agent"
AGENT_DESCRIPTION = "Manages study tasks, assignments, deadlines, and schedule viewing."

_SCHEDULE_SYSTEM_PROMPT = """
You are an organised study planner helping a student manage their workload.

You have two tools:
  • add_task       — call this when the student wants to add, schedule,
                     or remember a task, assignment, or study session.
  • view_schedule  — call this when the student wants to see, check,
                     or list their current tasks or schedule.

Rules:
  1. For add requests:
       - Extract the subject, a clear task description, and a due date
         (use "no due date" if the student doesn't mention one).
       - Call add_task, then confirm what was added in a friendly message.

  2. For view requests:
       - If the student mentions a subject, pass it as subject_filter.
       - Otherwise leave subject_filter empty to return all tasks.
       - Present the schedule in a clean, readable list.
       - If no tasks exist, encourage the student to add some.

  3. If the request is not schedule-related, reply:
     "NOT_SCHEDULE: This request is outside my specialty."

  4. Keep responses concise and encouraging.
""".strip()


def create_schedule_agent(session_id: Optional[str] = None) -> Agent:
    """
    Factory function to build a Strands Schedule Agent.

    Args:
        session_id: Unique identifier for the conversation session.
                    If provided, attaches session persistence for multi-turn history.

    Returns:
        Configured Strands Agent instance.
    """
    logger.info("Building Schedule Agent  |  session_id=%r", session_id)

    model = build_guarded_model(temperature=0.1, streaming=False)

    agent_kwargs = dict(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        model=model,
        system_prompt=_SCHEDULE_SYSTEM_PROMPT,
        tools=[add_task, view_schedule],
        callback_handler=None,  # silent — output flows through A2A
    )

    if session_id and not session_id.startswith("__"):
        agent_kwargs["session_manager"] = build_session_manager(f"{session_id}_schedule")

    return Agent(**agent_kwargs)
