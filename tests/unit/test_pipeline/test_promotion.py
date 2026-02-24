"""Unit tests for eval pipeline promotion gating."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from eval.pipeline.models import TrendPoint
from eval.pipeline.promotion import check_promotion_gate, execute_promotion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_point(
    run_id: str = "run1",
    pass_rate: float = 0.90,
    eval_type: str = "tone",
    hours_offset: int = 0,
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
        prompt_versions={"orchestrator-base": "v1"},
        eval_status="complete",
    )


# ---------------------------------------------------------------------------
# check_promotion_gate
# ---------------------------------------------------------------------------


class TestCheckPromotionGate:
    @patch("eval.pipeline.promotion.get_threshold")
    @patch("eval.pipeline.promotion.get_trend_points")
    @patch("eval.pipeline.promotion.get_eval_experiments")
    @patch("src.services.prompt_service.load_prompt_version")
    def test_all_pass_allowed(
        self, mock_load, mock_experiments, mock_points, mock_threshold
    ):
        mock_load.return_value = MagicMock(version=3)
        mock_experiments.return_value = [
            ("exp-tone", "tone"),
            ("exp-routing", "routing"),
        ]
        mock_threshold.return_value = 0.80

        def points_side_effect(exp_name, eval_type, limit=10):
            return [_make_point(run_id=f"{eval_type}_r1", pass_rate=0.90, eval_type=eval_type)]

        mock_points.side_effect = points_side_effect

        result = check_promotion_gate("orchestrator-base")

        assert result.allowed is True
        assert len(result.blocking_evals) == 0
        assert result.version == 3
        assert len(result.eval_results) == 2

    @patch("eval.pipeline.promotion.get_threshold")
    @patch("eval.pipeline.promotion.get_trend_points")
    @patch("eval.pipeline.promotion.get_eval_experiments")
    @patch("src.services.prompt_service.load_prompt_version")
    def test_one_fail_blocked(
        self, mock_load, mock_experiments, mock_points, mock_threshold
    ):
        mock_load.return_value = MagicMock(version=3)
        mock_experiments.return_value = [
            ("exp-tone", "tone"),
            ("exp-routing", "routing"),
        ]
        mock_threshold.return_value = 0.80

        def points_side_effect(exp_name, eval_type, limit=10):
            if eval_type == "tone":
                return [_make_point(run_id="t1", pass_rate=0.70, eval_type="tone")]
            return [_make_point(run_id="r1", pass_rate=0.90, eval_type="routing")]

        mock_points.side_effect = points_side_effect

        result = check_promotion_gate("orchestrator-base")

        assert result.allowed is False
        assert "tone" in result.blocking_evals

    @patch("eval.pipeline.promotion.get_threshold")
    @patch("eval.pipeline.promotion.get_trend_points")
    @patch("eval.pipeline.promotion.get_eval_experiments")
    @patch("src.services.prompt_service.load_prompt_version")
    def test_skips_eval_types_with_no_data(
        self, mock_load, mock_experiments, mock_points, mock_threshold
    ):
        mock_load.return_value = MagicMock(version=3)
        mock_experiments.return_value = [("exp-tone", "tone")]
        mock_threshold.return_value = 0.80
        mock_points.return_value = []  # No runs

        result = check_promotion_gate("orchestrator-base")

        assert result.allowed is True
        assert len(result.eval_results) == 0


# ---------------------------------------------------------------------------
# execute_promotion
# ---------------------------------------------------------------------------


class TestExecutePromotion:
    @patch("eval.pipeline.promotion._log_audit_tags")
    @patch("src.services.prompt_service.set_alias")
    @patch("src.services.prompt_service.load_prompt_version")
    def test_promotes_and_logs_audit(self, mock_load, mock_set_alias, mock_log_tags):
        mock_load.return_value = MagicMock(version=2)

        record = execute_promotion(
            prompt_name="orchestrator-base",
            to_alias="production",
            version=3,
            actor="cli-user",
            justifying_run_ids=["run1", "run2"],
        )

        mock_set_alias.assert_called_once_with("orchestrator-base", "production", 3)
        mock_log_tags.assert_called_once()

        assert record.action == "promote"
        assert record.prompt_name == "orchestrator-base"
        assert record.from_version == 2
        assert record.to_version == 3
        assert record.actor == "cli-user"

    @patch("eval.pipeline.promotion._log_audit_tags")
    @patch("src.services.prompt_service.set_alias")
    @patch("src.services.prompt_service.load_prompt_version")
    def test_uses_provided_from_version(self, mock_load, mock_set_alias, mock_log_tags):
        record = execute_promotion(
            prompt_name="test",
            to_alias="production",
            version=5,
            actor="dev",
            justifying_run_ids=["r1"],
            from_version=4,
        )

        assert record.from_version == 4
        # load_prompt_version should NOT be called when from_version is provided
        mock_load.assert_not_called()
