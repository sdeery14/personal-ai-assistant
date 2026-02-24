"""
Pydantic data models for the onboarding evaluation framework.

These models define the structure of:
- OnboardingTestCase: Individual persona-based test cases with multi-turn conversations
- OnboardingGoldenDataset: Complete dataset file structure
- OnboardingCaseResult: Per-case evaluation results including tool calls and transcript
- OnboardingMetrics: Aggregate metrics for an onboarding evaluation run
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class OnboardingExpectations(BaseModel):
    """Expected outcomes for an onboarding conversation."""

    memories_to_save: list[str] = Field(
        ...,
        min_length=1,
        description="Keywords expected in saved memories (e.g., 'name', 'role', 'schedule')",
    )
    entities_to_create: list[str] = Field(
        default_factory=list,
        description="Entity names expected to be created (e.g., 'PayFlow')",
    )
    topics_to_explore: list[str] = Field(
        default_factory=list,
        description="Topics the agent should explore (e.g., 'daily routine', 'goals')",
    )


class OnboardingTestCase(BaseModel):
    """A single onboarding evaluation test case with a persona and scripted user turns."""

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9-]+$",
        description="Unique case identifier (e.g., 'onboard-busy-engineer')",
    )
    persona: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Description of the user persona",
    )
    user_turns: list[str] = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Pre-scripted user messages for the onboarding conversation",
    )
    expectations: OnboardingExpectations = Field(
        ...,
        description="Expected outcomes for tool calls and conversation topics",
    )
    rubric: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Evaluation criteria for the conversation quality judge",
    )


class OnboardingGoldenDataset(BaseModel):
    """Complete onboarding evaluation dataset."""

    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Dataset schema version (semver)",
    )
    description: Optional[str] = Field(
        default=None,
        description="Dataset purpose description",
    )
    cases: list[OnboardingTestCase] = Field(
        ...,
        min_length=5,
        max_length=20,
        description="Array of onboarding test cases (5-20)",
    )

    @field_validator("cases")
    @classmethod
    def unique_ids(cls, v: list[OnboardingTestCase]) -> list[OnboardingTestCase]:
        """Validate that all case IDs are unique."""
        ids = [case.id for case in v]
        if len(ids) != len(set(ids)):
            duplicates = [id_ for id_ in ids if ids.count(id_) > 1]
            raise ValueError(f"Case IDs must be unique. Duplicates: {set(duplicates)}")
        return v


class OnboardingCaseResult(BaseModel):
    """Result of evaluating one onboarding conversation."""

    case_id: str = Field(..., description="Reference to OnboardingTestCase.id")
    persona: str = Field(..., description="Persona description for context")
    turn_count: int = Field(..., ge=0, description="Number of turns in the conversation")
    conversation_transcript: str = Field(
        default="", description="Full conversation transcript"
    )
    tool_calls: list[dict] = Field(
        default_factory=list,
        description="All tool calls made during the conversation",
    )
    memory_writes: list[str] = Field(
        default_factory=list,
        description="Contents of save_memory calls",
    )
    entity_creates: list[str] = Field(
        default_factory=list,
        description="Names of save_entity calls",
    )
    memory_recall: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of expected memories saved"
    )
    entity_recall: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of expected entities created"
    )
    quality_passed: Optional[bool] = Field(
        default=None, description="LLM judge pass/fail for conversation quality"
    )
    quality_rating: Optional[str] = Field(
        default=None, description="LLM judge rating (excellent/good/adequate/poor)"
    )
    total_latency_ms: int = Field(..., ge=0, description="Total conversation latency")
    error: Optional[str] = Field(default=None, description="Error if evaluation failed")


class OnboardingMetrics(BaseModel):
    """Aggregate metrics for an onboarding evaluation run."""

    total_cases: int = Field(..., description="Total number of test cases")
    conversation_quality_pass_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of cases rated 'excellent' or 'good'",
    )
    memory_extraction_recall: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average memory recall across cases",
    )
    entity_extraction_recall: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average entity recall across cases",
    )
    error_cases: int = Field(..., ge=0, description="Cases that errored")
    overall_passed: bool = Field(
        ...,
        description=(
            "True if quality_pass_rate >= 0.80 AND "
            "memory_recall >= 0.60 AND entity_recall >= 0.50"
        ),
    )
