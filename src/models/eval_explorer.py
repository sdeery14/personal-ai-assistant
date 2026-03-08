"""Pydantic response models for the eval explorer API."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Assessment & Trace models
# ---------------------------------------------------------------------------


class AssessmentDetailResponse(BaseModel):
    name: str
    raw_value: Any
    normalized_score: Optional[float] = None
    passed: Optional[bool] = None
    rationale: Optional[str] = None
    source_type: str = ""


class TraceDetailResponse(BaseModel):
    trace_id: str
    case_id: str
    user_prompt: str
    assistant_response: str
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    session_id: Optional[str] = None
    assessments: list[AssessmentDetailResponse]


class SessionGroupResponse(BaseModel):
    session_id: str
    eval_type: str
    traces: list[TraceDetailResponse]
    session_assessment: Optional[AssessmentDetailResponse] = None


class TracesResponse(BaseModel):
    traces: list[TraceDetailResponse]
    sessions: list[SessionGroupResponse]


# ---------------------------------------------------------------------------
# Run models
# ---------------------------------------------------------------------------


class RunSummaryResponse(BaseModel):
    run_id: str
    timestamp: datetime
    params: dict[str, str]
    metrics: dict[str, float]
    universal_quality: Optional[float] = None
    trace_count: int = 0


class RunsResponse(BaseModel):
    runs: list[RunSummaryResponse]


# ---------------------------------------------------------------------------
# Experiment models
# ---------------------------------------------------------------------------


class ExperimentSummaryResponse(BaseModel):
    experiment_id: str
    name: str
    eval_type: str
    run_count: int
    last_run_timestamp: Optional[datetime] = None
    latest_pass_rate: Optional[float] = None
    latest_universal_quality: Optional[float] = None


class ExperimentsResponse(BaseModel):
    experiments: list[ExperimentSummaryResponse]


# ---------------------------------------------------------------------------
# Quality trend models
# ---------------------------------------------------------------------------


class QualityTrendPointResponse(BaseModel):
    eval_type: str
    timestamp: datetime
    universal_quality: float
    run_id: str


class QualityTrendResponse(BaseModel):
    points: list[QualityTrendPointResponse]


# ---------------------------------------------------------------------------
# Dataset models
# ---------------------------------------------------------------------------


class DatasetCaseResponse(BaseModel):
    id: str
    user_prompt: str
    rubric: Optional[str] = None
    tags: list[str] = []
    extra: dict[str, Any] = {}


class DatasetDetailResponse(BaseModel):
    name: str
    file_path: str
    version: str
    description: str
    case_count: int
    cases: list[DatasetCaseResponse] = []


class DatasetsResponse(BaseModel):
    datasets: list[DatasetDetailResponse]
