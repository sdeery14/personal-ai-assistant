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
    # Security-specific fields (optional)
    expected_behavior: Optional[str] = Field(
        default=None,
        pattern=r"^(block|allow)$",
        description="Expected guardrail behavior: 'block' (should be blocked) or 'allow' (should pass)",
    )
    severity: Optional[str] = Field(
        default=None,
        pattern=r"^(critical|high|medium|low)$",
        description="Security severity level for adversarial cases",
    )
    attack_type: Optional[str] = Field(
        default=None,
        description="Type of attack (e.g., 'prompt_injection', 'disallowed_content')",
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
    # Security-specific metrics (optional)
    block_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="(correctly blocked adversarial) / (total adversarial cases)",
    )
    false_positive_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="(incorrectly blocked benign) / (total benign cases)",
    )
    top10_critical_miss: Optional[bool] = Field(
        default=None,
        description="True if any top 10 highest-severity cases failed to block",
    )
    security_gate_passed: Optional[bool] = Field(
        default=None,
        description="True if all security regression gates passed",
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


# Memory-specific models for Feature 004 evaluation


class MemorySetupItem(BaseModel):
    """A memory item to seed for a test case."""

    content: str = Field(..., min_length=1, description="Memory content text")
    type: str = Field(
        ...,
        pattern=r"^(fact|preference|decision|note)$",
        description="Memory type",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Override user_id for cross-user security tests",
    )


class MemoryTestCase(BaseModel):
    """A test case for memory retrieval evaluation."""

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9-]+$",
        description="Unique case identifier",
    )
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query to test retrieval",
    )
    user_id: str = Field(
        ...,
        description="User ID for the query (for user scoping)",
    )
    setup_memories: list[MemorySetupItem] = Field(
        default_factory=list,
        description="Memories to seed for this test case",
    )
    other_user_memories: Optional[list[MemorySetupItem]] = Field(
        default=None,
        description="Memories for other users (cross-user security tests)",
    )
    expected_retrievals: list[str] = Field(
        ...,
        description="Keywords/phrases expected in retrieved memories",
    )
    rubric: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Evaluation criteria for the judge",
    )


class MemoryGoldenDataset(BaseModel):
    """Complete memory evaluation dataset."""

    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Dataset schema version (semver)",
    )
    description: Optional[str] = Field(
        default=None,
        description="Dataset purpose description",
    )
    cases: list[MemoryTestCase] = Field(
        ...,
        min_length=5,
        max_length=50,
        description="Array of memory test cases",
    )

    @field_validator("cases")
    @classmethod
    def unique_ids(cls, v: list[MemoryTestCase]) -> list[MemoryTestCase]:
        """Validate that all case IDs are unique."""
        ids = [case.id for case in v]
        if len(ids) != len(set(ids)):
            duplicates = [id_ for id_ in ids if ids.count(id_) > 1]
            raise ValueError(f"Case IDs must be unique. Duplicates: {set(duplicates)}")
        return v


class MemoryEvalResult(BaseModel):
    """Result of evaluating one memory retrieval test case."""

    case_id: str = Field(..., description="Reference to MemoryTestCase.id")
    query: str = Field(..., description="Original query")
    retrieved_contents: list[str] = Field(..., description="Contents of retrieved memories")
    retrieved_count: int = Field(..., ge=0, description="Number of memories retrieved")
    expected_found: int = Field(..., ge=0, description="How many expected items were found")
    expected_total: int = Field(..., ge=0, description="Total expected items")
    recall: float = Field(..., ge=0.0, le=1.0, description="Recall score for this case")
    precision: float = Field(..., ge=0.0, le=1.0, description="Precision score for this case")
    latency_ms: int = Field(..., gt=0, description="Retrieval latency in milliseconds")
    token_count: int = Field(..., ge=0, description="Token count of retrieved memories")
    within_budget: bool = Field(..., description="Whether token budget was respected")
    cross_user_violation: bool = Field(
        default=False,
        description="True if memories from wrong user were returned",
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")


class MemoryMetrics(BaseModel):
    """Aggregate metrics for a memory evaluation run."""

    total_cases: int = Field(..., description="Total number of test cases")
    recall_at_5: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average recall@5 across all cases",
    )
    precision_at_5: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average precision@5 across all cases",
    )
    latency_p50: float = Field(..., ge=0.0, description="Median latency in ms")
    latency_p95: float = Field(..., ge=0.0, description="95th percentile latency in ms")
    token_compliance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of retrievals within token budget",
    )
    cross_user_violations: int = Field(
        ...,
        ge=0,
        description="Number of cases with cross-user data leakage",
    )
    error_cases: int = Field(..., ge=0, description="Cases that errored")
    overall_passed: bool = Field(
        ...,
        description="True if recall >= 0.80 AND precision >= 0.70 AND violations == 0",
    )


