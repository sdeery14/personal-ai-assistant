"""
Pydantic data models for the Alfred evaluation suite (Tier 1 & Tier 2).

Defines models for 11 eval types:

Tier 1:
- Tone & Personality (B1)
- Returning User Greeting (B2)
- Orchestrator Routing (B3)
- Memory-Informed Responses (B4)
- Multi-Capability Conversations (B5)

Tier 2:
- Schedule Cron Accuracy (B6)
- Notification Judgment (B7)
- Knowledge Graph Connections (B8)
- Error Recovery (B9)
- Long Conversation Coherence (B10)
- Contradiction Handling (B11)

Each eval type has: TestCase, GoldenDataset, CaseResult, Metrics.
Shared seed data types are defined here for pre-seeding eval data.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================
# Shared Seed Data Types
# ============================================================


class SeedMemory(BaseModel):
    """A memory item to pre-seed before running an eval case."""

    content: str = Field(..., min_length=1, description="Memory content text")
    type: str = Field(
        default="fact",
        pattern=r"^(fact|preference|decision|note)$",
        description="Memory type",
    )
    confidence: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Confidence score"
    )


class SeedEntity(BaseModel):
    """An entity to pre-seed before running an eval case."""

    name: str = Field(..., min_length=1, description="Entity name")
    type: str = Field(
        default="concept",
        pattern=r"^(person|project|tool|concept|organization)$",
        description="Entity type",
    )
    description: str = Field(default="", description="Entity description")


class SeedRelationship(BaseModel):
    """A relationship between entities to pre-seed."""

    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    type: str = Field(..., description="Relationship type (e.g., 'works_on')")


# ============================================================
# B1: Tone & Personality
# ============================================================


class ToneTestCase(BaseModel):
    """A single tone/personality evaluation test case."""

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9-]+$",
        description="Unique case identifier",
    )
    user_prompt: str = Field(
        ..., min_length=1, max_length=2000, description="User message"
    )
    context: str = Field(
        default="",
        max_length=500,
        description="Situational context for the message",
    )
    rubric: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Evaluation criteria for the judge",
    )
    tags: list[str] = Field(default_factory=list, description="Categorization tags")


class ToneGoldenDataset(BaseModel):
    """Complete tone/personality evaluation dataset."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = None
    eval_type: str = Field(default="tone", pattern=r"^tone$")
    cases: list[ToneTestCase] = Field(..., min_length=4, max_length=20)

    @field_validator("cases")
    @classmethod
    def unique_ids(cls, v: list[ToneTestCase]) -> list[ToneTestCase]:
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate case IDs: {set(dupes)}")
        return v


class ToneCaseResult(BaseModel):
    """Result of evaluating one tone/personality case."""

    case_id: str
    response: str = ""
    quality_passed: Optional[bool] = None
    quality_rating: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None


class ToneMetrics(BaseModel):
    """Aggregate metrics for tone/personality evaluation."""

    total_cases: int
    quality_pass_rate: float = Field(..., ge=0.0, le=1.0)
    error_cases: int = 0
    overall_passed: bool


# ============================================================
# B2: Returning User Greeting
# ============================================================


class ReturningGreetingTestCase(BaseModel):
    """A returning user greeting evaluation test case."""

    id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    persona: str = Field(
        ..., min_length=1, max_length=500, description="User persona description"
    )
    seed_memories: list[SeedMemory] = Field(
        ..., min_length=1, description="Memories to pre-seed"
    )
    seed_entities: list[SeedEntity] = Field(
        default_factory=list, description="Entities to pre-seed"
    )
    rubric: str = Field(..., min_length=10, max_length=2000)
    expected_references: list[str] = Field(
        default_factory=list,
        description="Keywords the greeting should reference from seeded data",
    )
    tags: list[str] = Field(default_factory=list)


