"""Unit tests for eval explorer API endpoints.

Tests all /admin/evals/explorer/* endpoints with mocked MLflow calls
and dependency overrides for admin authentication.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, mock_open, patch
from uuid import uuid4

import pandas as pd
import pytest

from src.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_admin():
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        username="admin",
        display_name="Admin",
        is_admin=True,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def _make_experiment(experiment_id="exp-1", name="eval-quality"):
    exp = MagicMock()
    exp.experiment_id = experiment_id
    exp.name = name
    return exp


def _make_runs_df(rows=None):
    """Build a DataFrame mimicking mlflow.search_runs output."""
    if rows is None:
        rows = [{
            "run_id": "run-1",
            "start_time": pd.Timestamp("2026-03-01 12:00:00+00:00"),
            "metrics.pass_rate": 0.90,
            "metrics.average_score": 4.2,
            "metrics.universal_quality": 85.0,
            "metrics.total_cases": 10.0,
            "params.model": "gpt-4o",
            "params.dataset": "golden",
        }]
    return pd.DataFrame(rows)


def _make_assessment(name="quality_judge", value=None, rationale="Good", source_type="LLM_JUDGE"):
    a = MagicMock()
    a.name = name
    a.value = value
    a.rationale = rationale
    a.feedback = None
    a.expectation = None
    src = MagicMock()
    src.source_type = source_type
    a.source = src
    return a


def _make_mlflow_run(run_id="run-1", experiment_id="exp-1"):
    """Create a mock MLflow Run object with info."""
    run = MagicMock()
    run.info.experiment_id = experiment_id
    run.info.run_id = run_id
    return run


def _make_trace(trace_id="trace-1", case_id="case-1", request=None, response=None,
                assessments=None, session_id=None, duration=1000):
    trace = MagicMock()
    info = MagicMock()
    info.trace_id = trace_id
    info.request_id = trace_id
    info.execution_duration = duration
    info.request_metadata = {"case_id": case_id}
    if session_id:
        info.request_metadata["mlflow.trace.session"] = session_id
    info.assessments = assessments or []
    trace.info = info

    data = MagicMock()
    data.request = request or '{"question": "Hello?"}'
    data.response = response or '{"response": "Hi there!"}'
    trace.data = data
    return trace


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user():
    return _make_admin()


@pytest.fixture
def client(admin_user):
    """TestClient with admin auth overrides and mocked lifespan."""
    with (
        patch("src.database.init_database", new_callable=AsyncMock),
        patch("src.database.run_migrations", new_callable=AsyncMock),
        patch("src.services.redis_service.get_redis", new_callable=AsyncMock),
        patch("src.database.close_database", new_callable=AsyncMock),
        patch("src.services.redis_service.close_redis", new_callable=AsyncMock),
        patch("src.services.memory_write_service.await_pending_writes", new_callable=AsyncMock),
    ):
        from fastapi.testclient import TestClient
        from src.api.dependencies import get_current_user, require_admin
        from src.main import app

        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[require_admin] = lambda: admin_user

        with TestClient(app) as tc:
            yield tc

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/experiments
# ---------------------------------------------------------------------------


class TestListExperiments:
    def test_returns_experiments_with_metadata(self, client):
        exp = _make_experiment()
        runs_df = _make_runs_df()

        with (
            patch("eval.pipeline.aggregator.get_eval_experiments",
                  return_value=[("eval-quality", "quality")]),
            patch("eval.pipeline_config.get_metric_names",
                  return_value={"pass_rate": "metrics.pass_rate", "average_score": "metrics.average_score"}),
            patch("mlflow.get_experiment_by_name", return_value=exp),
            patch("mlflow.search_runs", side_effect=[runs_df, runs_df]),
        ):
            resp = client.get("/admin/evals/explorer/experiments")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["experiments"]) == 1
        e = body["experiments"][0]
        assert e["experiment_id"] == "exp-1"
        assert e["name"] == "eval-quality"
        assert e["eval_type"] == "quality"
        assert e["run_count"] == 1
        assert e["latest_pass_rate"] == 0.90
        assert e["latest_universal_quality"] == 85.0

    def test_skips_missing_experiment(self, client):
        with (
            patch("eval.pipeline.aggregator.get_eval_experiments",
                  return_value=[("eval-missing", "quality")]),
            patch("eval.pipeline_config.get_metric_names",
                  return_value={"pass_rate": "metrics.pass_rate", "average_score": "metrics.average_score"}),
            patch("mlflow.get_experiment_by_name", return_value=None),
        ):
            resp = client.get("/admin/evals/explorer/experiments")

        assert resp.status_code == 200
        assert resp.json()["experiments"] == []

    def test_empty_experiments_list(self, client):
        with (
            patch("eval.pipeline.aggregator.get_eval_experiments", return_value=[]),
            patch("eval.pipeline_config.get_metric_names",
                  return_value={"pass_rate": "metrics.pass_rate", "average_score": "metrics.average_score"}),
        ):
            resp = client.get("/admin/evals/explorer/experiments")

        assert resp.status_code == 200
        assert resp.json()["experiments"] == []

    def test_experiment_with_no_runs(self, client):
        exp = _make_experiment()
        empty_df = pd.DataFrame()

        with (
            patch("eval.pipeline.aggregator.get_eval_experiments",
                  return_value=[("eval-quality", "quality")]),
            patch("eval.pipeline_config.get_metric_names",
                  return_value={"pass_rate": "metrics.pass_rate", "average_score": "metrics.average_score"}),
            patch("mlflow.get_experiment_by_name", return_value=exp),
            patch("mlflow.search_runs", return_value=empty_df),
        ):
            resp = client.get("/admin/evals/explorer/experiments")

        assert resp.status_code == 200
        e = resp.json()["experiments"][0]
        assert e["run_count"] == 0
        assert e["latest_pass_rate"] is None
        assert e["latest_universal_quality"] is None

    def test_multiple_experiments(self, client):
        exp_q = _make_experiment("exp-1", "eval-quality")
        exp_s = _make_experiment("exp-2", "eval-security")
        runs_df = _make_runs_df()

        with (
            patch("eval.pipeline.aggregator.get_eval_experiments",
                  return_value=[("eval-quality", "quality"), ("eval-security", "security")]),
            patch("eval.pipeline_config.get_metric_names",
                  return_value={"pass_rate": "metrics.pass_rate", "average_score": "metrics.average_score"}),
            patch("mlflow.get_experiment_by_name", side_effect=[exp_q, exp_s]),
            patch("mlflow.search_runs", return_value=runs_df),
        ):
            resp = client.get("/admin/evals/explorer/experiments")

        assert resp.status_code == 200
        assert len(resp.json()["experiments"]) == 2


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/experiments/{experiment_id}/runs
# ---------------------------------------------------------------------------


class TestListRuns:
    def test_returns_runs_with_params_and_metrics(self, client):
        exp = _make_experiment()
        runs_df = _make_runs_df()

        with (
            patch("mlflow.get_experiment", return_value=exp),
            patch("mlflow.search_runs", return_value=runs_df),
        ):
            resp = client.get("/admin/evals/explorer/experiments/exp-1/runs?eval_type=quality")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["runs"]) == 1
        run = body["runs"][0]
        assert run["run_id"] == "run-1"
        assert run["params"]["model"] == "gpt-4o"
        assert run["metrics"]["pass_rate"] == 0.90
        assert run["universal_quality"] == 85.0
        assert run["trace_count"] == 10

    def test_404_for_missing_experiment(self, client):
        with patch("mlflow.get_experiment", return_value=None):
            resp = client.get("/admin/evals/explorer/experiments/missing/runs?eval_type=quality")

        assert resp.status_code == 404

    def test_empty_runs(self, client):
        exp = _make_experiment()

        with (
            patch("mlflow.get_experiment", return_value=exp),
            patch("mlflow.search_runs", return_value=pd.DataFrame()),
        ):
            resp = client.get("/admin/evals/explorer/experiments/exp-1/runs?eval_type=quality")

        assert resp.status_code == 200
        assert resp.json()["runs"] == []

    def test_requires_eval_type_query_param(self, client):
        resp = client.get("/admin/evals/explorer/experiments/exp-1/runs")
        # Custom validation error handler returns 400
        assert resp.status_code == 400

    def test_multiple_runs_ordered(self, client):
        exp = _make_experiment()
        runs_df = _make_runs_df([
            {
                "run_id": "run-2",
                "start_time": pd.Timestamp("2026-03-02 12:00:00+00:00"),
                "metrics.universal_quality": 90.0,
                "metrics.total_cases": 5.0,
            },
            {
                "run_id": "run-1",
                "start_time": pd.Timestamp("2026-03-01 12:00:00+00:00"),
                "metrics.universal_quality": 80.0,
                "metrics.total_cases": 8.0,
            },
        ])

        with (
            patch("mlflow.get_experiment", return_value=exp),
            patch("mlflow.search_runs", return_value=runs_df),
        ):
            resp = client.get("/admin/evals/explorer/experiments/exp-1/runs?eval_type=quality")

        assert resp.status_code == 200
        runs = resp.json()["runs"]
        assert len(runs) == 2
        assert runs[0]["run_id"] == "run-2"
        assert runs[1]["run_id"] == "run-1"


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/runs/{run_id}/traces
# ---------------------------------------------------------------------------


class TestListTraces:
    def test_returns_traces_with_assessments(self, client):
        assessment = _make_assessment(value="excellent")
        trace = _make_trace(assessments=[assessment])

        with (
            patch("eval.pipeline_config.EVAL_SESSION_TYPES", frozenset()),
            patch("mlflow.get_run", return_value=_make_mlflow_run()),
            patch("mlflow.search_traces", return_value=[trace]),
        ):
            resp = client.get("/admin/evals/explorer/runs/run-1/traces?eval_type=quality")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["traces"]) == 1
        t = body["traces"][0]
        assert t["trace_id"] == "trace-1"
        assert t["case_id"] == "case-1"
        assert t["user_prompt"] == "Hello?"
        assert t["assistant_response"] == "Hi there!"
        assert t["duration_ms"] == 1000
        assert t["session_id"] is None
        assert len(t["assessments"]) == 1
        assert body["sessions"] == []

    def test_assessment_word_label_excellent(self, client):
        """Word label 'excellent' -> score 5.0, passed True."""
        assessment = _make_assessment(value="excellent")
        trace = _make_trace(assessments=[assessment])

        with (
            patch("eval.pipeline_config.EVAL_SESSION_TYPES", frozenset()),
            patch("mlflow.get_run", return_value=_make_mlflow_run()),
            patch("mlflow.search_traces", return_value=[trace]),
        ):
            resp = client.get("/admin/evals/explorer/runs/run-1/traces?eval_type=quality")

        a = resp.json()["traces"][0]["assessments"][0]
        assert a["normalized_score"] == 5.0
        assert a["passed"] is True

    def test_assessment_numeric_value(self, client):
        """Numeric 4.5 -> score 4.5, passed True."""
        assessment = _make_assessment(value=4.5)
        trace = _make_trace(assessments=[assessment])

        with (
            patch("eval.pipeline_config.EVAL_SESSION_TYPES", frozenset()),
            patch("mlflow.get_run", return_value=_make_mlflow_run()),
            patch("mlflow.search_traces", return_value=[trace]),
        ):
            resp = client.get("/admin/evals/explorer/runs/run-1/traces?eval_type=quality")

        a = resp.json()["traces"][0]["assessments"][0]
        assert a["normalized_score"] == 4.5
        assert a["passed"] is True

    def test_assessment_boolean_true(self, client):
        """Boolean True -> score 1.0, passed True."""
        assessment = _make_assessment(value=True)
        trace = _make_trace(assessments=[assessment])

        with (
            patch("eval.pipeline_config.EVAL_SESSION_TYPES", frozenset()),
            patch("mlflow.get_run", return_value=_make_mlflow_run()),
            patch("mlflow.search_traces", return_value=[trace]),
        ):
            resp = client.get("/admin/evals/explorer/runs/run-1/traces?eval_type=quality")

        a = resp.json()["traces"][0]["assessments"][0]
        assert a["normalized_score"] == 1.0
        assert a["passed"] is True

    def test_assessment_boolean_false(self, client):
        """Boolean False -> score 0.0, passed False."""
        assessment = _make_assessment(value=False)
        trace = _make_trace(assessments=[assessment])

        with (
            patch("eval.pipeline_config.EVAL_SESSION_TYPES", frozenset()),
            patch("mlflow.get_run", return_value=_make_mlflow_run()),
            patch("mlflow.search_traces", return_value=[trace]),
        ):
            resp = client.get("/admin/evals/explorer/runs/run-1/traces?eval_type=quality")

        a = resp.json()["traces"][0]["assessments"][0]
        assert a["normalized_score"] == 0.0
        assert a["passed"] is False

    def test_assessment_low_numeric_score(self, client):
        """Numeric 2.0 -> passed False (below 4.0 threshold)."""
        assessment = _make_assessment(value=2.0)
        trace = _make_trace(assessments=[assessment])

        with (
            patch("eval.pipeline_config.EVAL_SESSION_TYPES", frozenset()),
            patch("mlflow.get_run", return_value=_make_mlflow_run()),
            patch("mlflow.search_traces", return_value=[trace]),
        ):
            resp = client.get("/admin/evals/explorer/runs/run-1/traces?eval_type=quality")

        a = resp.json()["traces"][0]["assessments"][0]
        assert a["normalized_score"] == 2.0
        assert a["passed"] is False

    def test_assessment_word_label_poor(self, client):
        """Word label 'poor' -> score 2.0, passed False."""
        assessment = _make_assessment(value="poor")
        trace = _make_trace(assessments=[assessment])

        with (
            patch("eval.pipeline_config.EVAL_SESSION_TYPES", frozenset()),
            patch("mlflow.get_run", return_value=_make_mlflow_run()),
            patch("mlflow.search_traces", return_value=[trace]),
        ):
            resp = client.get("/admin/evals/explorer/runs/run-1/traces?eval_type=quality")

        a = resp.json()["traces"][0]["assessments"][0]
        assert a["normalized_score"] == 2.0
        assert a["passed"] is False

    def test_assessment_rationale_and_source(self, client):
        assessment = _make_assessment(value="good", rationale="Well structured", source_type="LLM_JUDGE")
        trace = _make_trace(assessments=[assessment])

        with (
            patch("eval.pipeline_config.EVAL_SESSION_TYPES", frozenset()),
            patch("mlflow.get_run", return_value=_make_mlflow_run()),
            patch("mlflow.search_traces", return_value=[trace]),
        ):
            resp = client.get("/admin/evals/explorer/runs/run-1/traces?eval_type=quality")

        a = resp.json()["traces"][0]["assessments"][0]
        assert a["rationale"] == "Well structured"
        assert a["source_type"] == "LLM_JUDGE"
        assert a["name"] == "quality_judge"

    def test_session_grouping(self, client):
        """Session eval types group traces by session_id."""
        assessment = _make_assessment(value="good")
        t1 = _make_trace(trace_id="t1", case_id="c1", session_id="session-A",
                         assessments=[])
        t2 = _make_trace(trace_id="t2", case_id="c2", session_id="session-A",
                         assessments=[assessment])

        with (
            patch("eval.pipeline_config.EVAL_SESSION_TYPES", frozenset({"onboarding"})),
            patch("mlflow.get_run", return_value=_make_mlflow_run()),
            patch("mlflow.search_traces", return_value=[t1, t2]),
        ):
            resp = client.get("/admin/evals/explorer/runs/run-1/traces?eval_type=onboarding")

        body = resp.json()
        assert len(body["traces"]) == 2
        assert len(body["sessions"]) == 1
        session = body["sessions"][0]
        assert session["session_id"] == "session-A"
        assert session["eval_type"] == "onboarding"
        assert len(session["traces"]) == 2
        # Last trace's assessment becomes session assessment
        assert session["session_assessment"]["normalized_score"] == 4.0
        assert session["session_assessment"]["passed"] is True

    def test_non_session_type_no_grouping(self, client):
        """Non-session eval types don't group even with session metadata."""
        trace = _make_trace(session_id="session-X")

        with (
            patch("eval.pipeline_config.EVAL_SESSION_TYPES", frozenset({"onboarding"})),
            patch("mlflow.get_run", return_value=_make_mlflow_run()),
            patch("mlflow.search_traces", return_value=[trace]),
        ):
            resp = client.get("/admin/evals/explorer/runs/run-1/traces?eval_type=quality")

        body = resp.json()
        assert len(body["traces"]) == 1
        assert body["traces"][0]["session_id"] is None
        assert body["sessions"] == []

    def test_no_traces_returns_empty(self, client):
        with (
            patch("eval.pipeline_config.EVAL_SESSION_TYPES", frozenset()),
            patch("mlflow.get_run", return_value=_make_mlflow_run()),
            patch("mlflow.search_traces", return_value=[]),
        ):
            resp = client.get("/admin/evals/explorer/runs/run-1/traces?eval_type=quality")

        assert resp.status_code == 200
        body = resp.json()
        assert body["traces"] == []
        assert body["sessions"] == []

    def test_requires_eval_type_query_param(self, client):
        resp = client.get("/admin/evals/explorer/runs/run-1/traces")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/trends/quality
