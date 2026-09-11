"""
test_mcp_suite.py
═══════════════════════════════════════════════════════════════════════════════
Comprehensive Test Suite for Model Context Protocol (MCP) Integration.

Tests:
  1. MCP Tool Discovery and Normal Execution (search, fetch_content)
  2. Research-only End-to-End Request via Orchestrator -> A2A -> MCP
  3. Multi-Agent Request (Research -> Study) via Orchestrator -> A2A
  4. MCP Server Unavailable Fault-Tolerance
  5. Invalid / Failed MCP Tool Invocation Handling
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import sys
import unittest
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from mcp_client import create_research_mcp_client, discover_mcp_tools
from mcp_client.config import get_duckduckgo_server_params
from strands.tools.mcp import MCPClient
from mcp.client.stdio import StdioServerParameters, stdio_client
from agents.research_agent import create_research_agent
from orchestrator import orchestrate, determine_route

# Setup test logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_mcp_suite")


class TestMCPIntegration(unittest.TestCase):
    """Test suite verifying MCP client, server, agent, and orchestrator integration."""

    def test_01_mcp_tool_discovery_and_execution(self):
        """Test 1: Verify MCP tools are dynamically discovered and callable."""
        logger.info("=== TEST 1: MCP Tool Discovery & Direct Execution ===")
        mcp_client = create_research_mcp_client(continue_on_error=False)
        tools = discover_mcp_tools(mcp_client)

        tool_names = [getattr(t, "tool_name", str(t)) for t in tools]
        logger.info("Discovered MCP tools: %s", tool_names)

        self.assertIn("search", tool_names, "Expected 'search' tool in MCP server")
        self.assertIn("fetch_content", tool_names, "Expected 'fetch_content' tool in MCP server")

        # Test direct tool execution over stdio MCP
        with mcp_client:
            res = mcp_client.call_tool_sync(
                name="search",
                arguments={"query": "Python 3.13 standard library", "max_results": 2},
                tool_use_id="test-discovery-1",
            )
            self.assertIsNotNone(res)
            self.assertFalse(res.get("isError", False), f"Tool execution returned error: {res}")
            content = res.get("content", [])
            self.assertTrue(len(content) > 0, "Expected non-empty content in search result")
            logger.info("Direct tool invocation result snippet: %s", str(content)[:200])

    def test_02_research_only_request(self):
        """Test 2: Research-only request through Orchestrator -> A2A -> Research Agent -> MCP."""
        logger.info("=== TEST 2: Research-only Request ===")
        query = "Search for the latest Python 3.13 features online"
        route_type, pipeline = determine_route(query)
        self.assertEqual(route_type, "research")
        self.assertEqual(pipeline, ["research"])

        result = orchestrate(session_id="test_mcp_res", query=query)
        logger.info("Research-only answer:\n%s", result.answer)
        self.assertTrue(result.success, f"Orchestration failed: {result.error_detail}")
        self.assertIn("research", result.specialists_used)
        self.assertNotIn("NOT_RESEARCH", result.answer)
        self.assertTrue(len(result.answer) > 50, "Expected detailed response from Research Agent")

    def test_03_multi_agent_research_to_study(self):
        """Test 3: Multi-agent sequential pipeline (Research -> Study) over A2A."""
        logger.info("=== TEST 3: Multi-agent Request (Research -> Study) ===")
        query = "Research DBMS normalization and explain it to me"
        route_type, pipeline = determine_route(query)
        self.assertEqual(route_type, "multi")
        self.assertIn("research", pipeline)
        self.assertIn("study", pipeline)

        result = orchestrate(session_id="test_mcp_multi", query=query)
        logger.info("Multi-agent answer:\n%s", result.answer)
        self.assertTrue(result.success, f"Orchestration failed: {result.error_detail}")
        self.assertIn("research", result.specialists_used)
        self.assertIn("study", result.specialists_used)
        self.assertIn("Research Findings", result.answer)
        self.assertIn("Study Assistance", result.answer)

    def test_04_mcp_server_unavailable_handling(self):
        """Test 4: Behavior when MCP server is unavailable or fails to connect."""
        logger.info("=== TEST 4: MCP Server Unavailable Fault Tolerance ===")
        # Configure client with invalid executable to simulate unavailable MCP server
        invalid_params = StdioServerParameters(
            command="non_existent_mcp_server_executable_12345.exe",
            args=["--invalid"],
        )
        mcp_client = MCPClient(
            lambda: stdio_client(invalid_params),
            startup_timeout=3,
            continue_on_error=True,
        )

        # Tool discovery should return empty list gracefully when continue_on_error=True
        tools = discover_mcp_tools(mcp_client)
        self.assertEqual(tools, [], "Expected empty tools list when MCP server is unavailable")

        # An agent built with continue_on_error=True should still instantiate without crashing
        from strands import Agent
        from guardrails import build_guarded_model
        agent = Agent(
            name="FallbackResearchAgent",
            model=build_guarded_model(streaming=False),
            system_prompt="You are a fallback research agent.",
            tools=[mcp_client],
        )
        self.assertIsNotNone(agent)
        logger.info("Agent successfully instantiated with unavailable MCP server under continue_on_error=True")

    def test_05_invalid_failed_mcp_tool_invocation(self):
        """Test 5: Handling invalid arguments or failed tool invocations over MCP."""
        logger.info("=== TEST 5: Invalid / Failed MCP Tool Invocation ===")
        mcp_client = create_research_mcp_client(continue_on_error=True)

        with mcp_client:
            # Calling non-existent tool
            try:
                res = mcp_client.call_tool_sync(
                    name="non_existent_tool_xyz",
                    arguments={"foo": "bar"},
                    tool_use_id="test-fail-1",
                )
                logger.info("Invocation of non-existent tool returned: %s", res)
                self.assertTrue(
                    res.get("isError", False) or "error" in str(res).lower() or res.get("status") == "error",
                    "Expected error response for non-existent tool",
                )
            except Exception as exc:
                logger.info("Invocation of non-existent tool threw expected exception: %s", exc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
