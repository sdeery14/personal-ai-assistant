"""Unit tests for eval pipeline data models."""

from datetime import datetime, timezone

from eval.pipeline.models import (
    RegressionReport,
    TrendPoint,
    TrendSummary,
)


class TestTrendPoint:
    def test_construction(self):
        tp = TrendPoint(
            run_id="abc123",
            timestamp=datetime(2026, 2, 24, 10, 0, tzinfo=timezone.utc),
            experiment_name="personal-ai-assistant-eval-tone",
            eval_type="tone",
            pass_rate=0.95,
            average_score=4.2,
            total_cases=10,
            error_cases=0,
            eval_status="complete",
        )
        assert tp.run_id == "abc123"
        assert tp.eval_type == "tone"
        assert tp.pass_rate == 0.95
        assert tp.eval_status == "complete"

    def test_partial_status(self):
        tp = TrendPoint(
            run_id="def456",
            timestamp=datetime(2026, 2, 24, tzinfo=timezone.utc),
            experiment_name="test",
            eval_type="quality",
            pass_rate=0.80,
            average_score=3.5,
            total_cases=10,
            error_cases=2,
            eval_status="partial",
        )
        assert tp.eval_status == "partial"
        assert tp.error_cases == 2


class TestTrendSummary:
    def test_construction(self):
        ts = TrendSummary(
            eval_type="tone",
            points=[],
            latest_pass_rate=0.95,
            trend_direction="stable",
        )
        assert ts.eval_type == "tone"
        assert ts.trend_direction == "stable"


class TestRegressionReportVerdict:
    def test_regression_below_threshold(self):
        verdict = RegressionReport.compute_verdict(
            current_pass_rate=0.70,
            baseline_pass_rate=0.90,
            threshold=0.80,
        )
        assert verdict == "REGRESSION"

    def test_warning_large_drop_above_threshold(self):
        verdict = RegressionReport.compute_verdict(
            current_pass_rate=0.82,
            baseline_pass_rate=0.95,
            threshold=0.80,
        )
        assert verdict == "WARNING"

    def test_improved(self):
        verdict = RegressionReport.compute_verdict(
            current_pass_rate=0.95,
            baseline_pass_rate=0.85,
            threshold=0.80,
        )
        assert verdict == "IMPROVED"

    def test_pass_stable(self):
        verdict = RegressionReport.compute_verdict(
            current_pass_rate=0.90,
            baseline_pass_rate=0.90,
            threshold=0.80,
        )
        assert verdict == "PASS"

    def test_pass_minor_drop(self):
        """A drop of < 10pp that stays above threshold is PASS."""
        verdict = RegressionReport.compute_verdict(
            current_pass_rate=0.85,
            baseline_pass_rate=0.90,
            threshold=0.80,
        )
        assert verdict == "PASS"

    def test_regression_exactly_at_threshold_boundary(self):
        """Pass rate equal to threshold is not a regression."""
        verdict = RegressionReport.compute_verdict(
            current_pass_rate=0.80,
            baseline_pass_rate=0.90,
            threshold=0.80,
        )
        assert verdict == "WARNING"  # -10pp but at threshold

    def test_regression_just_below_threshold(self):
        verdict = RegressionReport.compute_verdict(
            current_pass_rate=0.79,
            baseline_pass_rate=0.90,
            threshold=0.80,
        )
        assert verdict == "REGRESSION"


class TestRegressionReport:
    def test_construction(self):
        rr = RegressionReport(
            eval_type="tone",
            baseline_run_id="base1",
            current_run_id="curr1",
            baseline_pass_rate=0.90,
            current_pass_rate=0.70,
            delta_pp=-20.0,
            threshold=0.80,
            verdict="REGRESSION",
            baseline_timestamp=datetime(2026, 2, 23, tzinfo=timezone.utc),
            current_timestamp=datetime(2026, 2, 24, tzinfo=timezone.utc),
        )
        assert rr.verdict == "REGRESSION"
        assert rr.delta_pp == -20.0
