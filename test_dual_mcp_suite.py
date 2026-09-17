"""
test_dual_mcp_suite.py
═══════════════════════════════════════════════════════════════════════════════
Comprehensive Verification Suite for Dual MCP Architecture (Research + Study).

Verifies:
  1. Study MCP Server tool discovery & direct tool invocation
  2. Research MCP Server tool discovery & direct tool invocation
  3. Study Agent end-to-end concept explanation (Orchestrator -> A2A -> Study Agent -> MCP)
  4. Study Agent end-to-end quiz generation
  5. Research Agent end-to-end web research (Orchestrator -> A2A -> Research Agent -> MCP)
  6. Multi-agent sequential pipeline (Research -> Study) combining both MCP servers
  7. Fault tolerance and graceful handling when an MCP server is unavailable
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import sys
import unittest
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from mcp_client import (
    create_research_mcp_client,
    create_study_mcp_client,
    discover_mcp_tools,
)
from strands.tools.mcp import MCPClient
from mcp.client.stdio import StdioServerParameters, stdio_client
from orchestrator import orchestrate, determine_route

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_dual_mcp_suite")


class TestDualMCPIntegration(unittest.TestCase):
    """Test suite verifying both Research and Study MCP servers with Amazon Nova."""

    def test_01_study_mcp_discovery_and_execution(self):
        """Test 1: Discover and directly execute Study MCP tools."""
        logger.info("=== TEST 1: Study MCP Discovery & Execution ===")
        study_client = create_study_mcp_client(continue_on_error=False)
        tools = discover_mcp_tools(study_client)
        tool_names = [t.tool_name for t in tools]
        logger.info("Discovered Study MCP tools: %s", tool_names)

        self.assertIn("explain_concept", tool_names)
        self.assertIn("generate_study_quiz", tool_names)
        self.assertIn("get_concept_summary", tool_names)

        with study_client:
            res = study_client.call_tool_sync(
                name="explain_concept",
                arguments={"concept": "Photosynthesis", "level": "beginner"},
                tool_use_id="study-test-1",
            )
            self.assertEqual(res.get("status"), "success")
            self.assertIn("structuredContent", res)
            logger.info("Study MCP explain_concept output: %s", str(res.get("structuredContent"))[:250])

    def test_02_research_mcp_discovery_and_execution(self):
        """Test 2: Discover and directly execute Research MCP tools."""
        logger.info("=== TEST 2: Research MCP Discovery & Execution ===")
        res_client = create_research_mcp_client(continue_on_error=False)
        tools = discover_mcp_tools(res_client)
        tool_names = [t.tool_name for t in tools]
        logger.info("Discovered Research MCP tools: %s", tool_names)

        self.assertIn("search", tool_names)
        self.assertIn("fetch_content", tool_names)

        with res_client:
            res = res_client.call_tool_sync(
                name="search",
                arguments={"query": "Python 3.13 features", "max_results": 2},
                tool_use_id="res-test-1",
            )
            self.assertFalse(res.get("isError", False))

    def test_03_study_agent_explanation_request(self):
        """Test 3: End-to-end Study Agent request explaining a concept."""
        logger.info("=== TEST 3: End-to-end Study Agent Request ===")
        query = "Explain photosynthesis for a beginner"
        route_type, pipeline = determine_route(query)
        self.assertEqual(route_type, "study")
        self.assertEqual(pipeline, ["study"])

        result = orchestrate(session_id="test_dual_study", query=query)
        logger.info("Study Agent Answer:\n%s", result.answer)
        self.assertTrue(result.success)
        self.assertIn("study", result.specialists_used)
        self.assertNotIn("NOT_STUDY", result.answer)
        self.assertTrue(len(result.answer) > 80)

    def test_04_study_agent_quiz_request(self):
        """Test 4: End-to-end Study Agent quiz generation request."""
        logger.info("=== TEST 4: End-to-end Study Agent Quiz Request ===")
        query = "Quiz me on Newton's laws of motion - 3 questions"
        route_type, pipeline = determine_route(query)
        self.assertEqual(route_type, "study")

        result = orchestrate(session_id="test_dual_quiz", query=query)
        logger.info("Quiz Answer:\n%s", result.answer)
        self.assertTrue(result.success)
        self.assertIn("study", result.specialists_used)
        self.assertNotIn("NOT_STUDY", result.answer)

    def test_05_multi_agent_pipeline_research_to_study(self):
        """Test 5: Sequential Multi-Agent pipeline (Research MCP -> Study MCP over A2A)."""
        logger.info("=== TEST 5: Multi-agent Sequential Pipeline (Research -> Study) ===")
        query = "Research DBMS normalization and explain it to me"
        route_type, pipeline = determine_route(query)
        self.assertEqual(route_type, "multi")

        result = orchestrate(session_id="test_dual_multi", query=query)
        logger.info("Multi-agent Answer:\n%s", result.answer)
        self.assertTrue(result.success)
        self.assertIn("research", result.specialists_used)
        self.assertIn("study", result.specialists_used)
        self.assertIn("Research Findings", result.answer)
        self.assertIn("Study Assistance", result.answer)

    def test_06_mcp_server_unavailable_fault_tolerance(self):
        """Test 6: Fault tolerance when an MCP server executable is unavailable."""
        logger.info("=== TEST 6: MCP Fault Tolerance ===")
        invalid_params = StdioServerParameters(
            command="non_existent_server_bin_9999.exe",
            args=[],
        )
        client = MCPClient(lambda: stdio_client(invalid_params), startup_timeout=3, continue_on_error=True)
        tools = discover_mcp_tools(client)
        self.assertEqual(tools, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
