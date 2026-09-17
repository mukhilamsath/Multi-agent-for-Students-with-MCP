"""
mcp_client/decorators.py
═══════════════════════════════════════════════════════════════════════════════
Re-exports the `@mcp_tool` decorator from `mcp_client.config`.
═══════════════════════════════════════════════════════════════════════════════
"""

from mcp_client.config import mcp_tool

__all__ = ["mcp_tool"]
