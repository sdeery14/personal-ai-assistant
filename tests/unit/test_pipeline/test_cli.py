"""Unit tests for eval pipeline CLI commands."""

from datetime import datetime, timezone
from unittest.mock import patch

from click.testing import CliRunner

from eval.pipeline.cli import pipeline
from eval.pipeline.models import (
    AuditRecord,
    PromotionEvalCheck,
    PromotionResult,
    PromptChange,
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
                prompt_versions={"orchestrator-base": f"v{i + 1}"},
                eval_status="complete",
            )
        )
    changes = []
    if num_points >= 2:
        changes.append(
            PromptChange(
                timestamp=points[1].timestamp,
                run_id=points[1].run_id,
                prompt_name="orchestrator-base",
                from_version="v1",
                to_version="v2",
            )
        )
    return TrendSummary(
        eval_type=eval_type,
        points=points,
        latest_pass_rate=latest_pass_rate,
        trend_direction=trend_direction,
        prompt_changes=changes,
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
        changed_prompts=[
            PromptChange(
                timestamp=datetime(2026, 2, 24, 12, 0, tzinfo=timezone.utc),
                run_id="current_run_id_456",
                prompt_name="orchestrator-base",
                from_version="v1",
                to_version="v2",
            ),
        ],
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
    def test_changed_prompts_displayed(self, mock_check):
        mock_check.return_value = [_make_regression_report()]

        runner = CliRunner()
        result = runner.invoke(pipeline, ["check"])

        assert "orchestrator-base" in result.output
        assert "v1 -> v2" in result.output

    @patch("eval.pipeline.cli.check_all_regressions")
    def test_no_data_message(self, mock_check):
        mock_check.return_value = []

        runner = CliRunner()
        result = runner.invoke(pipeline, ["check"])

        assert result.exit_code == 0
        assert "No eval types with sufficient data" in result.output


# ---------------------------------------------------------------------------
# promote command tests
# ---------------------------------------------------------------------------


def _make_promotion_result(allowed: bool = True) -> PromotionResult:
    checks = [
        PromotionEvalCheck(eval_type="tone", pass_rate=0.95, threshold=0.80, passed=True, run_id="run1"),
        PromotionEvalCheck(eval_type="routing", pass_rate=0.85, threshold=0.80, passed=True, run_id="run2"),
    ]
    blocking = [] if allowed else ["tone"]
    if not allowed:
        checks[0] = PromotionEvalCheck(eval_type="tone", pass_rate=0.70, threshold=0.80, passed=False, run_id="run1")
    return PromotionResult(
        allowed=allowed,
        prompt_name="orchestrator-base",
        from_alias="experiment",
        to_alias="production",
        version=3,
        eval_results=checks,
        blocking_evals=blocking,
        justifying_run_ids=["run1", "run2"],
    )


class TestPromoteCommand:
    @patch("eval.pipeline.cli.execute_promotion")
    @patch("eval.pipeline.cli.check_promotion_gate")
    def test_successful_promotion(self, mock_gate, mock_exec):
        mock_gate.return_value = _make_promotion_result(allowed=True)
        mock_exec.return_value = AuditRecord(
            action="promote",
            prompt_name="orchestrator-base",
            from_version=2,
            to_version=3,
            alias="production",
            timestamp=datetime(2026, 2, 24, tzinfo=timezone.utc),
            actor="cli-user",
            reason="All pass",
            justifying_run_ids=["run1", "run2"],
        )

        runner = CliRunner()
        result = runner.invoke(pipeline, ["promote", "orchestrator-base"])

        assert result.exit_code == 0
        assert "SUCCESS" in result.output
        assert "v3" in result.output

    @patch("eval.pipeline.cli.check_promotion_gate")
    def test_blocked_promotion(self, mock_gate):
        mock_gate.return_value = _make_promotion_result(allowed=False)

        runner = CliRunner()
        result = runner.invoke(pipeline, ["promote", "orchestrator-base"])

        assert result.exit_code == 1
        assert "BLOCKED" in result.output
        assert "tone" in result.output

    @patch("eval.pipeline.cli.execute_promotion")
    @patch("eval.pipeline.cli.check_promotion_gate")
    def test_force_flag_bypasses_gate(self, mock_gate, mock_exec):
        mock_gate.return_value = _make_promotion_result(allowed=False)
        mock_exec.return_value = AuditRecord(
            action="promote",
            prompt_name="orchestrator-base",
            from_version=2,
            to_version=3,
            alias="production",
            timestamp=datetime(2026, 2, 24, tzinfo=timezone.utc),
            actor="cli-user",
            reason="Forced",
            justifying_run_ids=["run1"],
        )

        runner = CliRunner()
        result = runner.invoke(pipeline, ["promote", "orchestrator-base", "--force"])

        assert result.exit_code == 0
        assert "WARNING" in result.output
        assert "forced" in result.output.lower()


# ---------------------------------------------------------------------------
# rollback command tests
# ---------------------------------------------------------------------------


class TestRollbackCommand:
    @patch("src.services.prompt_service.load_prompt_version")
    @patch("eval.pipeline.cli.execute_rollback")
    @patch("eval.pipeline.cli.find_previous_version")
    def test_successful_rollback(self, mock_find, mock_exec, mock_load):
        from unittest.mock import MagicMock

        mock_find.return_value = 2
        mock_load.return_value = MagicMock(version=3)
        mock_exec.return_value = AuditRecord(
            action="rollback",
            prompt_name="orchestrator-base",
            from_version=3,
            to_version=2,
            alias="production",
            timestamp=datetime(2026, 2, 24, tzinfo=timezone.utc),
            actor="cli-user",
            reason="Tone regressed",
            justifying_run_ids=["run1"],
        )

        runner = CliRunner()
        result = runner.invoke(
            pipeline,
            ["rollback", "orchestrator-base", "--reason", "Tone regressed"],
        )

        assert result.exit_code == 0
        assert "SUCCESS" in result.output
        assert "v2" in result.output

    @patch("eval.pipeline.cli.find_previous_version")
    def test_no_previous_version(self, mock_find):
        mock_find.return_value = None

        runner = CliRunner()
        result = runner.invoke(
            pipeline,
            ["rollback", "orchestrator-base", "--reason", "test"],
        )

        assert result.exit_code == 1
        assert "No previous version" in result.output


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
