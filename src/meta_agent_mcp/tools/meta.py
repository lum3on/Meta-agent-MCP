"""Meta Agent MCP tools.

This module provides the main orchestrator tool that combines research,
reasoning, and strategy capabilities to handle complex queries.
"""

from __future__ import annotations

import logging
from typing import Any

from meta_agent_mcp.agents.meta import run_meta_agent
from meta_agent_mcp.mcp_instance import mcp
from meta_agent_mcp.models.meta import MetaAgentResult
from meta_agent_mcp.models.reasoning import ReasoningMethod

logger: logging.Logger = logging.getLogger(__name__)


@mcp.tool
async def meta_agent_query(
    query: str,
    reasoning_method: str = "beam_search",
) -> dict[str, Any]:
    """Process a complex query using the Meta Agent orchestrator.

    This is the main entry point for intelligent query processing. The Meta Agent
    analyzes your query and coordinates specialist agents:
    - Research Agent: Web crawling and information gathering
    - Reasoning Agent: Structured reasoning with Beam Search or MCTS
    - Strategy Agent: Decision analysis and strategic recommendations

    Use this for complex questions that may require:
    - Researching information from the web
    - Reasoning through problems step by step
    - Making strategic decisions or comparisons

    Args:
        query: Your question or request to process
        reasoning_method: Method for reasoning tasks - "beam_search" or "mcts"
                         (default: beam_search for most queries)

    Returns:
        dict containing:
        - query: Original query
        - task_type: Classification of the query (research/reasoning/strategy/combined)
        - summary: Executive summary of the response
        - detailed_response: Full detailed response
        - agent_results: Results from each specialist agent used
        - sources_used: URLs or sources consulted (if any)
        - confidence: Overall confidence level (0.0 to 1.0)
        - follow_up_suggestions: Suggested follow-up questions

    Examples:
        - "What are the latest developments in AI agents?" -> Research
        - "Should I use React or Vue for my new project?" -> Strategy
        - "Walk me through solving this optimization problem" -> Reasoning
        - "Research microservices patterns and recommend an architecture" -> Combined
    """
    logger.info(f"Meta agent processing query: {query[:100]}...")
    print(f"[DEBUG] meta_agent_query called with: {query[:100]}...", flush=True)

    # Validate reasoning method
    method: ReasoningMethod
    try:
        method = ReasoningMethod(reasoning_method.lower())
    except ValueError:
        method = ReasoningMethod.BEAM_SEARCH
        logger.warning(f"Unknown reasoning method '{reasoning_method}', using beam_search")

    print(f"[DEBUG] Using reasoning method: {method.value}", flush=True)

    try:
        # Pass reasoning method to meta agent
        print("[DEBUG] Calling run_meta_agent...", flush=True)
        result: MetaAgentResult = await run_meta_agent(query, method)
        print("[DEBUG] run_meta_agent completed successfully", flush=True)

        return {
            "query": result.query,
            "task_type": result.task_type.value,
            "summary": result.summary,
            "detailed_response": result.detailed_response,
            "agent_results": [ar.model_dump() for ar in result.agent_results],
            "sources_used": result.sources_used,
            "confidence": result.confidence,
            "follow_up_suggestions": result.follow_up_suggestions,
        }

    except Exception as e:
        logger.error(f"Meta agent error: {e}", exc_info=True)
        return {
            "query": query,
            "task_type": "error",
            "summary": f"Error processing query: {str(e)}",
            "detailed_response": f"An error occurred while processing your query: {str(e)}",
            "agent_results": [],
            "sources_used": [],
            "confidence": 0.0,
            "follow_up_suggestions": ["Try simplifying your query", "Check if the query is well-formed"],
        }

