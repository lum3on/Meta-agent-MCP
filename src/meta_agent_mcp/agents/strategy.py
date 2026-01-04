"""Strategy Agent implementation using Pydantic AI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic_ai import Agent

from meta_agent_mcp.models.strategy import (
    DecisionAnalysis,
    DecisionContext,
    Option,
    OptionComparison,
    StrategicRecommendation,
    StrategyResult,
)

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class StrategyDependencies:
    """Dependencies for the Strategy Agent."""

    include_alternatives: bool = True
    max_options: int = 5


@lru_cache(maxsize=1)
def _get_decision_analyzer() -> Agent[None, DecisionAnalysis]:
    """Get or create the decision analyzer agent (lazy initialization).

    Returns:
        Agent configured for decision analysis.
    """
    from meta_agent_mcp.models.base import get_strategy_model

    return Agent(
        model=get_strategy_model(),
        output_type=DecisionAnalysis,
        retries=3,  # Allow more retries for output validation
        output_retries=3,
        system_prompt="""\
You are a strategic analyst specialized in decision analysis.
Analyze the given situation and provide structured insights.

Focus on:
- Key factors driving the decision
- Opportunities and threats
- Information gaps that need to be filled
- Recommended strategic approach

Be thorough but concise in your analysis.
""",
    )


@lru_cache(maxsize=1)
def _get_option_comparer() -> Agent[None, OptionComparison]:
    """Get or create the option comparer agent (lazy initialization).

    Returns:
        Agent configured for option comparison.
    """
    from meta_agent_mcp.models.base import get_strategy_model

    return Agent(
        model=get_strategy_model(),
        output_type=OptionComparison,
        retries=3,  # Allow more retries for output validation
        output_retries=3,
        system_prompt="""\
You are an options analyst specialized in comparing decision alternatives.

For each option, evaluate:
- Feasibility (0-1): How achievable is this option?
- Impact (0-1): What's the potential positive outcome?
- Risk (0-1): What's the level of risk? (0=low, 1=high)

Calculate overall_score as: (feasibility * 0.3) + (impact * 0.4) + ((1-risk) * 0.3)

Provide clear pros and cons for each option and a justified recommendation.
""",
    )


@lru_cache(maxsize=1)
def _get_strategy_generator() -> Agent[None, StrategyResult]:
    """Get or create the strategy generator agent (lazy initialization).

    Returns:
        Agent configured for strategy generation.
    """
    from meta_agent_mcp.models.base import get_strategy_model

    return Agent(
        model=get_strategy_model(),
        output_type=StrategyResult,
        retries=3,  # Allow more retries for output validation
        output_retries=3,
        system_prompt="""\
You are a strategic advisor specialized in developing comprehensive strategies.

When generating a strategy:
1. Understand the context and objectives
2. Analyze available options
3. Develop a primary recommendation with clear action items
4. Define success criteria
5. Identify risks to monitor
6. Suggest alternative approaches

Be specific and actionable in your recommendations.
""",
    )


async def analyze_decision(situation: str) -> DecisionAnalysis:
    """Analyze a decision or situation.

    Args:
        situation: Description of the situation to analyze.

    Returns:
        DecisionAnalysis with insights and recommendations.
    """
    agent: Agent[None, DecisionAnalysis] = _get_decision_analyzer()
    result: AgentRunResult[DecisionAnalysis] = await agent.run(situation)
    return result.output


async def compare_options(
    context: str,
    options: list[str],
) -> OptionComparison:
    """Compare multiple options for a decision.

    Args:
        context: Context for the decision.
        options: List of option names/descriptions to compare.

    Returns:
        OptionComparison with analysis and recommendation.
    """
    prompt: str = f"Context: {context}\n\nOptions to compare:\n"
    for i, opt in enumerate(options, 1):
        prompt += f"{i}. {opt}\n"

    agent: Agent[None, OptionComparison] = _get_option_comparer()
    result: AgentRunResult[OptionComparison] = await agent.run(prompt)
    return result.output


async def generate_strategy(
    situation: str,
    objectives: list[str],
    constraints: list[str] | None = None,
) -> StrategyResult:
    """Generate a comprehensive strategy.

    Args:
        situation: Description of the current situation.
        objectives: Key objectives to achieve.
        constraints: Optional list of constraints.

    Returns:
        StrategyResult with full strategic analysis.
    """
    prompt: str = f"Situation: {situation}\n\n"
    prompt += "Objectives:\n" + "\n".join(f"- {obj}" for obj in objectives)

    if constraints:
        prompt += "\n\nConstraints:\n" + "\n".join(f"- {c}" for c in constraints)

    agent: Agent[None, StrategyResult] = _get_strategy_generator()
    result: AgentRunResult[StrategyResult] = await agent.run(prompt)
    return result.output

