"""
Pydantic data models for the evaluation framework.

These models define the structure of:
- TestCase: Individual golden dataset cases
- GoldenDataset: Complete dataset file structure
- EvalResult: Per-case evaluation results
- EvalRunMetrics: Aggregate metrics for a run
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TestCase(BaseModel):
    """A single golden dataset case for evaluation."""

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9-]+$",
        description="Unique case identifier (e.g., 'case-001')",
    )
    user_prompt: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="The question/prompt to send to the assistant",
    )
    rubric: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Evaluation criteria for the judge",
    )
    context: Optional[str] = Field(
        default=None,
        description="Optional notes about the test case",
    )
    tags: Optional[list[str]] = Field(
        default=None,
        description="Optional categorization tags",
    )


class GoldenDataset(BaseModel):
    """The complete golden dataset file structure."""

    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Dataset schema version (semver)",
    )
    description: Optional[str] = Field(
        default=None,
        description="Dataset purpose description",
    )
    cases: list[TestCase] = Field(
        ...,
        min_length=5,
        max_length=20,
        description="Array of test cases (5-20)",
    )

    @field_validator("cases")
    @classmethod
    def unique_ids(cls, v: list[TestCase]) -> list[TestCase]:
        """Validate that all case IDs are unique."""
        ids = [case.id for case in v]
        if len(ids) != len(set(ids)):
            duplicates = [id_ for id_ in ids if ids.count(id_) > 1]
            raise ValueError(f"Case IDs must be unique. Duplicates: {set(duplicates)}")
        return v


class EvalResult(BaseModel):
    """The result of evaluating one test case."""

    case_id: str = Field(..., description="Reference to TestCase.id")
    user_prompt: str = Field(..., description="Original prompt (for logging)")
    assistant_response: str = Field(..., description="Complete assistant response")
    score: int = Field(
        ...,
        ge=1,
        le=5,
        description="Judge's quality score (1-5)",
    )
    passed: bool = Field(..., description="True if score >= 4")
    justification: str = Field(
        ...,
        description="Judge's reasoning (1-2 sentences)",
    )
    duration_ms: int = Field(
        ...,
        gt=0,
        description="Total time for assistant + judge (ms)",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if evaluation failed",
    )

    @field_validator("passed")
    @classmethod
    def passed_matches_score(cls, v: bool, info) -> bool:
        """Validate that passed matches score >= 4."""
        score = info.data.get("score")
        if score is not None:
            expected = score >= 4
            if v != expected:
                raise ValueError(
                    f"passed={v} does not match score={score} (expected passed={expected})"
                )
        return v


class EvalRunParameters(BaseModel):
    """Configuration parameters for an evaluation run."""

    assistant_model: str = Field(..., description="Model used for assistant")
    judge_model: str = Field(..., description="Model used for judge")
    temperature: float = Field(..., description="Temperature setting")
    max_tokens: int = Field(..., description="Max tokens for assistant response")
    dataset_version: str = Field(..., description="Version from GoldenDataset.version")
    pass_rate_threshold: float = Field(..., description="Minimum required pass rate")
    score_threshold: float = Field(..., description="Minimum required average score")


class EvalRunMetrics(BaseModel):
    """Aggregate metrics for an evaluation run."""

    total_cases: int = Field(..., description="Total number of cases in dataset")
    passed_cases: int = Field(..., description="Cases with score >= 4")
    failed_cases: int = Field(..., description="Cases with score < 4")
    error_cases: int = Field(..., description="Cases that errored during evaluation")
    pass_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="passed_cases / (total_cases - error_cases)",
    )
    average_score: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description="Mean score of non-error cases",
    )
    overall_passed: bool = Field(
        ...,
        description="True if pass_rate >= threshold AND avg_score >= threshold",
    )


class EvalRun(BaseModel):
    """Complete results for an evaluation run (logged to MLflow)."""

    run_id: str = Field(..., description="MLflow run ID (UUID)")
    timestamp: datetime = Field(..., description="When the run started (UTC)")
    parameters: EvalRunParameters = Field(..., description="Configuration for this run")
    metrics: EvalRunMetrics = Field(..., description="Aggregate results")
    results: list[EvalResult] = Field(..., description="Per-case results")