class ReturningGreetingGoldenDataset(BaseModel):
    """Complete returning user greeting evaluation dataset."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = None
    eval_type: str = Field(default="returning_greeting", pattern=r"^returning_greeting$")
    cases: list[ReturningGreetingTestCase] = Field(..., min_length=3, max_length=20)

    @field_validator("cases")
    @classmethod
    def unique_ids(
        cls, v: list[ReturningGreetingTestCase],
    ) -> list[ReturningGreetingTestCase]:
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate case IDs: {set(dupes)}")
        return v


class ReturningGreetingCaseResult(BaseModel):
    """Result of evaluating one returning user greeting case."""

    case_id: str
    persona: str = ""
    response: str = ""
    quality_passed: Optional[bool] = None
    quality_rating: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None


class ReturningGreetingMetrics(BaseModel):
    """Aggregate metrics for returning user greeting evaluation."""

    total_cases: int
    quality_pass_rate: float = Field(..., ge=0.0, le=1.0)
    error_cases: int = 0
    overall_passed: bool


# ============================================================
# B3: Orchestrator Routing
# ============================================================


class RoutingTestCase(BaseModel):
    """A routing evaluation test case."""

    id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    user_prompt: str = Field(..., min_length=1, max_length=2000)
    expected_delegations: list[str] = Field(
        ...,
        description=(
            "Expected tool calls (e.g., 'ask_weather_agent', 'ask_memory_agent'). "
            "Empty list means no delegation expected."
        ),
    )
    seed_memories: list[SeedMemory] = Field(
        default_factory=list, description="Memories to pre-seed (if needed)"
    )
    seed_entities: list[SeedEntity] = Field(
        default_factory=list, description="Entities to pre-seed (if needed)"
    )
    rubric: str = Field(..., min_length=10, max_length=2000)
    tags: list[str] = Field(default_factory=list)


class RoutingGoldenDataset(BaseModel):
    """Complete routing evaluation dataset."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = None
    eval_type: str = Field(default="routing", pattern=r"^routing$")
    cases: list[RoutingTestCase] = Field(..., min_length=4, max_length=20)

    @field_validator("cases")
    @classmethod
    def unique_ids(cls, v: list[RoutingTestCase]) -> list[RoutingTestCase]:
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate case IDs: {set(dupes)}")
        return v


class RoutingCaseResult(BaseModel):
    """Result of evaluating one routing case."""

    case_id: str
    response: str = ""
    actual_delegations: list[str] = Field(default_factory=list)
    routing_correct: Optional[bool] = None
    quality_passed: Optional[bool] = None
    quality_rating: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None


class RoutingMetrics(BaseModel):
    """Aggregate metrics for routing evaluation."""

    total_cases: int
    routing_accuracy: float = Field(..., ge=0.0, le=1.0)
    quality_pass_rate: float = Field(..., ge=0.0, le=1.0)
    error_cases: int = 0
    overall_passed: bool


# ============================================================
# B4: Memory-Informed Responses
# ============================================================


class MemoryInformedTestCase(BaseModel):
    """A memory-informed response evaluation test case."""

    id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    persona: str = Field(..., min_length=1, max_length=500)
    seed_memories: list[SeedMemory] = Field(
        ..., min_length=1, description="Memories to pre-seed"
    )
    seed_entities: list[SeedEntity] = Field(
        default_factory=list, description="Entities to pre-seed"
    )
    user_turns: list[str] = Field(
        ..., min_length=1, max_length=5, description="Multi-turn user messages"
    )
    rubric: str = Field(..., min_length=10, max_length=2000)
    expected_memory_usage: list[str] = Field(
        default_factory=list,
        description="Keywords from memories the agent should apply in its responses",
    )
    tags: list[str] = Field(default_factory=list)


