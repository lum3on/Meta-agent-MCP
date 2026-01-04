"""Pydantic models for reasoning agent outputs."""

from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ReasoningMethod(str, Enum):
    """Available reasoning methods."""

    BEAM_SEARCH = "beam_search"
    MCTS = "mcts"


class ThoughtNode(BaseModel):
    """A single thought in the reasoning tree."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = Field(description="The thought content")
    parent_id: str | None = Field(default=None, description="Parent thought ID")
    depth: int = Field(default=0, description="Depth in the thought tree")
    score: float = Field(default=0.0, description="Evaluation score for this thought")
    visits: int = Field(default=0, description="Number of times this node was visited (MCTS)")
    children_ids: list[str] = Field(default_factory=list, description="Child thought IDs")

    # Evaluation dimensions
    logical_coherence: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    feasibility: float = Field(default=0.0, ge=0.0, le=1.0)


class ThoughtPath(BaseModel):
    """A path through the thought tree."""

    thoughts: list[ThoughtNode] = Field(description="Ordered list of thoughts in the path")
    total_score: float = Field(description="Sum of thought scores")
    average_score: float = Field(description="Average score across thoughts")


class ReasoningSession(BaseModel):
    """A complete reasoning session."""

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    problem: str = Field(description="The problem being reasoned about")
    method: ReasoningMethod = Field(description="Reasoning method used")
    root_id: str | None = Field(default=None, description="Root thought node ID")
    all_thoughts: dict[str, ThoughtNode] = Field(
        default_factory=dict, description="All thoughts indexed by ID"
    )
    best_path: ThoughtPath | None = Field(default=None, description="Best reasoning path found")
    nodes_explored: int = Field(default=0, description="Total nodes explored")
    max_depth_reached: int = Field(default=0, description="Maximum depth reached")


class ThoughtEvaluation(BaseModel):
    """Evaluation of a single thought."""

    thought_id: str = Field(description="ID of the evaluated thought")
    logical_coherence: float = Field(ge=0.0, le=1.0, description="Logical consistency score")
    relevance: float = Field(ge=0.0, le=1.0, description="Relevance to the problem")
    novelty: float = Field(ge=0.0, le=1.0, description="New insight contribution")
    feasibility: float = Field(ge=0.0, le=1.0, description="Actionability/verifiability")
    composite_score: float = Field(ge=0.0, le=1.0, description="Weighted overall score")
    reasoning: str = Field(description="Explanation of the evaluation")


class BeamSearchResult(BaseModel):
    """Result from beam search reasoning."""

    problem: str = Field(description="The problem that was reasoned about")
    best_path: ThoughtPath = Field(description="Best reasoning path found")
    alternative_paths: list[ThoughtPath] = Field(
        default_factory=list, description="Other promising paths"
    )
    beam_width: int = Field(description="Beam width used")
    max_depth: int = Field(description="Maximum depth reached")
    nodes_explored: int = Field(description="Total nodes explored")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the solution")


class MCTSResult(BaseModel):
    """Result from MCTS reasoning."""

    problem: str = Field(description="The problem that was reasoned about")
    best_path: ThoughtPath = Field(description="Best reasoning path found")
    simulations_run: int = Field(description="Number of simulations performed")
    nodes_explored: int = Field(description="Total nodes in the tree")
    exploration_weight: float = Field(description="UCB1 exploration constant used")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the solution")


class ReasoningResult(BaseModel):
    """Unified result from any reasoning method."""

    problem: str = Field(description="The problem that was reasoned about")
    method: ReasoningMethod = Field(description="Reasoning method used")
    conclusion: str = Field(description="Final conclusion or answer")
    reasoning_path: list[str] = Field(description="Key reasoning steps taken")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the conclusion")
    nodes_explored: int = Field(description="Number of thought nodes explored")
    session_id: str = Field(description="Session ID for tree visualization")

