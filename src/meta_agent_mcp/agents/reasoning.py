"""Reasoning Agent implementation using Pydantic AI."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic_ai import Agent, RunContext

from meta_agent_mcp.models.reasoning import (
    BeamSearchResult,
    MCTSResult,
    ReasoningMethod,
    ReasoningResult,
)
from meta_agent_mcp.reasoning import BeamSearchReasoner, MCTSReasoner

if TYPE_CHECKING:
    from fastmcp import Context
    from pydantic_ai.agent import AgentRunResult

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class ReasoningDependencies:
    """Dependencies for the Reasoning Agent."""

    default_method: ReasoningMethod = ReasoningMethod.BEAM_SEARCH
    beam_width: int = 3
    max_depth: int = 10
    mcts_simulations: int = 50
    # MCP Context for real-time streaming (optional)
    ctx: "Context | None" = None


# Lazy agent initialization
_reasoning_agent: Agent[ReasoningDependencies, ReasoningResult] | None = None


def _get_reasoning_agent() -> Agent[ReasoningDependencies, ReasoningResult]:
    """Get or create the reasoning agent (lazy initialization).

    Returns:
        Agent configured for reasoning tasks.
    """
    global _reasoning_agent
    if _reasoning_agent is not None:
        return _reasoning_agent

    from meta_agent_mcp.models.base import get_model

    agent: Agent[ReasoningDependencies, ReasoningResult] = Agent(
        model=get_model(),
        deps_type=ReasoningDependencies,
        output_type=ReasoningResult,
        retries=3,  # Allow more retries for tool calls
        output_retries=3,  # Allow more retries for output validation
        system_prompt="""\
You are a Reasoning Agent specialized in structured problem-solving.

IMPORTANT: You MUST use one of your available tools to perform reasoning. Do NOT try to reason on your own.

Your available tools:
1. run_beam_search - Use for structured, step-by-step problems
2. run_mcts - Use for complex, creative, or open-ended problems

REQUIRED WORKFLOW:
1. Read the problem carefully
2. Determine which reasoning method is requested (beam_search or mcts)
3. CALL the appropriate tool (run_beam_search or run_mcts) with the problem
4. Wait for the tool result
5. Use the tool's output to formulate your final ReasoningResult

When the user says "using beam_search" -> you MUST call run_beam_search tool
When the user says "using mcts" -> you MUST call run_mcts tool

After receiving the tool results, synthesize them into your response:
- Use the reasoning path from the tool output
- Extract the confidence score
- Formulate a clear conclusion based on the best path found

