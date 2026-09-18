"""
test_long_term_memory.py
═══════════════════════════════════════════════════════════════════════════════
Comprehensive Test Suite for Local Long-Term Memory (LTM).

Verifies:
  1. Local storage, update, and retrieval of student preferences.
  2. Recording and tracking studied topics across sessions.
  3. Storing and searching custom facts.
  4. Cross-session memory recall (session_A -> store -> session_B -> recall).
  5. Strands @tool integration for memory tools.
  6. End-to-end Orchestrator + LTM context enrichment.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import os
import tempfile
import unittest
from pathlib import Path

from memory.long_term_memory import LocalLongTermMemory, get_long_term_memory
from tools.memory_tools import (
    remember_student_preference,
    remember_student_fact,
    recall_student_memory,
)
from orchestrator import orchestrate

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("test_ltm")


class TestLocalLongTermMemory(unittest.TestCase):
    """Test suite for Local Long-Term Memory engine and tools."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file = Path(self.temp_dir.name) / "test_memory.json"
        self.ltm = LocalLongTermMemory(storage_file=self.temp_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_store_and_get_preferences(self):
        """Test storing and reading learning preferences."""
        logger.info("=== TEST 1: Store and Read Preferences ===")
        self.ltm.store_preference("explanation_style", "concise with analogies")
        self.ltm.store_preference("difficulty", "beginner")

        style = self.ltm.get_preference("explanation_style")
        diff = self.ltm.get_preference("difficulty")
        missing = self.ltm.get_preference("non_existent", default="default_val")

        self.assertEqual(style, "concise with analogies")
        self.assertEqual(diff, "beginner")
        self.assertEqual(missing, "default_val")

    def test_02_record_and_search_studied_topics(self):
        """Test recording and searching studied concepts."""
        logger.info("=== TEST 2: Record and Search Topics ===")
        self.ltm.record_studied_topic("Photosynthesis in Plants", summary="Light-dependent reactions", subject="Biology")
        self.ltm.record_studied_topic("Newton's Laws of Motion", summary="Classical mechanics", subject="Physics")

        results = self.ltm.search_memories("Photosynthesis")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["type"], "studied_topic")
        self.assertEqual(results[0]["topic"], "Photosynthesis in Plants")

    def test_03_remember_facts_and_search(self):
        """Test remembering cross-session facts and searching them."""
        logger.info("=== TEST 3: Remember Facts and Search ===")
        self.ltm.remember_fact("Student is preparing for AP Biology exam in May 2026", category="goals")
        self.ltm.remember_fact("Student prefers calculus examples with visual graphs", category="learning_style")

        results = self.ltm.search_memories("Biology exam")
        self.assertTrue(len(results) > 0)
        self.assertIn("AP Biology", results[0]["fact"])

    def test_04_context_summary_generation(self):
        """Test generating prompt-ready context summary from memory."""
        logger.info("=== TEST 4: Context Summary Generation ===")
        self.ltm.store_preference("difficulty", "beginner")
        self.ltm.record_studied_topic("Cellular Respiration", subject="Biology")
        self.ltm.remember_fact("Targeting pre-med track", category="goals")

        summary = self.ltm.get_context_summary()
        logger.info("Generated Context Summary:\n%s", summary)

        self.assertIn("Student Preferences:", summary)
        self.assertIn("difficulty: beginner", summary)
        self.assertIn("Cellular Respiration", summary)
        self.assertIn("Targeting pre-med track", summary)

    def test_05_memory_tools_execution(self):
        """Test the Strands @tool functions."""
        logger.info("=== TEST 5: Memory Tools Execution ===")
        pref_res = remember_student_preference(key="quiz_format", value="multiple-choice 4 options")
        self.assertEqual(pref_res["status"], "success")

        fact_res = remember_student_fact(fact="Student is a freshman majoring in Computer Science", category="profile")
        self.assertEqual(fact_res["status"], "success")

        recall_res = recall_student_memory(query="Computer Science")
        self.assertEqual(recall_res["status"], "success")
        self.assertTrue(recall_res["count"] > 0)

    def test_06_cross_session_orchestration(self):
        """Test cross-session recall in orchestrator with two distinct session IDs."""
        logger.info("=== TEST 6: Cross-Session Recall in Orchestrator ===")
        global_ltm = get_long_term_memory()
        global_ltm.store_preference("preferred_subject", "Organic Chemistry")
        global_ltm.remember_fact("Student excels in reaction mechanisms", category="academic")

        # Session 1: Ask study agent
        res1 = orchestrate(session_id="session_alpha_101", query="Explain photosynthesis for a beginner")
        self.assertTrue(res1.success)

        # Verify topic was recorded in LTM
        all_mems = global_ltm.get_all_memories()
        topics = list(all_mems.get("studied_topics", {}).keys())
        self.assertTrue(len(topics) > 0)

        # Session 2: A completely new session ID
        res2 = orchestrate(session_id="session_beta_202", query="Show me my full schedule")
        self.assertTrue(res2.success)


if __name__ == "__main__":
    unittest.main(verbosity=2)
