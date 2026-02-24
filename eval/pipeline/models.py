"""Pipeline data models for eval trend tracking, regression detection, and promotion gating."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PromptChange:
    """Annotation for a prompt version transition between two consecutive runs."""

    timestamp: datetime
    run_id: str
    prompt_name: str
    from_version: str
    to_version: str


@dataclass
class TrendPoint:
    """A single data point in an eval trend timeline."""

    run_id: str
    timestamp: datetime
    experiment_name: str
    eval_type: str
    pass_rate: float
    average_score: float
    total_cases: int
    error_cases: int
    prompt_versions: dict[str, str]
    eval_status: str  # "complete", "partial", or "error"


@dataclass
class TrendSummary:
    """Aggregated trend data for a single eval type."""

    eval_type: str
    points: list[TrendPoint]
    latest_pass_rate: float
    trend_direction: str  # "improving", "stable", or "degrading"
    prompt_changes: list[PromptChange]


@dataclass
class RegressionReport:
    """Comparison between a baseline run and the current run for one eval type."""

    eval_type: str
    baseline_run_id: str
    current_run_id: str
    baseline_pass_rate: float
    current_pass_rate: float
    delta_pp: float
    threshold: float
    verdict: str  # "REGRESSION", "WARNING", "PASS", or "IMPROVED"
    changed_prompts: list[PromptChange]
    baseline_timestamp: datetime
    current_timestamp: datetime

    @staticmethod
    def compute_verdict(
        current_pass_rate: float,
        baseline_pass_rate: float,
        threshold: float,
    ) -> str:
        """Compute the regression verdict based on pass rates and threshold.

        - REGRESSION: current crosses below threshold
        - WARNING: drop >= 10pp but still above threshold
        - IMPROVED: current > baseline
        - PASS: stable or minor fluctuation
        """
        delta_pp = round((current_pass_rate - baseline_pass_rate) * 100, 6)

        if current_pass_rate < threshold:
            return "REGRESSION"
        if delta_pp <= -10:
            return "WARNING"
        if delta_pp > 0:
            return "IMPROVED"
        return "PASS"


@dataclass
class PromotionEvalCheck:
    """Per-eval-type result within a promotion gate check."""

    eval_type: str
    pass_rate: float
    threshold: float
    passed: bool
    run_id: str


@dataclass
class PromotionResult:
    """Outcome of a promotion gate check."""

    allowed: bool
    prompt_name: str
    from_alias: str
    to_alias: str
    version: int
    eval_results: list[PromotionEvalCheck]
    blocking_evals: list[str]
    justifying_run_ids: list[str]


@dataclass
class AuditRecord:
    """Represents a promotion or rollback action stored as MLflow tags."""

    action: str  # "promote" or "rollback"
    prompt_name: str
    from_version: int
    to_version: int
    alias: str
    timestamp: datetime
    actor: str
    reason: str
    justifying_run_ids: list[str] = field(default_factory=list)

    def to_tags(self) -> dict[str, str]:
        """Convert to MLflow tag key-value pairs."""
        return {
            "audit.action": self.action,
            "audit.prompt_name": self.prompt_name,
            "audit.from_version": str(self.from_version),
            "audit.to_version": str(self.to_version),
            "audit.alias": self.alias,
            "audit.timestamp": self.timestamp.isoformat(),
            "audit.actor": self.actor,
            "audit.reason": self.reason,
        }
