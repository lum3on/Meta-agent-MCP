"""Pydantic models for meta agent outputs."""

from enum import Enum

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Types of tasks the meta agent can handle."""

    RESEARCH = "research"
    REASONING = "reasoning"
    STRATEGY = "strategy"
    COMBINED = "combined"


class AgentTask(BaseModel):
    """A task assigned to a specialist agent."""

    agent: str = Field(description="Which agent to use: research, reasoning, strategy")
    task: str = Field(description="The specific task for the agent")
    priority: int = Field(default=1, ge=1, le=5, description="Task priority 1-5")
    depends_on: list[int] = Field(
        default_factory=list, description="Indices of tasks this depends on"
    )


class TaskPlan(BaseModel):
    """Plan for executing a complex query."""

    original_query: str = Field(description="The original user query")
    task_type: TaskType = Field(description="Classified task type")
    tasks: list[AgentTask] = Field(description="Ordered list of tasks to execute")
    rationale: str = Field(description="Why this plan was chosen")


class AgentResult(BaseModel):
    """Result from a specialist agent."""

    agent: str = Field(description="Which agent produced this result")
    task: str = Field(description="The task that was executed")
    output: str = Field(description="The agent's output")
    success: bool = Field(default=True, description="Whether the task succeeded")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence level")


class MetaAgentResult(BaseModel):
    """Complete result from the meta agent orchestration."""

    query: str = Field(description="Original user query")
    task_type: TaskType = Field(description="Classified task type")
    summary: str = Field(description="Executive summary of the response")
    detailed_response: str = Field(description="Full detailed response")
    agent_results: list[AgentResult] = Field(
        description="Results from each specialist agent"
    )
    sources_used: list[str] = Field(
        default_factory=list, description="URLs or sources consulted"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence")
    follow_up_suggestions: list[str] = Field(
        default_factory=list, description="Suggested follow-up questions"
    )

