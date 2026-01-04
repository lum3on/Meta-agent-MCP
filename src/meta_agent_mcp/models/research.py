"""Pydantic models for research agent outputs."""

from pydantic import BaseModel, Field


class CrawlResult(BaseModel):
    """Result from crawling a single URL."""

    url: str = Field(description="The URL that was crawled")
    title: str | None = Field(default=None, description="Page title if available")
    markdown: str = Field(description="Extracted content as markdown")
    word_count: int = Field(description="Number of words in the content")
    success: bool = Field(default=True, description="Whether the crawl succeeded")
    error: str | None = Field(default=None, description="Error message if crawl failed")


class DeepCrawlResult(BaseModel):
    """Result from deep crawling multiple pages."""

    start_url: str = Field(description="Starting URL for the crawl")
    pages_crawled: int = Field(description="Number of pages successfully crawled")
    max_depth_reached: int = Field(description="Maximum depth reached during crawl")
    results: list[CrawlResult] = Field(description="Individual page results")
    total_word_count: int = Field(description="Total words across all pages")


class ExtractedData(BaseModel):
    """Result from structured data extraction."""

    url: str = Field(description="Source URL")
    schema_name: str = Field(description="Name of the extraction schema used")
    data: list[dict] = Field(description="Extracted structured data items")
    item_count: int = Field(description="Number of items extracted")


class ResearchFinding(BaseModel):
    """A single finding from research."""

    source_url: str = Field(description="URL where this finding was discovered")
    title: str = Field(description="Title or summary of the finding")
    content: str = Field(description="Detailed content of the finding")
    relevance_score: float = Field(
        ge=0.0, le=1.0, description="Relevance score from 0 to 1"
    )
    key_points: list[str] = Field(description="Key takeaways from this finding")


class ResearchResult(BaseModel):
    """Complete research result from the Research Agent."""

    query: str = Field(description="Original research query")
    summary: str = Field(description="Executive summary of findings")
    findings: list[ResearchFinding] = Field(description="Individual research findings")
    sources_consulted: int = Field(description="Number of sources consulted")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Overall confidence in the research"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Recommended next steps or areas to explore"
    )

    @property
    def sources(self) -> list[str]:
        """Extract unique source URLs from findings.

        Returns:
            List of unique source URLs consulted during research.
        """
        return list(dict.fromkeys(f.source_url for f in self.findings))