# ---------------------------------------------------------------------------


class TestQualityTrend:
    def test_returns_trend_points(self, client):
        exp = _make_experiment()
        runs_df = _make_runs_df()

        with (
            patch("eval.pipeline.aggregator.get_eval_experiments",
                  return_value=[("eval-quality", "quality")]),
            patch("mlflow.get_experiment_by_name", return_value=exp),
            patch("mlflow.search_runs", return_value=runs_df),
        ):
            resp = client.get("/admin/evals/explorer/trends/quality")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["points"]) == 1
        pt = body["points"][0]
        assert pt["eval_type"] == "quality"
        assert pt["universal_quality"] == 85.0
        assert pt["run_id"] == "run-1"

    def test_skips_experiments_without_uq_column(self, client):
        exp = _make_experiment()
        runs_df = pd.DataFrame([{
            "run_id": "run-1",
            "start_time": pd.Timestamp("2026-03-01 12:00:00+00:00"),
            "metrics.pass_rate": 0.90,
        }])

        with (
            patch("eval.pipeline.aggregator.get_eval_experiments",
                  return_value=[("eval-quality", "quality")]),
            patch("mlflow.get_experiment_by_name", return_value=exp),
            patch("mlflow.search_runs", return_value=runs_df),
        ):
            resp = client.get("/admin/evals/explorer/trends/quality")

        assert resp.status_code == 200
        assert resp.json()["points"] == []

    def test_empty_experiments(self, client):
        with patch("eval.pipeline.aggregator.get_eval_experiments", return_value=[]):
            resp = client.get("/admin/evals/explorer/trends/quality")

        assert resp.status_code == 200
        assert resp.json()["points"] == []

    def test_respects_limit_param(self, client):
        exp = _make_experiment()
        runs_df = _make_runs_df()

        with (
            patch("eval.pipeline.aggregator.get_eval_experiments",
                  return_value=[("eval-quality", "quality")]),
            patch("mlflow.get_experiment_by_name", return_value=exp),
            patch("mlflow.search_runs", return_value=runs_df) as mock_search,
        ):
            resp = client.get("/admin/evals/explorer/trends/quality?limit=5")

        assert resp.status_code == 200
        call_kwargs = mock_search.call_args
        assert call_kwargs[1]["max_results"] == 5

    def test_skips_experiment_not_found(self, client):
        with (
            patch("eval.pipeline.aggregator.get_eval_experiments",
                  return_value=[("eval-missing", "quality")]),
            patch("mlflow.get_experiment_by_name", return_value=None),
        ):
            resp = client.get("/admin/evals/explorer/trends/quality")

        assert resp.status_code == 200
        assert resp.json()["points"] == []


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/datasets
# ---------------------------------------------------------------------------


