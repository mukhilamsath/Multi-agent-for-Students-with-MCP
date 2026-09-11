"""
mcp_client/client.py
═══════════════════════════════════════════════════════════════════════════════
MCP Client Factory and Tool Discovery Layer.

Manages connections to local or remote Model Context Protocol (MCP) servers,
enabling Strands Agents to dynamically discover and invoke tools over MCP.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import Any, List, Optional

from mcp.client.stdio import stdio_client
from strands.tools.mcp import MCPAgentTool, MCPClient

from mcp_client.config import (
    DEFAULT_STARTUP_TIMEOUT_SECONDS,
    get_duckduckgo_server_params,
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