class MemoryInformedGoldenDataset(BaseModel):
    """Complete memory-informed evaluation dataset."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = None
    eval_type: str = Field(default="memory_informed", pattern=r"^memory_informed$")
    cases: list[MemoryInformedTestCase] = Field(..., min_length=3, max_length=20)

    @field_validator("cases")
    @classmethod
    def unique_ids(
        cls, v: list[MemoryInformedTestCase],
    ) -> list[MemoryInformedTestCase]:
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate case IDs: {set(dupes)}")
        return v


class MemoryInformedCaseResult(BaseModel):
    """Result of evaluating one memory-informed case."""

    case_id: str
    persona: str = ""
    conversation_transcript: str = ""
    quality_passed: Optional[bool] = None
    quality_rating: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None


class MemoryInformedMetrics(BaseModel):
    """Aggregate metrics for memory-informed evaluation."""

    total_cases: int
    quality_pass_rate: float = Field(..., ge=0.0, le=1.0)
    error_cases: int = 0
    overall_passed: bool


# ============================================================
# B5: Multi-Capability Conversations
# ============================================================


class MultiCapTestCase(BaseModel):
    """A multi-capability conversation evaluation test case."""

    id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    persona: str = Field(..., min_length=1, max_length=500)
    scenario: str = Field(
        ..., min_length=1, max_length=500, description="Scenario description"
    )
    seed_memories: list[SeedMemory] = Field(
        default_factory=list, description="Memories to pre-seed"
    )
    seed_entities: list[SeedEntity] = Field(
        default_factory=list, description="Entities to pre-seed"
    )
    seed_relationships: list[SeedRelationship] = Field(
        default_factory=list, description="Relationships to pre-seed"
    )
    user_turns: list[str] = Field(
        ..., min_length=2, max_length=6, description="Multi-turn user messages"
    )
    expected_capabilities: list[str] = Field(
        ...,
        min_length=1,
        description="Capabilities expected to be used (e.g., 'memory', 'weather', 'knowledge')",
    )
    rubric: str = Field(..., min_length=10, max_length=2000)
    tags: list[str] = Field(default_factory=list)


class MultiCapGoldenDataset(BaseModel):
    """Complete multi-capability evaluation dataset."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = None
    eval_type: str = Field(default="multi_cap", pattern=r"^multi_cap$")
    cases: list[MultiCapTestCase] = Field(..., min_length=3, max_length=20)

    @field_validator("cases")
    @classmethod
    def unique_ids(cls, v: list[MultiCapTestCase]) -> list[MultiCapTestCase]:
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate case IDs: {set(dupes)}")
        return v


class MultiCapCaseResult(BaseModel):
    """Result of evaluating one multi-capability case."""

    case_id: str
    persona: str = ""
    scenario: str = ""
    conversation_transcript: str = ""
    tool_calls: list[dict] = Field(default_factory=list)
    quality_passed: Optional[bool] = None
    quality_rating: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None


class MultiCapMetrics(BaseModel):
    """Aggregate metrics for multi-capability evaluation."""

    total_cases: int
    quality_pass_rate: float = Field(..., ge=0.0, le=1.0)
    error_cases: int = 0
    overall_passed: bool


# ============================================================
# B6: Schedule Cron Accuracy
# ============================================================


class ScheduleCronTestCase(BaseModel):
    """A schedule cron accuracy evaluation test case."""

    id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    user_prompt: str = Field(..., min_length=1, max_length=2000)
    expected_task_type: str = Field(
        default="recurring",
        pattern=r"^(one_time|recurring)$",
        description="Expected task type",
    )
    expected_cron: Optional[str] = Field(
        default=None,
        description="Expected cron expression (None for one_time tasks)",
    )
    rubric: str = Field(..., min_length=10, max_length=2000)
    tags: list[str] = Field(default_factory=list)


class ScheduleCronGoldenDataset(BaseModel):
    """Complete schedule cron accuracy evaluation dataset."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = None
    eval_type: str = Field(default="schedule_cron", pattern=r"^schedule_cron$")
    cases: list[ScheduleCronTestCase] = Field(..., min_length=4, max_length=20)

    @field_validator("cases")
    @classmethod
    def unique_ids(cls, v: list[ScheduleCronTestCase]) -> list[ScheduleCronTestCase]:
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate case IDs: {set(dupes)}")
        return v


class ScheduleCronCaseResult(BaseModel):
    """Result of evaluating one schedule cron case."""

    case_id: str
    response: str = ""
    actual_cron: Optional[str] = None
    actual_task_type: Optional[str] = None
    cron_correct: Optional[bool] = None
    quality_passed: Optional[bool] = None
    quality_rating: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None


class ScheduleCronMetrics(BaseModel):
    """Aggregate metrics for schedule cron evaluation."""

    total_cases: int
    cron_accuracy: float = Field(..., ge=0.0, le=1.0)
    quality_pass_rate: float = Field(..., ge=0.0, le=1.0)
    error_cases: int = 0
    overall_passed: bool


# ============================================================
# B7: Notification Judgment
# ============================================================


class NotificationJudgmentTestCase(BaseModel):
    """A notification judgment evaluation test case."""

    id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    user_prompt: str = Field(..., min_length=1, max_length=2000)
    expected_notification: Optional[bool] = Field(
        default=None,
        description="Whether a notification should be created (None = quality-only)",
    )
    rubric: str = Field(..., min_length=10, max_length=2000)
    tags: list[str] = Field(default_factory=list)


class NotificationJudgmentGoldenDataset(BaseModel):
    """Complete notification judgment evaluation dataset."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = None
    eval_type: str = Field(
        default="notification_judgment", pattern=r"^notification_judgment$"
    )
    cases: list[NotificationJudgmentTestCase] = Field(..., min_length=4, max_length=20)

    @field_validator("cases")
    @classmethod
    def unique_ids(
        cls, v: list[NotificationJudgmentTestCase],
    ) -> list[NotificationJudgmentTestCase]:
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate case IDs: {set(dupes)}")
        return v


