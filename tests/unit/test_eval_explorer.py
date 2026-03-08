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


def _make_mlflow_dataset(
    dataset_id="d-123",
    name="quality-v1.0.0",
    tags=None,
    records=None,
    experiment_ids=None,
    created_time=1709294400000,  # 2024-03-01 12:00 UTC
):
    """Build a mock MLflow dataset object."""
    if tags is None:
        tags = {"dataset_type": "quality", "version": "1.0.0", "source_file": "golden_dataset.json"}
    if records is None:
        records = [
            {
                "dataset_record_id": "dr-1",
                "dataset_id": dataset_id,
                "inputs": {"question": "Hello"},
                "expectations": {"rubric": "Be helpful"},
            }
        ]
    if experiment_ids is None:
        experiment_ids = ["1"]

    ds = MagicMock()
    ds.to_dict.return_value = {
        "dataset_id": dataset_id,
        "name": name,
        "tags": tags,
        "records": records,
        "experiment_ids": experiment_ids,
        "created_time": created_time,
    }
    return ds


class TestListDatasets:
    def test_returns_datasets(self, client):
        mock_ds = _make_mlflow_dataset()
        mock_exp = _make_experiment()

        with (
            patch("src.api.eval_explorer.asyncio") as mock_asyncio,
        ):
            # Make run_in_executor call the function synchronously
            mock_asyncio.get_event_loop.return_value.run_in_executor = (
                lambda _, fn: AsyncMock(return_value=fn())()
            )

            with (
                patch("mlflow.search_experiments", return_value=[mock_exp]),
                patch("mlflow.genai.datasets.search_datasets", return_value=[mock_ds]),
            ):
                resp = client.get("/admin/evals/explorer/datasets")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["datasets"]) == 1
        ds = body["datasets"][0]
        assert ds["name"] == "quality-v1.0.0"
        assert ds["dataset_id"] == "d-123"
        assert ds["dataset_type"] == "quality"
        assert ds["version"] == "1.0.0"
        assert ds["source_file"] == "golden_dataset.json"
        assert ds["case_count"] == 1
        assert ds["cases"] == []  # List endpoint doesn't include cases

    def test_empty_mlflow(self, client):
        with (
            patch("src.api.eval_explorer.asyncio") as mock_asyncio,
        ):
            mock_asyncio.get_event_loop.return_value.run_in_executor = (
                lambda _, fn: AsyncMock(return_value=fn())()
            )

            with patch("mlflow.search_experiments", return_value=[]):
                resp = client.get("/admin/evals/explorer/datasets")

        assert resp.status_code == 200
        assert resp.json()["datasets"] == []


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/datasets/{dataset_id}
# ---------------------------------------------------------------------------


class TestGetDataset:
    def test_returns_dataset_with_cases(self, client):
        mock_ds = _make_mlflow_dataset(
            records=[
                {
                    "dataset_record_id": "dr-1",
                    "dataset_id": "d-123",
                    "inputs": {"question": "What is AI?"},
                    "expectations": {"rubric": "Explain AI"},
                },
            ],
        )
        mock_exp = _make_experiment()

        with (
            patch("src.api.eval_explorer.asyncio") as mock_asyncio,
        ):
            mock_asyncio.get_event_loop.return_value.run_in_executor = (
                lambda _, fn: AsyncMock(return_value=fn())()
            )

            with (
                patch("mlflow.search_experiments", return_value=[mock_exp]),
                patch("mlflow.genai.datasets.search_datasets", return_value=[mock_ds]),
            ):
                resp = client.get("/admin/evals/explorer/datasets/d-123")

        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "quality-v1.0.0"
        assert body["dataset_id"] == "d-123"
        assert body["case_count"] == 1
        assert len(body["cases"]) == 1
        assert body["cases"][0]["inputs"]["question"] == "What is AI?"
        assert body["cases"][0]["expectations"]["rubric"] == "Explain AI"

    def test_404_for_missing_dataset(self, client):
        mock_exp = _make_experiment()

        with (
            patch("src.api.eval_explorer.asyncio") as mock_asyncio,
        ):
            mock_asyncio.get_event_loop.return_value.run_in_executor = (
                lambda _, fn: AsyncMock(return_value=fn())()
            )

            with (
                patch("mlflow.search_experiments", return_value=[mock_exp]),
                patch("mlflow.genai.datasets.search_datasets", return_value=[]),
            ):
                resp = client.get("/admin/evals/explorer/datasets/nonexistent")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Helpers for agent version tests