class TestListDatasets:
    def test_returns_datasets(self, client):
        fake_path = MagicMock()
        fake_path.stem = "quality_golden_dataset"
        fake_path.name = "quality_golden_dataset.json"

        dataset_json = '{"version": "1.0", "description": "Quality evals", "cases": [{"id": "c1", "user_prompt": "Hello", "rubric": "Be helpful", "tags": ["greeting"]}]}'

        with (
            patch("src.api.eval_explorer.Path") as MockPath,
            patch("builtins.open", mock_open(read_data=dataset_json)),
        ):
            mock_resolved = MagicMock()
            MockPath.return_value.resolve.return_value = mock_resolved
            mock_resolved.parent.parent.parent.__truediv__.return_value = MagicMock(
                glob=MagicMock(return_value=[fake_path])
            )

            resp = client.get("/admin/evals/explorer/datasets")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["datasets"]) == 1
        ds = body["datasets"][0]
        assert ds["name"] == "quality_golden_dataset"
        assert ds["version"] == "1.0"
        assert ds["description"] == "Quality evals"
        assert ds["case_count"] == 1
        assert ds["cases"] == []  # include_cases defaults to False

    def test_returns_cases_when_requested(self, client):
        fake_path = MagicMock()
        fake_path.stem = "quality_golden_dataset"
        fake_path.name = "quality_golden_dataset.json"

        dataset_json = '{"version": "1.0", "description": "Quality evals", "cases": [{"id": "c1", "user_prompt": "Hello", "rubric": "Be helpful", "tags": ["greeting"], "expected_behavior": "allow"}]}'

        with (
            patch("src.api.eval_explorer.Path") as MockPath,
            patch("builtins.open", mock_open(read_data=dataset_json)),
        ):
            mock_resolved = MagicMock()
            MockPath.return_value.resolve.return_value = mock_resolved
            mock_resolved.parent.parent.parent.__truediv__.return_value = MagicMock(
                glob=MagicMock(return_value=[fake_path])
            )

            resp = client.get("/admin/evals/explorer/datasets?include_cases=true")

        assert resp.status_code == 200
        ds = resp.json()["datasets"][0]
        assert ds["case_count"] == 1
        assert len(ds["cases"]) == 1
        case = ds["cases"][0]
        assert case["id"] == "c1"
        assert case["user_prompt"] == "Hello"
        assert case["rubric"] == "Be helpful"
        assert case["tags"] == ["greeting"]
        assert case["extra"] == {"expected_behavior": "allow"}

    def test_empty_eval_dir(self, client):
        with patch("src.api.eval_explorer.Path") as MockPath:
            mock_resolved = MagicMock()
            MockPath.return_value.resolve.return_value = mock_resolved
            mock_resolved.parent.parent.parent.__truediv__.return_value = MagicMock(
                glob=MagicMock(return_value=[])
            )

            resp = client.get("/admin/evals/explorer/datasets")

        assert resp.status_code == 200
        assert resp.json()["datasets"] == []


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/datasets/{dataset_name}
# ---------------------------------------------------------------------------


