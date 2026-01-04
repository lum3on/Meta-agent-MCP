"""MCP Tools for Meta Agent.

This package contains the tool implementations exposed via FastMCP:

Web Crawling Tools:
- crawl_url: Basic URL crawling with markdown extraction
- deep_crawl: Multi-page crawling with configurable depth
- extract_structured_data: CSS selector-based data extraction

Reasoning Tools:
- beam_search_reason: Beam search reasoning algorithm
- mcts_reason: Monte Carlo Tree Search reasoning
- get_reasoning_tree: Visualize reasoning process

Strategy Tools:
- analyze_decision: Strategic context analysis
- compare_options: Multi-criteria option comparison
- generate_strategy: Strategic recommendation generation

Meta Tool:
- meta_agent_query: Main orchestrator entry point
"""

from __future__ import annotations

from meta_agent_mcp.tools.crawling import (
    crawl_url,
    deep_crawl,
    extract_structured_data,
)
from meta_agent_mcp.tools.reasoning import (
    beam_search_reason,
    mcts_reason,
    get_reasoning_tree,
)
from meta_agent_mcp.tools.strategy import (
    analyze_decision,
    compare_options,
    generate_strategy,
)
from meta_agent_mcp.tools.meta import meta_agent_query

__all__: list[str] = [
    # Crawling
    "crawl_url",
    "deep_crawl",
    "extract_structured_data",
    # Reasoning
    "beam_search_reason",
    "mcts_reason",
    "get_reasoning_tree",
    # Strategy
    "analyze_decision",
    "compare_options",
    "generate_strategy",
    # Meta
    "meta_agent_query",
]

