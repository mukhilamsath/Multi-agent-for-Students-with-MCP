"""
mcp_client/config.py
═══════════════════════════════════════════════════════════════════════════════
Model Context Protocol (MCP) Server Configuration.

Defines the parameters and environment settings required to connect to the
open-source DuckDuckGo MCP server (`duckduckgo-mcp-server`) and any additional
MCP servers via stdio or SSE transports.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mcp.client.stdio import StdioServerParameters

# Default configuration settings
DEFAULT_STARTUP_TIMEOUT_SECONDS = 30
DEFAULT_SEARCH_RPM = 30
DEFAULT_FETCH_RPM = 20
DEFAULT_SAFE_SEARCH_MODE = "MODERATE"


@dataclass
class MCPServerSettings:
    """Settings for an MCP server process."""
    name: str = "duckduckgo"
    command: str = field(default_factory=lambda: sys.executable)
    args: List[str] = field(default_factory=lambda: ["-m", "duckduckgo_mcp_server.server"])
    env: Dict[str, str] = field(default_factory=dict)
    startup_timeout: int = DEFAULT_STARTUP_TIMEOUT_SECONDS
    continue_on_error: bool = True
    url: Optional[str] = None  # Populated for HTTP/SSE transport


def get_duckduckgo_server_params(
    custom_env: Optional[Dict[str, str]] = None,
) -> StdioServerParameters:
    """
    Build StdioServerParameters for launching the duckduckgo-mcp-server process.

    Args:
        custom_env: Optional extra environment variables to pass to the MCP subprocess.

    Returns:
        Configured StdioServerParameters instance.
    """
    env_vars = dict(os.environ)

    # Configure server tuning from environment variables if present
    env_vars["SAFE_SEARCH_MODE"] = os.getenv("MCP_SAFE_SEARCH_MODE", DEFAULT_SAFE_SEARCH_MODE)
    env_vars["SEARCH_RPM"] = os.getenv("MCP_SEARCH_RPM", str(DEFAULT_SEARCH_RPM))
    env_vars["FETCH_RPM"] = os.getenv("MCP_FETCH_RPM", str(DEFAULT_FETCH_RPM))

    if custom_env:
        env_vars.update(custom_env)

    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "duckduckgo_mcp_server.server"],
        env=env_vars,
    )


def get_mcp_servers_config() -> Dict[str, Any]:
    """
    Return a standard mcpServers configuration mapping suitable for MCPClient.load_servers.
    """
    return {
        "mcpServers": {
            "duckduckgo": {
                "command": sys.executable,
                "args": ["-m", "duckduckgo_mcp_server.server"],
                "env": {
                    "SAFE_SEARCH_MODE": os.getenv("MCP_SAFE_SEARCH_MODE", DEFAULT_SAFE_SEARCH_MODE),
                    "SEARCH_RPM": os.getenv("MCP_SEARCH_RPM", str(DEFAULT_SEARCH_RPM)),
                    "FETCH_RPM": os.getenv("MCP_FETCH_RPM", str(DEFAULT_FETCH_RPM)),
                },
                "continue_on_error": True,
            }
        }
    }
