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
from eval.pipeline.regression import check_all_regressions
from eval.pipeline.trigger import run_eval_suite


@click.group()
def pipeline() -> None:
    """Eval Dashboard & Regression Pipeline — trend tracking and regression detection."""
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
            f"  {'Run':<20} {'Date':<22} {'Pass Rate':<12} {'Score':<8}"
        )

        for point in reversed(summary.points):  # newest first
            run_short = point.run_id[:16] if len(point.run_id) > 16 else point.run_id
            date_str = point.timestamp.strftime("%Y-%m-%d %H:%M")
            pass_rate_str = f"{point.pass_rate:.1%}"
            score_str = f"{point.average_score:.1f}"
            click.echo(
                f"  {run_short:<20} {date_str:<22} {pass_rate_str:<12} {score_str:<8}"
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
