"""
mcp_client/__init__.py
═══════════════════════════════════════════════════════════════════════════════
Model Context Protocol (MCP) Integration Module.

Exposes client factories, tool discovery utilities, and server configuration
for the Student Assistant multi-agent architecture.
═══════════════════════════════════════════════════════════════════════════════
"""

from mcp_client.config import (
    MCPServerSettings,
    get_duckduckgo_server_params,
    get_mcp_servers_config,
)
from mcp_client.client import (
    create_research_mcp_client,
    discover_mcp_tools,
    test_mcp_connection,
)

__all__ = [
    "MCPServerSettings",
    "get_duckduckgo_server_params",
    "get_mcp_servers_config",
    "create_research_mcp_client",
    "discover_mcp_tools",
    "test_mcp_connection",
]
