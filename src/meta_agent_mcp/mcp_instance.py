"""FastMCP instance for Meta Agent MCP.

This module creates the FastMCP server instance that tools register with.
Separated from server.py to avoid circular imports.
"""

from __future__ import annotations

from typing import Final

from fastmcp import FastMCP

# Initialize FastMCP server with async-friendly configuration
mcp: Final[FastMCP] = FastMCP(
    name="Meta Agent MCP",
    instructions=(
        "A multi-agent orchestration MCP server combining web research, "
        "advanced reasoning (Beam Search, MCTS), and strategic decision making."
    ),
)

