"""
mcp_client/client.py
═══════════════════════════════════════════════════════════════════════════════
MCP Client Factory and Tool Discovery Layer.

Manages connections to Model Context Protocol (MCP) servers:
  • DuckDuckGo MCP Server for Research Agent
  • Study Concept MCP Server for Study Agent
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import sys
from pathlib import Path
from typing import Any, List, Optional

# Ensure project root is in sys.path when executed directly as a script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp.client.stdio import stdio_client
from strands.tools.mcp import MCPAgentTool, MCPClient

try:
    from mcp_client.config import (
        DEFAULT_STARTUP_TIMEOUT_SECONDS,
        get_duckduckgo_server_params,
        get_study_server_params,
    )
except ImportError:
    from config import (  # type: ignore
        DEFAULT_STARTUP_TIMEOUT_SECONDS,
        get_duckduckgo_server_params,
        get_study_server_params,
    )

logger = logging.getLogger(__name__)


def create_research_mcp_client(
    continue_on_error: bool = True,
    startup_timeout: int = DEFAULT_STARTUP_TIMEOUT_SECONDS,
) -> MCPClient:
    """
    Factory function to create an MCPClient instance for the Research Agent.

    Launches the open-source duckduckgo-mcp-server process via standard I/O (stdio)
    transport and provides MCP tool interfaces to the Strands Agent.

    Args:
        continue_on_error: If True, failures during tool execution or server startup
                           will not terminate the entire agent invocation ungracefully.
        startup_timeout: Timeout in seconds to wait for server process startup.

    Returns:
        MCPClient instance configured for DuckDuckGo MCP Server.
    """
    params = get_duckduckgo_server_params()
    logger.info("Initializing Research MCPClient | command=%r args=%r", params.command, params.args)

    return MCPClient(
        lambda: stdio_client(params),
        startup_timeout=startup_timeout,
        continue_on_error=continue_on_error,
        application_name="StudentAssistant-ResearchAgent",
        application_version="2.0.0",
    )


def create_study_mcp_client(
    continue_on_error: bool = True,
    startup_timeout: int = DEFAULT_STARTUP_TIMEOUT_SECONDS,
) -> MCPClient:
    """
    Factory function to create an MCPClient instance for the Study Agent.

    Launches the Study Concept MCP server process via standard I/O (stdio)
    transport and provides concept explanation & quiz tools to the Strands Agent.

    Args:
        continue_on_error: If True, failures during tool execution or server startup
                           will not terminate the entire agent invocation ungracefully.
        startup_timeout: Timeout in seconds to wait for server process startup.

    Returns:
        MCPClient instance configured for Study Concept MCP Server.
    """
    params = get_study_server_params()
    logger.info("Initializing Study MCPClient | command=%r args=%r", params.command, params.args)

    return MCPClient(
        lambda: stdio_client(params),
        startup_timeout=startup_timeout,
        continue_on_error=continue_on_error,
        application_name="StudentAssistant-StudyAgent",
        application_version="2.0.0",
    )


def discover_mcp_tools(client: MCPClient) -> List[MCPAgentTool]:
    """
    Discover all tools provided by an active MCP server.

    Args:
        client: The MCPClient instance to inspect.

    Returns:
        List of MCPAgentTool instances exposed by the server.
    """
    try:
        with client:
            tools = client.list_tools_sync()
            logger.info(
                "MCP tool discovery succeeded | count=%d tools=%s",
                len(tools),
                [getattr(t, "tool_name", str(t)) for t in tools],
            )
            return tools
    except Exception as exc:
        logger.error("Failed to discover MCP tools: %s", exc)
        return []


def test_mcp_connection(client: Optional[MCPClient] = None) -> bool:
    """
    Test connectivity and tool availability for an MCP client.

    Args:
        client: Optional MCPClient instance. If None, a new client is constructed.

    Returns:
        True if the server responds and exposes tools, False otherwise.
    """
    mcp_client = client or create_research_mcp_client(continue_on_error=False)
    try:
        tools = discover_mcp_tools(mcp_client)
        return len(tools) > 0
    except Exception as exc:
        logger.warning("MCP connectivity test failed: %s", exc)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    print("\n[MCP] 1. Testing Research MCP Client (DuckDuckGo)...")
    res_client = create_research_mcp_client(continue_on_error=False)
    res_tools = discover_mcp_tools(res_client)
    print(f"[OK] Discovered {len(res_tools)} Research tool(s): {[t.tool_name for t in res_tools]}")

    print("\n[MCP] 2. Testing Study Concept MCP Client...")
    study_client = create_study_mcp_client(continue_on_error=False)
    study_tools = discover_mcp_tools(study_client)
    print(f"[OK] Discovered {len(study_tools)} Study tool(s): {[t.tool_name for t in study_tools]}")

    print("\n[MCP] Executing test explain_concept tool call over stdio MCP...")
    with study_client:
        res = study_client.call_tool_sync(
            name="explain_concept",
            arguments={"concept": "Newton's Laws of Motion", "level": "beginner"},
            tool_use_id="cli-study-test-1",
        )
        print("[MCP] Study Tool Result Status:", res.get("status"))
        print("[MCP] Structured Content:", res.get("structuredContent"))