class NotificationJudgmentCaseResult(BaseModel):
    """Result of evaluating one notification judgment case."""

    case_id: str
    response: str = ""
    notification_created: bool = False
    notification_correct: Optional[bool] = None
    quality_passed: Optional[bool] = None
    quality_rating: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None


class NotificationJudgmentMetrics(BaseModel):
    """Aggregate metrics for notification judgment evaluation."""

    total_cases: int
    notification_accuracy: float = Field(..., ge=0.0, le=1.0)
    quality_pass_rate: float = Field(..., ge=0.0, le=1.0)
    error_cases: int = 0
    overall_passed: bool


# ============================================================
# B8: Knowledge Graph Connections
# ============================================================


class KnowledgeConnectionsTestCase(BaseModel):
    """A knowledge graph connections evaluation test case."""

    id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    user_prompt: str = Field(..., min_length=1, max_length=2000)
    seed_entities: list[SeedEntity] = Field(
        ..., min_length=1, description="Entities to pre-seed"
    )
    seed_relationships: list[SeedRelationship] = Field(
        default_factory=list, description="Relationships to pre-seed"
    )
    seed_memories: list[SeedMemory] = Field(
        default_factory=list, description="Memories to pre-seed"
    )
    rubric: str = Field(..., min_length=10, max_length=2000)
    expected_entity_references: list[str] = Field(
        default_factory=list,
        description="Entity names the response should reference",
    )
    tags: list[str] = Field(default_factory=list)


class KnowledgeConnectionsGoldenDataset(BaseModel):
    """Complete knowledge graph connections evaluation dataset."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = None
    eval_type: str = Field(
        default="knowledge_connections", pattern=r"^knowledge_connections$"
    )
    cases: list[KnowledgeConnectionsTestCase] = Field(..., min_length=3, max_length=20)

    @field_validator("cases")
    @classmethod
    def unique_ids(
        cls, v: list[KnowledgeConnectionsTestCase],
    ) -> list[KnowledgeConnectionsTestCase]:
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate case IDs: {set(dupes)}")
        return v


class KnowledgeConnectionsCaseResult(BaseModel):
    """Result of evaluating one knowledge graph connections case."""

    case_id: str
    response: str = ""
    quality_passed: Optional[bool] = None
    quality_rating: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None


class KnowledgeConnectionsMetrics(BaseModel):
    """Aggregate metrics for knowledge graph connections evaluation."""

    total_cases: int
    quality_pass_rate: float = Field(..., ge=0.0, le=1.0)
    error_cases: int = 0
    overall_passed: bool


# ============================================================
# B9: Error Recovery
# ============================================================


class ErrorRecoveryTestCase(BaseModel):
    """An error recovery evaluation test case."""

    id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    user_prompt: str = Field(..., min_length=1, max_length=2000)
    scenario: str = Field(
        ..., min_length=1, max_length=500, description="Error scenario description"
    )
    rubric: str = Field(..., min_length=10, max_length=2000)
    tags: list[str] = Field(default_factory=list)


class ErrorRecoveryGoldenDataset(BaseModel):
    """Complete error recovery evaluation dataset."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = None
    eval_type: str = Field(default="error_recovery", pattern=r"^error_recovery$")
    cases: list[ErrorRecoveryTestCase] = Field(..., min_length=3, max_length=20)

    @field_validator("cases")
    @classmethod
    def unique_ids(
        cls, v: list[ErrorRecoveryTestCase],
    ) -> list[ErrorRecoveryTestCase]:
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate case IDs: {set(dupes)}")
        return v


