"""Meta Orchestrator Agent implementation.

This module implements the Meta Agent orchestrator that coordinates specialist agents
(Research, Reasoning, Strategy) to handle complex multi-part queries.

Key features:
- Task decomposition: Breaks complex queries into agent-specific tasks
- Dependency resolution: Topological sorting for dependent tasks
- Parallel execution: Runs independent tasks concurrently
- Result synthesis: Combines agent outputs into coherent responses
- Error recovery: Graceful handling of partial failures
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic_ai import Agent

from meta_agent_mcp.agents.reasoning import run_reasoning
from meta_agent_mcp.agents.research import run_research
from meta_agent_mcp.agents.strategy import (
    analyze_decision,
)
from meta_agent_mcp.models.meta import (
    AgentResult,
    AgentTask,
    MetaAgentResult,
    TaskPlan,
)
from meta_agent_mcp.models.reasoning import ReasoningMethod, ReasoningResult
from meta_agent_mcp.models.research import ResearchResult
from meta_agent_mcp.models.strategy import DecisionAnalysis

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class MetaDependencies:
    """Dependencies for the Meta Agent."""

    max_research_sources: int = 5
    reasoning_method: ReasoningMethod = ReasoningMethod.BEAM_SEARCH
    include_follow_ups: bool = True
    max_retries: int = 2
    # Collected sources from research tasks
    sources_collected: list[str] = field(default_factory=list)


def _topological_sort(tasks: list[AgentTask]) -> list[list[int]]:
    """Sort tasks into execution levels based on dependencies.

    Uses Kahn's algorithm to produce a topological ordering grouped into
    parallel execution levels.

    Args:
        tasks: List of tasks with depends_on fields.

    Returns:
        List of levels, where each level is a list of task indices
        that can be executed in parallel.

    Raises:
        ValueError: If there's a circular dependency.
    """
    n = len(tasks)
    if n == 0:
        return []

    # Build adjacency list and in-degree count
    in_degree: list[int] = [0] * n
    dependents: dict[int, list[int]] = defaultdict(list)

    for i, task in enumerate(tasks):
        for dep_idx in task.depends_on:
            if 0 <= dep_idx < n:
                dependents[dep_idx].append(i)
                in_degree[i] += 1

    # Initialize queue with tasks that have no dependencies
    queue: deque[int] = deque()
    for i in range(n):
        if in_degree[i] == 0:
            queue.append(i)

    levels: list[list[int]] = []
    processed = 0

    while queue:
        # All tasks in current queue can run in parallel
        current_level: list[int] = list(queue)
        levels.append(current_level)
        queue.clear()

        for task_idx in current_level:
            processed += 1
            for dependent_idx in dependents[task_idx]:
                in_degree[dependent_idx] -= 1
                if in_degree[dependent_idx] == 0:
                    queue.append(dependent_idx)

    if processed != n:
        raise ValueError("Circular dependency detected in task plan")

    return levels


@lru_cache(maxsize=1)
def _get_task_planner() -> Agent[None, TaskPlan]:
    """Get or create the task planner agent (lazy initialization).

    Returns:
        Agent configured for task planning.
    """
    from meta_agent_mcp.models.base import get_model

    return Agent(
        model=get_model(),
        output_type=TaskPlan,
        retries=3,  # Allow more retries for output validation
        output_retries=3,
        system_prompt="""\
You are a task planner that breaks down complex queries into specialist agent tasks.

Available agents:
- research: Web crawling and information gathering
- reasoning: Structured reasoning with Beam Search or MCTS
- strategy: Decision analysis and strategic recommendations

Guidelines:
- Analyze the query to determine what type of task it is
- Break complex queries into sequential tasks for different agents
- Set appropriate priorities (1=highest, 5=lowest)
- Mark dependencies between tasks

Task types:
- RESEARCH: Information gathering queries
- REASONING: Problem-solving or analysis queries
- STRATEGY: Decision-making or planning queries
- COMBINED: Queries requiring multiple agent types
""",
    )


@lru_cache(maxsize=1)
def _get_synthesizer() -> Agent[None, MetaAgentResult]:
    """Get or create the response synthesizer agent (lazy initialization).

    Returns:
        Agent configured for response synthesis.
    """
    from meta_agent_mcp.models.base import get_model

    return Agent(
        model=get_model(),
        output_type=MetaAgentResult,
        retries=3,  # Allow more retries for output validation
        output_retries=3,
        system_prompt="""\
You are a response synthesizer that combines results from specialist agents.