class TestGetDataset:
    def test_returns_dataset_with_cases(self, client):
        dataset_json = '{"version": "2.0", "description": "Test dataset", "cases": [{"id": "c1", "question": "What is AI?", "rubric": "Explain AI"}]}'

        with patch("src.api.eval_explorer.Path") as MockPath:
            mock_resolved = MagicMock()
            MockPath.return_value.resolve.return_value = mock_resolved
            eval_dir = MagicMock()
            mock_resolved.parent.parent.parent.__truediv__.return_value = eval_dir

            # First candidate doesn't exist, second does
            candidate1 = MagicMock()
            candidate1.exists.return_value = False
            candidate2 = MagicMock()
            candidate2.exists.return_value = True
            candidate2.stem = "quality_golden_dataset"
            candidate2.name = "quality_golden_dataset.json"

            eval_dir.__truediv__ = MagicMock(side_effect=[candidate1, candidate2])

            with patch("builtins.open", mock_open(read_data=dataset_json)):
                resp = client.get("/admin/evals/explorer/datasets/quality")

        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "quality_golden_dataset"
        assert body["version"] == "2.0"
        assert body["case_count"] == 1
        assert len(body["cases"]) == 1
        # Uses "question" key fallback for user_prompt
        assert body["cases"][0]["user_prompt"] == "What is AI?"

    def test_404_for_missing_dataset(self, client):
        with patch("src.api.eval_explorer.Path") as MockPath:
            mock_resolved = MagicMock()
            MockPath.return_value.resolve.return_value = mock_resolved
            eval_dir = MagicMock()
            mock_resolved.parent.parent.parent.__truediv__.return_value = eval_dir

            candidate = MagicMock()
            candidate.exists.return_value = False
            eval_dir.__truediv__ = MagicMock(return_value=candidate)

            resp = client.get("/admin/evals/explorer/datasets/nonexistent")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_extra_fields_extracted(self, client):
        """Fields not in known_keys are put in 'extra'."""
        dataset_json = '{"version": "1.0", "description": "", "cases": [{"id": "c1", "user_prompt": "Hi", "expected_behavior": "block", "severity": "high"}]}'

        with patch("src.api.eval_explorer.Path") as MockPath:
            mock_resolved = MagicMock()
            MockPath.return_value.resolve.return_value = mock_resolved
            eval_dir = MagicMock()
            mock_resolved.parent.parent.parent.__truediv__.return_value = eval_dir

            candidate = MagicMock()
            candidate.exists.return_value = True
            candidate.stem = "security_golden_dataset"
            candidate.name = "security_golden_dataset.json"
            eval_dir.__truediv__ = MagicMock(return_value=candidate)

            with patch("builtins.open", mock_open(read_data=dataset_json)):
                resp = client.get("/admin/evals/explorer/datasets/security_golden_dataset")

        assert resp.status_code == 200
        case = resp.json()["cases"][0]
        assert case["extra"]["expected_behavior"] == "block"
        assert case["extra"]["severity"] == "high"

    def test_prompt_field_fallback(self, client):
        """Falls back to 'prompt' field when user_prompt and question are absent."""
        dataset_json = '{"version": "1.0", "description": "", "cases": [{"id": "c1", "prompt": "Tell me a story"}]}'

        with patch("src.api.eval_explorer.Path") as MockPath:
            mock_resolved = MagicMock()
            MockPath.return_value.resolve.return_value = mock_resolved
            eval_dir = MagicMock()
            mock_resolved.parent.parent.parent.__truediv__.return_value = eval_dir

            candidate = MagicMock()
            candidate.exists.return_value = True
            candidate.stem = "test_golden_dataset"
            candidate.name = "test_golden_dataset.json"
            eval_dir.__truediv__ = MagicMock(return_value=candidate)

            with patch("builtins.open", mock_open(read_data=dataset_json)):
                resp = client.get("/admin/evals/explorer/datasets/test_golden_dataset")

        assert resp.status_code == 200
        assert resp.json()["cases"][0]["user_prompt"] == "Tell me a story"