# Weather-specific models for Feature 005 evaluation


# Memory Write models for Feature 006 evaluation


class MemoryWriteExpectedAction(BaseModel):
    """An expected memory write or delete action."""

    action: str = Field(
        ...,
        pattern=r"^(save|delete|none)$",
        description="Expected action: save, delete, or none",
    )
    content_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords expected in the saved/deleted memory content",
    )
    memory_type: Optional[str] = Field(
        default=None,
        pattern=r"^(fact|preference|decision|note)$",
        description="Expected memory type for save actions",
    )


class MemoryWriteTestCase(BaseModel):
    """A test case for memory write evaluation."""

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9-]+$",
        description="Unique case identifier",
    )
    conversation: list[dict] = Field(
        ...,
        min_length=1,
        description="Conversation messages as list of {role, content} dicts",
    )
    expected_actions: list[MemoryWriteExpectedAction] = Field(
        ...,
        description="Expected memory write/delete actions",
    )
    rubric: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Evaluation criteria for judging extraction quality",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Categorization tags",
    )


class MemoryWriteGoldenDataset(BaseModel):
    """Complete memory write evaluation dataset."""

    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Dataset schema version (semver)",
    )
    description: Optional[str] = Field(
        default=None,
        description="Dataset purpose description",
    )
    cases: list[MemoryWriteTestCase] = Field(
        ...,
        min_length=5,
        max_length=30,
        description="Array of memory write test cases",
    )

    @field_validator("cases")
    @classmethod
    def unique_ids(cls, v: list[MemoryWriteTestCase]) -> list[MemoryWriteTestCase]:
        """Validate that all case IDs are unique."""
        ids = [case.id for case in v]
        if len(ids) != len(set(ids)):
            duplicates = [id_ for id_ in ids if ids.count(id_) > 1]
            raise ValueError(f"Case IDs must be unique. Duplicates: {set(duplicates)}")
        return v


class MemoryWriteEvalResult(BaseModel):
    """Result of evaluating one memory write test case."""

    case_id: str = Field(..., description="Reference to MemoryWriteTestCase.id")
    response: str = Field(default="", description="Assistant's response text")
    actual_writes: list[str] = Field(
        default_factory=list,
        description="Content of memories actually written",
    )
    actual_deletes: list[str] = Field(
        default_factory=list,
        description="Content of memories actually deleted",
    )
    precision: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of actual writes that were expected"
    )
    recall: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of expected writes that were made"
    )
    false_positive_count: int = Field(
        ..., ge=0, description="Number of unexpected writes"
    )
    judge_passed: Optional[bool] = Field(
        default=None, description="LLM judge pass/fail for response quality"
    )
    latency_ms: int = Field(..., ge=0, description="Processing latency")
    error: Optional[str] = Field(default=None, description="Error if evaluation failed")


class MemoryWriteMetrics(BaseModel):
    """Aggregate metrics for a memory write evaluation run."""

    total_cases: int = Field(..., description="Total number of test cases")
    extraction_precision: float = Field(
        ..., ge=0.0, le=1.0, description="Average precision across cases"
    )
    extraction_recall: float = Field(
        ..., ge=0.0, le=1.0, description="Average recall across cases"
    )
    false_positive_rate: float = Field(
        ..., ge=0.0, description="Average false positives per case"
    )
    judge_pass_rate: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="LLM judge pass rate"
    )
    error_cases: int = Field(..., ge=0, description="Cases that errored")
    overall_passed: bool = Field(
        ...,
        description="True if precision >= 0.70 AND recall >= 0.70 AND fp_rate <= 0.5",
    )


