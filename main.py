"""
main.py
═══════════════════════════════════════════════════════════════════════════════
Student Assistant — Multi-Agent System with A2A Protocol Communication.
Powered by Strands Agents SDK and Amazon Bedrock Guardrails.

Full Architecture:

                    USER  (terminal / CLI)
                           │
                           ▼
                  Python Orchestrator
                    (orchestrator.py)
                           │
                  ┌────────┼────────┐
                 A2A      A2A      A2A
                  │        │        │
                  ▼        ▼        ▼
               Study    Schedule  Research
               Agent      Agent     Agent
                  │        │        │
                Tools    Tools     Tools

Key Properties:
  • Orchestrator: Deterministic Python control flow, NO LLM, NO system prompt.
  • Specialists: Strands Agents equipped with native Python tools.
  • Safety: Amazon Bedrock Guardrails attached to specialist models.
  • Protocol: Agent-to-Agent (A2A) protocol for all coordination.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# ── Credentials must be loaded before any AWS/Strands import ─────────────────
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path if env_path.exists() else None)

from orchestrator import orchestrate, determine_route
from guardrails import guardrail_status
from logger_config import setup_logging
from telemetry_config import setup_telemetry

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Logging & Telemetry Setup (Console + Rotating File Log + Traces)
# ═══════════════════════════════════════════════════════════════════════════════
setup_logging()
setup_telemetry()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Startup & Configuration
# ═══════════════════════════════════════════════════════════════════════════════
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

_missing = [v for v in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY") if not os.getenv(v)]
if _missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(_missing)}\n"
        "Copy .env.example to .env and fill in your AWS credentials."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Session ID Resolution
# ═══════════════════════════════════════════════════════════════════════════════
def _resolve_session_id() -> str:
    """Return the session ID from argv[1] or prompt the user."""
    if len(sys.argv) > 1:
        return sys.argv[1].strip()

    print("\nEnter a session name to start or resume a session.")
    print("Use the same name next time to continue this conversation.")
    print("Press Enter to use 'default'.")
    raw = input("Session name: ").strip()
    return raw if raw else "default"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — UI & Banner Display
# ═══════════════════════════════════════════════════════════════════════════════
def _print_banner(session_id: str, is_resumed: bool) -> None:
    status = "▶  Resumed session" if is_resumed else "✨ New session"
    print("\n" + "═" * 70)
    print("  🎓 Student Assistant — Multi-Agent System (A2A Protocol)")
    print(f"  Architecture : Python Orchestrator + A2A + Strands Leaf Agents")
    print(f"  Model        : {os.getenv('BEDROCK_MODEL_ID', 'amazon.nova-micro-v1:0')}")
    print(f"  Region       : {AWS_REGION}")
    print(f"  Session      : {session_id}  ({status})")
    print(f"  {guardrail_status()}")
    print("═" * 70)
    print("Available Specialists:")
    print("  • 📚 Study Agent    — Concept explanations, academic questions, quizzes")
    print("  • 📅 Schedule Agent — Task planning, deadlines, schedule viewing")
    print("  • 🌐 Research Agent — Web search, online resources, content extraction")
    print("\nExample prompts:")
    print("  • Explain photosynthesis for a beginner")
    print("  • Quiz me on Newton's laws — 4 questions")
    print("  • Add Biology revision due Friday")
    print("  • Show me my full schedule")
    print("  • Search for the latest Python 3.13 features online")
    print("  • Research the latest AI learning resources and schedule two study sessions")
    print("  • Research DBMS normalization, explain it to me, and add a revision session")
    print("-" * 70 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Interactive Chat Loop
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    """Entry point — resolve session and run interactive multi-turn loop."""
    session_id = _resolve_session_id()

    # Check for existing sessions
    session_dir = Path(__file__).parent / "sessions"
    matching_sessions = list(session_dir.glob(f"session_{session_id}*"))
    is_resumed = len(matching_sessions) > 0

    _print_banner(session_id, is_resumed)

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye! Your session has been saved.")
            break

        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye! Your session has been saved.")
            break

        if not user_input:
            continue

        print()
        logger.info("User query: %r", user_input[:100])

        result = orchestrate(session_id=session_id, query=user_input)

        print("\n" + result.answer)
        print("\n" + "-" * 70 + "\n")


if __name__ == "__main__":
    main()
