"""Click CLI commands for the eval pipeline."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone

import click

from eval.pipeline.aggregator import (
    build_trend_summary,
    get_eval_experiments,
    get_trend_points,
)
from eval.pipeline.models import RegressionReport, TrendSummary
from eval.pipeline.promotion import check_promotion_gate, execute_promotion
from eval.pipeline.regression import check_all_regressions
from eval.pipeline.rollback import execute_rollback, find_previous_version
from eval.pipeline.trigger import run_eval_suite


@click.group()
def pipeline() -> None:
    """Eval Dashboard & Regression Pipeline — trend tracking, regression detection, and prompt promotion."""
    pass


# ---------------------------------------------------------------------------
# US1: trend command
# ---------------------------------------------------------------------------


@pipeline.command()
@click.option("--eval-type", default=None, help="Filter to a specific eval type.")
@click.option("--limit", default=10, help="Max runs per eval type to display.")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "json"]),
    help="Output format.",
)
def trend(eval_type: str | None, limit: int, output_format: str) -> None:
    """View eval pass rate trends over time."""
    experiments = get_eval_experiments()

    if eval_type:
        experiments = [(name, etype) for name, etype in experiments if etype == eval_type]
        if not experiments:
            click.echo(f"No experiments found for eval type: {eval_type}")
            sys.exit(2)

    summaries: list[TrendSummary] = []
    no_data_types: list[str] = []

    for exp_name, etype in experiments:
        points = get_trend_points(exp_name, etype, limit=limit)
        summary = build_trend_summary(etype, points)
        if summary.points:
            summaries.append(summary)
        else:
            no_data_types.append(etype)

    if not summaries and not no_data_types:
        click.echo("No eval runs found. Run evaluations first with: uv run python -m eval")
        return

    if output_format == "json":
        _print_trend_json(summaries)
    else:
        _print_trend_table(summaries, no_data_types, limit)


def _print_trend_table(
    summaries: list[TrendSummary],
    no_data_types: list[str],
    limit: int,
) -> None:
    """Print trend summaries in table format."""
    click.echo()
    click.echo(f"Eval Trend Summary (last {limit} runs)")
    click.echo("=" * 60)
    click.echo()

    for summary in summaries:
        direction = summary.trend_direction.upper()
        click.echo(
            f"{summary.eval_type} (latest: {summary.latest_pass_rate:.1%} pass rate, {direction})"
        )
        click.echo(
            f"  {'Run':<20} {'Date':<22} {'Pass Rate':<12} {'Score':<8} {'Prompts Changed'}"
        )

        # Build a lookup of prompt changes by run_id
        changes_by_run: dict[str, list[str]] = {}
        for pc in summary.prompt_changes:
            changes_by_run.setdefault(pc.run_id, []).append(
                f"{pc.prompt_name}: {pc.from_version}->{pc.to_version}"
            )

        for point in reversed(summary.points):  # newest first
            run_short = point.run_id[:16] if len(point.run_id) > 16 else point.run_id
            date_str = point.timestamp.strftime("%Y-%m-%d %H:%M")
            pass_rate_str = f"{point.pass_rate:.1%}"
            score_str = f"{point.average_score:.1f}"
            prompts_str = ", ".join(changes_by_run.get(point.run_id, ["-"]))
            click.echo(
                f"  {run_short:<20} {date_str:<22} {pass_rate_str:<12} {score_str:<8} {prompts_str}"
            )
        click.echo()

    if no_data_types:
        for etype in no_data_types:
            click.echo(f"No data: {etype} (0 runs)")
        click.echo()


def _print_trend_json(summaries: list[TrendSummary]) -> None:
    """Print trend summaries as JSON."""

    def _serialize(obj: object) -> object:
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    data = [asdict(s) for s in summaries]
    click.echo(json.dumps(data, default=_serialize, indent=2))


# ---------------------------------------------------------------------------
# US2: check command
# ---------------------------------------------------------------------------


@pipeline.command()
@click.option("--eval-type", default=None, help="Filter to a specific eval type.")
@click.option("--run-id", default=None, help="Specific run ID to check (default: latest).")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "json"]),
    help="Output format.",
)
def check(eval_type: str | None, run_id: str | None, output_format: str) -> None:
    """Detect regressions against previous baseline."""
    reports = check_all_regressions(eval_type_filter=eval_type, run_id=run_id)

    if not reports:
        click.echo("No eval types with sufficient data for regression check.")
        click.echo("Need at least 2 complete runs per eval type.")
        return

    if output_format == "json":
        _print_check_json(reports)
    else:
        _print_check_table(reports)

    # Exit code 1 if any REGRESSION
    has_regression = any(r.verdict == "REGRESSION" for r in reports)
    if has_regression:
        sys.exit(1)


def _print_check_table(reports: list[RegressionReport]) -> None:
    """Print regression check results in table format."""
    click.echo()
    click.echo("Regression Check")
    click.echo("=" * 60)
    click.echo()
    click.echo(
        f"  {'Eval Type':<24} {'Baseline':<12} {'Current':<12} {'Delta':<10} {'Threshold':<12} {'Verdict'}"
    )

    for r in reports:
        delta_str = f"{r.delta_pp:+.0f}pp"
        click.echo(
            f"  {r.eval_type:<24} {r.baseline_pass_rate:.1%}{'':>5} {r.current_pass_rate:.1%}{'':>5} "
            f"{delta_str:<10} {r.threshold:.1%}{'':>5} {r.verdict}"
        )

    click.echo()

    # Collect all changed prompts
    all_changes: list[str] = []
    for r in reports:
        for pc in r.changed_prompts:
            change_str = (
                f"  {pc.prompt_name}: {pc.from_version} -> {pc.to_version} "
                f"(between runs {r.baseline_run_id[:8]}.. and {r.current_run_id[:8]}..)"
            )
            if change_str not in all_changes:
                all_changes.append(change_str)

    if all_changes:
        click.echo("Changed Prompts:")
        for change in all_changes:
            click.echo(change)
        click.echo()

    # Summary counts
    counts: dict[str, int] = {}
    for r in reports:
        counts[r.verdict] = counts.get(r.verdict, 0) + 1

    has_regression = counts.get("REGRESSION", 0) > 0
    if has_regression:
        click.echo("Overall: REGRESSION DETECTED")
    else:
        click.echo("Overall: No regressions")

    summary_parts = [f"{count} {verdict}" for verdict, count in sorted(counts.items())]
    click.echo(", ".join(summary_parts))


def _print_check_json(reports: list[RegressionReport]) -> None:
    """Print regression check results as JSON."""

    def _serialize(obj: object) -> object:
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    data = [asdict(r) for r in reports]
    click.echo(json.dumps(data, default=_serialize, indent=2))


# ---------------------------------------------------------------------------
# US3: promote command
# ---------------------------------------------------------------------------


@pipeline.command()
@click.argument("prompt_name")
@click.option("--from-alias", default="experiment", help="Source alias.")
@click.option("--to-alias", default="production", help="Target alias.")
@click.option("--version", default=None, type=int, help="Specific version to promote.")
@click.option("--force", is_flag=True, default=False, help="Skip eval gate (with warning).")
@click.option("--actor", default="cli-user", help="Actor name for audit log.")
def promote(
    prompt_name: str,
    from_alias: str,
    to_alias: str,
    version: int | None,
    force: bool,
    actor: str,
) -> None:
    """Gate and execute prompt promotion."""
    result = check_promotion_gate(
        prompt_name=prompt_name,
        from_alias=from_alias,
        to_alias=to_alias,
        version=version,
    )

    click.echo()
    click.echo("Promotion Gate Check")
    click.echo("=" * 60)
    click.echo()
    click.echo(f"Prompt: {result.prompt_name} (v{result.version})")
    click.echo(f"From: @{result.from_alias} -> To: @{result.to_alias}")
    click.echo()

    click.echo(f"  {'Eval Type':<24} {'Pass Rate':<12} {'Threshold':<12} {'Status'}")
    for ec in result.eval_results:
        status = "PASS" if ec.passed else "FAIL"
        click.echo(
            f"  {ec.eval_type:<24} {ec.pass_rate:.1%}{'':>5} {ec.threshold:.1%}{'':>5} {status}"
        )
    click.echo()

    if result.allowed:
        click.echo(f"All {len(result.eval_results)} eval types pass. Promoting...")
        click.echo()
        record = execute_promotion(
            prompt_name=result.prompt_name,
            to_alias=result.to_alias,
            version=result.version,
            actor=actor,
            justifying_run_ids=result.justifying_run_ids,
        )
        click.echo(
            f"SUCCESS: {result.prompt_name} @{result.to_alias} now points to v{result.version}"
        )
        click.echo(f"Audit logged on runs: {', '.join(r[:8] for r in record.justifying_run_ids)}")
    elif force:
        click.echo("WARNING: Force flag set — bypassing eval gate.")
        click.echo()
        record = execute_promotion(
            prompt_name=result.prompt_name,
            to_alias=result.to_alias,
            version=result.version,
            actor=actor,
            justifying_run_ids=result.justifying_run_ids,
        )
        click.echo(
            f"SUCCESS (forced): {result.prompt_name} @{result.to_alias} now points to v{result.version}"
        )
    else:
        click.echo(f"BLOCKED: {len(result.blocking_evals)} eval type(s) below threshold.")
        for eval_type in result.blocking_evals:
            ec = next(e for e in result.eval_results if e.eval_type == eval_type)
            click.echo(f"  {eval_type}: {ec.pass_rate:.1%} < {ec.threshold:.1%} required")
        click.echo()
        click.echo("Fix the prompt and re-run evals before promoting.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# US5: rollback command
# ---------------------------------------------------------------------------


@pipeline.command()
@click.argument("prompt_name")
@click.option("--alias", default="production", help="Alias to roll back.")
@click.option("--reason", required=True, help="Reason for rollback.")
@click.option("--actor", default="cli-user", help="Actor name for audit log.")
def rollback(prompt_name: str, alias: str, reason: str, actor: str) -> None:
    """Revert prompt alias to previous version."""
    previous_version = find_previous_version(prompt_name, alias=alias)

    if previous_version is None:
        click.echo(f"No previous version available for {prompt_name} @{alias}.")
        click.echo("Cannot roll back.")
        sys.exit(1)

    # Get current version for display
    try:
        from src.services.prompt_service import load_prompt_version

        current = load_prompt_version(prompt_name, alias=alias)
        current_version = current.version
    except Exception:
        current_version = "unknown"

    click.echo()
    click.echo(f"Rollback: {prompt_name}")
    click.echo("=" * 60)
    click.echo()
    click.echo(f"Current: @{alias} -> v{current_version}")
    click.echo(f"Rolling back to: v{previous_version}")
    click.echo()

    record = execute_rollback(
        prompt_name=prompt_name,
        alias=alias,
        previous_version=previous_version,
        reason=reason,
        actor=actor,
    )

    click.echo(f"SUCCESS: {prompt_name} @{alias} now points to v{previous_version}")
    click.echo(f'Reason: "{reason}"')
    if record.justifying_run_ids:
        click.echo(f"Audit logged on run: {', '.join(r[:8] for r in record.justifying_run_ids)}")


# ---------------------------------------------------------------------------
# US4: run-evals command
# ---------------------------------------------------------------------------


@pipeline.command("run-evals")
@click.option(
    "--suite",
    default="core",
    type=click.Choice(["core", "full"]),
    help="Eval suite to run.",
)
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show per-case details.")
@click.option(
    "--check/--no-check",
    "run_check",
    default=True,
    help="Run regression check after completion.",
)
def run_evals(suite: str, verbose: bool, run_check: bool) -> None:
    """Run eval suite (core subset or full)."""
    from eval.pipeline_config import CORE_EVAL_DATASETS, FULL_EVAL_DATASETS
    from pathlib import Path

    datasets = CORE_EVAL_DATASETS if suite == "core" else FULL_EVAL_DATASETS
    total = len(datasets)

    click.echo()
    click.echo(f"Running {suite} eval suite ({total} types)...")
    click.echo()

    def progress(i: int, total: int, dataset_path: str, result: object) -> None:
        name = Path(dataset_path).stem.replace("_golden_dataset", "").replace("golden_dataset", "quality")
        status = "PASS" if result.passed else "FAIL"  # type: ignore[union-attr]
        click.echo(f"  [{i + 1}/{total}] {name:<30} {status}")

    results = run_eval_suite(suite=suite, verbose=verbose, progress_callback=progress)

    click.echo()

    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    if failed == 0:
        click.echo(f"All {total} eval types complete.")
    else:
        click.echo(f"{passed}/{total} eval types passed. {failed} failed.")

    # Run regression check if requested
    if run_check:
        click.echo()
        reports = check_all_regressions()
        if reports:
            regressions = [r for r in reports if r.verdict == "REGRESSION"]
            improvements = [r for r in reports if r.verdict == "IMPROVED"]
            if regressions:
                click.echo(f"Regression Check: {len(regressions)} REGRESSION(s) detected.")
                for r in regressions:
                    click.echo(f"  {r.eval_type}: {r.baseline_pass_rate:.1%} -> {r.current_pass_rate:.1%}")
            else:
                msg = "No regressions detected."
                if improvements:
                    msg += f" {len(improvements)} improvement(s)."
                click.echo(f"Regression Check (vs. previous baseline): {msg}")
        else:
            click.echo("Regression Check: Not enough data for comparison.")

    # Exit code
    if failed > 0:
        sys.exit(1)
    has_regression = run_check and any(r.verdict == "REGRESSION" for r in (reports if run_check and reports else []))
    if has_regression:
        sys.exit(1)
