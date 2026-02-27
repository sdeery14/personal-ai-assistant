"""Eval Dashboard API endpoints.

Thin proxy layer over eval pipeline functions (Feature 013).
All endpoints require admin authentication.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import require_admin
from src.models.eval_dashboard import (
    AuditRecordResponse,
    EvalRunRequest,
    EvalRunResultResponse,
    EvalRunStatusResponse,
    PromotionCheckRequest,
    PromotionExecuteRequest,
    PromotionEvalCheckResponse,
    PromotionGateResponse,
    PromptChangeResponse,
    PromptListItem,
    PromptsListResponse,
    RegressionsListResponse,
    RegressionReportResponse,
    RollbackExecuteRequest,
    RollbackInfoResponse,
    RunCaseResultResponse,
    RunDetailResponse,
    TrendPointResponse,
    TrendsListResponse,
    TrendSummaryResponse,
)
from src.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/evals", tags=["Eval Dashboard"])

# ---------------------------------------------------------------------------
# In-memory eval run state (single concurrent run)
# ---------------------------------------------------------------------------

_eval_run_state: Optional[dict] = None


# ---------------------------------------------------------------------------
# Helpers: convert pipeline dataclasses to Pydantic response models
# ---------------------------------------------------------------------------


def _trend_point_response(point) -> TrendPointResponse:
    return TrendPointResponse(
        run_id=point.run_id,
        timestamp=point.timestamp,
        eval_type=point.eval_type,
        pass_rate=point.pass_rate,
        average_score=point.average_score,
        total_cases=point.total_cases,
        error_cases=point.error_cases,
        prompt_versions=point.prompt_versions,
        eval_status=point.eval_status,
    )


def _prompt_change_response(change) -> PromptChangeResponse:
    return PromptChangeResponse(
        timestamp=change.timestamp,
        run_id=change.run_id,
        prompt_name=change.prompt_name,
        from_version=change.from_version,
        to_version=change.to_version,
    )


def _trend_summary_response(summary) -> TrendSummaryResponse:
    return TrendSummaryResponse(
        eval_type=summary.eval_type,
        latest_pass_rate=summary.latest_pass_rate,
        trend_direction=summary.trend_direction,
        run_count=len(summary.points),
        points=[_trend_point_response(p) for p in summary.points],
        prompt_changes=[_prompt_change_response(c) for c in summary.prompt_changes],
    )


def _regression_report_response(report) -> RegressionReportResponse:
    return RegressionReportResponse(
        eval_type=report.eval_type,
        baseline_run_id=report.baseline_run_id,
        current_run_id=report.current_run_id,
        baseline_pass_rate=report.baseline_pass_rate,
        current_pass_rate=report.current_pass_rate,
        delta_pp=report.delta_pp,
        threshold=report.threshold,
        verdict=report.verdict,
        changed_prompts=[_prompt_change_response(c) for c in report.changed_prompts],
        baseline_timestamp=report.baseline_timestamp,
        current_timestamp=report.current_timestamp,
    )


def _audit_record_response(record) -> AuditRecordResponse:
    return AuditRecordResponse(
        action=record.action,
        prompt_name=record.prompt_name,
        from_version=record.from_version,
        to_version=record.to_version,
        alias=record.alias,
        timestamp=record.timestamp,
        actor=record.actor,
        reason=record.reason,
    )


# ---------------------------------------------------------------------------
# GET /admin/evals/trends
# ---------------------------------------------------------------------------


@router.get("/trends")
async def get_trends(
    admin: User = Depends(require_admin),
    eval_type: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
) -> TrendsListResponse:
    """Get trend summaries for all (or filtered) eval types."""
    from eval.pipeline.aggregator import (
        build_trend_summary,
        get_eval_experiments,
        get_trend_points,
    )

    experiments = get_eval_experiments()
    if eval_type:
        experiments = [(name, et) for name, et in experiments if et == eval_type]

    summaries = []
    for exp_name, et in experiments:
        points = get_trend_points(exp_name, et, limit=limit)
        if points:
            summary = build_trend_summary(et, points)
            summaries.append(_trend_summary_response(summary))

    logger.info("eval_dashboard_trends", eval_type=eval_type, count=len(summaries))
    return TrendsListResponse(summaries=summaries)


# ---------------------------------------------------------------------------
# GET /admin/evals/runs/{run_id}/detail
# ---------------------------------------------------------------------------


@router.get("/runs/{run_id}/detail")
async def get_run_detail(
    run_id: str,
    eval_type: str = Query(...),
    admin: User = Depends(require_admin),
) -> RunDetailResponse:
    """Get full detail for a single eval run including per-case results."""
    from eval.pipeline.aggregator import get_run_detail as _get_run_detail

    loop = asyncio.get_event_loop()
    try:
        detail = await loop.run_in_executor(
            None, lambda: _get_run_detail(run_id, eval_type)
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    logger.info("eval_dashboard_run_detail", run_id=run_id, eval_type=eval_type)
    return RunDetailResponse(
        run_id=detail.run_id,
        eval_type=detail.eval_type,
        timestamp=detail.timestamp,
        params=detail.params,
        metrics=detail.metrics,
        cases=[
            RunCaseResultResponse(
                case_id=c.case_id,
                score=c.score,
                duration_ms=c.duration_ms,
                error=c.error,
                user_prompt=c.user_prompt,
                assistant_response=c.assistant_response,
                justification=c.justification,
                rating=c.rating,
                extra=c.extra,
            )
            for c in detail.cases
        ],
    )


# ---------------------------------------------------------------------------
# GET /admin/evals/regressions
# ---------------------------------------------------------------------------


@router.get("/regressions")
async def get_regressions(
    admin: User = Depends(require_admin),
    eval_type: Optional[str] = Query(default=None),
) -> RegressionsListResponse:
    """Get regression check results for all (or filtered) eval types."""
    from eval.pipeline.regression import check_all_regressions

    reports = check_all_regressions(eval_type_filter=eval_type)
    response_reports = [_regression_report_response(r) for r in reports]
    has_regressions = any(r.verdict == "REGRESSION" for r in reports)

    logger.info(
        "eval_dashboard_regressions",
        count=len(reports),
        has_regressions=has_regressions,
    )
    return RegressionsListResponse(
        reports=response_reports, has_regressions=has_regressions
    )


# ---------------------------------------------------------------------------
# GET /admin/evals/prompts
# ---------------------------------------------------------------------------


@router.get("/prompts")
async def list_prompts(
    admin: User = Depends(require_admin),
) -> PromptsListResponse:
    """List all registered prompts for promotion/rollback selection."""
    from src.services.prompt_service import get_active_prompt_versions

    versions = get_active_prompt_versions()
    prompts = [
        PromptListItem(name=name, current_version=ver)
        for name, ver in sorted(versions.items())
    ]
    return PromptsListResponse(prompts=prompts)


# ---------------------------------------------------------------------------
# POST /admin/evals/promote/check
# ---------------------------------------------------------------------------


@router.post("/promote/check")
async def check_promotion(
    request: PromotionCheckRequest,
    admin: User = Depends(require_admin),
) -> PromotionGateResponse:
    """Run promotion gate check (does NOT execute the promotion)."""
    from eval.pipeline.promotion import check_promotion_gate

    result = check_promotion_gate(
        prompt_name=request.prompt_name,
        from_alias=request.from_alias,
        to_alias=request.to_alias,
        version=request.version,
    )

    logger.info(
        "eval_dashboard_promote_check",
        prompt=request.prompt_name,
        allowed=result.allowed,
    )
    return PromotionGateResponse(
        allowed=result.allowed,
        prompt_name=result.prompt_name,
        from_alias=result.from_alias,
        to_alias=result.to_alias,
        version=result.version,
        eval_results=[
            PromotionEvalCheckResponse(
                eval_type=c.eval_type,
                pass_rate=c.pass_rate,
                threshold=c.threshold,
                passed=c.passed,
                run_id=c.run_id,
            )
            for c in result.eval_results
        ],
        blocking_evals=result.blocking_evals,
        justifying_run_ids=result.justifying_run_ids,
    )


# ---------------------------------------------------------------------------
# POST /admin/evals/promote/execute
# ---------------------------------------------------------------------------


@router.post("/promote/execute")
async def execute_promotion_endpoint(
    request: PromotionExecuteRequest,
    admin: User = Depends(require_admin),
) -> AuditRecordResponse:
    """Execute a prompt promotion (optionally forced)."""
    from eval.pipeline.promotion import check_promotion_gate, execute_promotion

    if not request.force:
        gate = check_promotion_gate(
            prompt_name=request.prompt_name,
            to_alias=request.to_alias,
            version=request.version,
        )
        if not gate.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Promotion blocked by failing evals: {', '.join(gate.blocking_evals)}",
            )
        justifying_run_ids = gate.justifying_run_ids
    else:
        justifying_run_ids = []

    record = execute_promotion(
        prompt_name=request.prompt_name,
        to_alias=request.to_alias,
        version=request.version,
        actor=admin.username,
        justifying_run_ids=justifying_run_ids,
    )

    logger.info(
        "eval_dashboard_promote_execute",
        prompt=request.prompt_name,
        version=request.version,
        force=request.force,
        actor=admin.username,
    )
    return _audit_record_response(record)


# ---------------------------------------------------------------------------
# POST /admin/evals/run
# ---------------------------------------------------------------------------


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def start_eval_run(
    request: EvalRunRequest,
    admin: User = Depends(require_admin),
) -> EvalRunStatusResponse:
    """Start an eval suite run (background task). Returns immediately."""
    global _eval_run_state

    if _eval_run_state and _eval_run_state.get("status") == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An eval suite run is already in progress",
        )

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    from eval.pipeline_config import CORE_EVAL_DATASETS, FULL_EVAL_DATASETS

    total = len(CORE_EVAL_DATASETS) if request.suite == "core" else len(FULL_EVAL_DATASETS)

    _eval_run_state = {
        "run_id": job_id,
        "suite": request.suite,
        "status": "running",
        "total": total,
        "completed": 0,
        "results": [],
        "regression_reports": None,
        "started_at": now,
        "finished_at": None,
    }

    logger.info(
        "eval_dashboard_run_start",
        job_id=job_id,
        suite=request.suite,
        total=total,
        actor=admin.username,
    )

    asyncio.create_task(_run_eval_suite_background(request.suite))

    return _build_run_status_response()


async def _run_eval_suite_background(suite: str) -> None:
    """Background task that runs the eval suite and regression check."""
    global _eval_run_state

    try:
        from eval.pipeline.regression import check_all_regressions
        from eval.pipeline.trigger import run_eval_suite

        def progress_callback(index: int, total: int, dataset_path: str, result) -> None:
            if _eval_run_state is not None:
                _eval_run_state["completed"] = index + 1
                _eval_run_state["results"].append({
                    "dataset_path": result.dataset_path,
                    "exit_code": result.exit_code,
                    "passed": result.passed,
                })

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, lambda: run_eval_suite(suite=suite, progress_callback=progress_callback)
        )

        regression_reports = await loop.run_in_executor(
            None, check_all_regressions
        )

        if _eval_run_state is not None:
            _eval_run_state["status"] = "completed"
            _eval_run_state["finished_at"] = datetime.now(timezone.utc)
            _eval_run_state["regression_reports"] = [
                _regression_report_response(r).model_dump() for r in regression_reports
            ]

        logger.info("eval_dashboard_run_complete", suite=suite)

    except Exception as exc:
        logger.error("eval_dashboard_run_failed", error=str(exc))
        if _eval_run_state is not None:
            _eval_run_state["status"] = "failed"
            _eval_run_state["finished_at"] = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# GET /admin/evals/run/status
# ---------------------------------------------------------------------------


@router.get("/run/status")
async def get_run_status(
    admin: User = Depends(require_admin),
) -> Optional[EvalRunStatusResponse]:
    """Get the status of the current or most recent eval suite run."""
    if _eval_run_state is None:
        return None
    return _build_run_status_response()


def _build_run_status_response() -> EvalRunStatusResponse:
    """Build response from current eval run state dict."""
    state = _eval_run_state
    assert state is not None

    regression_reports = None
    if state["regression_reports"] is not None:
        regression_reports = [
            RegressionReportResponse(**r) for r in state["regression_reports"]
        ]

    return EvalRunStatusResponse(
        run_id=state["run_id"],
        suite=state["suite"],
        status=state["status"],
        total=state["total"],
        completed=state["completed"],
        results=[EvalRunResultResponse(**r) for r in state["results"]],
        regression_reports=regression_reports,
        started_at=state["started_at"],
        finished_at=state["finished_at"],
    )


# ---------------------------------------------------------------------------
# GET /admin/evals/rollback/info
# ---------------------------------------------------------------------------


@router.get("/rollback/info")
async def get_rollback_info(
    admin: User = Depends(require_admin),
    prompt_name: str = Query(...),
    alias: str = Query(default="production"),
) -> RollbackInfoResponse:
    """Get rollback information for a prompt (current and previous version)."""
    from eval.pipeline.rollback import find_previous_version
    from src.services.prompt_service import load_prompt_version

    current = load_prompt_version(prompt_name, alias)
    previous = find_previous_version(prompt_name, alias)

    return RollbackInfoResponse(
        prompt_name=prompt_name,
        current_version=current.version,
        previous_version=previous,
        alias=alias,
    )


# ---------------------------------------------------------------------------
# POST /admin/evals/rollback/execute
# ---------------------------------------------------------------------------


@router.post("/rollback/execute")
async def execute_rollback_endpoint(
    request: RollbackExecuteRequest,
    admin: User = Depends(require_admin),
) -> AuditRecordResponse:
    """Execute a prompt rollback."""
    from eval.pipeline.rollback import execute_rollback

    record = execute_rollback(
        prompt_name=request.prompt_name,
        alias=request.alias,
        previous_version=request.previous_version,
        reason=request.reason,
        actor=admin.username,
    )

    logger.info(
        "eval_dashboard_rollback",
        prompt=request.prompt_name,
        from_version=record.from_version,
        to_version=record.to_version,
        actor=admin.username,
    )
    return _audit_record_response(record)
