"""Strategy MCP tools."""

from __future__ import annotations

import logging
from typing import Any

from meta_agent_mcp.agents.strategy import (
    analyze_decision as _analyze_decision,
    compare_options as _compare_options,
    generate_strategy as _generate_strategy,
)
from meta_agent_mcp.mcp_instance import mcp
from meta_agent_mcp.models.strategy import (
    DecisionAnalysis,
    Option,
    OptionComparison,
    StrategyResult,
)

logger: logging.Logger = logging.getLogger(__name__)


@mcp.tool
async def analyze_decision(situation: str) -> dict[str, Any]:
    """Analyze a decision situation and provide strategic insights.

    Use this to understand the key factors, opportunities, threats, and
    recommended approach for a strategic decision.

    Args:
        situation: Detailed description of the situation or decision to analyze

    Returns:
        dict containing:
        - situation_summary: Summary of the analyzed situation
        - key_factors: Key factors influencing the decision
        - opportunities: Identified opportunities
        - threats: Identified threats or challenges
        - information_gaps: Areas needing more information
        - recommended_approach: Recommended strategic approach
    """
    result: DecisionAnalysis = await _analyze_decision(situation)
    return result.model_dump()


@mcp.tool
async def compare_options(
    context: str,
    options: list[str],
) -> dict[str, Any]:
    """Compare multiple options for a decision using structured criteria.

    Evaluates each option on feasibility, impact, and risk to provide
    a data-driven recommendation.

    Args:
        context: Context or background for the decision
        options: List of options to compare (2-5 options recommended)

    Returns:
        dict containing:
        - options: List of analyzed options with scores
        - recommended_option: The recommended choice
        - recommendation_rationale: Why this option is recommended
        - trade_offs: Key trade-offs to consider
        - implementation_notes: Notes for implementation
    """
    if len(options) < 2:
        return {"error": "Please provide at least 2 options to compare"}

    effective_options: list[str] = options[:10] if len(options) > 10 else options

    result: OptionComparison = await _compare_options(context, effective_options)

    return {
        "options": [opt.model_dump() for opt in result.options],
        "recommended_option": result.recommended_option,
        "recommendation_rationale": result.recommendation_rationale,
        "trade_offs": result.trade_offs,
        "implementation_notes": result.implementation_notes,
    }


@mcp.tool
async def generate_strategy(
    situation: str,
    objectives: list[str],
    constraints: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a comprehensive strategic recommendation.

    Creates a full strategic plan with analysis, recommendations,
    action items, and success criteria.

    Args:
        situation: Description of the current situation
        objectives: List of key objectives to achieve
        constraints: Optional list of constraints to consider

    Returns:
        dict containing:
        - context: The analyzed decision context
        - analysis: Strategic analysis narrative
        - options: Options considered
        - recommendation: Primary recommendation with action items
        - alternative_strategies: Alternative approaches
        - confidence: Confidence level in the recommendation
    """
    if not objectives:
        return {"error": "Please provide at least one objective"}

    result: StrategyResult = await _generate_strategy(
        situation,
        objectives,
        constraints or [],
    )

    return {
        "context": result.context.model_dump(),
        "analysis": result.analysis,
        "options": [opt.model_dump() for opt in result.options],
        "recommendation": result.recommendation.model_dump(),
        "alternative_strategies": [
            alt.model_dump() for alt in result.alternative_strategies
        ],
        "confidence": result.confidence,
    }

