"""Research Agent implementation using Pydantic AI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai import Agent, RunContext

from meta_agent_mcp.crawling.crawler import WebCrawler, get_crawler
from meta_agent_mcp.models.research import CrawlResult, DeepCrawlResult, ResearchResult

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class ResearchDependencies:
    """Dependencies for the Research Agent."""

    crawler: WebCrawler
    max_sources: int = 5


# Lazy agent initialization
_research_agent: Agent[ResearchDependencies, ResearchResult] | None = None


def _get_research_agent() -> Agent[ResearchDependencies, ResearchResult]:
    """Get or create the research agent (lazy initialization).

    Returns:
        Agent configured for research tasks.
    """
    global _research_agent
    if _research_agent is not None:
        return _research_agent

    from meta_agent_mcp.models.base import get_model

    agent: Agent[ResearchDependencies, ResearchResult] = Agent(
        model=get_model(),
        deps_type=ResearchDependencies,
        output_type=ResearchResult,
        retries=3,  # Allow more retries for tool calls
        output_retries=3,  # Allow more retries for output validation
        system_prompt="""\
You are a Research Agent specialized in gathering and synthesizing information from the web.

Your capabilities:
1. Crawl and extract content from URLs using the crawl_url tool
2. Perform deep crawls to gather comprehensive information using deep_crawl
3. Synthesize findings into structured research results

Guidelines:
- Always cite your sources with URLs
- Evaluate the relevance of each finding (0.0 to 1.0 score)
- Extract key points from each source
- Provide an executive summary of your findings
- Include confidence level based on source quality and consistency
- Suggest next steps or areas needing more research

When given a research query:
1. Break it down into searchable components
2. Crawl relevant URLs to gather information
3. Synthesize findings into a coherent response
4. Rate your confidence based on source quality
""",
    )

    # Register tools on the agent
    @agent.tool
    async def crawl_url(
        ctx: RunContext[ResearchDependencies],
        url: str,
    ) -> str:
        """Crawl a URL and extract its content as markdown.

        Args:
            ctx: The run context with dependencies.
            url: The URL to crawl and extract content from.

        Returns:
            The extracted markdown content, or an error message.
        """
        result: CrawlResult = await ctx.deps.crawler.crawl_url(url)

        if result.success:
            return f"# {result.title or 'Untitled'}\n\nSource: {url}\nWords: {result.word_count}\n\n{result.markdown}"
        else:
            return f"Failed to crawl {url}: {result.error}"

    @agent.tool
    async def deep_crawl(
        ctx: RunContext[ResearchDependencies],
        start_url: str,
        max_depth: int = 2,
        max_pages: int = 5,
    ) -> str:
        """Perform a deep crawl of a website to gather comprehensive information.

        Args:
            ctx: The run context with dependencies.
            start_url: The starting URL for the deep crawl.
            max_depth: Maximum depth to follow links (1-5).
            max_pages: Maximum number of pages to crawl.

        Returns:
            Combined content from all crawled pages.
        """
        effective_max_pages: int = min(max_pages, ctx.deps.max_sources)

        result: DeepCrawlResult = await ctx.deps.crawler.deep_crawl(
            start_url,
            max_depth=max_depth,
            max_pages=effective_max_pages,
        )

        content_parts: list[str] = [
            f"# Deep Crawl Results\n\nStarted from: {start_url}\n"
            f"Pages crawled: {result.pages_crawled}\n"
            f"Total words: {result.total_word_count}\n\n---\n"
        ]

        for page in result.results:
            if page.success:
                content_parts.append(
                    f"## {page.title or 'Untitled'}\n"
                    f"URL: {page.url}\n\n"
                    f"{page.markdown[:2000]}...\n\n---\n"
                )

        return "\n".join(content_parts)

    _research_agent = agent
    return agent


async def run_research(query: str, urls: list[str] | None = None) -> ResearchResult:
    """Run a research query using the Research Agent.

    Args:
        query: The research question or topic.
        urls: Optional list of specific URLs to research.

    Returns:
        ResearchResult with findings and synthesis.
    """
    crawler: WebCrawler = await get_crawler()
    deps: ResearchDependencies = ResearchDependencies(crawler=crawler)

    prompt: str = f"Research the following: {query}"
    if urls:
        prompt += f"\n\nStart with these URLs: {', '.join(urls)}"

    agent: Agent[ResearchDependencies, ResearchResult] = _get_research_agent()
    result: AgentRunResult[ResearchResult] = await agent.run(prompt, deps=deps)
    return result.output

