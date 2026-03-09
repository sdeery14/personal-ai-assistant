"""Pipeline data models for eval trend tracking and regression detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


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
    eval_status: str  # "complete", "partial", or "error"
    overall_passed: bool | None = None  # gate result from metrics.overall_passed


@dataclass
class TrendSummary:
    """Aggregated trend data for a single eval type."""

    eval_type: str
    points: list[TrendPoint]
    latest_pass_rate: float
    trend_direction: str  # "improving", "stable", or "degrading"
    latest_overall_passed: bool | None = None  # gate result from latest run


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
class RunCaseResult:
    """Per-case result from an eval run's trace assessments."""

    case_id: str
    score: float | None
    duration_ms: int | None
    error: str | None
    user_prompt: str
    assistant_response: str
    justification: str | None
    rating: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunDetail:
    """Full detail for a single MLflow eval run."""

    run_id: str
    eval_type: str
    timestamp: datetime
    params: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    cases: list[RunCaseResult] = field(default_factory=list)
