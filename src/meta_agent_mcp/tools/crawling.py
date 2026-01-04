"""Web crawling MCP tools.

Note: Crawl4AI imports are done lazily inside functions to avoid
heavy Playwright initialization at module load time.
"""

from __future__ import annotations

import json
import logging
from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, Field

from meta_agent_mcp.mcp_instance import mcp

# Only import for type checking, not at runtime
if TYPE_CHECKING:
    from meta_agent_mcp.crawling.crawler import WebCrawler
    from meta_agent_mcp.models.research import CrawlResult, DeepCrawlResult, ExtractedData

logger: logging.Logger = logging.getLogger(__name__)


class CrawlUrlInput(BaseModel):
    """Input for crawl_url tool."""

    url: str = Field(description="The URL to crawl")
    timeout: int = Field(
        default=30, ge=5, le=120, description="Request timeout in seconds"
    )


class DeepCrawlInput(BaseModel):
    """Input for deep_crawl tool."""

    start_url: str = Field(description="Starting URL for the crawl")
    max_depth: int = Field(
        default=2, ge=1, le=5, description="Maximum depth to crawl (1-5)"
    )
    max_pages: int = Field(
        default=10, ge=1, le=50, description="Maximum pages to crawl (1-50)"
    )
    url_pattern: str | None = Field(
        default=None, description="Optional regex pattern to filter URLs"
    )


class ExtractStructuredDataInput(BaseModel):
    """Input for extract_structured_data tool."""

    url: str = Field(description="URL to extract data from")
    schema_name: str = Field(description="Name for the extraction schema")
    base_selector: str = Field(
        description="CSS selector for the base element containing items"
    )
    fields: list[dict[str, Any]] = Field(
        description="Field definitions: [{name, selector, type, attribute?}]"
    )


class SmartExtractInput(BaseModel):
    """Input for smart_extract tool."""

    url: str = Field(description="URL to extract data from")
    instruction: str = Field(
        description="Natural language instruction for what to extract"
    )
    output_schema: dict[str, Any] | None = Field(
        default=None, description="Optional Pydantic model schema for structured output"
    )


@mcp.tool
async def crawl_url(url: str, timeout: int = 30) -> dict[str, Any]:
    """Crawl a single URL and extract content as clean markdown.

    This tool fetches a webpage and converts it to LLM-friendly markdown,
    filtering out navigation, ads, and other non-content elements.

    Args:
        url: The URL to crawl (must be a valid http/https URL)
        timeout: Request timeout in seconds (5-120, default 30)

    Returns:
        dict containing:
        - url: The crawled URL
        - title: Page title if available
        - markdown: Extracted content as markdown
        - word_count: Number of words extracted
        - success: Whether the crawl succeeded
        - error: Error message if failed
    """
    # Lazy import to avoid Crawl4AI initialization at module load
    from meta_agent_mcp.crawling.crawler import WebCrawler, get_crawler
    from meta_agent_mcp.models.research import CrawlResult

    crawler: WebCrawler = await get_crawler()
    result: CrawlResult = await crawler.crawl_url(url, timeout=timeout)
    return result.model_dump()


@mcp.tool
async def deep_crawl(
    start_url: str,
    max_depth: int = 2,
    max_pages: int = 10,
    url_pattern: str | None = None,
) -> dict[str, Any]:
    """Perform deep crawl of a website starting from a URL.

    Crawls multiple pages by following links, respecting depth and page limits.
    Useful for gathering comprehensive information from a website.

    Args:
        start_url: Starting URL for the crawl
        max_depth: Maximum link depth to follow (1-5, default 2)
        max_pages: Maximum number of pages to crawl (1-50, default 10)
        url_pattern: Optional regex to filter which URLs to follow

    Returns:
        dict containing:
        - start_url: The starting URL
        - pages_crawled: Number of pages successfully crawled
        - max_depth_reached: Deepest level reached
        - results: List of individual page results
        - total_word_count: Total words across all pages
    """
    # Lazy import to avoid Crawl4AI initialization at module load
    from meta_agent_mcp.crawling.crawler import WebCrawler, get_crawler
    from meta_agent_mcp.models.research import DeepCrawlResult

    crawler: WebCrawler = await get_crawler()
    result: DeepCrawlResult = await crawler.deep_crawl(
        start_url,
        max_depth=max_depth,
        max_pages=max_pages,
        url_pattern=url_pattern,
    )
    return result.model_dump()


@mcp.tool
async def extract_structured_data(
    url: str,
    schema_name: str,
    base_selector: str,
    fields: list[dict[str, Any]],
) -> dict[str, Any]:
    """Extract structured data from a webpage using CSS selectors.

    Use this to extract repeating data items like product listings,
    article lists, or any structured content from a webpage.

    Args:
        url: URL to extract data from
        schema_name: Descriptive name for what you're extracting
        base_selector: CSS selector for container elements (e.g., '.product-card')
        fields: List of field definitions, each with:
            - name: Field name in output
            - selector: CSS selector relative to base
            - type: 'text', 'attribute', or 'html'
            - attribute: Attribute name if type is 'attribute'

    Returns:
        dict containing:
        - url: Source URL
        - schema_name: Schema used
        - data: List of extracted items
        - item_count: Number of items extracted
    """
    # Lazy imports to avoid Crawl4AI initialization at module load
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
    from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
    from meta_agent_mcp.models.research import ExtractedData

    schema: dict[str, Any] = {
        "name": schema_name,
        "baseSelector": base_selector,
        "fields": fields,
    }

    strategy = JsonCssExtractionStrategy(schema)
    config = CrawlerRunConfig(extraction_strategy=strategy)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)

        if result.success and result.extracted_content:
            data: list[dict[str, Any]] = json.loads(result.extracted_content)
            return ExtractedData(
                url=url,
                schema_name=schema_name,
                data=data,
                item_count=len(data),
            ).model_dump()

    return ExtractedData(
        url=url,
        schema_name=schema_name,
        data=[],
        item_count=0,
    ).model_dump()