class WeatherTestCase(BaseModel):
    """A test case for weather tool evaluation."""

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9-]+$",
        description="Unique case identifier (e.g., 'weather-001')",
    )
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Weather query to send to assistant",
    )
    expected_behavior: str = Field(
        ...,
        pattern=r"^(success|error|clarification)$",
        description="Expected response type: success (weather data), error (user-friendly error), clarification (ask for more info)",
    )
    expected_fields: list[str] = Field(
        default_factory=list,
        description="Fields expected in successful response (e.g., 'temperature', 'conditions')",
    )
    expected_error_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords expected in error response (e.g., 'couldn't find', 'try again')",
    )
    rubric: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Evaluation criteria for judging response quality",
    )
    context: Optional[str] = Field(
        default=None,
        description="Optional notes about the test case",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Categorization tags (e.g., 'current', 'forecast', 'error-handling')",
    )


class WeatherGoldenDataset(BaseModel):
    """Complete weather evaluation dataset."""

    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Dataset schema version (semver)",
    )
    description: Optional[str] = Field(
        default=None,
        description="Dataset purpose description",
    )
    cases: list[WeatherTestCase] = Field(
        ...,
        min_length=5,
        max_length=30,
        description="Array of weather test cases (5-30)",
    )

    @field_validator("cases")
    @classmethod
    def unique_ids(cls, v: list[WeatherTestCase]) -> list[WeatherTestCase]:
        """Validate that all case IDs are unique."""
        ids = [case.id for case in v]
        if len(ids) != len(set(ids)):
            duplicates = [id_ for id_ in ids if ids.count(id_) > 1]
            raise ValueError(f"Case IDs must be unique. Duplicates: {set(duplicates)}")
        return v


class WeatherEvalResult(BaseModel):
    """Result of evaluating one weather test case."""

    case_id: str = Field(..., description="Reference to WeatherTestCase.id")
    query: str = Field(..., description="Original weather query")
    response: str = Field(..., description="Assistant's response")
    expected_behavior: str = Field(..., description="Expected behavior type")
    actual_behavior: str = Field(
        ...,
        pattern=r"^(success|error|clarification|unknown)$",
        description="Detected behavior type",
    )
    behavior_match: bool = Field(..., description="Whether actual matches expected")
    fields_found: list[str] = Field(
        default_factory=list,
        description="Expected fields that were found in response",
    )
    fields_missing: list[str] = Field(
        default_factory=list,
        description="Expected fields that were missing",
    )
    latency_ms: int = Field(..., gt=0, description="Response latency in milliseconds")
    cache_hit: bool = Field(default=False, description="Whether response came from cache")
    error: Optional[str] = Field(default=None, description="Error message if evaluation failed")


class WeatherMetrics(BaseModel):
    """Aggregate metrics for a weather evaluation run."""

    total_cases: int = Field(..., description="Total number of test cases")
    success_cases: int = Field(..., description="Cases where behavior matched expected")
    success_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of cases where behavior matched",
    )
    error_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of cases that returned errors",
    )
    cache_hit_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of responses from cache",
    )
    latency_p50: float = Field(..., ge=0.0, description="Median latency in ms")
    latency_p95: float = Field(..., ge=0.0, description="95th percentile latency in ms")
    valid_response_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of responses with all expected fields",
    )
    error_cases: int = Field(..., ge=0, description="Cases that errored during evaluation")
    overall_passed: bool = Field(
        ...,
        description="True if success_rate >= 0.95 AND latency_p95 < 3000ms",
    )


# Graph Extraction models for Feature 007 evaluation


class GraphExpectedEntity(BaseModel):
    """An expected entity to be extracted."""

    name: str = Field(..., description="Expected entity name")
    type: str = Field(
        ...,
        pattern=r"^(person|project|tool|concept|organization)$",
        description="Expected entity type",
    )
    keywords: list[str] = Field(
        ...,
        min_length=1,
        description="Keywords to match against extracted entity names",
    )


