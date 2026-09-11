"""
tools/schedule_tools.py
═══════════════════════════════════════════════════════════════════════════════
Two scheduling tools that the Schedule Agent uses:

  add_task       — adds a study task to the in-memory schedule
  view_schedule  — lists all scheduled tasks, optionally filtered by subject

Why in-memory storage?
    This project focuses on teaching the multi-agent + session-manager pattern.
    Persisting to a database would add complexity without adding clarity.
    The session manager (FileSessionManager) handles the CONVERSATION history
    automatically; the schedule itself is intentionally kept simple.

    In a real app you would swap _SCHEDULE (the list below) for a database
    call or a file write, and nothing else would need to change.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from datetime import datetime
from strands import tool

logger = logging.getLogger(__name__)

# ── In-memory task store ──────────────────────────────────────────────────────
# A plain Python list of dicts.  Lives for the duration of one process run.
# Each entry looks like:
#   {"id": 1, "subject": "Maths", "task": "Practice integration", "due": "Friday", "added_at": "..."}
_SCHEDULE: list[dict] = []
_next_id: int = 1          # auto-increment ID counter


@tool
def add_task(subject: str, task: str, due: str = "no due date") -> dict:
    """
    Add a new study task to the student's schedule.

    Use this tool when the student wants to add, schedule, plan, or remember
    a study task, assignment, or revision session.

    Args:
        subject:  The subject or course this task belongs to.
                  Examples: "Mathematics", "Biology", "History", "Python".
        task:     A short description of what needs to be done.
                  Examples: "Read chapter 5", "Practice past papers",
                  "Watch lecture on cellular respiration".
        due:      When the task is due or should be done by.
                  Accepts any natural description: "Friday", "tomorrow",
                  "next Monday", "end of week".  Defaults to "no due date".

    Returns:
        A dict with keys:
          status    — "added"
          task_id   — the numeric ID assigned to this task
          subject   — subject as stored
          task      — task description as stored
          due       — due date/description as stored
          message   — a human-readable confirmation sentence
    """
    global _next_id

    logger.info("add_task called  |  subject=%r  task=%r  due=%r", subject, task, due)

    entry = {
        "id":       _next_id,
        "subject":  subject,
        "task":     task,
        "due":      due,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    _SCHEDULE.append(entry)
    _next_id += 1

    message = f"Task #{entry['id']} added: [{subject}] {task} — due: {due}."
    logger.info("add_task done    |  %s", message)

    return {
        "status":   "added",
        "task_id":  entry["id"],
        "subject":  subject,
        "task":     task,
        "due":      due,
        "message":  message,
    }


@tool
def view_schedule(subject_filter: str = "") -> dict:
    """
    Return the student's current study schedule.

    Use this tool when the student asks to see, check, or list their schedule,
    tasks, assignments, or what they have planned.

    Args:
        subject_filter: Optional.  If provided, only tasks belonging to this
                        subject are returned (case-insensitive partial match).
                        Leave empty to return all tasks.
                        Examples: "Maths", "bio", "" (all tasks).

    Returns:
        A dict with keys:
          total_tasks  — total number of tasks returned
          filter_used  — the filter string that was applied (empty = no filter)
          tasks        — list of task dicts, each with id/subject/task/due/added_at
          summary      — a human-readable summary line
    """
    logger.info("view_schedule called  |  filter=%r", subject_filter)

    if subject_filter:
        # Case-insensitive partial match on the subject field.
        filtered = [
            t for t in _SCHEDULE
            if subject_filter.lower() in t["subject"].lower()
        ]
    else:
        filtered = list(_SCHEDULE)   # shallow copy — don't expose internal list

    if not filtered:
        summary = (
            f"No tasks found{' for subject: ' + subject_filter if subject_filter else ''}. "
            "The schedule is empty."
        )
    else:
        lines = [f"#{t['id']} [{t['subject']}] {t['task']} — due: {t['due']}" for t in filtered]
        summary = f"{len(filtered)} task(s) scheduled:\n" + "\n".join(lines)

    logger.info("view_schedule done    |  %d task(s) returned", len(filtered))

    return {
        "total_tasks":  len(filtered),
        "filter_used":  subject_filter,
        "tasks":        filtered,
        "summary":      summary,
    }
