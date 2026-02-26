"""Unit tests for eval pipeline aggregator."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from eval.pipeline.aggregator import (
    build_trend_summary,
    get_eval_experiments,
    get_trend_points,
)
from eval.pipeline.models import TrendPoint


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_point(
    run_id: str = "run1",
    pass_rate: float = 0.90,
    average_score: float = 4.0,
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
        average_score=average_score,
        total_cases=10,
        error_cases=error_cases,
        prompt_versions=prompt_versions or {"orchestrator-base": "v1"},
        eval_status="complete" if error_cases == 0 else "partial",
    )


def _make_runs_df(rows: list[dict]) -> pd.DataFrame:
    """Create a DataFrame mimicking mlflow.search_runs output."""
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# get_eval_experiments
# ---------------------------------------------------------------------------


class TestGetEvalExperiments:
    @patch("eval.pipeline.aggregator.get_base_experiment_name")
    @patch("eval.pipeline.aggregator.mlflow")
    def test_discovers_experiments(self, mock_mlflow, mock_base_name):
        mock_base_name.return_value = "personal-ai-assistant-eval"

        exp1 = MagicMock()
        exp1.name = "personal-ai-assistant-eval"
        exp2 = MagicMock()
        exp2.name = "personal-ai-assistant-eval-tone"
        exp3 = MagicMock()
        exp3.name = "personal-ai-assistant-eval-routing"
        exp_other = MagicMock()
        exp_other.name = "unrelated-experiment"

        mock_mlflow.search_experiments.return_value = [exp1, exp2, exp3, exp_other]

        result = get_eval_experiments()

        assert len(result) == 3
        eval_types = [etype for _, etype in result]
        assert "quality" in eval_types
        assert "tone" in eval_types
        assert "routing" in eval_types

    @patch("eval.pipeline.aggregator.get_base_experiment_name")
    @patch("eval.pipeline.aggregator.mlflow")
    def test_empty_when_no_experiments(self, mock_mlflow, mock_base_name):
        mock_base_name.return_value = "personal-ai-assistant-eval"
        mock_mlflow.search_experiments.return_value = []
        result = get_eval_experiments()
        assert result == []

    @patch("eval.pipeline.aggregator.get_base_experiment_name")
    @patch("eval.pipeline.aggregator.mlflow")
    def test_handles_mlflow_error(self, mock_mlflow, mock_base_name):
        mock_base_name.return_value = "personal-ai-assistant-eval"
        mock_mlflow.search_experiments.side_effect = Exception("connection error")
        result = get_eval_experiments()
        assert result == []


# ---------------------------------------------------------------------------
# get_trend_points
# ---------------------------------------------------------------------------


class TestGetTrendPoints:
    @patch("eval.pipeline.aggregator.mlflow")
    def test_returns_sorted_points_quality(self, mock_mlflow):
        """Quality eval uses metrics.pass_rate directly."""
        df = _make_runs_df([
            {
                "run_id": "run2",
                "start_time": pd.Timestamp("2026-02-24 12:00:00", tz="UTC"),
                "status": "FINISHED",
                "metrics.pass_rate": 0.90,
                "metrics.average_score": 4.0,
                "metrics.total_cases": 10,
                "metrics.error_cases": 0,
                "params.prompt.orchestrator-base": "v2",
            },
            {
                "run_id": "run1",
                "start_time": pd.Timestamp("2026-02-24 10:00:00", tz="UTC"),
                "status": "FINISHED",
                "metrics.pass_rate": 0.85,
                "metrics.average_score": 3.8,
                "metrics.total_cases": 10,
                "metrics.error_cases": 0,
                "params.prompt.orchestrator-base": "v1",
            },
        ])
        mock_mlflow.search_runs.return_value = df

        points = get_trend_points("personal-ai-assistant-eval", "quality", limit=10)

        assert len(points) == 2
        assert points[0].run_id == "run1"  # older first
        assert points[1].run_id == "run2"  # newer second
        assert points[0].pass_rate == 0.85
        assert points[1].pass_rate == 0.90

    @patch("eval.pipeline.aggregator.mlflow")
    def test_returns_sorted_points_tone(self, mock_mlflow):
        """Tone eval uses metrics.tone_quality_pass_rate (prefixed metric)."""
        df = _make_runs_df([
            {
                "run_id": "run2",
                "start_time": pd.Timestamp("2026-02-24 12:00:00", tz="UTC"),
                "status": "FINISHED",
                "metrics.tone_quality_pass_rate": 0.90,
                "metrics.tone_error_cases": 0,
                "params.total_cases": 10,
                "params.prompt.orchestrator-base": "v2",
            },
            {
                "run_id": "run1",
                "start_time": pd.Timestamp("2026-02-24 10:00:00", tz="UTC"),
                "status": "FINISHED",
                "metrics.tone_quality_pass_rate": 0.85,
                "metrics.tone_error_cases": 0,
                "params.total_cases": 10,
                "params.prompt.orchestrator-base": "v1",
            },
        ])
        mock_mlflow.search_runs.return_value = df

        points = get_trend_points("personal-ai-assistant-eval-tone", "tone", limit=10)

        assert len(points) == 2
        assert points[0].run_id == "run1"
        assert points[1].run_id == "run2"
        assert points[0].pass_rate == 0.85
        assert points[1].pass_rate == 0.90

    @patch("eval.pipeline.aggregator.mlflow")
    def test_reads_memory_metrics(self, mock_mlflow):
        """Memory eval uses memory_recall_at_5 as its pass rate."""
        df = _make_runs_df([
            {
                "run_id": "run1",
                "start_time": pd.Timestamp("2026-02-24 10:00:00", tz="UTC"),
                "status": "FINISHED",
                "metrics.memory_recall_at_5": 0.92,
                "metrics.memory_error_cases": 1,
                "params.total_cases": 8,
            },
        ])
        mock_mlflow.search_runs.return_value = df

        points = get_trend_points("test", "memory")
        assert points[0].pass_rate == 0.92
        assert points[0].total_cases == 8
        assert points[0].error_cases == 1

    @patch("eval.pipeline.aggregator.mlflow")
    def test_reads_weather_metrics(self, mock_mlflow):
        """Weather eval uses weather_success_rate as its pass rate."""
        df = _make_runs_df([
            {
                "run_id": "run1",
                "start_time": pd.Timestamp("2026-02-24 10:00:00", tz="UTC"),
                "status": "FINISHED",
                "metrics.weather_success_rate": 0.75,
                "metrics.weather_error_cases": 2,
                "params.total_cases": 10,
            },
        ])
        mock_mlflow.search_runs.return_value = df

        points = get_trend_points("test", "weather")
        assert points[0].pass_rate == 0.75
        assert points[0].error_cases == 2

    @patch("eval.pipeline.aggregator.mlflow")
    def test_extracts_prompt_versions(self, mock_mlflow):
        df = _make_runs_df([
            {
                "run_id": "run1",
                "start_time": pd.Timestamp("2026-02-24 10:00:00", tz="UTC"),
                "status": "FINISHED",
                "metrics.tone_quality_pass_rate": 0.90,
                "metrics.tone_error_cases": 0,
                "params.total_cases": 10,
                "params.prompt.orchestrator-base": "v2",
                "params.prompt.onboarding": "v1",
            },
        ])
        mock_mlflow.search_runs.return_value = df

        points = get_trend_points("test", "tone")
        assert points[0].prompt_versions == {
            "orchestrator-base": "v2",
            "onboarding": "v1",
        }

    @patch("eval.pipeline.aggregator.mlflow")
    def test_computes_eval_status_complete(self, mock_mlflow):
        df = _make_runs_df([
            {
                "run_id": "run1",
                "start_time": pd.Timestamp("2026-02-24 10:00:00", tz="UTC"),
                "status": "FINISHED",
                "metrics.tone_quality_pass_rate": 0.90,
                "metrics.tone_error_cases": 0,
                "params.total_cases": 10,
            },
        ])
        mock_mlflow.search_runs.return_value = df
        points = get_trend_points("test", "tone")
        assert points[0].eval_status == "complete"

    @patch("eval.pipeline.aggregator.mlflow")
    def test_computes_eval_status_partial(self, mock_mlflow):
        df = _make_runs_df([
            {
                "run_id": "run1",
                "start_time": pd.Timestamp("2026-02-24 10:00:00", tz="UTC"),
                "status": "FINISHED",
                "metrics.tone_quality_pass_rate": 0.80,
                "metrics.tone_error_cases": 2,
                "params.total_cases": 10,
            },
        ])
        mock_mlflow.search_runs.return_value = df
        points = get_trend_points("test", "tone")
        assert points[0].eval_status == "partial"

    @patch("eval.pipeline.aggregator.mlflow")
    def test_empty_dataframe(self, mock_mlflow):
        mock_mlflow.search_runs.return_value = pd.DataFrame()
        points = get_trend_points("test", "tone")
        assert points == []

    @patch("eval.pipeline.aggregator.mlflow")
    def test_handles_mlflow_error(self, mock_mlflow):
        mock_mlflow.search_runs.side_effect = Exception("connection error")
        points = get_trend_points("test", "tone")
        assert points == []

    @patch("eval.pipeline.aggregator.mlflow")
    def test_unknown_eval_type_falls_back_to_default(self, mock_mlflow):
        """Unknown eval types fall back to metrics.pass_rate (quality pattern)."""
        df = _make_runs_df([
            {
                "run_id": "run1",
                "start_time": pd.Timestamp("2026-02-24 10:00:00", tz="UTC"),
                "status": "FINISHED",
                "metrics.pass_rate": 0.77,
                "metrics.average_score": 3.5,
                "metrics.total_cases": 5,
                "metrics.error_cases": 0,
            },
        ])
        mock_mlflow.search_runs.return_value = df
        points = get_trend_points("test", "some-future-eval")
        assert points[0].pass_rate == 0.77
        assert points[0].average_score == 3.5


# ---------------------------------------------------------------------------
# build_trend_summary
# ---------------------------------------------------------------------------


class TestBuildTrendSummary:
    def test_empty_points(self):
        summary = build_trend_summary("tone", [])
        assert summary.eval_type == "tone"
        assert summary.latest_pass_rate == 0.0
        assert summary.trend_direction == "stable"
        assert summary.prompt_changes == []

    def test_improving_trend(self):
        points = [
            _make_point(run_id="r1", pass_rate=0.80, hours_offset=0),
            _make_point(run_id="r2", pass_rate=0.85, hours_offset=1),
            _make_point(run_id="r3", pass_rate=0.95, hours_offset=2),
        ]
        summary = build_trend_summary("tone", points)
        assert summary.trend_direction == "improving"
        assert summary.latest_pass_rate == 0.95

    def test_degrading_trend(self):
        points = [
            _make_point(run_id="r1", pass_rate=0.95, hours_offset=0),
            _make_point(run_id="r2", pass_rate=0.90, hours_offset=1),
            _make_point(run_id="r3", pass_rate=0.80, hours_offset=2),
        ]
        summary = build_trend_summary("tone", points)
        assert summary.trend_direction == "degrading"

    def test_stable_trend(self):
        points = [
            _make_point(run_id="r1", pass_rate=0.90, hours_offset=0),
            _make_point(run_id="r2", pass_rate=0.90, hours_offset=1),
            _make_point(run_id="r3", pass_rate=0.90, hours_offset=2),
        ]
        summary = build_trend_summary("tone", points)
        assert summary.trend_direction == "stable"

    def test_detects_prompt_changes(self):
        points = [
            _make_point(
                run_id="r1",
                hours_offset=0,
                prompt_versions={"orchestrator-base": "v1"},
            ),
            _make_point(
                run_id="r2",
                hours_offset=1,
                prompt_versions={"orchestrator-base": "v2"},
            ),
        ]
        summary = build_trend_summary("tone", points)
        assert len(summary.prompt_changes) == 1
        assert summary.prompt_changes[0].prompt_name == "orchestrator-base"
        assert summary.prompt_changes[0].from_version == "v1"
        assert summary.prompt_changes[0].to_version == "v2"

    def test_no_prompt_changes_when_versions_stable(self):
        points = [
            _make_point(
                run_id="r1",
                hours_offset=0,
                prompt_versions={"orchestrator-base": "v1"},
            ),
            _make_point(
                run_id="r2",
                hours_offset=1,
                prompt_versions={"orchestrator-base": "v1"},
            ),
        ]
        summary = build_trend_summary("tone", points)
        assert summary.prompt_changes == []

    def test_single_point(self):
        points = [_make_point(run_id="r1", pass_rate=0.90)]
        summary = build_trend_summary("tone", points)
        assert summary.latest_pass_rate == 0.90
        assert summary.trend_direction == "stable"
