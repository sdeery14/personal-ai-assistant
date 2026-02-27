"""Unit tests for eval pipeline aggregator."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from eval.pipeline.aggregator import (
    _build_extra,
    _extract_case_id_from_session,
    _extract_primary_assessment,
    _parse_session_traces,
    _parse_single_turn_traces,
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


def _make_assessment(name: str, value, rationale: str | None = None, source_type: str = "LLM_JUDGE"):
    """Create a mock assessment object."""
    assessment = MagicMock()
    assessment.name = name
    assessment.value = value
    assessment.rationale = rationale
    assessment.feedback = None
    assessment.expectation = None
    source = MagicMock()
    source.source_type = source_type
    assessment.source = source
    return assessment


def _make_trace(
    request: dict | str | None = None,
    response: dict | str | None = None,
    assessments: list | None = None,
    execution_time_ms: int | None = 150,
    trace_metadata: dict | None = None,
    request_time: int = 1708776000000,
):
    """Create a mock trace object."""
    trace = MagicMock()
    trace.info.assessments = assessments or []
    trace.info.execution_time_ms = execution_time_ms
    trace.info.execution_duration = execution_time_ms
    trace.info.trace_metadata = trace_metadata or {}
    trace.info.request_metadata = trace_metadata or {}
    trace.info.request_time = request_time
    trace.info.timestamp_ms = request_time

    if request is not None:
        trace.data.request = json.dumps(request) if isinstance(request, dict) else request
    else:
        trace.data.request = None

    if response is not None:
        trace.data.response = json.dumps(response) if isinstance(response, dict) else response
    else:
        trace.data.response = None

    return trace


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


# ---------------------------------------------------------------------------
# _extract_primary_assessment
# ---------------------------------------------------------------------------


class TestExtractPrimaryAssessment:
    """Tests for extracting rating/score/passed/justification from assessments."""

    def test_string_value_excellent(self):
        assessments = [_make_assessment("quality", "excellent", "Great response")]
        rating, score, passed, justification = _extract_primary_assessment(assessments, "quality")
        assert rating == "excellent"
        assert score == 5.0
        assert passed is True
        assert justification == "Great response"

    def test_string_value_poor(self):
        assessments = [_make_assessment("quality", "poor", "Bad response")]
        rating, score, passed, justification = _extract_primary_assessment(assessments, "quality")
        assert rating == "poor"
        assert score == 1.0
        assert passed is False

    def test_string_value_adequate(self):
        assessments = [_make_assessment("quality", "adequate")]
        rating, score, passed, justification = _extract_primary_assessment(assessments, "quality")
        assert rating == "adequate"
        assert score == 3.0
        assert passed is True

    def test_string_value_case_insensitive(self):
        assessments = [_make_assessment("quality", " Good ")]
        rating, score, passed, justification = _extract_primary_assessment(assessments, "quality")
        assert rating == "good"
        assert score == 4.0

    def test_boolean_value_true(self):
        assessments = [_make_assessment("weather_behavior_scorer", True, "Correct tool call")]
        rating, score, passed, justification = _extract_primary_assessment(assessments, "weather_behavior_scorer")
        assert rating is None
        assert score == 1.0
        assert passed is True
        assert justification == "Correct tool call"

    def test_boolean_value_false(self):
        assessments = [_make_assessment("weather_behavior_scorer", False)]
        rating, score, passed, justification = _extract_primary_assessment(assessments, "weather_behavior_scorer")
        assert score == 0.0
        assert passed is False

    def test_numeric_value(self):
        assessments = [_make_assessment("memory_retrieval", 0.85, "recall=0.85")]
        rating, score, passed, justification = _extract_primary_assessment(assessments, "memory_retrieval")
        assert score == 0.85
        assert passed is False  # 0.85 < 3.0 threshold
        assert justification == "recall=0.85"

    def test_numeric_value_matching_rating_threshold(self):
        assessments = [_make_assessment("quality", 5.0)]
        rating, score, passed, justification = _extract_primary_assessment(assessments, "quality")
        assert rating == "excellent"
        assert score == 5.0
        assert passed is True

    def test_no_matching_assessment(self):
        assessments = [_make_assessment("rubric", "some value")]
        rating, score, passed, justification = _extract_primary_assessment(assessments, "quality")
        assert rating is None
        assert score is None
        assert passed is None
        assert justification is None

    def test_empty_assessments(self):
        rating, score, passed, justification = _extract_primary_assessment([], "quality")
        assert rating is None
        assert score is None
        assert passed is None
        assert justification is None

    def test_skips_non_primary_assessments(self):
        assessments = [
            _make_assessment("rubric", "test rubric"),
            _make_assessment("tone_quality", "excellent", "Warm and friendly"),
        ]
        rating, score, passed, justification = _extract_primary_assessment(assessments, "tone_quality")
        assert rating == "excellent"
        assert justification == "Warm and friendly"


# ---------------------------------------------------------------------------
# _build_extra
# ---------------------------------------------------------------------------


class TestBuildExtra:
    """Tests for building the extra dict from non-primary assessments."""

    def test_excludes_primary_scorer(self):
        assessments = [
            _make_assessment("quality", "excellent", "Great"),
            _make_assessment("rubric", "test rubric", "Human annotation"),
        ]
        extra = _build_extra(assessments, "quality")
        assert "quality" not in extra
        assert "rubric" in extra

    def test_includes_rationale_when_present(self):
        assessments = [_make_assessment("rubric", "test rubric", "Human annotation")]
        extra = _build_extra(assessments, "quality")
        assert extra["rubric"] == {"value": "test rubric", "rationale": "Human annotation"}

    def test_value_only_when_no_rationale(self):
        assessments = [_make_assessment("rubric", "test rubric", None)]
        extra = _build_extra(assessments, "quality")
        assert extra["rubric"] == "test rubric"

    def test_empty_assessments(self):
        extra = _build_extra([], "quality")
        assert extra == {}

    def test_multiple_non_primary(self):
        assessments = [
            _make_assessment("quality", "good"),  # primary — excluded
            _make_assessment("rubric", "criteria text"),
            _make_assessment("entity_recall_scorer", 0.9, "High recall"),
        ]
        extra = _build_extra(assessments, "quality")
        assert len(extra) == 2
        assert extra["rubric"] == "criteria text"
        assert extra["entity_recall_scorer"] == {"value": 0.9, "rationale": "High recall"}

    def test_assessment_with_expectation_value(self):
        """Expectation assessments store value in .expectation.value."""
        assessment = MagicMock()
        assessment.name = "expected_answer"
        assessment.value = None
        assessment.feedback = None
        exp = MagicMock()
        exp.value = "The capital of France is Paris."
        assessment.expectation = exp
        assessment.rationale = None

        extra = _build_extra([assessment], "quality")
        assert extra["expected_answer"] == "The capital of France is Paris."


# ---------------------------------------------------------------------------
# _parse_single_turn_traces
# ---------------------------------------------------------------------------


class TestParseSingleTurnTraces:
    """Tests for parsing single-turn traces into RunCaseResult objects."""

    def test_basic_trace_parsing(self):
        traces = [
            _make_trace(
                request={"question": "What is 2+2?"},
                response={"response": "4"},
                assessments=[_make_assessment("quality", "excellent", "Perfect answer")],
                execution_time_ms=200,
            ),
        ]
        results = _parse_single_turn_traces(traces, "quality")
        assert len(results) == 1
        r = results[0]
        assert r.case_id == "case_0"
        assert r.user_prompt == "What is 2+2?"
        assert r.assistant_response == "4"
        assert r.rating == "excellent"
        assert r.score == 5.0
        assert r.passed is True
        assert r.justification == "Perfect answer"
        assert r.duration_ms == 200

    def test_query_key_in_request(self):
        traces = [
            _make_trace(
                request={"query": "search term"},
                response={"response": "result"},
                assessments=[],
            ),
        ]
        results = _parse_single_turn_traces(traces, "quality")
        assert results[0].user_prompt == "search term"

    def test_user_message_key_in_request(self):
        traces = [
            _make_trace(
                request={"user_message": "hello"},
                response={"response": "hi"},
                assessments=[],
            ),
        ]
        results = _parse_single_turn_traces(traces, "quality")
        assert results[0].user_prompt == "hello"

    def test_plain_string_response(self):
        traces = [
            _make_trace(
                request={"question": "test"},
                response='"just a string"',
                assessments=[],
            ),
        ]
        results = _parse_single_turn_traces(traces, "quality")
        assert results[0].assistant_response == "just a string"

    def test_no_assessments(self):
        traces = [
            _make_trace(
                request={"question": "test"},
                response={"response": "answer"},
                assessments=[],
            ),
        ]
        results = _parse_single_turn_traces(traces, "quality")
        r = results[0]
        assert r.rating is None
        assert r.score is None
        assert r.passed is None
        assert r.justification is None

    def test_extra_from_non_primary_assessments(self):
        traces = [
            _make_trace(
                request={"question": "test"},
                response={"response": "answer"},
                assessments=[
                    _make_assessment("quality", "good", "Nice"),
                    _make_assessment("rubric", "Be helpful", "Human label"),
                ],
            ),
        ]
        results = _parse_single_turn_traces(traces, "quality")
        assert "rubric" in results[0].extra
        assert results[0].extra["rubric"] == {"value": "Be helpful", "rationale": "Human label"}

    def test_multiple_traces(self):
        traces = [
            _make_trace(
                request={"question": "Q1"},
                response={"response": "A1"},
                assessments=[_make_assessment("quality", "good")],
            ),
            _make_trace(
                request={"question": "Q2"},
                response={"response": "A2"},
                assessments=[_make_assessment("quality", "poor")],
            ),
        ]
        results = _parse_single_turn_traces(traces, "quality")
        assert len(results) == 2
        assert results[0].case_id == "case_0"
        assert results[1].case_id == "case_1"
        assert results[0].user_prompt == "Q1"
        assert results[1].user_prompt == "Q2"

    def test_null_request_response(self):
        traces = [
            _make_trace(request=None, response=None, assessments=[]),
        ]
        results = _parse_single_turn_traces(traces, "quality")
        assert results[0].user_prompt == ""
        assert results[0].assistant_response == ""

    def test_null_execution_time(self):
        traces = [
            _make_trace(
                request={"question": "test"},
                response={"response": "answer"},
                assessments=[],
                execution_time_ms=None,
            ),
        ]
        results = _parse_single_turn_traces(traces, "quality")
        assert results[0].duration_ms is None


# ---------------------------------------------------------------------------
# _parse_session_traces
# ---------------------------------------------------------------------------


class TestParseSessionTraces:
    """Tests for parsing session-grouped traces into RunCaseResult objects."""

    def test_groups_by_session(self):
        traces = [
            _make_trace(
                request={"user_message": "Hello"},
                response='"Hi there!"',
                assessments=[],
                trace_metadata={"mlflow.trace.session": "sess-abc123-greeting"},
                request_time=1000,
            ),
            _make_trace(
                request={"user_message": "How are you?"},
                response='"I am fine"',
                assessments=[_make_assessment("quality", "good", "Friendly")],
                trace_metadata={"mlflow.trace.session": "sess-abc123-greeting"},
                request_time=2000,
            ),
        ]
        results = _parse_session_traces(traces, "run1", "quality")
        assert len(results) == 1
        r = results[0]
        assert r.rating == "good"
        assert r.justification == "Friendly"
        assert "conversation_transcript" in r.extra
        assert len(r.extra["conversation_transcript"]) == 4  # 2 user + 2 assistant

    def test_multiple_sessions(self):
        traces = [
            _make_trace(
                request={"user_message": "Msg A"},
                response='"Reply A"',
                assessments=[_make_assessment("quality", "excellent")],
                trace_metadata={"mlflow.trace.session": "sess-aaa-case1"},
                request_time=1000,
            ),
            _make_trace(
                request={"user_message": "Msg B"},
                response='"Reply B"',
                assessments=[_make_assessment("quality", "poor")],
                trace_metadata={"mlflow.trace.session": "sess-bbb-case2"},
                request_time=1000,
            ),
        ]
        results = _parse_session_traces(traces, "run1", "quality")
        assert len(results) == 2

    def test_accumulates_duration(self):
        traces = [
            _make_trace(
                request={"user_message": "T1"},
                response='"R1"',
                assessments=[],
                execution_time_ms=100,
                trace_metadata={"mlflow.trace.session": "sess-abc-test"},
                request_time=1000,
            ),
            _make_trace(
                request={"user_message": "T2"},
                response='"R2"',
                assessments=[],
                execution_time_ms=200,
                trace_metadata={"mlflow.trace.session": "sess-abc-test"},
                request_time=2000,
            ),
        ]
        results = _parse_session_traces(traces, "run1", "quality")
        assert results[0].duration_ms == 300

    def test_user_prompt_is_first_assistant_response_is_last(self):
        traces = [
            _make_trace(
                request={"user_message": "First question"},
                response='"First answer"',
                assessments=[],
                trace_metadata={"mlflow.trace.session": "sess-abc-test"},
                request_time=1000,
            ),
            _make_trace(
                request={"user_message": "Follow up"},
                response='"Final answer"',
                assessments=[],
                trace_metadata={"mlflow.trace.session": "sess-abc-test"},
                request_time=2000,
            ),
        ]
        results = _parse_session_traces(traces, "run1", "quality")
        assert results[0].user_prompt == "First question"
        assert results[0].assistant_response == "Final answer"

    def test_skips_traces_without_session(self):
        traces = [
            _make_trace(
                request={"user_message": "Orphan"},
                response='"Reply"',
                assessments=[],
                trace_metadata={},  # No session
            ),
        ]
        results = _parse_session_traces(traces, "run1", "quality")
        assert len(results) == 0

    def test_assessment_from_any_trace_in_session(self):
        """Assessments can be on any trace in the session, not just the last."""
        traces = [
            _make_trace(
                request={"user_message": "T1"},
                response='"R1"',
                assessments=[_make_assessment("quality", "excellent", "Great conversation")],
                trace_metadata={"mlflow.trace.session": "sess-abc-test"},
                request_time=1000,
            ),
            _make_trace(
                request={"user_message": "T2"},
                response='"R2"',
                assessments=[],  # No assessments on this trace
                trace_metadata={"mlflow.trace.session": "sess-abc-test"},
                request_time=2000,
            ),
        ]
        results = _parse_session_traces(traces, "run1", "quality")
        assert results[0].rating == "excellent"
        assert results[0].justification == "Great conversation"


# ---------------------------------------------------------------------------
# _extract_case_id_from_session
# ---------------------------------------------------------------------------


class TestExtractCaseIdFromSession:
    """Tests for extracting readable case IDs from session IDs."""

    def test_typical_session_id(self):
        result = _extract_case_id_from_session("contra-abc12345-contra-subtle-mismatch")
        assert result == "contra-subtle-mismatch"

    def test_short_session_id_passthrough(self):
        result = _extract_case_id_from_session("simple")
        assert result == "simple"

    def test_no_uuid_segment(self):
        result = _extract_case_id_from_session("onb-short-case")
        assert result == "onb-short-case"

    def test_uuid_at_start(self):
        result = _extract_case_id_from_session("prefix-abcdef01-meaningful-suffix")
        assert result == "meaningful-suffix"

    def test_empty_after_uuid(self):
        """If nothing follows the UUID-like segment, return the full ID."""
        result = _extract_case_id_from_session("contra-abcdef01")
        assert result == "contra-abcdef01"
