"""Regression detection — compare eval runs against baselines and flag regressions."""

from __future__ import annotations

import structlog

from eval.pipeline.aggregator import get_eval_experiments, get_trend_points
from eval.pipeline.models import PromptChange, RegressionReport, TrendPoint
from eval.pipeline_config import get_threshold

logger = structlog.get_logger(__name__)


def get_baseline_run(
    points: list[TrendPoint],
    current_run_id: str | None = None,
) -> TrendPoint | None:
    """Find the most recent complete run before the current run.

    Args:
        points: Chronologically sorted TrendPoints (oldest first).
        current_run_id: If provided, find baseline before this run.
            If None, use the second-to-last complete run.

    Returns:
        The baseline TrendPoint, or None if no valid baseline exists.
    """
    complete_points = [p for p in points if p.eval_status == "complete"]

    if not complete_points:
        return None

    if current_run_id:
        # Find runs before the specified run
        for i, p in enumerate(complete_points):
            if p.run_id == current_run_id:
                if i > 0:
                    return complete_points[i - 1]
                return None
        # run_id not found in complete points — return last complete as baseline
        return complete_points[-1]

    # No specific run_id: return second-to-last complete run
    if len(complete_points) >= 2:
        return complete_points[-2]
    return None


def compare_runs(
    baseline: TrendPoint,
    current: TrendPoint,
    threshold: float,
) -> RegressionReport:
    """Compare a baseline run against the current run and produce a RegressionReport.

    Args:
        baseline: The baseline TrendPoint.
        current: The current TrendPoint.
        threshold: Pass rate threshold for this eval type.

    Returns:
        A RegressionReport with verdict and changed prompts.
    """
    delta_pp = round((current.pass_rate - baseline.pass_rate) * 100, 6)
    verdict = RegressionReport.compute_verdict(
        current_pass_rate=current.pass_rate,
        baseline_pass_rate=baseline.pass_rate,
        threshold=threshold,
    )

    changed_prompts = _detect_prompt_changes(baseline, current)

    return RegressionReport(
        eval_type=current.eval_type,
        baseline_run_id=baseline.run_id,
        current_run_id=current.run_id,
        baseline_pass_rate=baseline.pass_rate,
        current_pass_rate=current.pass_rate,
        delta_pp=delta_pp,
        threshold=threshold,
        verdict=verdict,
        changed_prompts=changed_prompts,
        baseline_timestamp=baseline.timestamp,
        current_timestamp=current.timestamp,
    )


def check_all_regressions(
    eval_type_filter: str | None = None,
    run_id: str | None = None,
) -> list[RegressionReport]:
    """Check regressions across all eval experiments.

    Args:
        eval_type_filter: If provided, only check this eval type.
        run_id: If provided, check this specific run against its baseline.

    Returns:
        List of RegressionReport objects, one per eval type that has >= 2 complete runs.
    """
    experiments = get_eval_experiments()

    if eval_type_filter:
        experiments = [(name, etype) for name, etype in experiments if etype == eval_type_filter]

    reports: list[RegressionReport] = []

    for exp_name, eval_type in experiments:
        points = get_trend_points(exp_name, eval_type, limit=50)
        complete_points = [p for p in points if p.eval_status == "complete"]

        if len(complete_points) < 2:
            continue

        if run_id:
            # Find the specified run
            current = next((p for p in complete_points if p.run_id == run_id), None)
            if current is None:
                continue
        else:
            current = complete_points[-1]

        baseline = get_baseline_run(points, current.run_id)
        if baseline is None:
            continue

        threshold = get_threshold(eval_type)
        report = compare_runs(baseline, current, threshold)
        reports.append(report)

    return reports


def _detect_prompt_changes(
    baseline: TrendPoint,
    current: TrendPoint,
) -> list[PromptChange]:
    """Detect prompt version changes between two runs."""
    changes: list[PromptChange] = []

    all_prompts = set(baseline.prompt_versions.keys()) | set(current.prompt_versions.keys())
    for prompt_name in sorted(all_prompts):
        prev_version = baseline.prompt_versions.get(prompt_name)
        curr_version = current.prompt_versions.get(prompt_name)

        if prev_version != curr_version and prev_version is not None and curr_version is not None:
            changes.append(
                PromptChange(
                    timestamp=current.timestamp,
                    run_id=current.run_id,
                    prompt_name=prompt_name,
                    from_version=prev_version,
                    to_version=curr_version,
                )
            )

    return changes
