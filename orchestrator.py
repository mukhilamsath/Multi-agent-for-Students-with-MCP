"""
orchestrator.py
═══════════════════════════════════════════════════════════════════════════════
Deterministic Python Orchestrator for the Student Assistant Multi-Agent System.

ARCHITECTURAL SPECIFICATION:
  • Pure Python control flow and deterministic routing.
  • NO LLM inside the orchestrator.
  • NO Strands Agent inside the orchestrator.
  • NO system prompt.
  • Dispatches all specialist tasks exclusively via the A2A protocol.
  • Supports single-agent routing (Study, Schedule, Research) and
    multi-agent sequential pipelines (e.g. Research → Study → Schedule).
  • Instruments execution with OpenTelemetry distributed traces saved locally.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from dotenv import load_dotenv

# Ensure .env is loaded regardless of invocation working directory
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path if _env_path.exists() else None)

from a2a import send_a2a_message_sync
from logger_config import setup_logging
from telemetry_config import setup_telemetry, get_tracer

setup_logging()
setup_telemetry()

logger = logging.getLogger(__name__)
tracer = get_tracer("student-assistant.orchestrator")


@dataclass
class OrchestrationResult:
    """Structured result returned by the orchestrator."""
    session_id: str
    query: str
    answer: str
    specialists_used: list[str] = field(default_factory=list)
    success: bool = True
    error_detail: Optional[str] = None

    def __str__(self) -> str:
        return self.answer


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Deterministic Routing & Intent Analysis
# ═══════════════════════════════════════════════════════════════════════════════

# Distinct verb/action pattern rules for routing intents without an LLM
_STUDY_PATTERNS = [
    r"\b(explain|learn|quiz(\s+me)?|summarise|summarize|teach|what\s+is|what\s+are|how\s+does|why\s+does|difference\s+between|concept\s+of|help\s+me\s+understand|give\s+me\s+a\s+quiz|test\s+me|practice\s+questions?)\b",
    r"\b(academic|definition\s+of|overview\s+of|tutorial\s+on)\b",
]

_SCHEDULE_PATTERNS = [
    r"\b(schedule|task|assignment|plan|reminder|calendar|agenda|todo|to-do|deadlines?)\b",
    r"\badd\b.*?\b(task|revision|study\s+session|session|assignment|homework|practice|test)\b",
    r"\b(add|schedule|plan)\b.*?\b(for|due|by|on)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|next|tonight|weekend|\d+)",
    r"\b(view\s+schedule|show\s+(me\s+)?(my\s+)?(schedule|tasks|plans)|what('s|\s+is)\s+on\s+my\s+schedule|list\s+(my\s+)?tasks|check\s+(my\s+)?schedule|what\s+do\s+i\s+have\s+planned)\b",
    r"\b(due\s+(on|by|this|next|tomorrow|friday|monday|tuesday|wednesday|thursday|saturday|sunday))\b",
]

_RESEARCH_PATTERNS = [
    r"\b(research|search(\s+for|\s+the\s+web|\s+online)?|find\s+(online|resources?|articles?|docs?|the\s+latest)|look\s+up|latest\s+information|web\s+search)\b",
    r"\b(compare\s+websites|current\s+information|recent\s+news|online\s+sources?|browse|find\s+the\s+latest)\b",
]


def _match_intent(text: str, patterns: list[str]) -> bool:
    """Return True if any pattern matches the lowercased text."""
    lower_text = text.lower()
    return any(re.search(pat, lower_text) for pat in patterns)


def determine_route(query: str) -> tuple[str, list[str]]:
    """
    Deterministically analyze the query and determine the execution plan.

    Returns:
        tuple (route_type, specialist_keys_in_order)
        where route_type is one of 'study', 'schedule', 'research', 'multi', or 'default'.
    """
    has_research = _match_intent(query, _RESEARCH_PATTERNS)
    has_study = _match_intent(query, _STUDY_PATTERNS)
    has_schedule = _match_intent(query, _SCHEDULE_PATTERNS)

    active_intents = []
    if has_research:
        active_intents.append("research")
    if has_study:
        active_intents.append("study")
    if has_schedule:
        active_intents.append("schedule")

    # Multi-agent requests (more than one distinct intent detected)
    if len(active_intents) > 1:
        logger.info("ORCHESTRATOR | Multi-agent intent detected: %s", " -> ".join(active_intents))
        return "multi", active_intents

    # Single-agent requests
    if has_research:
        logger.info("ORCHESTRATOR | Routing query -> research")
        return "research", ["research"]
    if has_schedule:
        logger.info("ORCHESTRATOR | Routing query -> schedule")
        return "schedule", ["schedule"]
    if has_study:
        logger.info("ORCHESTRATOR | Routing query -> study")
        return "study", ["study"]

    # Fallback default: default to study agent for general academic questions
    logger.info("ORCHESTRATOR | Query did not match specific patterns -> defaulting to study")
    return "default", ["study"]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Sub-query Extraction for Pipelines
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_agent_subquery(full_query: str, agent_key: str) -> str:
    """
    Extract or tailor the relevant segment of a compound request for a given specialist.
    """
    clauses = re.split(r"\b(?:and\s+then|and|also|then)\b|,", full_query, flags=re.IGNORECASE)

    matching_clauses = []
    for clause in clauses:
        clause_clean = clause.strip()
        if not clause_clean:
            continue
        if agent_key == "research" and _match_intent(clause_clean, _RESEARCH_PATTERNS):
            matching_clauses.append(clause_clean)
        elif agent_key == "study" and _match_intent(clause_clean, _STUDY_PATTERNS):
            matching_clauses.append(clause_clean)
        elif agent_key == "schedule" and _match_intent(clause_clean, _SCHEDULE_PATTERNS):
            matching_clauses.append(clause_clean)

    if matching_clauses:
        return " and ".join(matching_clauses)
    return full_query


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Orchestrator Execution with OpenTelemetry Spans
# ═══════════════════════════════════════════════════════════════════════════════

def orchestrate(session_id: str, query: str) -> OrchestrationResult:
    """
    Orchestrate the user request deterministically using the A2A protocol.

    Args:
        session_id: Conversation session identifier.
        query: User input query.

    Returns:
        OrchestrationResult containing the aggregated answer and execution metadata.
    """
    clean_session_id = session_id.strip() if session_id else "default"
    clean_query = query.strip()

    if not clean_query:
        return OrchestrationResult(
            session_id=clean_session_id,
            query=query,
            answer="Please enter a valid question or request.",
            specialists_used=[],
            success=False,
        )

    logger.info("ORCHESTRATOR | Starting request [session_id=%s] | query=%r", clean_session_id, clean_query[:80])

    route_type, pipeline = determine_route(clean_query)
    specialists_used: list[str] = []
    intermediate_results: dict[str, str] = {}

    with tracer.start_as_current_span("orchestrator.orchestrate") as span:
        span.set_attribute("session.id", clean_session_id)
        span.set_attribute("user.query", clean_query)
        span.set_attribute("orchestrator.route_type", route_type)
        span.set_attribute("orchestrator.pipeline", ",".join(pipeline))

        try:
            if route_type == "multi":
                # Execute sequential pipeline: Research -> Study -> Schedule (or subset)
                final_sections = []

                for step_idx, specialist in enumerate(pipeline, start=1):
                    sub_query = _extract_agent_subquery(clean_query, specialist)
                    logger.info("ORCHESTRATOR | Step %d/%d: Dispatching to %s via A2A", step_idx, len(pipeline), specialist)

                    # If we have prior research or study output, enrich the specialist prompt
                    prompt_to_send = sub_query
                    if specialist == "study" and "research" in intermediate_results:
                        prompt_to_send = (
                            f"{sub_query}\n\n"
                            f"[Context from Web Research]:\n{intermediate_results['research']}"
                        )
                    elif specialist == "schedule" and ("research" in intermediate_results or "study" in intermediate_results):
                        context_summary = intermediate_results.get("study") or intermediate_results.get("research")
                        prompt_to_send = (
                            f"{sub_query}\n\n"
                            f"[Context]: Relevant topics: {context_summary[:300]}"
                        )

                    with tracer.start_as_current_span(f"pipeline.step.{specialist}") as step_span:
                        step_span.set_attribute("step.index", step_idx)
                        step_span.set_attribute("step.specialist", specialist)
                        step_span.set_attribute("step.query", prompt_to_send)

                        result_text = send_a2a_message_sync(
                            agent_key=specialist,
                            query=prompt_to_send,
                            session_id=clean_session_id,
                        )
                        step_span.set_attribute("step.result_length", len(result_text))

                    intermediate_results[specialist] = result_text
                    specialists_used.append(specialist)

                    # Format section heading
                    title_map = {
                        "research": "🌐 Research Findings",
                        "study": "📚 Study Assistance",
                        "schedule": "📅 Schedule Update",
                    }
                    section_title = title_map.get(specialist, specialist.capitalize())
                    final_sections.append(f"### {section_title}\n{result_text}")

                aggregated_answer = "\n\n".join(final_sections)
                logger.info("ORCHESTRATOR | Multi-agent request completed successfully")

                span.set_attribute("specialists.used", ",".join(specialists_used))
                span.set_attribute("orchestrator.success", True)

                return OrchestrationResult(
                    session_id=clean_session_id,
                    query=clean_query,
                    answer=aggregated_answer,
                    specialists_used=specialists_used,
                    success=True,
                )

            else:
                # Single specialist routing
                target_specialist = pipeline[0]
                logger.info("ORCHESTRATOR | Dispatching single-agent task to %s via A2A", target_specialist)

                result_text = send_a2a_message_sync(
                    agent_key=target_specialist,
                    query=clean_query,
                    session_id=clean_session_id,
                )
                specialists_used.append(target_specialist)
                logger.info("ORCHESTRATOR | Request completed successfully")

                span.set_attribute("specialists.used", target_specialist)
                span.set_attribute("orchestrator.success", True)

                return OrchestrationResult(
                    session_id=clean_session_id,
                    query=clean_query,
                    answer=result_text,
                    specialists_used=specialists_used,
                    success=True,
                )

        except Exception as exc:
            logger.exception("ORCHESTRATOR | Execution failed: %s", exc)
            span.record_exception(exc)
            span.set_attribute("orchestrator.success", False)
            error_msg = f"Sorry, I encountered an error while processing your request: {str(exc)}"
            return OrchestrationResult(
                session_id=clean_session_id,
                query=clean_query,
                answer=error_msg,
                specialists_used=specialists_used,
                success=False,
                error_detail=str(exc),
            )
