"""
memory/long_term_memory.py
═══════════════════════════════════════════════════════════════════════════════
Local Long-Term Persistent Memory Store.

Stores student preferences, mastered concepts, study habits, and cross-session
facts in a local JSON database (`memory/long_term_memory.json`).
Preserves context across different session IDs and process restarts.
═══════════════════════════════════════════════════════════════════════════════
"""

import datetime
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_STORAGE_FILE = Path(__file__).parent / "long_term_memory.json"
_LOCK = threading.Lock()


class LocalLongTermMemory:
    """
    Local file-backed Long-Term Memory (LTM) engine.

    Structure:
        {
            "profile": { ... },
            "preferences": { ... },
            "studied_topics": { ... },
            "custom_facts": [ ... ]
        }
    """

    def __init__(self, storage_file: Optional[Path] = None):
        self.storage_file = Path(storage_file or _DEFAULT_STORAGE_FILE)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Create empty memory database file if it does not exist."""
        with _LOCK:
            if not self.storage_file.exists():
                initial_data = {
                    "_meta": {
                        "version": "1.0.0",
                        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    },
                    "profile": {},
                    "preferences": {},
                    "studied_topics": {},
                    "custom_facts": [],
                }
                self._save_raw_unlocked(initial_data)

    def _load_raw_unlocked(self) -> Dict[str, Any]:
        """Load raw JSON dictionary from disk."""
        try:
            if not self.storage_file.exists():
                return {}
            with open(self.storage_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.error("Failed to read long-term memory file %s: %s", self.storage_file, exc)
            return {}

    def _save_raw_unlocked(self, data: Dict[str, Any]) -> bool:
        """Write raw JSON dictionary atomically to disk."""
        try:
            temp_file = self.storage_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.storage_file)
            return True
        except Exception as exc:
            logger.error("Failed to write long-term memory file %s: %s", self.storage_file, exc)
            return False

    def store_preference(self, key: str, value: Any) -> bool:
        """
        Store a student learning preference (e.g. key='difficulty', value='beginner').
        """
        with _LOCK:
            data = self._load_raw_unlocked()
            if "preferences" not in data:
                data["preferences"] = {}
            data["preferences"][key] = {
                "value": value,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            logger.info("LTM | Stored preference %r = %r", key, value)
            return self._save_raw_unlocked(data)

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Retrieve a stored student preference."""
        with _LOCK:
            data = self._load_raw_unlocked()
            pref = data.get("preferences", {}).get(key)
            if pref and isinstance(pref, dict):
                return pref.get("value", default)
            return default

    def record_studied_topic(self, topic: str, summary: Optional[str] = None, subject: Optional[str] = None) -> bool:
        """
        Record a topic the student studied in a session.
        """
        with _LOCK:
            data = self._load_raw_unlocked()
            if "studied_topics" not in data:
                data["studied_topics"] = {}

            clean_topic = topic.strip()
            data["studied_topics"][clean_topic] = {
                "subject": subject or "General",
                "summary": summary or "",
                "last_studied": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            logger.info("LTM | Recorded studied topic: %r", clean_topic)
            return self._save_raw_unlocked(data)

    def remember_fact(self, fact: str, category: str = "general") -> bool:
        """
        Remember a general fact or user statement across sessions.
        """
        clean_fact = fact.strip()
        if not clean_fact:
            return False

        with _LOCK:
            data = self._load_raw_unlocked()
            if "custom_facts" not in data:
                data["custom_facts"] = []

            # Avoid exact duplicate facts
            for item in data["custom_facts"]:
                if isinstance(item, dict) and item.get("fact", "").lower() == clean_fact.lower():
                    item["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    return self._save_raw_unlocked(data)

            data["custom_facts"].append({
                "category": category,
                "fact": clean_fact,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            })
            logger.info("LTM | Remembered fact (%s): %r", category, clean_fact)
            return self._save_raw_unlocked(data)

    def search_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search memories across preferences, studied topics, and custom facts.
        """
        query_terms = [t.lower() for t in query.split() if len(t) > 2]
        if not query_terms:
            return []

        results = []
        with _LOCK:
            data = self._load_raw_unlocked()

            # Search preferences
            for k, v in data.get("preferences", {}).items():
                val_str = str(v.get("value", "")) if isinstance(v, dict) else str(v)
                score = sum(1 for term in query_terms if term in k.lower() or term in val_str.lower())
                if score > 0:
                    results.append({"type": "preference", "key": k, "value": val_str, "score": score})

            # Search studied topics
            for topic, details in data.get("studied_topics", {}).items():
                text = f"{topic} {details.get('subject', '')} {details.get('summary', '')}".lower()
                score = sum(1 for term in query_terms if term in text)
                if score > 0:
                    results.append({"type": "studied_topic", "topic": topic, "details": details, "score": score})

            # Search custom facts
            for item in data.get("custom_facts", []):
                fact_text = item.get("fact", "").lower()
                score = sum(1 for term in query_terms if term in fact_text)
                if score > 0:
                    results.append({"type": "fact", "fact": item.get("fact"), "category": item.get("category"), "score": score})

        # Rank by score descending
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:limit]

    def get_context_summary(self, max_items: int = 6) -> str:
        """
        Build a compact plain-text summary of long-term memory for prompt context injection.
        """
        with _LOCK:
            data = self._load_raw_unlocked()

        sections = []

        # 1. Preferences
        prefs = data.get("preferences", {})
        if prefs:
            pref_lines = []
            for k, v in list(prefs.items())[:max_items]:
                val = v.get("value", "") if isinstance(v, dict) else str(v)
                pref_lines.append(f"• {k}: {val}")
            sections.append("Student Preferences:\n" + "\n".join(pref_lines))

        # 2. Studied Topics
        topics = data.get("studied_topics", {})
        if topics:
            recent_topics = list(topics.keys())[-max_items:]
            sections.append("Recently Studied Topics:\n" + ", ".join(recent_topics))

        # 3. Custom Facts
        facts = data.get("custom_facts", [])
        if facts:
            fact_lines = [f"• {f.get('fact')}" for f in facts[-max_items:] if isinstance(f, dict) and f.get("fact")]
            if fact_lines:
                sections.append("Saved Student Facts:\n" + "\n".join(fact_lines))

        return "\n\n".join(sections)

    def get_all_memories(self) -> Dict[str, Any]:
        """Return a copy of the entire memory store."""
        with _LOCK:
            return self._load_raw_unlocked()

    def clear_memories(self) -> bool:
        """Reset long-term memory store."""
        with _LOCK:
            empty_data = {
                "_meta": {
                    "version": "1.0.0",
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
                "profile": {},
                "preferences": {},
                "studied_topics": {},
                "custom_facts": [],
            }
            return self._save_raw_unlocked(empty_data)


# Global singleton instance
_GLOBAL_LTM: Optional[LocalLongTermMemory] = None


def get_long_term_memory() -> LocalLongTermMemory:
    """Return the global LocalLongTermMemory singleton."""
    global _GLOBAL_LTM
    if _GLOBAL_LTM is None:
        _GLOBAL_LTM = LocalLongTermMemory()
    return _GLOBAL_LTM
