"""Reasoning MCP tools."""

from __future__ import annotations

import logging
from typing import Any

from meta_agent_mcp.config import settings
from meta_agent_mcp.mcp_instance import mcp
from meta_agent_mcp.models.reasoning import (
    BeamSearchResult,
    MCTSResult,
    ReasoningSession,
    ThoughtNode,
    ThoughtPath,
)
from meta_agent_mcp.reasoning import BeamSearchReasoner, MCTSReasoner, get_session
from meta_agent_mcp.reasoning.thought_tree import ThoughtTree

logger: logging.Logger = logging.getLogger(__name__)


@mcp.tool
async def beam_search_reason(
    problem: str,
    beam_width: int = 3,
    max_depth: int = 5,
) -> dict[str, Any]:
    """Solve a problem using Beam Search reasoning.

    Beam Search maintains multiple promising reasoning paths simultaneously,
    evaluating and selecting the best ones at each depth level.

    Best for:
    - Problems with multiple valid approaches
    - When you want to compare alternative solutions
    - Structured, step-by-step reasoning

    Args:
        problem: The problem or question to reason about
        beam_width: Number of parallel paths to maintain (1-10, default 3)
        max_depth: Maximum reasoning depth (1-20, default 5)

    Returns:
        dict containing:
        - problem: The input problem
        - best_path: Best reasoning path with thoughts and scores
        - alternative_paths: Other promising paths found
        - nodes_explored: Total reasoning steps explored
        - confidence: Confidence score (0-1)
    """
    effective_beam_width: int = max(1, min(beam_width, 10))
    effective_max_depth: int = max(1, min(max_depth, 20))

    reasoner: BeamSearchReasoner = BeamSearchReasoner(
        beam_width=effective_beam_width,
        max_depth=effective_max_depth,
    )
    result: BeamSearchResult = await reasoner.reason(problem)

    return {
        "problem": result.problem,
        "best_path": {
            "thoughts": [t.content for t in result.best_path.thoughts],
            "total_score": result.best_path.total_score,
            "average_score": result.best_path.average_score,
        },
        "alternative_paths": [
            {
                "thoughts": [t.content for t in path.thoughts],
                "average_score": path.average_score,
            }
            for path in result.alternative_paths[:3]
        ],
        "beam_width": result.beam_width,
        "max_depth": result.max_depth,
        "nodes_explored": result.nodes_explored,
        "confidence": result.confidence,
    }


@mcp.tool
async def mcts_reason(
    problem: str,
    num_simulations: int = 50,
    exploration_weight: float = 1.414,
    max_depth: int = 10,
) -> dict[str, Any]:
    """Solve a problem using Monte Carlo Tree Search (MCTS) reasoning.

    MCTS balances exploration of new ideas with exploitation of promising paths
    using statistical sampling. Good for complex problems with large solution spaces.

    Best for:
    - Complex problems with many possible approaches
    - When exhaustive search is infeasible
    - Problems requiring creative exploration

    Args:
        problem: The problem or question to reason about
        num_simulations: Number of MCTS simulations (10-150, default 50)
        exploration_weight: UCB1 exploration constant (default √2 ≈ 1.414)
        max_depth: Maximum tree depth (1-30, default 10)

    Returns:
        dict containing:
        - problem: The input problem
        - best_path: Best reasoning path found
        - simulations_run: Number of simulations performed
        - nodes_explored: Total nodes in the reasoning tree
        - confidence: Confidence score (0-1)
    """
    effective_num_simulations: int = max(10, min(num_simulations, 150))
    effective_max_depth: int = max(1, min(max_depth, 30))

    reasoner: MCTSReasoner = MCTSReasoner(
        num_simulations=effective_num_simulations,
        exploration_weight=exploration_weight,
        max_depth=effective_max_depth,
    )
    result: MCTSResult = await reasoner.reason(problem)

    return {
        "problem": result.problem,
        "best_path": {
            "thoughts": [t.content for t in result.best_path.thoughts],
            "total_score": result.best_path.total_score,
            "average_score": result.best_path.average_score,
        },
        "simulations_run": result.simulations_run,
        "exploration_weight": result.exploration_weight,
        "nodes_explored": result.nodes_explored,
        "confidence": result.confidence,
    }


@mcp.tool
async def get_reasoning_tree(session_id: str) -> dict[str, Any]:
    """Get the full reasoning tree for a completed reasoning session.

    Use this to visualize or analyze the reasoning process after calling
    beam_search_reason or mcts_reason.

    Args:
        session_id: Session ID from a previous reasoning call

    Returns:
        dict containing the full thought tree with all nodes and paths
    """
    session: ThoughtTree | None = get_session(session_id)

    if not session:
        return {"error": f"Session {session_id} not found"}

    tree_data: ReasoningSession = session.to_session()

    return {
        "session_id": tree_data.session_id,
        "problem": tree_data.problem,
        "method": tree_data.method.value,
        "nodes_explored": tree_data.nodes_explored,
        "max_depth_reached": tree_data.max_depth_reached,
        "nodes": {
            nid: {
                "content": n.content,
                "depth": n.depth,
                "score": n.score,
                "visits": n.visits,
                "parent_id": n.parent_id,
                "children_ids": n.children_ids,
            }
            for nid, n in tree_data.all_thoughts.items()
        },
        "best_path": {
            "thoughts": [t.content for t in tree_data.best_path.thoughts],
            "average_score": tree_data.best_path.average_score,
        } if tree_data.best_path else None,
    }

