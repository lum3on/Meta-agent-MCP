"""Monte Carlo Tree Search (MCTS) reasoning implementation."""

from __future__ import annotations

import asyncio
import logging
import math
import random
import uuid
from typing import TYPE_CHECKING, Any

from pydantic_ai import Agent

from meta_agent_mcp.config import settings
from meta_agent_mcp.models.reasoning import (
    MCTSResult,
    ReasoningMethod,
    ThoughtEvaluation,
    ThoughtNode,
    ThoughtPath,
)
from meta_agent_mcp.reasoning.beam_search import (
    _extract_evaluation_from_text,
    _extract_json_array_from_text,
    get_thought_evaluator,
    get_thought_generator,
)
from meta_agent_mcp.reasoning.thought_tree import ThoughtTree, store_session

if TYPE_CHECKING:
    from fastmcp import Context

logger: logging.Logger = logging.getLogger(__name__)


class MCTSReasoner:
    """Monte Carlo Tree Search reasoning algorithm."""

    def __init__(
        self,
        num_simulations: int | None = None,
        exploration_weight: float = 1.414,
        max_depth: int | None = None,
        mcp_ctx: "Context | None" = None,
    ) -> None:
        """Initialize MCTS reasoner.

        Args:
            num_simulations: Number of simulations to run.
            exploration_weight: UCB1 exploration constant.
            max_depth: Maximum tree depth.
            mcp_ctx: Optional MCP Context for real-time streaming.
        """
        self.num_simulations: int = min(
            num_simulations or settings.default_mcts_simulations,
            150,
        )
        self.exploration_weight: float = exploration_weight
        self.max_depth: int = min(
            max_depth or settings.default_max_depth,
            50,
        )
        self.mcp_ctx: "Context | None" = mcp_ctx

    async def _log(self, message: str) -> None:
        """Log message to MCP context if available.

        Args:
            message: The message to log.
        """
        if self.mcp_ctx:
            await self.mcp_ctx.info(message)
        logger.info(message)

    async def reason(self, problem: str) -> MCTSResult:
        """Perform MCTS reasoning on a problem.

        Args:
            problem: The problem to reason about.

        Returns:
            MCTSResult with the best reasoning path.
        """
        await self._log(f"🎲 MCTS: simulations={self.num_simulations}, max_depth={self.max_depth}")

        tree: ThoughtTree = ThoughtTree(problem, ReasoningMethod.MCTS)

        # Create root node
        root: ThoughtNode = tree.add_thought(f"Root: {problem}")
        root.visits = 1

        # Run simulations
        log_interval = max(1, self.num_simulations // 10)  # Log ~10 times during execution
        for sim_idx in range(self.num_simulations):
            # Selection: traverse tree using UCB1
            selected_id: str = await self._select(tree, root.id)

            # Expansion: add new child nodes
            expanded_id: str = await self._expand(tree, selected_id, problem)

            # Simulation: rollout to estimate value
            value: float = await self._simulate(tree, expanded_id, problem)

            # Backpropagation: update scores along path
            self._backpropagate(tree, expanded_id, value)

            # Log progress at intervals
            if sim_idx % log_interval == 0 or sim_idx == self.num_simulations - 1:
                progress_pct = ((sim_idx + 1) / self.num_simulations) * 100
                await self._log(f"   🔄 Simulation {sim_idx + 1}/{self.num_simulations} ({progress_pct:.0f}%) - {len(tree.nodes)} nodes")

            # Yield control periodically to prevent blocking
            if sim_idx % 10 == 0:
                await asyncio.sleep(0)

        # Store session for visualization
        await self._log(f"📈 MCTS complete: {len(tree.nodes)} nodes explored")
        store_session(tree)

        # Get best path
        best_path: ThoughtPath = self._get_best_path_by_visits(tree)

        return MCTSResult(
            problem=problem,
            best_path=best_path,
            simulations_run=self.num_simulations,
            nodes_explored=len(tree.nodes),
            exploration_weight=self.exploration_weight,
            confidence=best_path.average_score if best_path.thoughts else 0.0,
        )

    async def _select(self, tree: ThoughtTree, node_id: str) -> str:
        """Select a node using UCB1.

        Args:
            tree: The thought tree.
            node_id: The starting node ID.

        Returns:
            The ID of the selected node.
        """
        current_id: str = node_id

        while True:
            node: ThoughtNode | None = tree.get_node(current_id)
            if not node:
                break

            children: list[ThoughtNode] = tree.get_children(current_id)

            # If no children or at max depth, return current
            if not children or node.depth >= self.max_depth:
                return current_id

            # Check for unexpanded children
            unexplored: list[ThoughtNode] = [c for c in children if c.visits == 0]
            if unexplored:
                return random.choice(unexplored).id

            # UCB1 selection
            total_visits: int = sum(c.visits for c in children)
            log_total: float = math.log(total_visits) if total_visits > 0 else 0.0

            def ucb1(child: ThoughtNode) -> float:
                if child.visits == 0:
                    return float("inf")
                exploit: float = child.score / child.visits
                explore: float = self.exploration_weight * math.sqrt(log_total / child.visits)
                return exploit + explore

            current_id = max(children, key=ucb1).id

        return current_id

    async def _expand(self, tree: ThoughtTree, node_id: str, problem: str) -> str:
        """Expand a node by adding children.

        Args:
            tree: The thought tree.
            node_id: The node to expand.
            problem: The problem being reasoned about.

        Returns:
            The ID of the first expanded child node.
        """
        node: ThoughtNode | None = tree.get_node(node_id)
        if not node or node.depth >= self.max_depth:
            return node_id

        # Skip if already has children
        if node.children_ids:
            return node_id

        # Generate children
        path: ThoughtPath = tree.get_path_to_node(node_id)
        path_texts: list[str] = [n.content for n in path.thoughts if n.id != tree.root_id]

        prompt: str = f"Problem: {problem}\n\n"
        if path_texts:
            prompt += f"Current reasoning: {' -> '.join(path_texts)}\n"
        prompt += "Generate next reasoning steps."

        try:
            result = await get_thought_generator().run(prompt)
            thoughts = result.output[:3]  # Limit branching factor
        except Exception as e:
            logger.warning(f"MCTS: Structured output failed for thought generation: {e}")
            # Try fallback: run with string output and parse
            try:
                fallback_agent = Agent(
                    model=get_thought_generator().model,
                    output_type=str,
                    system_prompt="Generate 3 reasoning thoughts as a numbered list.",
                )
                fallback_result = await fallback_agent.run(prompt)
                extracted = _extract_json_array_from_text(fallback_result.output)
                thoughts = extracted[:3] if extracted else ["Continue reasoning from a new angle."]
                logger.info(f"MCTS: Fallback parsing succeeded: {len(thoughts)} thoughts")
            except Exception as fallback_e:
                logger.warning(f"MCTS: Fallback also failed: {fallback_e}")
                thoughts = ["Continue reasoning from a new angle."]

        for thought in thoughts:
            tree.add_thought(thought, parent_id=node_id)

        children: list[ThoughtNode] = tree.get_children(node_id)
        return children[0].id if children else node_id

    async def _simulate(self, tree: ThoughtTree, node_id: str, problem: str) -> float:
        """Simulate/rollout to estimate value.

        Args:
            tree: The thought tree.
            node_id: The node to simulate from.
            problem: The problem being reasoned about.

        Returns:
            The estimated value of the node.
        """
        node: ThoughtNode | None = tree.get_node(node_id)
        if not node:
            return 0.0

        path: ThoughtPath = tree.get_path_to_node(node_id)
        path_texts: list[str] = [n.content for n in path.thoughts if n.id != tree.root_id]

        if not path_texts:
            return 0.5

        # Evaluate the path
        prompt: str = f"Problem: {problem}\nReasoning path: {' -> '.join(path_texts)}"

        try:
            result = await get_thought_evaluator().run(prompt)
            return result.output.composite_score
        except Exception as e:
            logger.warning(f"MCTS: Structured output failed for evaluation: {e}")
            # Try fallback: run with string output and parse
            try:
                fallback_agent = Agent(
                    model=get_thought_evaluator().model,
                    output_type=str,
                    system_prompt="Evaluate the thought and provide scores (0-1) for: logical_coherence, relevance, novelty, feasibility, composite_score.",
                )
                fallback_result = await fallback_agent.run(prompt)
                extracted = _extract_evaluation_from_text(fallback_result.output)
                if extracted:
                    logger.info("MCTS: Fallback parsing succeeded for evaluation")
                    return extracted.composite_score
            except Exception as fallback_e:
                logger.warning(f"MCTS: Fallback also failed: {fallback_e}")

            # Return a default score to continue
            return 0.5

    def _backpropagate(self, tree: ThoughtTree, node_id: str, value: float) -> None:
        """Backpropagate value up the tree.

        Args:
            tree: The thought tree.
            node_id: The starting node ID.
            value: The value to propagate.
        """
        current_id: str | None = node_id

        while current_id is not None:
            node: ThoughtNode | None = tree.get_node(current_id)
            if not node:
                break
            node.visits += 1
            node.score += value
            current_id = node.parent_id

    def _get_best_path_by_visits(self, tree: ThoughtTree) -> ThoughtPath:
        """Get the best path by following most visited children.

        Args:
            tree: The thought tree.

        Returns:
            The best ThoughtPath based on visit counts.
        """
        if not tree.root_id:
            return ThoughtPath(thoughts=[], total_score=0, average_score=0)

        path_ids: list[str] = []
        current_id: str | None = tree.root_id

        while current_id:
            path_ids.append(current_id)
            children: list[ThoughtNode] = tree.get_children(current_id)
            if not children:
                break
            current_id = max(children, key=lambda c: c.visits).id

        return tree.get_path_to_node(path_ids[-1]) if path_ids else ThoughtPath(
            thoughts=[], total_score=0, average_score=0
        )

