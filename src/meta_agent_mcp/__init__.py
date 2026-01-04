"""
Meta Agent MCP Server

A multi-agent orchestration system combining:
- FastMCP 2.0+ for MCP tool exposure
- Pydantic AI for agent orchestration with structured outputs
- Crawl4AI patterns for web crawling and data extraction
- Advanced reasoning algorithms (Beam Search, MCTS)
"""

from __future__ import annotations

from typing import Final

__version__: Final[str] = "0.1.0"

from meta_agent_mcp.config import Settings, settings
from meta_agent_mcp.mcp_instance import mcp

__all__: list[str] = ["mcp", "settings", "Settings", "__version__"]