# ---------------------------------------------------------------------------


def _make_logged_model(
    model_id="model-1",
    name="assistant",
    tags=None,
    creation_timestamp=1709300000000,
    metrics=None,
):
    """Create a mock LoggedModel object."""
    model = MagicMock()
    model.model_id = model_id
    model.name = name
    model.tags = tags or {
        "mlflow.source.git.branch": "main",
        "mlflow.source.git.commit": "abc1234def5678",
        "mlflow.source.git.dirty": "false",
    }
    model.creation_timestamp = creation_timestamp
    model.metrics = metrics or []
    return model


def _make_model_metric(key="universal_quality", value=85.0):
    """Create a mock model metric."""
    m = MagicMock()
    m.key = key
    m.value = value
    return m


def _make_trace_for_agent(
    trace_id="trace-1",
    experiment_id="exp-1",
    source_run="run-1",
    assessments=None,
):
    """Create a mock trace for agent version detail tests."""
    trace = MagicMock()
    info = MagicMock()
    info.trace_id = trace_id
    info.experiment_id = experiment_id
    info.request_metadata = {"mlflow.sourceRun": source_run}
    info.assessments = assessments or []
    trace.info = info
    return trace


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/agents
# ---------------------------------------------------------------------------


class TestListAgentVersions:
    """Tests for GET /admin/evals/explorer/agents.

    All tests mock both search_experiments (required to get experiment IDs)
    and search_logged_models (which requires experiment_ids to return results).
    """

    def _mock_agents(self, client, models):
        """Helper: mock search_experiments + search_logged_models and GET /agents."""
        mock_exp = _make_experiment()
        with (
            patch("mlflow.search_experiments", return_value=[mock_exp]),
            patch("mlflow.search_logged_models", return_value=models),
        ):
            return client.get("/admin/evals/explorer/agents")

    def test_returns_agents_with_git_metadata(self, client):
        model = _make_logged_model()
        resp = self._mock_agents(client, [model])

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["agents"]) == 1
        agent = body["agents"][0]
        assert agent["model_id"] == "model-1"
        assert agent["name"] == "assistant"
        assert agent["git_branch"] == "main"
        assert agent["git_commit"] == "abc1234def5678"
        assert agent["git_commit_short"] == "abc1234"
        assert agent["git_dirty"] is False

    def test_skips_models_without_git_commit(self, client):
        model_no_git = _make_logged_model(
            model_id="model-no-git",
            tags={"mlflow.source.git.branch": "main"},  # no commit tag
        )
        model_with_git = _make_logged_model(model_id="model-with-git")
        resp = self._mock_agents(client, [model_no_git, model_with_git])

        assert resp.status_code == 200
        agents = resp.json()["agents"]
        assert len(agents) == 1
        assert agents[0]["model_id"] == "model-with-git"

    def test_handles_empty_result(self, client):
        resp = self._mock_agents(client, [])

        assert resp.status_code == 200
        assert resp.json()["agents"] == []

    def test_sorts_by_creation_timestamp_desc(self, client):
        model_old = _make_logged_model(
            model_id="model-old",
            creation_timestamp=1709200000000,
        )
        model_new = _make_logged_model(
            model_id="model-new",
            creation_timestamp=1709400000000,
        )
        resp = self._mock_agents(client, [model_old, model_new])

        assert resp.status_code == 200
        agents = resp.json()["agents"]
        assert len(agents) == 2
        assert agents[0]["model_id"] == "model-new"
        assert agents[1]["model_id"] == "model-old"

    def test_extracts_aggregate_quality_from_metrics(self, client):
        metrics = [
            _make_model_metric("quality_universal_quality", 80.0),
            _make_model_metric("security_universal_quality", 90.0),
        ]
        model = _make_logged_model(metrics=metrics)
        resp = self._mock_agents(client, [model])

        assert resp.status_code == 200
        agent = resp.json()["agents"][0]
        assert agent["aggregate_quality"] == 85.0

    def test_handles_search_exception(self, client):
        with patch("mlflow.search_experiments", side_effect=Exception("MLflow down")):
            resp = client.get("/admin/evals/explorer/agents")

        assert resp.status_code == 200
        assert resp.json()["agents"] == []

    def test_git_dirty_true(self, client):
        model = _make_logged_model(tags={
            "mlflow.source.git.branch": "feature",
            "mlflow.source.git.commit": "deadbeef12345678",
            "mlflow.source.git.dirty": "True",
        })
        resp = self._mock_agents(client, [model])

        assert resp.status_code == 200
        assert resp.json()["agents"][0]["git_dirty"] is True


