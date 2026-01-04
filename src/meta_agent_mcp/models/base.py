"""Base model configuration for Pydantic AI with OpenRouter."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

if TYPE_CHECKING:
    from meta_agent_mcp.config import Settings


def _get_settings() -> Settings:
    """Lazy import settings to avoid circular imports."""
    from meta_agent_mcp.config import settings
    return settings


@lru_cache(maxsize=1)
def get_openrouter_provider() -> OpenRouterProvider:
    """Get cached OpenRouter provider instance.

    Returns:
        OpenRouterProvider: Configured OpenRouter provider.

    Raises:
        ValueError: If OPENROUTER_API_KEY is not set.
    """
    settings = _get_settings()
    if not settings.openrouter_api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable is required. "
            "Please set it in your .env file or environment."
        )

    return OpenRouterProvider(
        api_key=settings.openrouter_api_key,
        app_url=settings.openrouter_app_url,
        app_title=settings.openrouter_app_title,
    )


def get_model(model_name: str | None = None) -> OpenRouterModel:
    """Get an OpenRouter model instance.

    Args:
        model_name: Optional model name override. Defaults to settings.meta_agent_model.

    Returns:
        OpenRouterModel: Configured model instance ready for use with Pydantic AI agents.
    """
    settings = _get_settings()
    model_id: str = model_name or settings.meta_agent_model
    provider: OpenRouterProvider = get_openrouter_provider()

    return OpenRouterModel(
        model_id,
        provider=provider,
    )


def get_reasoning_model() -> OpenRouterModel:
    """Get the model configured for reasoning tasks (Beam Search, MCTS).

    Uses REASONING_MODEL setting - typically a fast/cheap model like Claude Haiku.

    Returns:
        OpenRouterModel: Model instance for reasoning tasks.
    """
    settings = _get_settings()
    return get_model(settings.reasoning_model)


def get_strategy_model() -> OpenRouterModel:
    """Get the model configured for strategy tasks.

    Uses STRATEGY_MODEL setting - typically a high-quality model like Claude Sonnet.

    Returns:
        OpenRouterModel: Model instance for strategy tasks.
    """
    settings = _get_settings()
    return get_model(settings.strategy_model)


def get_meta_model() -> OpenRouterModel:
    """Get the model configured for meta agent orchestration.

    Uses META_AGENT_MODEL setting - the main orchestrator model.

    Returns:
        OpenRouterModel: Model instance for meta agent tasks.
    """
    settings = _get_settings()
    return get_model(settings.meta_agent_model)

