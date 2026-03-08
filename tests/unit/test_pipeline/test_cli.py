"""Unit tests for eval pipeline CLI commands."""

from datetime import datetime, timezone
from unittest.mock import patch

from click.testing import CliRunner

from eval.pipeline.cli import pipeline
from eval.pipeline.models import (
    RegressionReport,
    TrendPoint,
    TrendSummary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_summary(
    eval_type: str = "tone",
    latest_pass_rate: float = 0.95,
    trend_direction: str = "stable",
    num_points: int = 2,
) -> TrendSummary:
    points = []
    for i in range(num_points):
        points.append(
            TrendPoint(
                run_id=f"run{i}",
                timestamp=datetime(2026, 2, 24, 10 + i, 0, tzinfo=timezone.utc),
                experiment_name=f"personal-ai-assistant-eval-{eval_type}",
                eval_type=eval_type,
                pass_rate=latest_pass_rate - 0.05 * (num_points - 1 - i),
                average_score=4.0,
                total_cases=10,
                error_cases=0,
                eval_status="complete",
            )
        )
    return TrendSummary(
        eval_type=eval_type,
        points=points,
        latest_pass_rate=latest_pass_rate,
        trend_direction=trend_direction,
    )


# ---------------------------------------------------------------------------
# trend command tests
# ---------------------------------------------------------------------------


class TestTrendCommand:
    @patch("eval.pipeline.cli.get_trend_points")
    @patch("eval.pipeline.cli.get_eval_experiments")
    def test_table_output(self, mock_experiments, mock_points):
        mock_experiments.return_value = [
            ("personal-ai-assistant-eval-tone", "tone"),
        ]
        summary = _make_summary()
        mock_points.return_value = summary.points

        runner = CliRunner()
        result = runner.invoke(pipeline, ["trend"])

        assert result.exit_code == 0
        assert "tone" in result.output
        assert "95.0%" in result.output
        # With 2 points (0.90 -> 0.95) the trend is IMPROVING
        assert "IMPROVING" in result.output

    @patch("eval.pipeline.cli.get_trend_points")
    @patch("eval.pipeline.cli.get_eval_experiments")
    def test_json_output(self, mock_experiments, mock_points):
        mock_experiments.return_value = [
            ("personal-ai-assistant-eval-tone", "tone"),
        ]
        summary = _make_summary()
        mock_points.return_value = summary.points

        runner = CliRunner()
        result = runner.invoke(pipeline, ["trend", "--format", "json"])

        assert result.exit_code == 0
        assert '"eval_type": "tone"' in result.output

    @patch("eval.pipeline.cli.get_trend_points")
    @patch("eval.pipeline.cli.get_eval_experiments")
    def test_eval_type_filter(self, mock_experiments, mock_points):
        mock_experiments.return_value = [
            ("personal-ai-assistant-eval-tone", "tone"),
            ("personal-ai-assistant-eval-routing", "routing"),
        ]
        mock_points.return_value = _make_summary(eval_type="tone").points

        runner = CliRunner()
        result = runner.invoke(pipeline, ["trend", "--eval-type", "tone"])

        assert result.exit_code == 0
        assert "tone" in result.output
        # Only called for tone, not routing
        mock_points.assert_called_once()

    @patch("eval.pipeline.cli.get_eval_experiments")
    def test_empty_state(self, mock_experiments):
        mock_experiments.return_value = []

        runner = CliRunner()
        result = runner.invoke(pipeline, ["trend"])

        assert result.exit_code == 0
        assert "No eval runs found" in result.output

    @patch("eval.pipeline.cli.get_trend_points")
    @patch("eval.pipeline.cli.get_eval_experiments")
    def test_no_data_for_eval_type(self, mock_experiments, mock_points):
        mock_experiments.return_value = [
            ("personal-ai-assistant-eval-tone", "tone"),
        ]
        mock_points.return_value = []

        runner = CliRunner()
        result = runner.invoke(pipeline, ["trend"])

        assert result.exit_code == 0
        assert "No data: tone" in result.output


# ---------------------------------------------------------------------------
# check command tests
# ---------------------------------------------------------------------------


def _make_regression_report(
    eval_type: str = "tone",
    verdict: str = "REGRESSION",
    baseline_pass_rate: float = 0.90,
    current_pass_rate: float = 0.70,
    delta_pp: float = -20.0,
) -> RegressionReport:
    return RegressionReport(
        eval_type=eval_type,
        baseline_run_id="baseline_run_id_123",
        current_run_id="current_run_id_456",
        baseline_pass_rate=baseline_pass_rate,
        current_pass_rate=current_pass_rate,
        delta_pp=delta_pp,
        threshold=0.80,
        verdict=verdict,
        baseline_timestamp=datetime(2026, 2, 24, 10, 0, tzinfo=timezone.utc),
        current_timestamp=datetime(2026, 2, 24, 12, 0, tzinfo=timezone.utc),
    )


class TestCheckCommand:
    @patch("eval.pipeline.cli.check_all_regressions")
    def test_regression_detected_exit_code_1(self, mock_check):
        mock_check.return_value = [_make_regression_report(verdict="REGRESSION")]

        runner = CliRunner()
        result = runner.invoke(pipeline, ["check"])

        assert result.exit_code == 1
        assert "REGRESSION" in result.output
        assert "REGRESSION DETECTED" in result.output

    @patch("eval.pipeline.cli.check_all_regressions")
    def test_no_regression_exit_code_0(self, mock_check):
        mock_check.return_value = [
            _make_regression_report(
                verdict="PASS",
                baseline_pass_rate=0.90,
                current_pass_rate=0.88,
                delta_pp=-2.0,
            ),
        ]

        runner = CliRunner()
        result = runner.invoke(pipeline, ["check"])

        assert result.exit_code == 0
        assert "No regressions" in result.output

    @patch("eval.pipeline.cli.check_all_regressions")
    def test_no_data_message(self, mock_check):
        mock_check.return_value = []

        runner = CliRunner()
        result = runner.invoke(pipeline, ["check"])

        assert result.exit_code == 0
        assert "No eval types with sufficient data" in result.output


# ---------------------------------------------------------------------------
# run-evals command tests
# ---------------------------------------------------------------------------


class TestRunEvalsCommand:
    @patch("eval.pipeline.cli.check_all_regressions")
    @patch("eval.pipeline.cli.run_eval_suite")
    def test_core_suite_output(self, mock_run, mock_check):
        from eval.pipeline.trigger import EvalRunResult

        mock_run.return_value = [
            EvalRunResult(dataset_path=f"eval/d{i}.json", exit_code=0, passed=True, output="ok")
            for i in range(5)
        ]
        mock_check.return_value = []

        runner = CliRunner()
        result = runner.invoke(pipeline, ["run-evals", "--suite", "core"])

        assert result.exit_code == 0
        assert "core eval suite" in result.output
        assert "All 5 eval types complete" in result.output

    @patch("eval.pipeline.cli.check_all_regressions")
    @patch("eval.pipeline.cli.run_eval_suite")
    def test_failed_eval_exit_code_1(self, mock_run, mock_check):
        from eval.pipeline.trigger import EvalRunResult

        mock_run.return_value = [
            EvalRunResult(dataset_path="eval/d1.json", exit_code=0, passed=True, output="ok"),
            EvalRunResult(dataset_path="eval/d2.json", exit_code=1, passed=False, output="fail"),
        ]
        mock_check.return_value = []

        runner = CliRunner()
        result = runner.invoke(pipeline, ["run-evals", "--suite", "core"])

        assert result.exit_code == 1