class GraphExpectedRelationship(BaseModel):
    """An expected relationship to be extracted."""

    type: str = Field(
        ...,
        pattern=r"^(USES|PREFERS|DECIDED|WORKS_ON|WORKS_WITH|KNOWS|DEPENDS_ON|PART_OF)$",
        description="Expected relationship type",
    )
    source_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords to match against source entity name",
    )
    target_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords to match against target entity name",
    )


class GraphExtractionTestCase(BaseModel):
    """A test case for graph extraction evaluation."""

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9-]+$",
        description="Unique case identifier",
    )
    user_prompt: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Message to send to the assistant",
    )
    expected_entities: list[GraphExpectedEntity] = Field(
        default_factory=list,
        description="Entities expected to be extracted",
    )
    expected_relationships: list[GraphExpectedRelationship] = Field(
        default_factory=list,
        description="Relationships expected to be extracted",
    )
    rubric: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Evaluation criteria for judging extraction quality",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Categorization tags",
    )


class GraphExtractionGoldenDataset(BaseModel):
    """Complete graph extraction evaluation dataset."""

    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Dataset schema version (semver)",
    )
    description: Optional[str] = Field(
        default=None,
        description="Dataset purpose description",
    )
    cases: list[GraphExtractionTestCase] = Field(
        ...,
        min_length=5,
        max_length=30,
        description="Array of graph extraction test cases",
    )

    @field_validator("cases")
    @classmethod
    def unique_ids(
        cls, v: list[GraphExtractionTestCase]
    ) -> list[GraphExtractionTestCase]:
        """Validate that all case IDs are unique."""
        ids = [case.id for case in v]
        if len(ids) != len(set(ids)):
            duplicates = [id_ for id_ in ids if ids.count(id_) > 1]
            raise ValueError(f"Case IDs must be unique. Duplicates: {set(duplicates)}")
        return v


class GraphExtractionEvalResult(BaseModel):
    """Result of evaluating one graph extraction test case."""

    case_id: str = Field(..., description="Reference to GraphExtractionTestCase.id")
    response: str = Field(default="", description="Assistant's response text")
    actual_entities: list[dict] = Field(
        default_factory=list,
        description="Entities extracted via save_entity tool calls",
    )
    actual_relationships: list[dict] = Field(
        default_factory=list,
        description="Relationships extracted via save_relationship tool calls",
    )
    entity_precision: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of extracted entities that were expected"
    )
    entity_recall: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of expected entities that were extracted"
    )
    relationship_precision: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of extracted relationships that were expected"
    )
    relationship_recall: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of expected relationships that were extracted"
    )
    entity_false_positives: int = Field(
        ..., ge=0, description="Number of unexpected entity extractions"
    )
    relationship_false_positives: int = Field(
        ..., ge=0, description="Number of unexpected relationship extractions"
    )
    latency_ms: int = Field(..., ge=0, description="Processing latency")
    error: Optional[str] = Field(default=None, description="Error if evaluation failed")


class GraphExtractionMetrics(BaseModel):
    """Aggregate metrics for a graph extraction evaluation run."""

    total_cases: int = Field(..., description="Total number of test cases")
    entity_precision: float = Field(
        ..., ge=0.0, le=1.0, description="Average entity precision across cases"
    )
    entity_recall: float = Field(
        ..., ge=0.0, le=1.0, description="Average entity recall across cases"
    )
    relationship_precision: float = Field(
        ..., ge=0.0, le=1.0, description="Average relationship precision across cases"
    )
    relationship_recall: float = Field(
        ..., ge=0.0, le=1.0, description="Average relationship recall across cases"
    )
    entity_false_positive_rate: float = Field(
        ..., ge=0.0, description="Average entity false positives per case"
    )
    relationship_false_positive_rate: float = Field(
        ..., ge=0.0, description="Average relationship false positives per case"
    )
    error_cases: int = Field(..., ge=0, description="Cases that errored")
    overall_passed: bool = Field(
        ...,
        description="True if entity_precision >= 0.60 AND entity_recall >= 0.60",
    )
