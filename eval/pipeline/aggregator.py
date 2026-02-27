"""Aggregator — query MLflow runs and compute eval pass rate trends per experiment."""

from __future__ import annotations

from datetime import datetime, timezone

import mlflow
import structlog

from eval.pipeline.models import PromptChange, RunCaseResult, RunDetail, TrendPoint, TrendSummary
from eval.pipeline_config import EVAL_SESSION_TYPES, EXPERIMENT_SUFFIXES, get_base_experiment_name, get_metric_names, get_primary_scorer

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

        metric_names = get_metric_names(eval_type)
        pass_rate = _safe_float(row, metric_names["pass_rate"], 0.0)
        average_score = (
            _safe_float(row, metric_names["average_score"], 0.0)
            if metric_names["average_score"]
            else 0.0
        )
        total_cases = int(_safe_float(row, metric_names["total_cases"], 0))
        error_cases = int(_safe_float(row, metric_names["error_cases"], 0))

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
    """Fetch full detail for a single MLflow run including per-case trace assessments.

    Args:
        run_id: MLflow run ID.
        eval_type: Eval type name (used to determine primary scorer and parse strategy).

    Returns:
        RunDetail with params, metrics, and parsed case results.

    Raises:
        FileNotFoundError: If the run cannot be found.
    """
    import json

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

    # Add canonical keys so the frontend can always read pass_rate, total_cases, etc.
    metric_names = get_metric_names(eval_type)
    for canonical_key, column_name in metric_names.items():
        if not column_name or canonical_key in metrics:
            continue
        if column_name.startswith("params."):
            param_key = column_name[len("params."):]
            if param_key in params:
                try:
                    metrics[canonical_key] = float(params[param_key])
                except (ValueError, TypeError):
                    pass
        elif column_name.startswith("metrics."):
            metric_key = column_name[len("metrics."):]
            if metric_key in metrics:
                metrics[canonical_key] = metrics[metric_key]

    # Determine timestamp
    start_time = run.info.start_time
    if start_time is not None:
        timestamp = datetime.fromtimestamp(start_time / 1000, tz=timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)

    # Search traces for this run and parse into case results
    cases: list[RunCaseResult] = []
    primary_scorer = get_primary_scorer(eval_type)
    if primary_scorer:
        try:
            experiment_id = run.info.experiment_id
            traces = mlflow.search_traces(
                run_id=run_id,
                locations=[experiment_id],
                return_type="list",
            )
            if eval_type in EVAL_SESSION_TYPES:
                cases = _parse_session_traces(traces, run_id, primary_scorer)
            else:
                cases = _parse_single_turn_traces(traces, primary_scorer)
        except Exception as exc:
            logger.warning(
                "mlflow_search_traces_failed",
                run_id=run_id,
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


# Quality-rating string → numeric score mapping.
_RATING_SCORES: dict[str, float] = {
    "excellent": 5.0,
    "good": 4.0,
    "adequate": 3.0,
    "poor": 1.0,
}


def _parse_single_turn_traces(traces: list, primary_scorer: str) -> list[RunCaseResult]:
    """Parse single-turn traces into RunCaseResult objects.

    Each trace maps to one case. Assessment data is read from trace.info.assessments.
    """
    import json

    results: list[RunCaseResult] = []
    for i, trace in enumerate(traces):
        info = trace.info
        assessments = info.assessments or []

        # Extract request/response from trace data
        user_prompt = ""
        assistant_response = ""
        try:
            request_json = trace.data.request
            if request_json:
                req = json.loads(request_json) if isinstance(request_json, str) else request_json
                if isinstance(req, dict):
                    user_prompt = str(req.get("question") or req.get("query") or req.get("user_message") or "")
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            response_json = trace.data.response
            if response_json:
                resp = json.loads(response_json) if isinstance(response_json, str) else response_json
                if isinstance(resp, dict):
                    assistant_response = str(resp.get("response") or "")
                elif isinstance(resp, str):
                    assistant_response = resp
        except (json.JSONDecodeError, TypeError):
            pass

        # Extract primary assessment
        rating, score, justification = _extract_primary_assessment(assessments, primary_scorer)

        # Duration from trace execution time
        duration_ms: int | None = None
        exec_time = getattr(info, "execution_time_ms", None) or getattr(info, "execution_duration", None)
        if exec_time is not None:
            try:
                duration_ms = int(exec_time)
            except (ValueError, TypeError):
                pass

        # Build extra dict from non-primary assessments
        extra = _build_extra(assessments, primary_scorer)

        results.append(
            RunCaseResult(
                case_id=f"case_{i}",
                score=score,
                duration_ms=duration_ms,
                error=None,
                user_prompt=user_prompt,
                assistant_response=assistant_response,
                justification=justification,
                rating=rating,
                extra=extra,
            )
        )
    return results


def _parse_session_traces(traces: list, run_id: str, primary_scorer: str) -> list[RunCaseResult]:
    """Parse session-grouped traces into RunCaseResult objects.

    Traces are grouped by mlflow.trace.session metadata. Each session produces
    one RunCaseResult with conversation transcript in extra.
    """
    import json
    from collections import defaultdict

    # Group traces by session
    by_session: dict[str, list] = defaultdict(list)
    for trace in traces:
        metadata = getattr(trace.info, "trace_metadata", None) or getattr(trace.info, "request_metadata", {})
        session_id = metadata.get("mlflow.trace.session", "")
        if session_id:
            by_session[session_id].append(trace)

    results: list[RunCaseResult] = []
    for session_id in sorted(by_session.keys()):
        session_traces = by_session[session_id]
        # Sort by timestamp within session
        session_traces.sort(key=lambda t: getattr(t.info, "request_time", 0) or getattr(t.info, "timestamp_ms", 0))

        # Reconstruct conversation transcript from all turns
        conversation: list[dict[str, str]] = []
        total_duration_ms = 0
        assessments_found: list = []

        for trace in session_traces:
            # Extract turn request/response
            try:
                request_json = trace.data.request
                if request_json:
                    req = json.loads(request_json) if isinstance(request_json, str) else request_json
                    if isinstance(req, dict):
                        user_msg = str(req.get("user_message") or req.get("question") or req.get("query") or "")
                        if user_msg:
                            conversation.append({"role": "user", "content": user_msg})
            except (json.JSONDecodeError, TypeError):
                pass

            try:
                response_json = trace.data.response
                if response_json:
                    resp = json.loads(response_json) if isinstance(response_json, str) else response_json
                    if isinstance(resp, dict):
                        assistant_msg = str(resp.get("response") or "")
                    elif isinstance(resp, str):
                        assistant_msg = resp
                    else:
                        assistant_msg = ""
                    if assistant_msg:
                        conversation.append({"role": "assistant", "content": assistant_msg})
            except (json.JSONDecodeError, TypeError):
                pass

            # Accumulate duration
            exec_time = getattr(trace.info, "execution_time_ms", None) or getattr(trace.info, "execution_duration", None)
            if exec_time is not None:
                try:
                    total_duration_ms += int(exec_time)
                except (ValueError, TypeError):
                    pass

            # Collect assessments from whichever trace has them
            trace_assessments = trace.info.assessments or []
            if trace_assessments:
                assessments_found = trace_assessments

        # Extract case_id from session ID
        case_id = _extract_case_id_from_session(session_id)

        # Extract primary assessment from the trace that had assessments
        rating, score, justification = _extract_primary_assessment(assessments_found, primary_scorer)
        extra = _build_extra(assessments_found, primary_scorer)

        # Add conversation transcript to extra for frontend rendering
        if conversation:
            extra["conversation_transcript"] = conversation

        # User prompt = first user message, assistant response = last assistant message
        user_prompt = ""
        assistant_response = ""
        for msg in conversation:
            if msg["role"] == "user" and not user_prompt:
                user_prompt = msg["content"]
            if msg["role"] == "assistant":
                assistant_response = msg["content"]

        results.append(
            RunCaseResult(
                case_id=case_id,
                score=score,
                duration_ms=total_duration_ms if total_duration_ms > 0 else None,
                error=None,
                user_prompt=user_prompt,
                assistant_response=assistant_response,
                justification=justification,
                rating=rating,
                extra=extra,
            )
        )
    return results


def _extract_case_id_from_session(session_id: str) -> str:
    """Extract a readable case_id from a session ID.

    Session IDs typically have a format like 'contra-{uuid_prefix}-contra-subtle-mismatch'.
    This extracts the meaningful suffix after the UUID-like prefix.
    """
    parts = session_id.split("-")
    # Find the second occurrence of the eval prefix (e.g., 'contra', 'onb', 'meminf')
    # and take everything from there onwards
    if len(parts) >= 3:
        # Try to find a UUID-like segment (8+ hex chars) and skip past it
        for i, part in enumerate(parts[1:], start=1):
            if len(part) >= 8 and all(c in "0123456789abcdef" for c in part.lower()):
                # Found UUID-like prefix — return everything after it
                remainder = "-".join(parts[i + 1:])
                if remainder:
                    return remainder
    return session_id


def _extract_primary_assessment(
    assessments: list, primary_scorer: str
) -> tuple[str | None, float | None, str | None]:
    """Extract rating, score, and justification from the primary assessment.

    Returns:
        Tuple of (rating, score, justification).
    """
    for assessment in assessments:
        name = getattr(assessment, "name", "")
        if name != primary_scorer:
            continue

        # Get value — could be on .value (Feedback) or .feedback.value
        value = getattr(assessment, "value", None)
        if value is None:
            fb = getattr(assessment, "feedback", None)
            if fb is not None:
                value = getattr(fb, "value", None)

        rationale = getattr(assessment, "rationale", None)

        # Classify value type and derive canonical fields
        if isinstance(value, str):
            rating = value.strip().lower()
            score = _RATING_SCORES.get(rating)
            return rating, score, rationale

        if isinstance(value, bool):
            return None, (1.0 if value else 0.0), rationale

        if isinstance(value, (int, float)):
            score_val = float(value)
            # Numeric scores: derive rating if on 1-5 scale
            rating = None
            for label, threshold in _RATING_SCORES.items():
                if abs(score_val - threshold) < 0.01:
                    rating = label
                    break
            return rating, score_val, rationale

    return None, None, None


def _build_extra(assessments: list, primary_scorer: str) -> dict:
    """Build an extra dict from all non-primary assessments."""
    extra: dict = {}
    for assessment in assessments:
        name = getattr(assessment, "name", "")
        if name == primary_scorer or not name:
            continue

        value = getattr(assessment, "value", None)
        if value is None:
            fb = getattr(assessment, "feedback", None)
            if fb is not None:
                value = getattr(fb, "value", None)
            ex = getattr(assessment, "expectation", None)
            if ex is not None:
                value = getattr(ex, "value", None)

        rationale = getattr(assessment, "rationale", None)

        if rationale:
            extra[name] = {"value": value, "rationale": rationale}
        else:
            extra[name] = value

    return extra


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
