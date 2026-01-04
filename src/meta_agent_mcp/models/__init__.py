"""Pydantic models for structured outputs and tool inputs/outputs."""

from __future__ import annotations

from meta_agent_mcp.models.base import get_model, get_openrouter_provider
from meta_agent_mcp.models.research import (
    CrawlResult,
    DeepCrawlResult,
    ExtractedData,
    ResearchFinding,
    ResearchResult,
)

__all__: list[str] = [
    "get_model",
    "get_openrouter_provider",
    "CrawlResult",
    "DeepCrawlResult",
    "ExtractedData",
    "ResearchFinding",
    "ResearchResult",
]

