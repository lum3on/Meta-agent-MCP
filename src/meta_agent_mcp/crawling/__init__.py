"""Web crawling implementations using Crawl4AI patterns.

This package provides web crawling functionality:
- AsyncWebCrawler wrapper for async crawling
- Content extraction with markdown generation
- Structured data extraction strategies
- LLM-based smart extraction
"""

from __future__ import annotations

from meta_agent_mcp.crawling.crawler import WebCrawler, get_crawler

__all__: list[str] = [
    "WebCrawler",
    "get_crawler",
]

