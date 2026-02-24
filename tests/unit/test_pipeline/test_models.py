"""Unit tests for eval pipeline data models."""

from datetime import datetime, timezone

from eval.pipeline.models import (
    AuditRecord,
    PromotionEvalCheck,
    PromotionResult,
    PromptChange,
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
            prompt_versions={"orchestrator-base": "v2"},
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
            prompt_versions={},
            eval_status="partial",
        )
        assert tp.eval_status == "partial"
        assert tp.error_cases == 2


class TestPromptChange:
    def test_construction(self):
        pc = PromptChange(
            timestamp=datetime(2026, 2, 24, tzinfo=timezone.utc),
            run_id="abc123",
            prompt_name="orchestrator-base",
            from_version="v1",
            to_version="v2",
        )
        assert pc.prompt_name == "orchestrator-base"
        assert pc.from_version == "v1"
        assert pc.to_version == "v2"


class TestTrendSummary:
    def test_construction(self):
        ts = TrendSummary(
            eval_type="tone",
            points=[],
            latest_pass_rate=0.95,
            trend_direction="stable",
            prompt_changes=[],
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
            changed_prompts=[],
            baseline_timestamp=datetime(2026, 2, 23, tzinfo=timezone.utc),
            current_timestamp=datetime(2026, 2, 24, tzinfo=timezone.utc),
        )
        assert rr.verdict == "REGRESSION"
        assert rr.delta_pp == -20.0


class TestPromotionResult:
    def test_allowed(self):
        result = PromotionResult(
            allowed=True,
            prompt_name="orchestrator-base",
            from_alias="experiment",
            to_alias="production",
            version=3,
            eval_results=[
                PromotionEvalCheck(
                    eval_type="tone",
                    pass_rate=0.95,
                    threshold=0.80,
                    passed=True,
                    run_id="run1",
                ),
            ],
            blocking_evals=[],
            justifying_run_ids=["run1"],
        )
        assert result.allowed is True
        assert len(result.blocking_evals) == 0

    def test_blocked(self):
        result = PromotionResult(
            allowed=False,
            prompt_name="orchestrator-base",
            from_alias="experiment",
            to_alias="production",
            version=3,
            eval_results=[
                PromotionEvalCheck(
                    eval_type="tone",
                    pass_rate=0.70,
                    threshold=0.80,
                    passed=False,
                    run_id="run1",
                ),
            ],
            blocking_evals=["tone"],
            justifying_run_ids=["run1"],
        )
        assert result.allowed is False
        assert "tone" in result.blocking_evals


class TestAuditRecord:
    def test_to_tags(self):
        record = AuditRecord(
            action="promote",
            prompt_name="orchestrator-base",
            from_version=2,
            to_version=3,
            alias="production",
            timestamp=datetime(2026, 2, 24, 12, 0, 0, tzinfo=timezone.utc),
            actor="cli-user",
            reason="All evals pass",
            justifying_run_ids=["run1", "run2"],
        )
        tags = record.to_tags()
        assert tags["audit.action"] == "promote"
        assert tags["audit.prompt_name"] == "orchestrator-base"
        assert tags["audit.from_version"] == "2"
        assert tags["audit.to_version"] == "3"
        assert tags["audit.alias"] == "production"
        assert tags["audit.actor"] == "cli-user"
        assert "2026-02-24" in tags["audit.timestamp"]

    def test_rollback_tags(self):
        record = AuditRecord(
            action="rollback",
            prompt_name="onboarding",
            from_version=3,
            to_version=2,
            alias="production",
            timestamp=datetime(2026, 2, 24, tzinfo=timezone.utc),
            actor="developer",
            reason="Tone eval regressed",
        )
        tags = record.to_tags()
        assert tags["audit.action"] == "rollback"
        assert tags["audit.reason"] == "Tone eval regressed"
