"""Aggregator — query MLflow runs and compute eval pass rate trends per experiment."""

from __future__ import annotations

from datetime import datetime, timezone

import mlflow
import structlog

from eval.pipeline.models import PromptChange, RunCaseResult, RunDetail, TrendPoint, TrendSummary
from eval.pipeline_config import EXPERIMENT_SUFFIXES, get_artifact_filename, get_base_experiment_name

logger = structlog.get_logger(__name__)


def get_eval_experiments() -> list[tuple[str, str]]:
    """Discover all eval experiments by prefix-matching against the base experiment name.

    Returns:
        List of (experiment_name, eval_type) tuples.
    """
    base_name = get_base_experiment_name()
    results: list[tuple[str, str]] = []

    try:
        experiments = mlflow.search_experiments()
    except Exception:
        logger.warning("mlflow_search_experiments_failed")
        return []

    for exp in experiments:
        name = exp.name
        if name == base_name:
            # Base experiment (quality/security)
            eval_type = EXPERIMENT_SUFFIXES.get("", "quality")
            results.append((name, eval_type))
        elif name.startswith(base_name + "-"):
            suffix = name[len(base_name):]
            eval_type = EXPERIMENT_SUFFIXES.get(suffix, suffix.lstrip("-"))
            results.append((name, eval_type))

    results.sort(key=lambda x: x[1])
    return results


def get_trend_points(
    experiment_name: str,
    eval_type: str,
    limit: int = 10,
) -> list[TrendPoint]:
    """Query MLflow runs for an experiment and return TrendPoints sorted chronologically.

    Args:
        experiment_name: Full MLflow experiment name.
        eval_type: Short eval type name (e.g., "tone").
        limit: Max runs to retrieve.

    Returns:
        List of TrendPoint objects sorted oldest → newest.
    """
    try:
        runs_df = mlflow.search_runs(
            experiment_names=[experiment_name],
            filter_string="attributes.status = 'FINISHED'",
            order_by=["start_time DESC"],
            max_results=limit,
        )
    except Exception:
        logger.warning("mlflow_search_runs_failed", experiment=experiment_name)
        return []

    if runs_df.empty:
        return []

    points: list[TrendPoint] = []
    for _, row in runs_df.iterrows():
        run_id = row.get("run_id", "")
        start_time = row.get("start_time")

        if start_time is not None:
            if hasattr(start_time, "to_pydatetime"):
                timestamp = start_time.to_pydatetime()
            else:
                timestamp = start_time
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)

        pass_rate = _safe_float(row, "metrics.pass_rate", 0.0)
        average_score = _safe_float(row, "metrics.average_score", 0.0)
        total_cases = int(_safe_float(row, "metrics.total_cases", 0))
        error_cases = int(_safe_float(row, "metrics.error_cases", 0))

        # Extract prompt versions from params.prompt.* columns
        prompt_versions: dict[str, str] = {}
        for col in runs_df.columns:
            if col.startswith("params.prompt."):
                val = row.get(col)
                if val is not None and str(val) != "nan":
                    prompt_name = col[len("params.prompt."):]
                    prompt_versions[prompt_name] = str(val)

        # Compute eval_status from existing metrics
        run_status = row.get("status", "FINISHED")
        if run_status == "FAILED":
            eval_status = "error"
        elif error_cases > 0:
            eval_status = "partial"
        else:
            eval_status = "complete"

        points.append(
            TrendPoint(
                run_id=run_id,
                timestamp=timestamp,
                experiment_name=experiment_name,
                eval_type=eval_type,
                pass_rate=pass_rate,
                average_score=average_score,
                total_cases=total_cases,
                error_cases=error_cases,
                prompt_versions=prompt_versions,
                eval_status=eval_status,
            )
        )

    # Sort oldest → newest
    points.sort(key=lambda p: p.timestamp)
    return points


def build_trend_summary(eval_type: str, points: list[TrendPoint]) -> TrendSummary:
    """Build a TrendSummary from a list of chronologically-sorted TrendPoints.

    Computes trend direction from last 3 runs and detects prompt version changes.
    """
    if not points:
        return TrendSummary(
            eval_type=eval_type,
            points=[],
            latest_pass_rate=0.0,
            trend_direction="stable",
            prompt_changes=[],
        )

    latest_pass_rate = points[-1].pass_rate
    trend_direction = _compute_trend_direction(points)
    prompt_changes = _detect_prompt_changes(points)

    return TrendSummary(
        eval_type=eval_type,
        points=points,
        latest_pass_rate=latest_pass_rate,
        trend_direction=trend_direction,
        prompt_changes=prompt_changes,
    )


def _compute_trend_direction(points: list[TrendPoint]) -> str:
    """Determine trend direction from the last 3 data points.

    - improving: last point > first of the 3
    - degrading: last point < first of the 3
    - stable: otherwise
    """
    recent = points[-3:] if len(points) >= 3 else points
    if len(recent) < 2:
        return "stable"

    first_rate = recent[0].pass_rate
    last_rate = recent[-1].pass_rate
    delta = last_rate - first_rate

    if delta > 0.01:
        return "improving"
    if delta < -0.01:
        return "degrading"
    return "stable"


