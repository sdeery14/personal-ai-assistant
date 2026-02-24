"""Unit tests for eval pipeline rollback."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from eval.pipeline.models import TrendPoint
from eval.pipeline.rollback import execute_rollback, find_previous_version


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_point(
    run_id: str = "run1",
    pass_rate: float = 0.90,
    eval_type: str = "tone",
    hours_offset: int = 0,
    prompt_versions: dict | None = None,
) -> TrendPoint:
    return TrendPoint(
        run_id=run_id,
        timestamp=datetime(2026, 2, 24, 10 + hours_offset, 0, tzinfo=timezone.utc),
        experiment_name=f"personal-ai-assistant-eval-{eval_type}",
        eval_type=eval_type,
        pass_rate=pass_rate,
        average_score=4.0,
        total_cases=10,
        error_cases=0,
        prompt_versions=prompt_versions or {"orchestrator-base": "v1"},
        eval_status="complete",
    )


# ---------------------------------------------------------------------------
# find_previous_version
# ---------------------------------------------------------------------------


class TestFindPreviousVersion:
    @patch("eval.pipeline.rollback.get_trend_points")
    @patch("eval.pipeline.rollback.get_eval_experiments")
    @patch("src.services.prompt_service.load_prompt_version")
    def test_finds_previous_version_from_eval_history(
        self, mock_load, mock_experiments, mock_points
    ):
        mock_load.return_value = MagicMock(version=3)
        mock_experiments.return_value = [("exp-tone", "tone")]
        mock_points.return_value = [
            _make_point(run_id="r1", hours_offset=0, prompt_versions={"orchestrator-base": "v2"}),
            _make_point(run_id="r2", hours_offset=1, prompt_versions={"orchestrator-base": "v3"}),
        ]

        result = find_previous_version("orchestrator-base")
        assert result == 2

    @patch("eval.pipeline.rollback.get_trend_points")
    @patch("eval.pipeline.rollback.get_eval_experiments")
    @patch("src.services.prompt_service.load_prompt_version")
    def test_returns_none_for_version_1(
        self, mock_load, mock_experiments, mock_points
    ):
        mock_load.return_value = MagicMock(version=1)

        result = find_previous_version("orchestrator-base")
        assert result is None

    @patch("eval.pipeline.rollback.get_trend_points")
    @patch("eval.pipeline.rollback.get_eval_experiments")
    @patch("src.services.prompt_service.load_prompt_version")
    def test_falls_back_to_current_minus_1(
        self, mock_load, mock_experiments, mock_points
    ):
        mock_load.return_value = MagicMock(version=5)
        mock_experiments.return_value = [("exp-tone", "tone")]
        # No matching prompt in eval history — use a key that won't match
        mock_points.return_value = [
            _make_point(run_id="r1", prompt_versions={"other-prompt": "v1"}),
        ]

        result = find_previous_version("orchestrator-base")
        assert result == 4


# ---------------------------------------------------------------------------
# execute_rollback
# ---------------------------------------------------------------------------


class TestExecuteRollback:
    @patch("eval.pipeline.rollback._log_audit_tags")
    @patch("eval.pipeline.rollback._find_recent_run_ids")
    @patch("src.services.prompt_service.set_alias")
    @patch("src.services.prompt_service.load_prompt_version")
    def test_executes_rollback_and_logs_audit(
        self, mock_load, mock_set_alias, mock_find_runs, mock_log_tags
    ):
        mock_load.return_value = MagicMock(version=3)
        mock_find_runs.return_value = ["run1"]

        record = execute_rollback(
            prompt_name="orchestrator-base",
            alias="production",
            previous_version=2,
            reason="Tone eval regressed",
            actor="developer",
        )

        mock_set_alias.assert_called_once_with("orchestrator-base", "production", 2)
        mock_log_tags.assert_called_once()

        assert record.action == "rollback"
        assert record.prompt_name == "orchestrator-base"
        assert record.from_version == 3
        assert record.to_version == 2
        assert record.reason == "Tone eval regressed"
        assert record.actor == "developer"
