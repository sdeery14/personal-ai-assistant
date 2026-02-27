"""Pydantic request/response models for the eval dashboard API."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared response building blocks
# ---------------------------------------------------------------------------


class TrendPointResponse(BaseModel):
    run_id: str
    timestamp: datetime
    eval_type: str
    pass_rate: float
    average_score: float
    total_cases: int
    error_cases: int
    prompt_versions: dict[str, str]
    eval_status: str


class PromptChangeResponse(BaseModel):
    timestamp: datetime
    run_id: str
    prompt_name: str
    from_version: str
    to_version: str


class TrendSummaryResponse(BaseModel):
    eval_type: str
    latest_pass_rate: float
    trend_direction: str
    run_count: int
    points: list[TrendPointResponse]
    prompt_changes: list[PromptChangeResponse]


class RegressionReportResponse(BaseModel):
    eval_type: str
    baseline_run_id: str
    current_run_id: str
    baseline_pass_rate: float
    current_pass_rate: float
    delta_pp: float
    threshold: float
    verdict: str
    changed_prompts: list[PromptChangeResponse]
    baseline_timestamp: datetime
    current_timestamp: datetime


class PromotionEvalCheckResponse(BaseModel):
    eval_type: str
    pass_rate: float
    threshold: float
    passed: bool
    run_id: str


class PromotionGateResponse(BaseModel):
    allowed: bool
    prompt_name: str
    from_alias: str
    to_alias: str
    version: int
    eval_results: list[PromotionEvalCheckResponse]
    blocking_evals: list[str]
    justifying_run_ids: list[str]


class AuditRecordResponse(BaseModel):
    action: str
    prompt_name: str
    from_version: int
    to_version: int
    alias: str
    timestamp: datetime
    actor: str
    reason: str


class EvalRunResultResponse(BaseModel):
    dataset_path: str
    exit_code: int
    passed: bool


class EvalRunStatusResponse(BaseModel):
    run_id: str
    suite: str
    status: str
    total: int
    completed: int
    results: list[EvalRunResultResponse]
    regression_reports: Optional[list[RegressionReportResponse]] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


class PromptListItem(BaseModel):
    name: str
    current_version: int


class RollbackInfoResponse(BaseModel):
    prompt_name: str
    current_version: int
    previous_version: Optional[int] = None
    alias: str


# ---------------------------------------------------------------------------
# Wrapper responses (top-level envelopes)
# ---------------------------------------------------------------------------


class TrendsListResponse(BaseModel):
    summaries: list[TrendSummaryResponse]


class RegressionsListResponse(BaseModel):
    reports: list[RegressionReportResponse]
    has_regressions: bool


class PromptsListResponse(BaseModel):
    prompts: list[PromptListItem]


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class PromotionCheckRequest(BaseModel):
    prompt_name: str
    from_alias: str = "experiment"
    to_alias: str = "production"
    version: Optional[int] = None


class PromotionExecuteRequest(BaseModel):
    prompt_name: str
    to_alias: str = "production"
    version: int
    force: bool = False
    reason: str = ""


class EvalRunRequest(BaseModel):
    suite: str = Field(default="core", pattern="^(core|full)$")


class RollbackExecuteRequest(BaseModel):
    prompt_name: str
    alias: str = "production"
    previous_version: int
    reason: str


# ---------------------------------------------------------------------------
# Run detail drill-down
# ---------------------------------------------------------------------------


class RunCaseResultResponse(BaseModel):
    case_id: str
    score: float | None
    duration_ms: int | None
    error: str | None
    user_prompt: str
    assistant_response: str
    justification: str | None
    rating: str | None = None
    extra: dict[str, Any]


class RunDetailResponse(BaseModel):
    run_id: str
    eval_type: str
    timestamp: datetime
    params: dict[str, str]
    metrics: dict[str, float]
    cases: list[RunCaseResultResponse]
