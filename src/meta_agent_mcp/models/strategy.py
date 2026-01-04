"""Pydantic models for strategy agent outputs."""

from pydantic import BaseModel, Field


class DecisionContext(BaseModel):
    """Context for a decision analysis."""

    situation: str = Field(description="Description of the current situation")
    objectives: list[str] = Field(description="Key objectives to achieve")
    constraints: list[str] = Field(default_factory=list, description="Known constraints")
    stakeholders: list[str] = Field(default_factory=list, description="Key stakeholders")
    timeline: str | None = Field(default=None, description="Decision timeline")


class Option(BaseModel):
    """A decision option with analysis."""

    name: str = Field(description="Option name or label")
    description: str = Field(description="Detailed description of the option")
    pros: list[str] = Field(description="Advantages of this option")
    cons: list[str] = Field(description="Disadvantages or risks")
    feasibility: float = Field(ge=0.0, le=1.0, description="Feasibility score")
    impact: float = Field(ge=0.0, le=1.0, description="Potential impact score")
    risk: float = Field(ge=0.0, le=1.0, description="Risk level (0=low, 1=high)")
    overall_score: float = Field(ge=0.0, le=1.0, description="Overall weighted score")


class OptionComparison(BaseModel):
    """Comparison of multiple options."""

    options: list[Option] = Field(description="All analyzed options")
    recommended_option: str = Field(description="Name of the recommended option")
    recommendation_rationale: str = Field(description="Why this option is recommended")
    trade_offs: list[str] = Field(description="Key trade-offs to consider")
    implementation_notes: list[str] = Field(
        default_factory=list, description="Notes for implementation"
    )


class StrategicRecommendation(BaseModel):
    """A strategic recommendation."""

    title: str = Field(description="Recommendation title")
    summary: str = Field(description="Executive summary")
    rationale: str = Field(description="Detailed rationale")
    action_items: list[str] = Field(description="Specific actions to take")
    success_criteria: list[str] = Field(description="How to measure success")
    risks: list[str] = Field(description="Potential risks to monitor")
    priority: str = Field(description="Priority level: high/medium/low")


class StrategyResult(BaseModel):
    """Complete strategy analysis result."""

    context: DecisionContext = Field(description="The analyzed context")
    analysis: str = Field(description="Strategic analysis narrative")
    options: list[Option] = Field(description="Options considered")
    recommendation: StrategicRecommendation = Field(
        description="Primary recommendation"
    )
    alternative_strategies: list[StrategicRecommendation] = Field(
        default_factory=list, description="Alternative approaches"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in recommendation")


class DecisionAnalysis(BaseModel):
    """Analysis of a decision or situation."""

    situation_summary: str = Field(description="Summary of the situation")
    key_factors: list[str] = Field(description="Key factors influencing the decision")
    opportunities: list[str] = Field(description="Identified opportunities")
    threats: list[str] = Field(description="Identified threats or challenges")
    information_gaps: list[str] = Field(
        default_factory=list, description="Areas needing more information"
    )
    recommended_approach: str = Field(description="Recommended strategic approach")

