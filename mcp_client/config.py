"""
mcp_client/config.py
═══════════════════════════════════════════════════════════════════════════════
Model Context Protocol (MCP) Server Configuration & Tool Decorator Layer.

Defines:
  1. MCP server process parameters (DuckDuckGo & Study Concept MCP servers).
  2. Server configuration settings, rate limits, and environment mappings.
  3. The `@mcp_tool` decorator allowing agents to connect directly to MCP tools
     as clean Python functions without exposing raw URLs or connection endpoints.
═══════════════════════════════════════════════════════════════════════════════
"""

import functools
import inspect
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Ensure project root is in sys.path when executed directly
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from strands import tool
from mcp.client.stdio import StdioServerParameters

logger = logging.getLogger(__name__)

# Default configuration settings
DEFAULT_STARTUP_TIMEOUT_SECONDS = 30
DEFAULT_SEARCH_RPM = 30
DEFAULT_FETCH_RPM = 20
DEFAULT_SAFE_SEARCH_MODE = "MODERATE"

# Path to the dedicated Study MCP server
STUDY_MCP_SERVER_SCRIPT = str(_PROJECT_ROOT / "servers" / "study_mcp" / "server.py")


@dataclass
class MCPServerSettings:
    """Settings for an MCP server process."""
    name: str
    command: str = field(default_factory=lambda: sys.executable)
    args: List[str] = field(default_factory=list)
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


def get_study_server_params(
    custom_env: Optional[Dict[str, str]] = None,
) -> StdioServerParameters:
    """
    Build StdioServerParameters for launching the Study Concept MCP server.

    Args:
        custom_env: Optional extra environment variables to pass to the MCP subprocess.

    Returns:
        Configured StdioServerParameters instance.
    """
    env_vars = dict(os.environ)
    if custom_env:
        env_vars.update(custom_env)

    return StdioServerParameters(
        command=sys.executable,
        args=[STUDY_MCP_SERVER_SCRIPT],
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
            },
            "study": {
                "command": sys.executable,
                "args": [STUDY_MCP_SERVER_SCRIPT],
                "env": {},
                "continue_on_error": True,
            },
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MCP Tool Decorator & Client Lifecycle Manager
# ═══════════════════════════════════════════════════════════════════════════════
# MCP Tool Decorator & Client Lifecycle Manager
# ═══════════════════════════════════════════════════════════════════════════════

def _create_mcp_client(server_name: str) -> Any:
    """Create an MCP client instance for the given server."""
    from mcp_client.client import create_research_mcp_client, create_study_mcp_client

    if server_name in {"duckduckgo", "research"}:
        return create_research_mcp_client(continue_on_error=True)
    elif server_name in {"study", "concept"}:
        return create_study_mcp_client(continue_on_error=True)
    else:
        raise ValueError(f"Unknown MCP server identifier: {server_name!r}")


def mcp_tool(server_name: str, tool_name: Optional[str] = None) -> Callable:
    """
    Decorator that connects a Python function directly to an underlying MCP server tool.

    Hides all MCP URLs, stdio subprocesses, and JSON-RPC payloads behind a standard
    Python function interface compatible with Strands Agents.

    Usage:
        @mcp_tool(server_name="duckduckgo", tool_name="search")
        def search_web(query: str, max_results: int = 5) -> dict:
            '''Search the web using DuckDuckGo MCP tool.'''
            ...

    Args:
        server_name: The internal MCP server name ("duckduckgo" or "study").
        tool_name: Optional name of the tool on the MCP server. Defaults to the decorated function's name.

    Returns:
        Decorated Strands Agent tool.
    """
    def decorator(func: Callable) -> Callable:
        target_mcp_tool = tool_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Map positional and keyword arguments to the tool signature
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            call_arguments = bound.arguments

            log_msg = f"MCP | Calling tool: {target_mcp_tool} | args: {call_arguments}"
            print(f"\n{log_msg}")
            logger.info(log_msg)

            client = _create_mcp_client(server_name)
            tool_use_id = f"mcp-call-{target_mcp_tool}"

            try:
                with client:
                    result = client.call_tool_sync(
                        name=target_mcp_tool,
                        arguments=call_arguments,
                        tool_use_id=tool_use_id,
                    )

                # Format human-readable output snippet for logging
                snippet = ""
                if isinstance(result, dict):
                    if "structuredContent" in result and result["structuredContent"]:
                        snippet = str(result["structuredContent"])
                    elif "content" in result and result["content"]:
                        texts = [c.get("text", "") for c in result["content"] if isinstance(c, dict) and "text" in c]
                        snippet = "\n".join(texts)
                    else:
                        snippet = str(result)
                else:
                    snippet = str(result)

                preview = snippet.strip()
                if len(preview) > 400:
                    preview = preview[:400] + " ... [truncated]"

                res_msg = f"MCP | Tool result: {preview}"
                print(f"{res_msg}\n")
                logger.info(res_msg)

                # Return structured content or clean dictionary
                if isinstance(result, dict):
                    if "structuredContent" in result and result["structuredContent"]:
                        return result["structuredContent"]
                    if "content" in result and result["content"]:
                        texts = [c.get("text", "") for c in result["content"] if isinstance(c, dict) and "text" in c]
                        if texts:
                            return {"result": "\n".join(texts)}

                return result

            except Exception as exc:
                error_msg = f"MCP | Error calling tool {target_mcp_tool}: {str(exc)}"
                print(f"{error_msg}\n")
                logger.error(error_msg)
                return {"error": str(exc), "status": "failed"}

        # Return as Strands @tool
        return tool(wrapper)

    return decorator


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    ddg_params = get_duckduckgo_server_params()
    study_params = get_study_server_params()
    print("Research MCP Server Stdio Parameters:")
    print(f"  Command : {ddg_params.command} {' '.join(ddg_params.args)}")
    print("\nStudy MCP Server Stdio Parameters:")
    print(f"  Command : {study_params.command} {' '.join(study_params.args)}")
