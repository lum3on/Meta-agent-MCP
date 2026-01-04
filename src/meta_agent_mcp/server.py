"""FastMCP Server for Meta Agent MCP.

This module sets up the FastMCP server with all registered tools
for web crawling, reasoning, and strategic decision making.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from meta_agent_mcp.config import settings
from meta_agent_mcp.mcp_instance import mcp

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger: logging.Logger = logging.getLogger(__name__)

# Import tool modules to register them with the MCP server
# The @mcp.tool decorators in these modules register the tools automatically
from meta_agent_mcp.tools import crawling  # noqa: F401
from meta_agent_mcp.tools import reasoning  # noqa: F401
from meta_agent_mcp.tools import strategy  # noqa: F401
from meta_agent_mcp.tools import meta  # noqa: F401

# Valid transport types
VALID_TRANSPORTS = ("stdio", "sse", "streamable-http")


# HTTP Health endpoint for Docker/Kubernetes health checks
@mcp.custom_route("/health", methods=["GET"])
async def http_health_check(request: Request) -> JSONResponse:
    """HTTP endpoint for container health checks."""
    return JSONResponse({
        "status": "healthy",
        "version": "0.1.0",
        "model": settings.meta_agent_model,
        "transport": settings.transport,
    })


@mcp.tool
async def health_check() -> dict[str, Any]:
    """Check the health status of the Meta Agent MCP server.

    Returns:
        dict: Health status information including version and configuration.
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "model": settings.meta_agent_model,
        "features": {
            "web_crawling": True,
            "reasoning": True,
            "strategy": True,
        },
    }


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Meta Agent MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Transport Options:
  stdio            Standard I/O (default, may cause high CPU on Windows)
  sse              Server-Sent Events over HTTP (recommended for Windows)
  streamable-http  Streamable HTTP transport (recommended for Windows)

Examples:
  python -m meta_agent_mcp.server --transport sse
  python -m meta_agent_mcp.server --transport streamable-http --port 8080
  META_AGENT_TRANSPORT=sse python -m meta_agent_mcp.server
""",
    )
    parser.add_argument(
        "-t", "--transport",
        choices=VALID_TRANSPORTS,
        default=None,
        help=f"Transport type: {', '.join(VALID_TRANSPORTS)} (default: from config or stdio)",
    )
    parser.add_argument(
        "-H", "--host",
        default=None,
        help="Host for HTTP transports (default: 127.0.0.1)",
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=None,
        help="Port for HTTP transports (default: 8080)",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point for the Meta Agent MCP server."""
    args = parse_args()

    # Determine transport (CLI arg > env/config > default)
    transport = args.transport or settings.transport
    host = args.host or settings.transport_host
    port = args.port or settings.transport_port

    if transport not in VALID_TRANSPORTS:
        logger.error(f"Invalid transport '{transport}'. Must be one of: {VALID_TRANSPORTS}")
        sys.exit(1)

    logger.info("Starting Meta Agent MCP Server...")
    logger.info(f"Using model: {settings.meta_agent_model}")
    logger.info(f"Transport: {transport}")

    if transport == "stdio":
        # STDIO transport - may cause high CPU on Windows due to busy-polling
        logger.warning(
            "Using STDIO transport. On Windows, this may cause high CPU usage. "
            "Consider using --transport sse or --transport streamable-http instead."
        )
        mcp.run(transport="stdio")
    elif transport == "sse":
        # SSE transport - HTTP-based, works well on Windows
        logger.info(f"SSE server listening on http://{host}:{port}")
        mcp.run(transport="sse", host=host, port=port)
    elif transport == "streamable-http":
        # Streamable HTTP transport - HTTP-based, works well on Windows
        logger.info(f"Streamable HTTP server listening on http://{host}:{port}")
        mcp.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    main()