Your job:
1. Synthesize all agent outputs into a coherent response
2. Provide an executive summary
3. Give a detailed, well-structured response
4. Suggest relevant follow-up questions
5. Rate overall confidence based on agent results

Be clear, comprehensive, and actionable in your synthesis.
""",
    )


async def execute_task(
    task_type: str,
    task: str,
    deps: MetaDependencies,
    retry_count: int = 0,
) -> AgentResult:
    """Execute a single task using the appropriate agent with retry support.

    Args:
        task_type: The type of agent to use (research, reasoning, strategy).
        task: The task description.
        deps: The meta agent dependencies.
        retry_count: Current retry attempt (internal use).

    Returns:
        AgentResult with the task output.
    """
    try:
        if task_type == "research":
            result: ResearchResult = await run_research(task)
            # Collect sources for later aggregation
            if result.sources:
                deps.sources_collected.extend(result.sources)
            return AgentResult(
                agent="research",
                task=task,
                output=result.summary,
                success=True,
                confidence=result.confidence,
            )

        elif task_type == "reasoning":
            reasoning_result: ReasoningResult = await run_reasoning(
                task, deps.reasoning_method
            )
            return AgentResult(
                agent="reasoning",
                task=task,
                output=reasoning_result.conclusion,
                success=True,
                confidence=reasoning_result.confidence,
            )

        elif task_type == "strategy":
            strategy_result: DecisionAnalysis = await analyze_decision(task)
            return AgentResult(
                agent="strategy",
                task=task,
                output=strategy_result.recommended_approach,
                success=True,
                confidence=0.85,
            )

        else:
            logger.warning(f"Unknown agent type requested: {task_type}")
            return AgentResult(
                agent=task_type,
                task=task,
                output=f"Unknown agent type: {task_type}",
                success=False,
                confidence=0.0,
            )

    except Exception as e:
        logger.error(f"Error executing {task_type} task: {e}")

        # Retry logic for transient failures
        if retry_count < deps.max_retries:
            logger.info(f"Retrying task (attempt {retry_count + 2}/{deps.max_retries + 1})")
            await asyncio.sleep(1.0 * (retry_count + 1))  # Exponential backoff
            return await execute_task(task_type, task, deps, retry_count + 1)

        return AgentResult(
            agent=task_type,
            task=task,
            output=f"Error after {retry_count + 1} attempts: {str(e)}",
            success=False,
            confidence=0.0,
        )


async def _execute_task_batch(
    tasks: list[AgentTask],
    indices: list[int],
    deps: MetaDependencies,
) -> list[tuple[int, AgentResult]]:
    """Execute a batch of tasks in parallel.

    Args:
        tasks: The full list of tasks.
        indices: Indices of tasks to execute in this batch.
        deps: The meta agent dependencies.

    Returns:
        List of (index, result) tuples.
    """
    async def run_with_index(idx: int) -> tuple[int, AgentResult]:
        task = tasks[idx]
        result = await execute_task(task.agent, task.task, deps)
        return (idx, result)

    # Run all tasks in this batch concurrently
    results = await asyncio.gather(
        *(run_with_index(idx) for idx in indices),
        return_exceptions=True,
    )

    # Handle any exceptions that occurred
    processed_results: list[tuple[int, AgentResult]] = []
    for i, result in enumerate(results):
        idx = indices[i]
        if isinstance(result, Exception):
            logger.error(f"Task {idx} failed with exception: {result}")
            processed_results.append((
                idx,
                AgentResult(
                    agent=tasks[idx].agent,
                    task=tasks[idx].task,
                    output=f"Unexpected error: {str(result)}",
                    success=False,
                    confidence=0.0,
                ),
            ))
        else:
            processed_results.append(result)

    return processed_results


async def run_meta_agent(
    query: str,
    reasoning_method: ReasoningMethod = ReasoningMethod.BEAM_SEARCH,
    timeout_seconds: float = 120.0,
) -> MetaAgentResult:
    """Run the meta agent to handle a complex query.

    This function orchestrates the full meta agent workflow:
    1. Task Planning: Decomposes the query into agent-specific tasks
    2. Dependency Resolution: Sorts tasks topologically for correct execution order
    3. Parallel Execution: Runs independent tasks concurrently
    4. Result Synthesis: Combines all agent outputs into a coherent response

    Args:
        query: The user's query or request.
        reasoning_method: Method for reasoning tasks (beam_search or mcts).
        timeout_seconds: Maximum time for the entire operation (default 120s).

    Returns:
        MetaAgentResult with synthesized response from all agents.
    """
    deps: MetaDependencies = MetaDependencies(
        reasoning_method=reasoning_method,
        sources_collected=[],
    )

    logger.info(f"Meta agent starting for query: {query[:100]}...")

    # Step 1: Plan the tasks with timeout
    logger.debug("Step 1: Planning tasks...")
    task_planner: Agent[None, TaskPlan] = _get_task_planner()

    try:
        async with asyncio.timeout(timeout_seconds / 2):  # Half timeout for planning
            plan_result: AgentRunResult[TaskPlan] = await task_planner.run(
                f"Plan tasks for: {query}"
            )
    except asyncio.TimeoutError:
        logger.error(f"Task planning timed out after {timeout_seconds / 2}s")
        raise TimeoutError(f"Task planning timed out after {timeout_seconds / 2} seconds")

    plan: TaskPlan = plan_result.output

    logger.info(
        f"Task plan created: {len(plan.tasks)} tasks, type={plan.task_type.value}"
    )

    # Step 2: Resolve dependencies and get execution levels
    logger.debug("Step 2: Resolving task dependencies...")
    try:
        execution_levels: list[list[int]] = _topological_sort(plan.tasks)
    except ValueError as e:
        logger.error(f"Dependency resolution failed: {e}")
        # Fall back to sequential execution
        execution_levels = [[i] for i in range(len(plan.tasks))]

    # Step 3: Execute tasks level by level (parallel within each level)
    logger.debug("Step 3: Executing tasks...")
    all_results: dict[int, AgentResult] = {}

    for level_idx, task_indices in enumerate(execution_levels):
        logger.debug(
            f"Executing level {level_idx + 1}/{len(execution_levels)}: "
            f"{len(task_indices)} tasks in parallel"
        )

        level_results = await _execute_task_batch(plan.tasks, task_indices, deps)

        for idx, result in level_results:
            all_results[idx] = result

        # Yield control between levels
        await asyncio.sleep(0)

    # Convert to ordered list
    agent_results: list[AgentResult] = [
        all_results[i] for i in range(len(plan.tasks)) if i in all_results
    ]

    # Count successes/failures
    successful = sum(1 for r in agent_results if r.success)
    failed = len(agent_results) - successful
    logger.info(f"Task execution complete: {successful} succeeded, {failed} failed")

    # Step 4: Synthesize results with timeout
    logger.debug("Step 4: Synthesizing results...")
    synth_prompt: str = _build_synthesis_prompt(query, plan, agent_results, deps)

    synthesizer: Agent[None, MetaAgentResult] = _get_synthesizer()

    try:
        async with asyncio.timeout(timeout_seconds / 2):  # Half timeout for synthesis
            synth_result: AgentRunResult[MetaAgentResult] = await synthesizer.run(synth_prompt)
    except asyncio.TimeoutError:
        logger.error(f"Result synthesis timed out after {timeout_seconds / 2}s")
        raise TimeoutError(f"Result synthesis timed out after {timeout_seconds / 2} seconds")

    # Enrich result with collected sources
    final_result = synth_result.output
    if deps.sources_collected:
        # Deduplicate sources
        unique_sources = list(dict.fromkeys(deps.sources_collected))
        final_result = MetaAgentResult(
            query=final_result.query or query,
            task_type=final_result.task_type,
            summary=final_result.summary,
            detailed_response=final_result.detailed_response,
            agent_results=agent_results,
            sources_used=unique_sources,
            confidence=final_result.confidence,
            follow_up_suggestions=final_result.follow_up_suggestions,
        )

    logger.info("Meta agent completed successfully")
    return final_result


def _build_synthesis_prompt(
    query: str,
    plan: TaskPlan,
    results: list[AgentResult],
    deps: MetaDependencies,
) -> str:
    """Build the prompt for result synthesis.

    Args:
        query: Original user query.
        plan: The task plan that was executed.
        results: Results from all agent tasks.
        deps: Dependencies with collected sources.

    Returns:
        Formatted prompt for the synthesizer.
    """
    lines: list[str] = [
        f"Original query: {query}",
        f"Task type: {plan.task_type.value}",
        f"Planning rationale: {plan.rationale}",
        "",
        "Agent Results:",
    ]

    for i, r in enumerate(results):
        status = "✓" if r.success else "✗"
        lines.append(
            f"{i + 1}. [{status}] {r.agent.upper()}: {r.task}"
        )
        lines.append(f"   Output: {r.output}")
        lines.append(f"   Confidence: {r.confidence:.2f}")
        lines.append("")

    if deps.sources_collected:
        lines.append("Sources consulted:")
        for src in deps.sources_collected[:10]:  # Limit to top 10
            lines.append(f"  - {src}")

    return "\n".join(lines)
