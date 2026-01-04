"""Agent implementations for Meta Agent MCP.

This package contains the Pydantic AI agents:
- ResearchAgent: Web crawling and information gathering
- ReasoningAgent: Structured reasoning with Beam Search and MCTS
- StrategyAgent: Decision analysis and recommendations
- MetaAgent: Orchestrator that coordinates all specialist agents

All agents are lazily initialized to avoid requiring API keys at import time.
Use the run_* functions to execute agents.
"""

from __future__ import annotations

from meta_agent_mcp.agents.research import run_research
from meta_agent_mcp.agents.reasoning import run_reasoning
from meta_agent_mcp.agents.strategy import (
    analyze_decision,
    compare_options,
    generate_strategy,
)
from meta_agent_mcp.agents.meta import run_meta_agent

__all__: list[str] = [
    "run_research",
    "run_reasoning",
    "analyze_decision",
    "compare_options",
    "generate_strategy",
    "run_meta_agent",
]

