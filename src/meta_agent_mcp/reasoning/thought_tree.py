"""Thought tree data structures for reasoning."""

from __future__ import annotations

import logging
from typing import Final
from uuid import uuid4

from meta_agent_mcp.models.reasoning import (
    ReasoningMethod,
    ReasoningSession,
    ThoughtNode,
    ThoughtPath,
)

logger: logging.Logger = logging.getLogger(__name__)


class ThoughtTree:
    """Manages a tree of thoughts for reasoning."""

    def __init__(self, problem: str, method: ReasoningMethod) -> None:
        """Initialize a thought tree.

        Args:
            problem: The problem being reasoned about.
            method: The reasoning method being used.
        """
        self.session_id: str = str(uuid4())
        self.problem: str = problem
        self.method: ReasoningMethod = method
        self.nodes: dict[str, ThoughtNode] = {}
        self.root_id: str | None = None

    def add_thought(
        self,
        content: str,
        parent_id: str | None = None,
        score: float = 0.0,
    ) -> ThoughtNode:
        """Add a thought to the tree.

        Args:
            content: The thought content.
            parent_id: ID of the parent thought (None for root).
            score: Initial score for the thought.

        Returns:
            The created ThoughtNode.
        """
        depth: int = 0
        if parent_id and parent_id in self.nodes:
            depth = self.nodes[parent_id].depth + 1

        node: ThoughtNode = ThoughtNode(
            content=content,
            parent_id=parent_id,
            depth=depth,
            score=score,
        )

        self.nodes[node.id] = node

        if parent_id is None:
            self.root_id = node.id
        elif parent_id in self.nodes:
            self.nodes[parent_id].children_ids.append(node.id)

        return node

    def get_node(self, node_id: str) -> ThoughtNode | None:
        """Get a node by ID.

        Args:
            node_id: The ID of the node to retrieve.

        Returns:
            The ThoughtNode if found, None otherwise.
        """
        return self.nodes.get(node_id)

    def get_children(self, node_id: str) -> list[ThoughtNode]:
        """Get all children of a node.

        Args:
            node_id: The ID of the parent node.

        Returns:
            List of child ThoughtNodes.
        """
        node: ThoughtNode | None = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[cid] for cid in node.children_ids if cid in self.nodes]

    def get_path_to_node(self, node_id: str) -> ThoughtPath:
        """Get the path from root to a specific node.

        Args:
            node_id: The ID of the target node.

        Returns:
            ThoughtPath containing all nodes from root to target.
        """
        path: list[ThoughtNode] = []
        current_id: str | None = node_id

        while current_id is not None:
            node: ThoughtNode | None = self.nodes.get(current_id)
            if node is None:
                break
            path.insert(0, node)
            current_id = node.parent_id

        total_score: float = sum(n.score for n in path)
        avg_score: float = total_score / len(path) if path else 0.0

        return ThoughtPath(
            thoughts=path,
            total_score=total_score,
            average_score=avg_score,
        )

    def get_leaf_nodes(self) -> list[ThoughtNode]:
        """Get all leaf nodes (nodes with no children).

        Returns:
            List of leaf ThoughtNodes.
        """
        return [n for n in self.nodes.values() if not n.children_ids]

    def get_best_leaf(self) -> ThoughtNode | None:
        """Get the leaf node with the highest score.

        Returns:
            The best scoring leaf node, or None if tree is empty.
        """
        leaves: list[ThoughtNode] = self.get_leaf_nodes()
        if not leaves:
            return None
        return max(leaves, key=lambda n: n.score)

    def get_best_path(self) -> ThoughtPath | None:
        """Get the best path from root to a leaf.

        Returns:
            The best ThoughtPath, or None if tree is empty.
        """
        best_leaf: ThoughtNode | None = self.get_best_leaf()
        if not best_leaf:
            return None
        return self.get_path_to_node(best_leaf.id)

    def get_max_depth(self) -> int:
        """Get the maximum depth in the tree.

        Returns:
            The maximum depth, or 0 if tree is empty.
        """
        if not self.nodes:
            return 0
        return max(n.depth for n in self.nodes.values())

    def to_session(self) -> ReasoningSession:
        """Convert to a ReasoningSession for serialization.

        Returns:
            ReasoningSession containing all tree data.
        """
        return ReasoningSession(
            session_id=self.session_id,
            problem=self.problem,
            method=self.method,
            root_id=self.root_id,
            all_thoughts=self.nodes,
            best_path=self.get_best_path(),
            nodes_explored=len(self.nodes),
            max_depth_reached=self.get_max_depth(),
        )


# Global session storage for visualization
_sessions: dict[str, ThoughtTree] = {}


def get_session(session_id: str) -> ThoughtTree | None:
    """Get a stored reasoning session.

    Args:
        session_id: The ID of the session to retrieve.

    Returns:
        The ThoughtTree if found, None otherwise.
    """
    return _sessions.get(session_id)


def store_session(tree: ThoughtTree) -> None:
    """Store a reasoning session for later retrieval.

    Args:
        tree: The ThoughtTree to store.
    """
    _sessions[tree.session_id] = tree

