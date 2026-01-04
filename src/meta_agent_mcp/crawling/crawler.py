"""Web crawling implementation using Crawl4AI patterns.

Note: Crawl4AI imports are done lazily to avoid heavy Playwright
initialization at module load time.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crawl4ai import AsyncWebCrawler

from meta_agent_mcp.config import settings
from meta_agent_mcp.models.research import CrawlResult, DeepCrawlResult

logger: logging.Logger = logging.getLogger(__name__)


class WebCrawler:
    """Async web crawler wrapping Crawl4AI functionality."""

    def __init__(self) -> None:
        """Initialize the web crawler."""
        self._crawler: AsyncWebCrawler | None = None
        self._lock: asyncio.Lock = asyncio.Lock()

    async def _get_crawler(self) -> AsyncWebCrawler:
        """Get or create the async crawler instance.

        Returns:
            AsyncWebCrawler: The initialized crawler instance.
        """
        async with self._lock:
            if self._crawler is None:
                from crawl4ai import AsyncWebCrawler
                self._crawler = AsyncWebCrawler()
                await self._crawler.__aenter__()
            return self._crawler

    async def close(self) -> None:
        """Close the crawler and release resources."""
        async with self._lock:
            if self._crawler is not None:
                await self._crawler.__aexit__(None, None, None)
                self._crawler = None

    async def crawl_url(
        self,
        url: str,
        *,
        timeout: int | None = None,
        extract_media: bool = False,
    ) -> CrawlResult:
        """Crawl a single URL and extract content as markdown.

        Args:
            url: The URL to crawl.
            timeout: Request timeout in seconds.
            extract_media: Whether to extract media links.

        Returns:
            CrawlResult with extracted content.
        """
        # Lazy imports for Crawl4AI components
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

        effective_timeout: int = timeout or settings.default_crawl_timeout
        crawler: AsyncWebCrawler = await self._get_crawler()

        try:
            # Configure markdown generation with content filtering
            md_generator = DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(
                    threshold=0.4,
                    threshold_type="fixed",
                )
            )

            config = CrawlerRunConfig(
                markdown_generator=md_generator,
                page_timeout=effective_timeout * 1000,  # Convert to ms
            )

            result = await crawler.arun(url=url, config=config)

            if result.success:
                markdown: str = result.markdown.fit_markdown or result.markdown.raw_markdown or ""
                return CrawlResult(
                    url=url,
                    title=result.metadata.get("title") if result.metadata else None,
                    markdown=markdown,
                    word_count=len(markdown.split()) if markdown else 0,
                    success=True,
                )
            else:
                return CrawlResult(
                    url=url,
                    title=None,
                    markdown="",
                    word_count=0,
                    success=False,
                    error=result.error_message or "Unknown error",
                )

        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return CrawlResult(
                url=url,
                title=None,
                markdown="",
                word_count=0,
                success=False,
                error=str(e),
            )

    async def deep_crawl(
        self,
        start_url: str,
        *,
        max_depth: int | None = None,
        max_pages: int | None = None,
        url_pattern: str | None = None,
    ) -> DeepCrawlResult:
        """Perform deep crawl starting from a URL.

        Args:
            start_url: Starting URL for the crawl.
            max_depth: Maximum depth to crawl.
            max_pages: Maximum number of pages to crawl.
            url_pattern: Optional regex pattern to filter URLs.

        Returns:
            DeepCrawlResult with all crawled pages.
        """
        effective_max_depth: int = min(
            max_depth or settings.max_crawl_depth,
            settings.max_crawl_depth
        )
        effective_max_pages: int = min(
            max_pages or settings.max_crawl_pages,
            settings.max_crawl_pages
        )

        results: list[CrawlResult] = []
        visited: set[str] = set()
        to_visit: list[tuple[str, int]] = [(start_url, 0)]
        max_depth_reached: int = 0

        while to_visit and len(results) < effective_max_pages:
            url, depth = to_visit.pop(0)

            if url in visited or depth > effective_max_depth:
                continue

            visited.add(url)
            result: CrawlResult = await self.crawl_url(url)
            results.append(result)

            if result.success:
                max_depth_reached = max(max_depth_reached, depth)

            # Yield control to event loop to prevent blocking
            await asyncio.sleep(0)

        total_words: int = sum(r.word_count for r in results if r.success)

        return DeepCrawlResult(
            start_url=start_url,
            pages_crawled=len([r for r in results if r.success]),
            max_depth_reached=max_depth_reached,
            results=results,
            total_word_count=total_words,
        )


# Global crawler instance with lock for thread safety
_crawler: WebCrawler | None = None
_crawler_lock: asyncio.Lock = asyncio.Lock()


async def get_crawler() -> WebCrawler:
    """Get the global web crawler instance.

    Returns:
        WebCrawler: The singleton web crawler instance.
    """
    global _crawler
    async with _crawler_lock:
        if _crawler is None:
            _crawler = WebCrawler()
        return _crawler

