"""Beam Search reasoning implementation."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from pydantic_ai import Agent

from meta_agent_mcp.config import settings
from meta_agent_mcp.models.reasoning import (
    BeamSearchResult,
    ReasoningMethod,
    ThoughtEvaluation,
    ThoughtNode,
    ThoughtPath,
)
from meta_agent_mcp.reasoning.thought_tree import ThoughtTree, store_session

if TYPE_CHECKING:
    from fastmcp import Context
    from pydantic_ai.models.openrouter import OpenRouterModel

logger: logging.Logger = logging.getLogger(__name__)


def _extract_json_array_from_text(text: str) -> list[str] | None:
    """Try to extract a JSON array from text that might contain other content.

    Args:
        text: The text that might contain a JSON array.

    Returns:
        A list of strings if extraction succeeds, None otherwise.
    """
    # Try to find JSON array in the text
    json_match = re.search(r'\[[\s\S]*?\]', text)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                return parsed
        except json.JSONDecodeError:
            pass

    # Fallback: extract numbered or bulleted items
    lines = text.strip().split('\n')
    thoughts = []
    for line in lines:
        # Match patterns like "1. ", "- ", "* ", "• "
        cleaned = re.sub(r'^[\d]+\.\s*|^[-*•]\s*', '', line.strip())
        if cleaned and len(cleaned) > 10:  # Skip very short lines
            thoughts.append(cleaned)

    return thoughts[:5] if thoughts else None


def _extract_evaluation_from_text(text: str) -> ThoughtEvaluation | None:
    """Try to extract evaluation scores from text.

    Args:
        text: The text that might contain evaluation scores.

    Returns:
        A ThoughtEvaluation if extraction succeeds, None otherwise.
    """
    # Try to find JSON object in the text
    json_match = re.search(r'\{[\s\S]*?\}', text)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            return ThoughtEvaluation(
                thought_id=parsed.get("thought_id", str(uuid.uuid4())[:8]),
                logical_coherence=float(parsed.get("logical_coherence", 0.5)),
                relevance=float(parsed.get("relevance", 0.5)),
                novelty=float(parsed.get("novelty", 0.5)),
                feasibility=float(parsed.get("feasibility", 0.5)),
                composite_score=float(parsed.get("composite_score", 0.5)),
                reasoning=parsed.get("reasoning", "Extracted from text response"),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    # Fallback: try to extract scores from text patterns
    scores: dict[str, float] = {}
    patterns = {
        "logical_coherence": r'logical[_\s]*coherence[:\s]*([0-9.]+)',
        "relevance": r'relevance[:\s]*([0-9.]+)',
        "novelty": r'novelty[:\s]*([0-9.]+)',
        "feasibility": r'feasibility[:\s]*([0-9.]+)',
        "composite_score": r'composite[_\s]*score[:\s]*([0-9.]+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                scores[key] = min(1.0, max(0.0, float(match.group(1))))
            except ValueError:
                pass

    if scores:
        return ThoughtEvaluation(
            thought_id=str(uuid.uuid4())[:8],
            logical_coherence=scores.get("logical_coherence", 0.5),
            relevance=scores.get("relevance", 0.5),
            novelty=scores.get("novelty", 0.5),
            feasibility=scores.get("feasibility", 0.5),
            composite_score=scores.get("composite_score", 0.5),
            reasoning="Extracted from text response",
        )

    return None


@lru_cache(maxsize=1)
def get_thought_generator() -> Agent[None, list[str]]:
    """Get or create the thought generator agent (lazy initialization).

    Returns:
        Agent configured to generate reasoning thoughts.
    """
    from meta_agent_mcp.models.base import get_reasoning_model

    return Agent(
        model=get_reasoning_model(),
        output_type=list[str],
        retries=3,  # Allow more retries for output validation
        system_prompt="""\
You are a reasoning assistant that generates next logical thoughts.
Given a problem and the current reasoning path, generate the next possible thoughts.
Each thought should be a distinct, logical step that advances the reasoning.

CRITICAL: You MUST return your response as a valid JSON array of strings.
Do NOT include any text before or after the JSON array.
Do NOT use markdown code blocks.

Example output format:
["First logical next step to consider", "Second alternative approach", "Third possible direction"]