NEVER skip calling the tool. The tools contain the actual reasoning algorithms.
""",
    )

    @agent.tool
    async def run_beam_search(
        ctx: RunContext[ReasoningDependencies],
        problem: str,
        beam_width: int | None = None,
        max_depth: int | None = None,
    ) -> str:
        """Run Beam Search reasoning on a problem.

        Args:
            ctx: The run context with dependencies.
            problem: The problem to reason about.
            beam_width: Number of parallel paths to explore.
            max_depth: Maximum reasoning depth.

        Returns:
            Formatted reasoning results.
        """
        mcp_ctx = ctx.deps.ctx  # Get MCP context for streaming

        if mcp_ctx:
            await mcp_ctx.info("🔍 Starting Beam Search reasoning...")

        reasoner: BeamSearchReasoner = BeamSearchReasoner(
            beam_width=beam_width or ctx.deps.beam_width,
            max_depth=max_depth or ctx.deps.max_depth,
            mcp_ctx=mcp_ctx,  # Pass context for streaming
        )

        result: BeamSearchResult = await reasoner.reason(problem)

        if mcp_ctx:
            await mcp_ctx.info(f"✅ Beam Search complete: {result.nodes_explored} nodes explored")

        output: str = f"## Beam Search Results\n\n"
        output += f"**Problem:** {result.problem}\n\n"
        output += f"**Best Reasoning Path:**\n"

        for i, thought in enumerate(result.best_path.thoughts, 1):
            output += f"{i}. {thought.content} (score: {thought.score:.2f})\n"

        output += f"\n**Confidence:** {result.confidence:.2%}\n"
        output += f"**Nodes Explored:** {result.nodes_explored}\n"

        if result.alternative_paths:
            output += f"\n**Alternative Paths:** {len(result.alternative_paths)} found\n"

        return output

    @agent.tool
    async def run_mcts(
        ctx: RunContext[ReasoningDependencies],
        problem: str,
        num_simulations: int | None = None,
        max_depth: int | None = None,
    ) -> str:
        """Run MCTS reasoning on a problem.

        Args:
            ctx: The run context with dependencies.
            problem: The problem to reason about.
            num_simulations: Number of MCTS simulations.
            max_depth: Maximum tree depth.

        Returns:
            Formatted reasoning results.
        """
        mcp_ctx = ctx.deps.ctx  # Get MCP context for streaming

        if mcp_ctx:
            await mcp_ctx.info("🎲 Starting MCTS reasoning...")

        reasoner: MCTSReasoner = MCTSReasoner(
            num_simulations=num_simulations or ctx.deps.mcts_simulations,
            max_depth=max_depth or ctx.deps.max_depth,
            mcp_ctx=mcp_ctx,  # Pass context for streaming
        )

        result: MCTSResult = await reasoner.reason(problem)

        if mcp_ctx:
            await mcp_ctx.info(f"✅ MCTS complete: {result.simulations_run} simulations, {result.nodes_explored} nodes")

        output: str = f"## MCTS Results\n\n"
        output += f"**Problem:** {result.problem}\n\n"
        output += f"**Best Reasoning Path:**\n"

        for i, thought in enumerate(result.best_path.thoughts, 1):
            if i > 1:  # Skip root node
                output += f"{i-1}. {thought.content}\n"

        output += f"\n**Confidence:** {result.confidence:.2%}\n"
        output += f"**Simulations:** {result.simulations_run}\n"
        output += f"**Nodes Explored:** {result.nodes_explored}\n"

        return output

    _reasoning_agent = agent
    return agent


async def run_reasoning(
    problem: str,
    method: ReasoningMethod = ReasoningMethod.BEAM_SEARCH,
    ctx: "Context | None" = None,
) -> ReasoningResult:
    """Run reasoning using the Reasoning Agent with LLM-driven tool calling.

    This function uses the Reasoning Agent which has access to beam_search and
    mcts tools. The LLM decides how to call the tools and synthesizes the results.

    Args:
        problem: The problem to reason about.
        method: The reasoning method to use.
        ctx: Optional MCP Context for real-time streaming.

    Returns:
        ReasoningResult with conclusions and confidence.
    """
    logger.info(f"Running reasoning with method={method.value} for: {problem[:100]}...")

    if ctx:
        await ctx.info(f"🧠 Initializing {method.value} reasoning agent...")

    deps: ReasoningDependencies = ReasoningDependencies(
        default_method=method,
        ctx=ctx,  # Pass context for streaming
    )

    # Create a prompt that explicitly tells the LLM which tool to use
    prompt: str = f"""Reason about the following problem using {method.value}.

IMPORTANT: You MUST call the {'run_beam_search' if method == ReasoningMethod.BEAM_SEARCH else 'run_mcts'} tool with this problem.

Problem: {problem}

Call the tool now and then provide your ReasoningResult based on the tool's output."""

    try:
        agent: Agent[ReasoningDependencies, ReasoningResult] = _get_reasoning_agent()
        result: AgentRunResult[ReasoningResult] = await agent.run(prompt, deps=deps)

        if ctx:
            await ctx.info(f"🎯 Reasoning complete with confidence: {result.output.confidence:.1%}")

        return result.output

    except Exception as e:
        logger.error(f"Reasoning agent failed: {e}", exc_info=True)
        if ctx:
            await ctx.error(f"❌ Reasoning failed: {str(e)}")
        # Return a minimal result on error
        return ReasoningResult(
            problem=problem,
            method=method,
            conclusion=f"Reasoning encountered an error: {str(e)}",
            reasoning_path=[],
            confidence=0.0,
            nodes_explored=0,
            session_id="error",
        )

