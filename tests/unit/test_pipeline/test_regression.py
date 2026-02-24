"""Unit tests for eval pipeline regression detection."""

from datetime import datetime, timezone
from unittest.mock import patch

from eval.pipeline.models import TrendPoint
from eval.pipeline.regression import (
    check_all_regressions,
    compare_runs,
    get_baseline_run,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_point(
    run_id: str = "run1",
    pass_rate: float = 0.90,
    eval_type: str = "tone",
    hours_offset: int = 0,
    prompt_versions: dict | None = None,
    error_cases: int = 0,
) -> TrendPoint:
    return TrendPoint(
        run_id=run_id,
        timestamp=datetime(2026, 2, 24, 10 + hours_offset, 0, tzinfo=timezone.utc),
        experiment_name=f"personal-ai-assistant-eval-{eval_type}",
        eval_type=eval_type,
        pass_rate=pass_rate,
        average_score=4.0,
        total_cases=10,
        error_cases=error_cases,
        prompt_versions=prompt_versions or {"orchestrator-base": "v1"},
        eval_status="complete" if error_cases == 0 else "partial",
    )


# ---------------------------------------------------------------------------
# get_baseline_run
# ---------------------------------------------------------------------------


class TestGetBaselineRun:
    def test_returns_previous_complete_run(self):
        points = [
            _make_point(run_id="r1", hours_offset=0),
            _make_point(run_id="r2", hours_offset=1),
            _make_point(run_id="r3", hours_offset=2),
        ]
        baseline = get_baseline_run(points, current_run_id="r3")
        assert baseline is not None
        assert baseline.run_id == "r2"

    def test_skips_partial_runs(self):
        points = [
            _make_point(run_id="r1", hours_offset=0),
            _make_point(run_id="r2", hours_offset=1, error_cases=2),  # partial
            _make_point(run_id="r3", hours_offset=2),
        ]
        baseline = get_baseline_run(points, current_run_id="r3")
        assert baseline is not None
        assert baseline.run_id == "r1"

    def test_no_baseline_for_first_run(self):
        points = [
            _make_point(run_id="r1", hours_offset=0),
        ]
        baseline = get_baseline_run(points, current_run_id="r1")
        assert baseline is None

    def test_no_baseline_when_empty(self):
        baseline = get_baseline_run([], current_run_id="r1")
        assert baseline is None

    def test_default_second_to_last(self):
        points = [
            _make_point(run_id="r1", hours_offset=0),
            _make_point(run_id="r2", hours_offset=1),
            _make_point(run_id="r3", hours_offset=2),
        ]
        baseline = get_baseline_run(points)
        assert baseline is not None
        assert baseline.run_id == "r2"


# ---------------------------------------------------------------------------
# compare_runs
# ---------------------------------------------------------------------------


class TestCompareRuns:
    def test_regression_verdict(self):
        baseline = _make_point(run_id="r1", pass_rate=0.90)
        current = _make_point(run_id="r2", pass_rate=0.70, hours_offset=1)

        report = compare_runs(baseline, current, threshold=0.80)

        assert report.verdict == "REGRESSION"
        assert report.delta_pp == -20.0
        assert report.baseline_run_id == "r1"
        assert report.current_run_id == "r2"

    def test_warning_verdict(self):
        baseline = _make_point(run_id="r1", pass_rate=0.95)
        current = _make_point(run_id="r2", pass_rate=0.82, hours_offset=1)

        report = compare_runs(baseline, current, threshold=0.80)

        assert report.verdict == "WARNING"
        assert report.delta_pp == -13.0

    def test_improved_verdict(self):
        baseline = _make_point(run_id="r1", pass_rate=0.85)
        current = _make_point(run_id="r2", pass_rate=0.95, hours_offset=1)

        report = compare_runs(baseline, current, threshold=0.80)

        assert report.verdict == "IMPROVED"
        assert report.delta_pp == 10.0

    def test_pass_verdict(self):
        baseline = _make_point(run_id="r1", pass_rate=0.90)
        current = _make_point(run_id="r2", pass_rate=0.88, hours_offset=1)

        report = compare_runs(baseline, current, threshold=0.80)

        assert report.verdict == "PASS"

    def test_detects_changed_prompts(self):
        baseline = _make_point(
            run_id="r1",
            prompt_versions={"orchestrator-base": "v1", "onboarding": "v1"},
        )
        current = _make_point(
            run_id="r2",
            hours_offset=1,
            prompt_versions={"orchestrator-base": "v2", "onboarding": "v1"},
        )

        report = compare_runs(baseline, current, threshold=0.80)

        assert len(report.changed_prompts) == 1
        assert report.changed_prompts[0].prompt_name == "orchestrator-base"
        assert report.changed_prompts[0].from_version == "v1"
        assert report.changed_prompts[0].to_version == "v2"

    def test_detects_multiple_prompt_changes_simultaneously(self):
        baseline = _make_point(
            run_id="r1",
            prompt_versions={"orchestrator-base": "v1", "onboarding": "v1", "guardrails": "v2"},
        )
        current = _make_point(
            run_id="r2",
            hours_offset=1,
            prompt_versions={"orchestrator-base": "v2", "onboarding": "v3", "guardrails": "v2"},
        )

        report = compare_runs(baseline, current, threshold=0.80)

        assert len(report.changed_prompts) == 2
        names = [c.prompt_name for c in report.changed_prompts]
        assert "onboarding" in names
        assert "orchestrator-base" in names


# ---------------------------------------------------------------------------
# check_all_regressions
# ---------------------------------------------------------------------------


class TestCheckAllRegressions:
    @patch("eval.pipeline.regression.get_threshold")
    @patch("eval.pipeline.regression.get_trend_points")
    @patch("eval.pipeline.regression.get_eval_experiments")
    def test_returns_reports_for_experiments_with_data(
        self, mock_experiments, mock_points, mock_threshold
    ):
        mock_experiments.return_value = [
            ("exp-tone", "tone"),
            ("exp-routing", "routing"),
        ]
        mock_threshold.return_value = 0.80

        tone_points = [
            _make_point(run_id="t1", pass_rate=0.90, eval_type="tone", hours_offset=0),
            _make_point(run_id="t2", pass_rate=0.85, eval_type="tone", hours_offset=1),
        ]
        routing_points = [
            _make_point(run_id="r1", pass_rate=0.80, eval_type="routing", hours_offset=0),
            _make_point(run_id="r2", pass_rate=0.90, eval_type="routing", hours_offset=1),
        ]

        def points_side_effect(exp_name, eval_type, limit=50):
            if eval_type == "tone":
                return tone_points
            return routing_points

        mock_points.side_effect = points_side_effect

        reports = check_all_regressions()

        assert len(reports) == 2
        eval_types = [r.eval_type for r in reports]
        assert "tone" in eval_types
        assert "routing" in eval_types

    @patch("eval.pipeline.regression.get_threshold")
    @patch("eval.pipeline.regression.get_trend_points")
    @patch("eval.pipeline.regression.get_eval_experiments")
    def test_skips_experiments_with_single_run(
        self, mock_experiments, mock_points, mock_threshold
    ):
        mock_experiments.return_value = [("exp-tone", "tone")]
        mock_threshold.return_value = 0.80
        mock_points.return_value = [
            _make_point(run_id="t1", pass_rate=0.90, eval_type="tone"),
        ]

        reports = check_all_regressions()
        assert len(reports) == 0

    @patch("eval.pipeline.regression.get_threshold")
    @patch("eval.pipeline.regression.get_trend_points")
    @patch("eval.pipeline.regression.get_eval_experiments")
    def test_filters_by_eval_type(
        self, mock_experiments, mock_points, mock_threshold
    ):
        mock_experiments.return_value = [
            ("exp-tone", "tone"),
            ("exp-routing", "routing"),
        ]
        mock_threshold.return_value = 0.80
        mock_points.return_value = [
            _make_point(run_id="t1", pass_rate=0.90, eval_type="tone", hours_offset=0),
            _make_point(run_id="t2", pass_rate=0.85, eval_type="tone", hours_offset=1),
        ]

        reports = check_all_regressions(eval_type_filter="tone")

        # Should only have checked tone
        assert mock_points.call_count == 1
