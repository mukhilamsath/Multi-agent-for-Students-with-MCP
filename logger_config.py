"""
logger_config.py
═══════════════════════════════════════════════════════════════════════════════
Centralized logging configuration for the Student Assistant Multi-Agent System.

Configures both console output and persistent file logging into `logs/student_assistant.log`.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Directory where log files are stored
_LOGS_DIR = Path(__file__).parent / "logs"
_LOG_FILE = _LOGS_DIR / "student_assistant.log"

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(
    log_level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB per file
    backup_count: int = 5,
) -> Path:
    """
    Initialize central logging with both console and rotating file output.

    Args:
        log_level: Default logging level for project modules (default INFO).
        max_bytes: Max log file size before rotation (default 5MB).
        backup_count: Number of rotated log files to retain (default 5).

    Returns:
        Path to the primary active log file.
    """
    global _configured
    if _configured:
        return _LOG_FILE

    # Ensure logs directory exists
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # ── 1. Root Logger Configuration ───────────────────────────────────────────
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)

    # Remove pre-existing duplicate handlers if any
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # ── 2. Console Handler ────────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # ── 3. Rotating File Handler ──────────────────────────────────────────────
    file_handler = RotatingFileHandler(
        filename=_LOG_FILE,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # ── 4. Set Specific Project Module Log Levels ──────────────────────────────
    project_loggers = [
        "orchestrator",
        "a2a",
        "a2a.client",
        "agents",
        "agents.study_agent",
        "agents.schedule_agent",
        "agents.research_agent",
        "tools",
        "tools.study_tools",
        "tools.schedule_tools",
        "tools.research_tools",
        "session_manager",
        "guardrails",
        "api",
        "main",
    ]

    for name in project_loggers:
        logging.getLogger(name).setLevel(log_level)

    # Keep third-party libraries less verbose unless debugging
    logging.getLogger("strands").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    _configured = True
    logging.getLogger(__name__).info("Logging initialized -> active log file: %s", _LOG_FILE)
    return _LOG_FILE


def get_log_file_path() -> Path:
    """Return the absolute path to the active log file."""
    return _LOG_FILE
