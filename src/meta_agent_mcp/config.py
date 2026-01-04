"""Configuration management for Meta Agent MCP Server."""

from __future__ import annotations

from functools import lru_cache
from typing import Final

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenRouter API Configuration
    openrouter_api_key: str = Field(
        default="",
        description="OpenRouter API key for LLM access",
    )
    openrouter_app_url: str | None = Field(
        default=None,
        description="Optional app URL for OpenRouter attribution",
    )
    openrouter_app_title: str | None = Field(
        default="Meta Agent MCP",
        description="Optional app title for OpenRouter attribution",
    )

    # Model Configuration
    meta_agent_model: str = Field(
        default="x-ai/grok-4.1-fast",
        description="Default LLM model for meta agent orchestration via OpenRouter",
    )
    reasoning_model: str = Field(
        default="anthropic/claude-3-haiku",
        description="LLM model for reasoning tasks (Beam Search, MCTS) - fast/cheap",
    )
    strategy_model: str = Field(
        default="anthropic/claude-3.5-sonnet",
        description="LLM model for strategy tasks (decision analysis, comparisons)",
    )

    # Server Configuration
    meta_agent_host: str = Field(
        default="localhost",
        description="Host to bind the server to",
    )
    meta_agent_port: int = Field(
        default=8000,
        description="Port to bind the server to",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    # Reasoning Configuration
    default_beam_width: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Default beam width for beam search reasoning",
    )
    default_max_depth: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Default maximum depth for reasoning",
    )
    default_mcts_simulations: int = Field(
        default=50,
        ge=1,
        le=150,
        description="Default number of MCTS simulations",
    )

    # Transport Configuration
    transport: str = Field(
        default="stdio",
        description="Transport type: 'stdio', 'sse', or 'streamable-http'. "
        "Use 'sse' or 'streamable-http' on Windows to avoid high CPU usage.",
    )
    transport_host: str = Field(
        default="127.0.0.1",
        description="Host for HTTP-based transports (sse, streamable-http)",
    )
    transport_port: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="Port for HTTP-based transports (sse, streamable-http)",
    )

    # Web Crawling Configuration
    default_crawl_timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Default timeout for web crawling in seconds",
    )
    max_crawl_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum depth for deep crawling",
    )
    max_crawl_pages: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum pages to crawl in deep crawl",
    )

    model_config = {
        "env_prefix": "",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: The application settings singleton.
    """
    return Settings()


# Global settings instance
settings: Final[Settings] = get_settings()