class ErrorRecoveryCaseResult(BaseModel):
    """Result of evaluating one error recovery case."""

    case_id: str
    response: str = ""
    quality_passed: Optional[bool] = None
    quality_rating: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None


class ErrorRecoveryMetrics(BaseModel):
    """Aggregate metrics for error recovery evaluation."""

    total_cases: int
    quality_pass_rate: float = Field(..., ge=0.0, le=1.0)
    error_cases: int = 0
    overall_passed: bool


# ============================================================
# B10: Long Conversation Coherence
# ============================================================


class LongConversationTestCase(BaseModel):
    """A long conversation coherence evaluation test case."""

    id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    persona: str = Field(..., min_length=1, max_length=500)
    scenario: str = Field(
        ..., min_length=1, max_length=500, description="Scenario description"
    )
    seed_memories: list[SeedMemory] = Field(
        default_factory=list, description="Memories to pre-seed"
    )
    seed_entities: list[SeedEntity] = Field(
        default_factory=list, description="Entities to pre-seed"
    )
    seed_relationships: list[SeedRelationship] = Field(
        default_factory=list, description="Relationships to pre-seed"
    )
    user_turns: list[str] = Field(
        ..., min_length=5, max_length=15, description="Multi-turn user messages"
    )
    rubric: str = Field(..., min_length=10, max_length=2000)
    tags: list[str] = Field(default_factory=list)


class LongConversationGoldenDataset(BaseModel):
    """Complete long conversation coherence evaluation dataset."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = None
    eval_type: str = Field(
        default="long_conversation", pattern=r"^long_conversation$"
    )
    cases: list[LongConversationTestCase] = Field(..., min_length=2, max_length=10)

    @field_validator("cases")
    @classmethod
    def unique_ids(
        cls, v: list[LongConversationTestCase],
    ) -> list[LongConversationTestCase]:
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate case IDs: {set(dupes)}")
        return v


class LongConversationCaseResult(BaseModel):
    """Result of evaluating one long conversation case."""

    case_id: str
    persona: str = ""
    scenario: str = ""
    conversation_transcript: str = ""
    quality_passed: Optional[bool] = None
    quality_rating: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None


class LongConversationMetrics(BaseModel):
    """Aggregate metrics for long conversation evaluation."""

    total_cases: int
    quality_pass_rate: float = Field(..., ge=0.0, le=1.0)
    error_cases: int = 0
    overall_passed: bool


# ============================================================
# B11: Contradiction Handling
# ============================================================


class ContradictionHandlingTestCase(BaseModel):
    """A contradiction handling evaluation test case."""

    id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    persona: str = Field(..., min_length=1, max_length=500)
    seed_memories: list[SeedMemory] = Field(
        ..., min_length=1, description="Memories to pre-seed (containing facts to contradict)"
    )
    user_turns: list[str] = Field(
        ..., min_length=1, max_length=5, description="Multi-turn user messages"
    )
    rubric: str = Field(..., min_length=10, max_length=2000)
    tags: list[str] = Field(default_factory=list)


class ContradictionHandlingGoldenDataset(BaseModel):
    """Complete contradiction handling evaluation dataset."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = None
    eval_type: str = Field(
        default="contradiction_handling", pattern=r"^contradiction_handling$"
    )
    cases: list[ContradictionHandlingTestCase] = Field(..., min_length=3, max_length=20)

    @field_validator("cases")
    @classmethod
    def unique_ids(
        cls, v: list[ContradictionHandlingTestCase],
    ) -> list[ContradictionHandlingTestCase]:
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            dupes = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate case IDs: {set(dupes)}")
        return v


class ContradictionHandlingCaseResult(BaseModel):
    """Result of evaluating one contradiction handling case."""

    case_id: str
    persona: str = ""
    conversation_transcript: str = ""
    quality_passed: Optional[bool] = None
    quality_rating: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None


class ContradictionHandlingMetrics(BaseModel):
    """Aggregate metrics for contradiction handling evaluation."""

    total_cases: int
    quality_pass_rate: float = Field(..., ge=0.0, le=1.0)
    error_cases: int = 0
    overall_passed: bool