Return 3-5 possible next thoughts as a JSON array of strings.
""",
    )


@lru_cache(maxsize=1)
def get_thought_evaluator() -> Agent[None, ThoughtEvaluation]:
    """Get or create the thought evaluator agent (lazy initialization).

    Returns:
        Agent configured to evaluate reasoning thoughts.
    """
    from meta_agent_mcp.models.base import get_reasoning_model

    return Agent(
        model=get_reasoning_model(),
        output_type=ThoughtEvaluation,
        retries=3,  # Allow more retries for output validation
        system_prompt="""\
You are a thought evaluator that scores reasoning steps.
Evaluate the given thought on these dimensions (0.0 to 1.0):
- logical_coherence: Does it logically follow from previous thoughts?
- relevance: Does it address the problem?
- novelty: Does it add new insight?
- feasibility: Is it actionable or verifiable?

Compute a composite score as weighted average and explain your reasoning.

CRITICAL: You MUST return your response as a valid JSON object.
Do NOT include any text before or after the JSON object.
Do NOT use markdown code blocks.

Example output format:
{"thought_id": "t1", "logical_coherence": 0.8, "relevance": 0.9, "novelty": 0.7, "feasibility": 0.85, "composite_score": 0.81, "reasoning": "This thought follows logically and addresses the core problem."}
""",
    )


class BeamSearchReasoner:
    """Beam search reasoning algorithm."""

    def __init__(
        self,
        beam_width: int | None = None,
        max_depth: int | None = None,
        mcp_ctx: "Context | None" = None,
    ) -> None:
        """Initialize beam search reasoner.

        Args:
            beam_width: Number of paths to track (1-10).
            max_depth: Maximum reasoning depth.
            mcp_ctx: Optional MCP Context for real-time streaming.
        """
        self.beam_width: int = min(
            beam_width or settings.default_beam_width,
            10,
        )
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

    async def reason(self, problem: str) -> BeamSearchResult:
        """Perform beam search reasoning on a problem.

        Args:
            problem: The problem to reason about.

        Returns:
            BeamSearchResult with the best reasoning path.
        """
        await self._log(f"📊 Beam Search: width={self.beam_width}, max_depth={self.max_depth}")

        tree: ThoughtTree = ThoughtTree(problem, ReasoningMethod.BEAM_SEARCH)

        # Generate initial thoughts
        await self._log("💭 Generating initial thoughts...")
        initial_thoughts: list[str] = await self._generate_thoughts(problem, [])
        await self._log(f"   Generated {len(initial_thoughts)} initial thoughts")

        # Create root nodes for each initial thought
        current_beam: list[str] = []
        for i, thought in enumerate(initial_thoughts[: self.beam_width], 1):
            node: ThoughtNode = tree.add_thought(thought)
            evaluation: ThoughtEvaluation = await self._evaluate_thought(problem, thought, [])
            node.score = evaluation.composite_score
            node.logical_coherence = evaluation.logical_coherence
            node.relevance = evaluation.relevance
            node.novelty = evaluation.novelty
            node.feasibility = evaluation.feasibility
            current_beam.append(node.id)
            await self._log(f"   🔸 Thought {i}: score={node.score:.2f}")

        # Beam search loop
        for depth in range(1, self.max_depth):
            if not current_beam:
                break

            await self._log(f"🔄 Depth {depth}/{self.max_depth}: exploring {len(current_beam)} paths...")

            candidates: list[tuple[str, float]] = []

            for node_id in current_beam:
                node = tree.get_node(node_id)
                if not node:
                    continue

                path: ThoughtPath = tree.get_path_to_node(node_id)
                path_texts: list[str] = [n.content for n in path.thoughts]

                # Generate next thoughts
                next_thoughts: list[str] = await self._generate_thoughts(problem, path_texts)

                for thought in next_thoughts:
                    child: ThoughtNode = tree.add_thought(thought, parent_id=node_id)
                    evaluation = await self._evaluate_thought(problem, thought, path_texts)
                    child.score = evaluation.composite_score
                    child.logical_coherence = evaluation.logical_coherence
                    child.relevance = evaluation.relevance
                    child.novelty = evaluation.novelty
                    child.feasibility = evaluation.feasibility

                    path_to_child: ThoughtPath = tree.get_path_to_node(child.id)
                    candidates.append((child.id, path_to_child.average_score))

                # Yield control to event loop to prevent blocking
                await asyncio.sleep(0)

            # Select top-k candidates for next beam
            candidates.sort(key=lambda x: x[1], reverse=True)
            current_beam = [c[0] for c in candidates[: self.beam_width]]

            if candidates:
                best_score = candidates[0][1]
                await self._log(f"   ✅ Selected {len(current_beam)} best paths (top score: {best_score:.2f})")

        # Store session for visualization
        await self._log(f"📈 Beam Search complete: {len(tree.nodes)} nodes explored")
        store_session(tree)

        # Get best path and alternatives
        best_path: ThoughtPath | None = tree.get_best_path()
        leaves: list[ThoughtNode] = tree.get_leaf_nodes()
        leaves.sort(key=lambda n: n.score, reverse=True)

        alternative_paths: list[ThoughtPath] = [
            tree.get_path_to_node(leaf.id)
            for leaf in leaves[1: self.beam_width]
            if leaf.id != (best_path.thoughts[-1].id if best_path and best_path.thoughts else None)
        ]

        return BeamSearchResult(
            problem=problem,
            best_path=best_path or ThoughtPath(thoughts=[], total_score=0, average_score=0),
            alternative_paths=[p for p in alternative_paths if p],
            beam_width=self.beam_width,
            max_depth=tree.get_max_depth(),
            nodes_explored=len(tree.nodes),
            confidence=best_path.average_score if best_path else 0.0,
        )

    async def _generate_thoughts(
        self,
        problem: str,
        current_path: list[str],
    ) -> list[str]:
        """Generate possible next thoughts.

        Args:
            problem: The problem being reasoned about.
            current_path: The current reasoning path.

        Returns:
            List of possible next thoughts.
        """
        prompt: str = f"Problem: {problem}\n\n"
        if current_path:
            prompt += "Current reasoning path:\n"
            for i, thought in enumerate(current_path, 1):
                prompt += f"{i}. {thought}\n"
            prompt += "\nGenerate the next possible reasoning steps."
        else:
            prompt += "Generate initial thoughts to start reasoning about this problem."

        try:
            result = await get_thought_generator().run(prompt)
            return result.output
        except Exception as e:
            logger.warning(f"Structured output failed for thought generation: {e}")
            # Try fallback: run with string output and parse
            try:
                fallback_agent = Agent(
                    model=get_thought_generator().model,
                    output_type=str,
                    system_prompt="Generate 3-5 reasoning thoughts as a numbered list.",
                )
                fallback_result = await fallback_agent.run(prompt)
                extracted = _extract_json_array_from_text(fallback_result.output)
                if extracted:
                    logger.info(f"Fallback parsing succeeded: {len(extracted)} thoughts")
                    return extracted
            except Exception as fallback_e:
                logger.warning(f"Fallback also failed: {fallback_e}")

            # Return a generic thought to continue reasoning
            return ["Continue analyzing the problem from a different angle."]

    async def _evaluate_thought(
        self,
        problem: str,
        thought: str,
        context: list[str],
    ) -> ThoughtEvaluation:
        """Evaluate a thought's quality.

        Args:
            problem: The problem being reasoned about.
            thought: The thought to evaluate.
            context: Previous thoughts in the reasoning path.

        Returns:
            ThoughtEvaluation with scores and reasoning.
        """
        prompt: str = f"Problem: {problem}\n\n"
        if context:
            prompt += "Previous thoughts:\n"
            for t in context:
                prompt += f"- {t}\n"
        prompt += f"\nThought to evaluate: {thought}"

        try:
            result = await get_thought_evaluator().run(prompt)
            return result.output
        except Exception as e:
            logger.warning(f"Structured output failed for thought evaluation: {e}")
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
                    logger.info("Fallback parsing succeeded for evaluation")
                    return extracted
            except Exception as fallback_e:
                logger.warning(f"Fallback also failed: {fallback_e}")

            # Return a default evaluation to continue reasoning
            return ThoughtEvaluation(
                thought_id=str(uuid.uuid4())[:8],
                logical_coherence=0.5,
                relevance=0.5,
                novelty=0.5,
                feasibility=0.5,
                composite_score=0.5,
                reasoning="Default evaluation due to parsing failure",
            )