# ---------------------------------------------------------------------------
# GET /admin/evals/explorer/agents/{model_id}
# ---------------------------------------------------------------------------


class TestGetAgentVersionDetail:
    def test_returns_detail_with_experiment_results(self, client):
        model = _make_logged_model()
        assessment = _make_assessment(value=4.5)
        trace = _make_trace_for_agent(
            experiment_id="exp-1",
            source_run="run-1",
            assessments=[assessment],
        )
        exp = _make_experiment("exp-1", "eval-quality")

        with (
            patch("mlflow.get_logged_model", return_value=model),
            patch("mlflow.search_traces", return_value=[trace]),
            patch("eval.pipeline.aggregator.get_eval_experiments",
                  return_value=[("eval-quality", "quality")]),
            patch("mlflow.get_experiment_by_name", return_value=exp),
        ):
            resp = client.get("/admin/evals/explorer/agents/model-1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["model_id"] == "model-1"
        assert body["git_branch"] == "main"
        assert body["git_commit"] == "abc1234def5678"
        assert body["git_commit_short"] == "abc1234"
        assert body["git_dirty"] is False
        assert body["total_traces"] == 1
        assert len(body["experiment_results"]) == 1
        er = body["experiment_results"][0]
        assert er["experiment_name"] == "eval-quality"
        assert er["experiment_id"] == "exp-1"
        assert er["eval_type"] == "quality"
        assert er["run_count"] == 1
        assert er["average_quality"] == 4.5
        assert er["pass_rate"] == 1.0
        assert er["latest_run_id"] == "run-1"

    def test_returns_404_for_unknown_model(self, client):
        with patch("mlflow.get_logged_model", side_effect=Exception("Not found")):
            resp = client.get("/admin/evals/explorer/agents/nonexistent")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_handles_no_traces(self, client):
        model = _make_logged_model()

        with (
            patch("mlflow.get_logged_model", return_value=model),
            patch("mlflow.search_traces", return_value=[]),
            patch("eval.pipeline.aggregator.get_eval_experiments", return_value=[]),
        ):
            resp = client.get("/admin/evals/explorer/agents/model-1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_traces"] == 0
        assert body["experiment_results"] == []
        assert body["aggregate_quality"] is None

    def test_includes_git_diff_and_repo_url(self, client):
        model = _make_logged_model(tags={
            "mlflow.source.git.branch": "feature-x",
            "mlflow.source.git.commit": "abc1234def5678",
            "mlflow.source.git.dirty": "true",
            "mlflow.source.git.diff": "--- a/file.py\n+++ b/file.py",
            "mlflow.source.git.repoURL": "https://github.com/user/repo",
        })

        with (
            patch("mlflow.get_logged_model", return_value=model),
            patch("mlflow.search_traces", return_value=[]),
            patch("eval.pipeline.aggregator.get_eval_experiments", return_value=[]),
        ):
            resp = client.get("/admin/evals/explorer/agents/model-1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["git_diff"] == "--- a/file.py\n+++ b/file.py"
        assert body["git_repo_url"] == "https://github.com/user/repo"
        assert body["git_dirty"] is True

    def test_multiple_experiments_aggregate_quality(self, client):
        model = _make_logged_model()
        assessment1 = _make_assessment(value=4.0)
        assessment2 = _make_assessment(value=5.0)
        trace1 = _make_trace_for_agent(
            trace_id="t1", experiment_id="exp-1", source_run="run-1",
            assessments=[assessment1],
        )
        trace2 = _make_trace_for_agent(
            trace_id="t2", experiment_id="exp-2", source_run="run-2",
            assessments=[assessment2],
        )
        exp1 = _make_experiment("exp-1", "eval-quality")
        exp2 = _make_experiment("exp-2", "eval-security")

        with (
            patch("mlflow.get_logged_model", return_value=model),
            patch("mlflow.search_traces", return_value=[trace1, trace2]),
            patch("eval.pipeline.aggregator.get_eval_experiments",
                  return_value=[("eval-quality", "quality"), ("eval-security", "security")]),
            patch("mlflow.get_experiment_by_name", side_effect=[exp1, exp2]),
        ):
            resp = client.get("/admin/evals/explorer/agents/model-1")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["experiment_results"]) == 2
        # Aggregate quality: average of 4.0 and 5.0 = 4.5
        assert body["aggregate_quality"] == 4.5