def _detect_prompt_changes(points: list[TrendPoint]) -> list[PromptChange]:
    """Detect prompt version transitions between consecutive runs."""
    changes: list[PromptChange] = []

    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]

        # Compare prompt versions
        all_prompts = set(prev.prompt_versions.keys()) | set(curr.prompt_versions.keys())
        for prompt_name in all_prompts:
            prev_version = prev.prompt_versions.get(prompt_name)
            curr_version = curr.prompt_versions.get(prompt_name)

            if prev_version != curr_version and prev_version is not None and curr_version is not None:
                changes.append(
                    PromptChange(
                        timestamp=curr.timestamp,
                        run_id=curr.run_id,
                        prompt_name=prompt_name,
                        from_version=prev_version,
                        to_version=curr_version,
                    )
                )

    return changes


def get_run_detail(run_id: str, eval_type: str) -> RunDetail:
    """Fetch full detail for a single MLflow run including per-case artifact.

    Args:
        run_id: MLflow run ID.
        eval_type: Eval type name (used to determine artifact filename).

    Returns:
        RunDetail with params, metrics, and parsed case results.

    Raises:
        FileNotFoundError: If the run or artifact cannot be found.
    """
    import json
    import tempfile
    from pathlib import Path

    try:
        run = mlflow.get_run(run_id)
    except Exception as exc:
        logger.warning("mlflow_get_run_failed", run_id=run_id, error=str(exc))
        raise FileNotFoundError(f"Run {run_id} not found") from exc

    # Extract params and metrics
    params: dict[str, str] = dict(run.data.params)
    metrics: dict[str, float] = {}
    for k, v in run.data.metrics.items():
        try:
            metrics[k] = float(v)
        except (ValueError, TypeError):
            pass

    # Determine timestamp
    start_time = run.info.start_time
    if start_time is not None:
        timestamp = datetime.fromtimestamp(start_time / 1000, tz=timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)

    # Download and parse artifact
    cases: list[RunCaseResult] = []
    artifact_filename = get_artifact_filename(eval_type)
    if artifact_filename:
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                local_path = mlflow.artifacts.download_artifacts(
                    run_id=run_id,
                    artifact_path=artifact_filename,
                    dst_path=tmp_dir,
                )
                artifact_file = Path(local_path)
                if artifact_file.is_file():
                    raw_cases = json.loads(artifact_file.read_text(encoding="utf-8"))
                    cases = _parse_case_results(raw_cases)
        except Exception as exc:
            logger.warning(
                "mlflow_artifact_download_failed",
                run_id=run_id,
                artifact=artifact_filename,
                error=str(exc),
            )

    return RunDetail(
        run_id=run_id,
        eval_type=eval_type,
        timestamp=timestamp,
        params=params,
        metrics=metrics,
        cases=cases,
    )


# Well-known fields extracted explicitly from per-case result dicts.
_COMMON_CASE_FIELDS = frozenset({
    "case_id", "score", "passed", "duration_ms", "error",
    "user_prompt", "assistant_response", "justification",
    # Also skip these common keys that aren't useful in extra
    "question", "expected_answer", "rubric",
})


def _parse_case_results(raw_cases: list[dict]) -> list[RunCaseResult]:
    """Parse a list of raw case dicts into RunCaseResult objects."""
    results: list[RunCaseResult] = []
    for i, raw in enumerate(raw_cases):
        extra = {k: v for k, v in raw.items() if k not in _COMMON_CASE_FIELDS}
        results.append(
            RunCaseResult(
                case_id=str(raw.get("case_id", f"case_{i}")),
                score=_opt_float(raw.get("score")),
                passed=_opt_bool(raw.get("passed")),
                duration_ms=_opt_int(raw.get("duration_ms")),
                error=raw.get("error"),
                user_prompt=str(raw.get("user_prompt", raw.get("question", ""))),
                assistant_response=str(raw.get("assistant_response", raw.get("expected_answer", ""))),
                justification=raw.get("justification"),
                extra=extra,
            )
        )
    return results


def _opt_float(val: object) -> float | None:
    if val is None:
        return None
    try:
        result = float(val)  # type: ignore[arg-type]
        return None if result != result else result  # NaN → None
    except (ValueError, TypeError):
        return None


def _opt_bool(val: object) -> bool | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    return None


def _opt_int(val: object) -> int | None:
    if val is None:
        return None
    try:
        return int(val)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None


def _safe_float(row: object, key: str, default: float) -> float:
    """Safely extract a float from a DataFrame row, handling NaN."""
    val = row.get(key) if hasattr(row, "get") else None  # type: ignore[union-attr]
    if val is None:
        return default
    try:
        result = float(val)
        if result != result:  # NaN check
            return default
        return result
    except (ValueError, TypeError):
        return default
