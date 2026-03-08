"""Eval Explorer API endpoints.

Read-only browsing of MLflow eval data: experiments, runs, traces,
assessments, quality trends, and golden datasets.
All endpoints require admin authentication.
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import require_admin
from src.models.eval_explorer import (
    AgentVersionDetailResponse,
    AgentVersionSummaryResponse,
    AgentVersionsResponse,
    AssessmentDetailResponse,
    DatasetCaseResponse,
    DatasetDetailResponse,
    DatasetsResponse,
    ExperimentResultResponse,
    ExperimentSummaryResponse,
    ExperimentsResponse,
    QualityTrendPointResponse,
    QualityTrendResponse,
    RunSummaryResponse,
    RunsResponse,
    SessionGroupResponse,
    TraceDetailResponse,
    TracesResponse,
)
from src.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/evals/explorer", tags=["Eval Explorer"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Label-to-score mapping (reuses logic from eval/pipeline/aggregator.py)
_LABEL_TO_SCORE: dict[str, float] = {
    "excellent": 5.0,
    "good": 4.0,
    "adequate": 3.0,
    "poor": 2.0,
    "unacceptable": 1.0,
}

_SCORE_TO_LABEL: dict[float, str] = {v: k for k, v in _LABEL_TO_SCORE.items()}


def _normalize_assessment(assessment) -> AssessmentDetailResponse:
    """Convert an MLflow assessment object to a response model."""
    name = assessment.name

    # Extract raw value from assessment
    raw_value = None
    rationale = getattr(assessment, "rationale", None)
    source_type = ""

    if hasattr(assessment, "value") and assessment.value is not None:
        raw_value = assessment.value
    elif hasattr(assessment, "feedback") and assessment.feedback is not None:
        raw_value = getattr(assessment.feedback, "value", None)
    elif hasattr(assessment, "expectation") and assessment.expectation is not None:
        raw_value = getattr(assessment.expectation, "value", None)

    if hasattr(assessment, "source") and assessment.source is not None:
        source_type = str(getattr(assessment.source, "source_type", ""))

    # Normalize to 1-5 scale
    normalized_score: float | None = None
    passed: bool | None = None

    if raw_value is not None:
        if isinstance(raw_value, bool):
            normalized_score = 1.0 if raw_value else 0.0
            passed = raw_value
        elif isinstance(raw_value, (int, float)):
            normalized_score = float(raw_value)
            if 1.0 <= normalized_score <= 5.0:
                passed = normalized_score >= 4.0
        elif isinstance(raw_value, str):
            # Try label mapping
            label_score = _LABEL_TO_SCORE.get(raw_value.lower())
            if label_score is not None:
                normalized_score = label_score
                passed = label_score >= 4.0
            else:
                # Try numeric string
                try:
                    normalized_score = float(raw_value)
                    if 1.0 <= normalized_score <= 5.0:
                        passed = normalized_score >= 4.0
                except ValueError:
                    pass

    return AssessmentDetailResponse(
        name=name,
        raw_value=raw_value if raw_value is not None else "",
        normalized_score=normalized_score,
        passed=passed,
        rationale=rationale,
        source_type=source_type,
    )


def _extract_text(data, keys: list[str]) -> str:
    """Extract text from trace data trying multiple keys."""
    if data is None:
        return ""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data
    if isinstance(data, dict):
        for key in keys:
            if key in data:
                val = data[key]
                return str(val) if val is not None else ""
    return str(data) if data else ""


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/experiments
# ---------------------------------------------------------------------------


@router.get("/experiments")
async def list_experiments(
    admin: User = Depends(require_admin),
) -> ExperimentsResponse:
    """List all eval experiments with aggregated metadata."""
    from eval.pipeline.aggregator import get_eval_experiments
    from eval.pipeline_config import get_metric_names

    loop = asyncio.get_event_loop()

    def _fetch():
        import mlflow

        experiments_list = get_eval_experiments()
        results = []

        for exp_name, eval_type in experiments_list:
            try:
                exp = mlflow.get_experiment_by_name(exp_name)
                if exp is None:
                    continue

                metric_cols = get_metric_names(eval_type)
                pass_rate_col = metric_cols["pass_rate"].replace("metrics.", "")

                runs_df = mlflow.search_runs(
                    experiment_ids=[exp.experiment_id],
                    order_by=["start_time DESC"],
                    max_results=1,
                )

                run_count = 0
                last_ts = None
                latest_pass_rate = None
                latest_uq = None

                if not runs_df.empty:
                    all_runs = mlflow.search_runs(
                        experiment_ids=[exp.experiment_id],
                    )
                    run_count = len(all_runs)

                    latest = runs_df.iloc[0]
                    last_ts = latest.get("start_time")
                    if last_ts is not None:
                        last_ts = str(last_ts)

                    pr_col = f"metrics.{pass_rate_col}"
                    if pr_col in runs_df.columns:
                        val = latest.get(pr_col)
                        if val is not None and str(val) != "nan":
                            latest_pass_rate = float(val)

                    uq_col = "metrics.universal_quality"
                    if uq_col in runs_df.columns:
                        val = latest.get(uq_col)
                        if val is not None and str(val) != "nan":
                            latest_uq = float(val)

                results.append(ExperimentSummaryResponse(
                    experiment_id=exp.experiment_id,
                    name=exp_name,
                    eval_type=eval_type,
                    run_count=run_count,
                    last_run_timestamp=last_ts,
                    latest_pass_rate=latest_pass_rate,
                    latest_universal_quality=latest_uq,
                ))
            except Exception as exc:
                logger.warning("eval_explorer_experiment_error", experiment=exp_name, error=str(exc))
                continue

        return results

    experiments = await loop.run_in_executor(None, _fetch)
    logger.info("eval_explorer_experiments", count=len(experiments))
    return ExperimentsResponse(experiments=experiments)


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/experiments/{experiment_id}/runs
# ---------------------------------------------------------------------------


@router.get("/experiments/{experiment_id}/runs")
async def list_runs(
    experiment_id: str,
    eval_type: str = Query(...),
    admin: User = Depends(require_admin),
) -> RunsResponse:
    """List all runs for an experiment with params and metrics."""
    loop = asyncio.get_event_loop()

    def _fetch():
        import mlflow

        exp = mlflow.get_experiment(experiment_id)
        if exp is None:
            raise FileNotFoundError(f"Experiment {experiment_id} not found")

        runs_df = mlflow.search_runs(
            experiment_ids=[experiment_id],
            order_by=["start_time DESC"],
        )

        results = []
        for _, row in runs_df.iterrows():
            params = {
                k.replace("params.", ""): str(v)
                for k, v in row.items()
                if k.startswith("params.") and v is not None and str(v) != "nan"
            }
            metrics = {
                k.replace("metrics.", ""): float(v)
                for k, v in row.items()
                if k.startswith("metrics.") and v is not None and str(v) != "nan"
            }

            uq = metrics.get("universal_quality")

            results.append(RunSummaryResponse(
                run_id=row["run_id"],
                timestamp=str(row.get("start_time", "")),
                params=params,
                metrics=metrics,
                universal_quality=uq,
                trace_count=int(metrics.get("total_cases", 0)),
                dataset_id=params.get("mlflow_dataset_id"),
                git_sha=params.get("git_sha"),
            ))

        return results

    try:
        runs = await loop.run_in_executor(None, _fetch)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )

    logger.info("eval_explorer_runs", experiment_id=experiment_id, count=len(runs))
    return RunsResponse(runs=runs)


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/runs/{run_id}/traces
# ---------------------------------------------------------------------------


@router.get("/runs/{run_id}/traces")
async def list_traces(
    run_id: str,
    eval_type: str = Query(...),
    admin: User = Depends(require_admin),
) -> TracesResponse:
    """List all traces for a run with full assessment data."""
    from eval.pipeline_config import EVAL_SESSION_TYPES

    loop = asyncio.get_event_loop()

    def _fetch():
        import mlflow

        # Get the experiment ID for this run (required by search_traces)
        run = mlflow.get_run(run_id)
        experiment_id = run.info.experiment_id

        traces = mlflow.search_traces(
            run_id=run_id,
            experiment_ids=[experiment_id],
            return_type="list",
        )

        if not traces:
            return [], []

        is_session_type = eval_type in EVAL_SESSION_TYPES

        trace_results = []
        session_map: dict[str, list[TraceDetailResponse]] = {}
        session_assessments: dict[str, AssessmentDetailResponse | None] = {}

        for trace in traces:
            info = trace.info
            data = trace.data

            # Extract case ID from metadata
            case_id = ""
            if hasattr(info, "request_metadata") and info.request_metadata:
                case_id = info.request_metadata.get("case_id", "")

            # Extract user prompt and assistant response
            user_prompt = _extract_text(
                data.request if data else None,
                ["question", "query", "user_message", "message", "input"],
            )
            assistant_response = _extract_text(
                data.response if data else None,
                ["response", "output", "answer"],
            )

            # Duration
            duration_ms = None
            if hasattr(info, "execution_duration") and info.execution_duration:
                duration_ms = int(info.execution_duration)

            # Session ID
            session_id = None
            if is_session_type and hasattr(info, "request_metadata") and info.request_metadata:
                session_id = info.request_metadata.get("mlflow.trace.session")

            # Assessments
            assessments = []
            if hasattr(info, "assessments") and info.assessments:
                for a in info.assessments:
                    assessments.append(_normalize_assessment(a))

            trace_detail = TraceDetailResponse(
                trace_id=getattr(info, "trace_id", "") or getattr(info, "request_id", ""),
                case_id=case_id,
                user_prompt=user_prompt,
                assistant_response=assistant_response,
                duration_ms=duration_ms,
                error=None,
                session_id=session_id,
                assessments=assessments,
            )

            trace_results.append(trace_detail)

            # Group by session
            if session_id:
                if session_id not in session_map:
                    session_map[session_id] = []
                    session_assessments[session_id] = None
                session_map[session_id].append(trace_detail)
                # Last trace's assessment is the session-level assessment
                if assessments:
                    session_assessments[session_id] = assessments[0]

        # Build session groups
        sessions = []
        for sid, session_traces in session_map.items():
            # Sort by trace order (request_time)
            sessions.append(SessionGroupResponse(
                session_id=sid,
                eval_type=eval_type,
                traces=session_traces,
                session_assessment=session_assessments.get(sid),
            ))

        return trace_results, sessions

    try:
        trace_list, session_list = await loop.run_in_executor(None, _fetch)
    except Exception as exc:
        logger.error("eval_explorer_traces_error", run_id=run_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    logger.info("eval_explorer_traces", run_id=run_id, count=len(trace_list), sessions=len(session_list))
    return TracesResponse(traces=trace_list, sessions=session_list)


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/trends/quality
# ---------------------------------------------------------------------------


@router.get("/trends/quality")
async def get_quality_trend(
    limit: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(require_admin),
) -> QualityTrendResponse:
    """Cross-experiment universal quality trend data."""
    from eval.pipeline.aggregator import get_eval_experiments

    loop = asyncio.get_event_loop()

    def _fetch():
        import mlflow

        experiments_list = get_eval_experiments()
        points = []

        for exp_name, eval_type in experiments_list:
            try:
                exp = mlflow.get_experiment_by_name(exp_name)
                if exp is None:
                    continue

                runs_df = mlflow.search_runs(
                    experiment_ids=[exp.experiment_id],
                    order_by=["start_time DESC"],
                    max_results=limit,
                )

                if runs_df.empty:
                    continue

                uq_col = "metrics.universal_quality"
                if uq_col not in runs_df.columns:
                    continue

                for _, row in runs_df.iterrows():
                    val = row.get(uq_col)
                    if val is not None and str(val) != "nan":
                        points.append(QualityTrendPointResponse(
                            eval_type=eval_type,
                            timestamp=str(row.get("start_time", "")),
                            universal_quality=float(val),
                            run_id=row["run_id"],
                        ))
            except Exception as exc:
                logger.warning("eval_explorer_trend_error", experiment=exp_name, error=str(exc))
                continue

        return points

    trend_points = await loop.run_in_executor(None, _fetch)
    logger.info("eval_explorer_quality_trend", count=len(trend_points))
    return QualityTrendResponse(points=trend_points)


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/datasets
# ---------------------------------------------------------------------------


@router.get("/datasets")
async def list_datasets(
    admin: User = Depends(require_admin),
) -> DatasetsResponse:
    """List all datasets registered in MLflow."""
    loop = asyncio.get_event_loop()

    def _fetch():
        import mlflow
        from mlflow.genai.datasets import search_datasets
        from datetime import datetime, timezone

        # Get all experiments to search across
        experiments = mlflow.search_experiments()
        exp_ids = [e.experiment_id for e in experiments]

        if not exp_ids:
            return []

        raw_datasets = search_datasets(experiment_ids=exp_ids)

        # Deduplicate by dataset_id (same dataset may appear in multiple experiments)
        seen: dict[str, dict] = {}
        for ds in raw_datasets:
            d = ds.to_dict()
            ds_id = d["dataset_id"]
            if ds_id not in seen:
                seen[ds_id] = d
            else:
                # Merge experiment_ids
                existing_exp_ids = set(seen[ds_id].get("experiment_ids", []))
                existing_exp_ids.update(d.get("experiment_ids", []))
                seen[ds_id]["experiment_ids"] = list(existing_exp_ids)

        results = []
        for d in seen.values():
            tags = d.get("tags", {})
            records = d.get("records", [])

            # Parse creation timestamp
            created_ts = d.get("created_time")
            created_str = None
            if isinstance(created_ts, (int, float)):
                created_str = datetime.fromtimestamp(
                    created_ts / 1000, tz=timezone.utc
                ).isoformat()

            results.append(DatasetDetailResponse(
                dataset_id=d["dataset_id"],
                name=d["name"],
                dataset_type=tags.get("dataset_type", ""),
                version=tags.get("version", ""),
                source_file=tags.get("source_file", ""),
                case_count=len(records),
                experiment_ids=d.get("experiment_ids", []),
                created_time=created_str,
                cases=[],  # List endpoint doesn't include cases
            ))

        # Sort by name
        results.sort(key=lambda r: r.name)
        return results

    datasets = await loop.run_in_executor(None, _fetch)
    logger.info("eval_explorer_datasets", count=len(datasets))
    return DatasetsResponse(datasets=datasets)


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/datasets/{dataset_name}
# ---------------------------------------------------------------------------


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    admin: User = Depends(require_admin),
) -> DatasetDetailResponse:
    """Get a single dataset with all cases from MLflow."""
    loop = asyncio.get_event_loop()

    def _fetch():
        import mlflow
        from mlflow.genai.datasets import search_datasets
        from datetime import datetime, timezone

        # Search all experiments to find this dataset
        experiments = mlflow.search_experiments()
        exp_ids = [e.experiment_id for e in experiments]

        if not exp_ids:
            raise FileNotFoundError(f"Dataset '{dataset_id}' not found")

        raw_datasets = search_datasets(experiment_ids=exp_ids)

        target = None
        all_exp_ids: set[str] = set()
        for ds in raw_datasets:
            d = ds.to_dict()
            if d["dataset_id"] == dataset_id:
                if target is None:
                    target = d
                all_exp_ids.update(d.get("experiment_ids", []))

        if target is None:
            raise FileNotFoundError(f"Dataset '{dataset_id}' not found")

        target["experiment_ids"] = list(all_exp_ids)

        tags = target.get("tags", {})
        records = target.get("records", [])

        # Parse creation timestamp
        created_ts = target.get("created_time")
        created_str = None
        if isinstance(created_ts, (int, float)):
            created_str = datetime.fromtimestamp(
                created_ts / 1000, tz=timezone.utc
            ).isoformat()

        # Convert records to cases
        cases = []
        for r in records:
            inputs = r.get("inputs", {})
            expectations = r.get("expectations", {})
            known_keys = {"dataset_record_id", "dataset_id", "inputs",
                          "expectations", "tags", "source", "source_type",
                          "created_time", "last_update_time",
                          "created_by", "last_updated_by", "outputs"}
            extra = {k: v for k, v in r.items()
                     if k not in known_keys and v is not None}

            cases.append(DatasetCaseResponse(
                record_id=r.get("dataset_record_id", ""),
                inputs=inputs if isinstance(inputs, dict) else {},
                expectations=expectations if isinstance(expectations, dict) else {},
                extra=extra,
            ))

        return DatasetDetailResponse(
            dataset_id=target["dataset_id"],
            name=target["name"],
            dataset_type=tags.get("dataset_type", ""),
            version=tags.get("version", ""),
            source_file=tags.get("source_file", ""),
            case_count=len(records),
            experiment_ids=target.get("experiment_ids", []),
            created_time=created_str,
            cases=cases,
        )

    try:
        result = await loop.run_in_executor(None, _fetch)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found",
        )

    logger.info("eval_explorer_dataset_detail", dataset_id=dataset_id)
    return result


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/agents
# ---------------------------------------------------------------------------


@router.get("/agents")
async def list_agent_versions(
    admin: User = Depends(require_admin),
) -> AgentVersionsResponse:
    """List all agent versions (LoggedModels) with git metadata."""
    loop = asyncio.get_event_loop()

    def _fetch():
        import mlflow
        from datetime import datetime, timezone

        try:
            # Must pass experiment_ids for search to return results
            experiments = mlflow.search_experiments()
            exp_ids = [e.experiment_id for e in experiments]
            if not exp_ids:
                return []
            models = mlflow.search_logged_models(
                experiment_ids=exp_ids, output_format="list"
            )
        except Exception:
            return []

        # Deduplicate by model_id (same model may appear across experiments)
        seen = {}
        for model in models:
            if model.model_id not in seen:
                seen[model.model_id] = model
        models = list(seen.values())

        results = []
        for model in models:
            tags = model.tags or {}
            git_branch = tags.get("mlflow.source.git.branch", "")
            git_commit = tags.get("mlflow.source.git.commit", "")
            git_dirty = tags.get("mlflow.source.git.dirty", "false").lower() == "true"

            if not git_commit:
                continue  # Skip models without git versioning

            git_commit_short = git_commit[:7] if git_commit else ""

            # Parse creation timestamp
            ts = model.creation_timestamp
            if isinstance(ts, (int, float)):
                creation_ts = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
            else:
                creation_ts = str(ts) if ts else ""

            # Aggregate quality from model metrics
            aggregate_quality = None
            if model.metrics:
                quality_values = []
                for m in model.metrics:
                    if "universal_quality" in m.key:
                        quality_values.append(m.value)
                if quality_values:
                    aggregate_quality = round(sum(quality_values) / len(quality_values), 2)

            results.append(AgentVersionSummaryResponse(
                model_id=model.model_id,
                name=model.name or "",
                git_branch=git_branch,
                git_commit=git_commit,
                git_commit_short=git_commit_short,
                git_dirty=git_dirty,
                creation_timestamp=creation_ts,
                aggregate_quality=aggregate_quality,
                experiment_count=0,  # Enriched in detail endpoint
                total_traces=0,  # Enriched in detail endpoint
            ))

        # Sort by creation timestamp descending (newest first)
        results.sort(key=lambda r: r.creation_timestamp, reverse=True)
        return results

    agents = await loop.run_in_executor(None, _fetch)
    logger.info("eval_explorer_agents", count=len(agents))
    return AgentVersionsResponse(agents=agents)


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/agents/{model_id}
# ---------------------------------------------------------------------------


@router.get("/agents/{model_id}")
async def get_agent_version_detail(
    model_id: str,
    admin: User = Depends(require_admin),
) -> AgentVersionDetailResponse:
    """Get detailed info for a single agent version."""
    from eval.pipeline.aggregator import get_eval_experiments

    loop = asyncio.get_event_loop()

    def _fetch():
        import mlflow
        from datetime import datetime, timezone

        try:
            model = mlflow.get_logged_model(model_id)
        except Exception:
            raise FileNotFoundError(f"Agent version {model_id} not found")

        tags = model.tags or {}
        git_branch = tags.get("mlflow.source.git.branch", "")
        git_commit = tags.get("mlflow.source.git.commit", "")
        git_dirty = tags.get("mlflow.source.git.dirty", "false").lower() == "true"
        git_diff = tags.get("mlflow.source.git.diff", "")
        git_repo_url = tags.get("mlflow.source.git.repoURL", "")
        git_commit_short = git_commit[:7] if git_commit else ""

        ts = model.creation_timestamp
        if isinstance(ts, (int, float)):
            creation_ts = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
        else:
            creation_ts = str(ts) if ts else ""

        # Get traces for this model
        try:
            traces = mlflow.search_traces(model_id=model_id, return_type="list")
        except Exception:
            traces = []

        total_traces = len(traces)

        # Aggregate per-experiment results from traces
        experiment_results_map: dict = {}
        for trace in traces:
            info = trace.info
            exp_id = getattr(info, "experiment_id", None)
            if not exp_id:
                continue
            if exp_id not in experiment_results_map:
                experiment_results_map[exp_id] = {
                    "run_ids": set(),
                    "quality_scores": [],
                    "pass_count": 0,
                    "total_count": 0,
                }
            entry = experiment_results_map[exp_id]

            # Track runs
            source_run = ""
            if hasattr(info, "request_metadata") and info.request_metadata:
                source_run = info.request_metadata.get("mlflow.sourceRun", "")
            if source_run:
                entry["run_ids"].add(source_run)

            # Track assessments for quality
            if hasattr(info, "assessments") and info.assessments:
                for a in info.assessments:
                    val = getattr(a, "value", None)
                    if val is None and hasattr(a, "feedback") and a.feedback is not None:
                        val = getattr(a.feedback, "value", None)
                    if val is not None:
                        try:
                            score = float(val) if not isinstance(val, bool) else (1.0 if val else 0.0)
                            if 1.0 <= score <= 5.0:
                                entry["quality_scores"].append(score)
                                entry["total_count"] += 1
                                if score >= 4.0:
                                    entry["pass_count"] += 1
                        except (ValueError, TypeError):
                            pass

        # Map experiment IDs to names/types
        experiments_list = get_eval_experiments()
        exp_name_map: dict = {}
        for exp_name, eval_type in experiments_list:
            try:
                exp = mlflow.get_experiment_by_name(exp_name)
                if exp:
                    exp_name_map[exp.experiment_id] = (exp_name, eval_type)
            except Exception:
                continue

        experiment_results = []
        for exp_id, data in experiment_results_map.items():
            exp_name, eval_type = exp_name_map.get(exp_id, (f"experiment-{exp_id}", "unknown"))
            avg_quality = round(sum(data["quality_scores"]) / len(data["quality_scores"]), 2) if data["quality_scores"] else None
            pass_rate = round(data["pass_count"] / data["total_count"], 3) if data["total_count"] > 0 else None
            run_ids = sorted(data["run_ids"])

            experiment_results.append(ExperimentResultResponse(
                experiment_name=exp_name,
                experiment_id=exp_id,
                eval_type=eval_type,
                run_count=len(run_ids),
                pass_rate=pass_rate,
                average_quality=avg_quality,
                latest_run_id=run_ids[-1] if run_ids else None,
            ))

        # Aggregate quality across experiments
        all_quality = [er.average_quality for er in experiment_results if er.average_quality is not None]
        aggregate_quality = round(sum(all_quality) / len(all_quality), 2) if all_quality else None

        return AgentVersionDetailResponse(
            model_id=model.model_id,
            name=model.name or "",
            git_branch=git_branch,
            git_commit=git_commit,
            git_commit_short=git_commit_short,
            git_dirty=git_dirty,
            git_diff=git_diff,
            git_repo_url=git_repo_url,
            creation_timestamp=creation_ts,
            aggregate_quality=aggregate_quality,
            experiment_results=experiment_results,
            total_traces=total_traces,
        )

    try:
        detail = await loop.run_in_executor(None, _fetch)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent version {model_id} not found",
        )

    logger.info("eval_explorer_agent_detail", model_id=model_id)
    return detail
