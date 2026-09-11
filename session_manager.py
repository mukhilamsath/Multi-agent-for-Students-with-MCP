"""
session_manager.py
═══════════════════════════════════════════════════════════════════════════════
Thin wrapper around Strands' built-in FileSessionManager.

What is a Session Manager?
───────────────────────────
By default a Strands Agent holds its conversation history only in RAM.
When the Python process ends, all messages are lost.

A SessionManager solves this by automatically persisting every message
to disk (or a cloud store) as the conversation happens — no manual
"save" calls needed.  When the same session_id is used again, Strands
restores the full history so the agent remembers previous turns.

Persistence lifecycle (handled by Strands automatically):
  • Startup         — existing messages are loaded from disk into agent.messages
  • Each message    — new message is written to disk immediately
  • Post-invocation — agent state and conversation-manager state are synced

FileSessionManager on disk (inside sessions/):
  sessions/
  └── session_<SESSION_ID>/
      ├── session.json            ← session metadata
      └── agents/
          └── agent_<agent_id>/
              ├── agent.json      ← agent state
              └── messages/
                  ├── message_0.json
                  ├── message_1.json
                  └── ...

Usage (from specialist agents):
    from session_manager import build_session_manager
    sm = build_session_manager("alice_study")
    agent = Agent(..., session_manager=sm)
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import os
from pathlib import Path

# FileSessionManager is the built-in file-based backend that ships with
# the strands-agents package — no extra install required.
from strands.session import FileSessionManager

logger = logging.getLogger(__name__)

# Directory where all session folders will be stored.
# Resolved relative to this file so it works regardless of where the user
# runs the script from.
_SESSIONS_DIR = str(Path(__file__).parent / "sessions")


def build_session_manager(session_id: str) -> FileSessionManager:
    """
    Create (or resume) a FileSessionManager for the given session ID.

    Args:
        session_id: A short string that uniquely identifies this user session.
                    Allowed characters: letters, digits, hyphens, underscores.
                    The same ID can be reused across process restarts to
                    resume the conversation.
                    Examples: "alice", "student-001", "demo-session"

    Returns:
        A configured FileSessionManager instance ready to be passed to an
        Agent constructor via the session_manager= parameter.

    Side effects:
        Creates  sessions/session_<session_id>/  on first use.
        Subsequent calls with the same ID resume the existing session.
    """
    # Sanitise: replace spaces with hyphens so the directory name stays safe.
    # FileSessionManager disallows path separators (/ and \) in the ID.
    clean_id = session_id.strip().replace(" ", "-")

    logger.info(
        "SessionManager  |  session_id=%r  storage_dir=%r",
        clean_id,
        _SESSIONS_DIR,
    )

    # FileSessionManager.__init__(session_id, storage_dir)
    # • session_id   — identifies this conversation thread
    # • storage_dir  — parent folder; sub-folders are created automatically
    sm = FileSessionManager(
        session_id=clean_id,
        storage_dir=_SESSIONS_DIR,
    )

    # Check whether this is a brand-new session or a resumed one.
    existing = sm.read_session(clean_id)
    if existing:
        logger.info("SessionManager  |  existing session found — history will be restored")
    else:
        logger.info("SessionManager  |  new session — starting fresh")

    return sm
