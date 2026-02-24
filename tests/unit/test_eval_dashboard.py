"""Unit tests for eval dashboard API endpoints (Feature 014).

Tests all /admin/evals/* endpoints with mocked pipeline functions
and dependency overrides for admin authentication.
"""

from datetime import datetime, timezone
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

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


@dataclass
class FakeTrendPoint:
    run_id: str = "run-1"
    timestamp: datetime = field(default_factory=lambda: datetime(2026, 2, 24, tzinfo=timezone.utc))
    experiment_name: str = "eval-quality"
    eval_type: str = "quality"
    pass_rate: float = 0.90
    average_score: float = 4.2
    total_cases: int = 10
    error_cases: int = 0
    prompt_versions: dict = field(default_factory=lambda: {"system": "1"})
    eval_status: str = "complete"


@dataclass
class FakePromptChange:
    timestamp: datetime = field(default_factory=lambda: datetime(2026, 2, 24, tzinfo=timezone.utc))
    run_id: str = "run-1"
    prompt_name: str = "system"
    from_version: str = "1"
    to_version: str = "2"


@dataclass
class FakeTrendSummary:
    eval_type: str = "quality"
    latest_pass_rate: float = 0.90
    trend_direction: str = "stable"
    points: list = field(default_factory=lambda: [FakeTrendPoint()])
    prompt_changes: list = field(default_factory=list)


@dataclass
class FakeRegressionReport:
    eval_type: str = "quality"
    baseline_run_id: str = "run-0"
    current_run_id: str = "run-1"
    baseline_pass_rate: float = 0.85
    current_pass_rate: float = 0.90
    delta_pp: float = 0.05
    threshold: float = 0.80
    verdict: str = "PASS"
    changed_prompts: list = field(default_factory=list)
    baseline_timestamp: datetime = field(default_factory=lambda: datetime(2026, 2, 23, tzinfo=timezone.utc))
    current_timestamp: datetime = field(default_factory=lambda: datetime(2026, 2, 24, tzinfo=timezone.utc))


@dataclass
class FakePromotionEvalCheck:
    eval_type: str = "quality"
    pass_rate: float = 0.90
    threshold: float = 0.80
    passed: bool = True
    run_id: str = "run-1"


@dataclass
class FakePromotionResult:
    allowed: bool = True
    prompt_name: str = "system"
    from_alias: str = "experiment"
    to_alias: str = "production"
    version: int = 2
    eval_results: list = field(default_factory=lambda: [FakePromotionEvalCheck()])
    blocking_evals: list = field(default_factory=list)
    justifying_run_ids: list = field(default_factory=lambda: ["run-1"])


@dataclass
class FakeAuditRecord:
    action: str = "promote"
    prompt_name: str = "system"
    from_version: int = 1
    to_version: int = 2
    alias: str = "production"
    timestamp: datetime = field(default_factory=lambda: datetime(2026, 2, 24, tzinfo=timezone.utc))
    actor: str = "admin"
    reason: str = ""
    justifying_run_ids: list = field(default_factory=list)


@dataclass
class FakePromptVersionInfo:
    name: str = "system"
    version: int = 2
    alias: str = "production"
    template: str = "You are a helpful assistant"
    model_config: dict = None
    is_fallback: bool = False


@dataclass
class FakeEvalRunResult:
    dataset_path: str = "eval/golden_dataset.json"
    exit_code: int = 0
    passed: bool = True
    output: str = ""


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
# GET /admin/evals/trends
# ---------------------------------------------------------------------------


class TestGetTrends:
    def test_returns_summaries(self, client):
        with (
            patch("eval.pipeline.aggregator.get_eval_experiments", return_value=[("eval-quality", "quality")]),
            patch("eval.pipeline.aggregator.get_trend_points", return_value=[FakeTrendPoint()]),
            patch("eval.pipeline.aggregator.build_trend_summary", return_value=FakeTrendSummary()),
        ):
            resp = client.get("/admin/evals/trends")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["summaries"]) == 1
        assert body["summaries"][0]["eval_type"] == "quality"
        assert body["summaries"][0]["latest_pass_rate"] == 0.90

    def test_filters_by_eval_type(self, client):
        with (
            patch("eval.pipeline.aggregator.get_eval_experiments", return_value=[
                ("eval-quality", "quality"),
                ("eval-security", "security"),
            ]),
            patch("eval.pipeline.aggregator.get_trend_points", return_value=[FakeTrendPoint()]),
            patch("eval.pipeline.aggregator.build_trend_summary", return_value=FakeTrendSummary()),
        ):
            resp = client.get("/admin/evals/trends?eval_type=quality")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["summaries"]) == 1

    def test_respects_limit_param(self, client):
        with (
            patch("eval.pipeline.aggregator.get_eval_experiments", return_value=[("eval-quality", "quality")]),
            patch("eval.pipeline.aggregator.get_trend_points", return_value=[FakeTrendPoint()]) as mock_points,
            patch("eval.pipeline.aggregator.build_trend_summary", return_value=FakeTrendSummary()),
        ):
            resp = client.get("/admin/evals/trends?limit=5")

        assert resp.status_code == 200
        mock_points.assert_called_once_with("eval-quality", "quality", limit=5)

    def test_empty_state(self, client):
        with patch("eval.pipeline.aggregator.get_eval_experiments", return_value=[]):
            resp = client.get("/admin/evals/trends")

        assert resp.status_code == 200
        assert resp.json()["summaries"] == []


# ---------------------------------------------------------------------------
# GET /admin/evals/regressions
# ---------------------------------------------------------------------------


class TestGetRegressions:
    def test_returns_reports(self, client):
        with patch("eval.pipeline.regression.check_all_regressions", return_value=[FakeRegressionReport()]):
            resp = client.get("/admin/evals/regressions")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["reports"]) == 1
        assert body["reports"][0]["verdict"] == "PASS"
        assert body["has_regressions"] is False

    def test_has_regressions_flag(self, client):
        report = FakeRegressionReport(verdict="REGRESSION", delta_pp=-0.15)
        with patch("eval.pipeline.regression.check_all_regressions", return_value=[report]):
            resp = client.get("/admin/evals/regressions")

        assert resp.status_code == 200
        assert resp.json()["has_regressions"] is True

    def test_filters_by_eval_type(self, client):
        with patch("eval.pipeline.regression.check_all_regressions", return_value=[]) as mock_fn:
            resp = client.get("/admin/evals/regressions?eval_type=security")

        assert resp.status_code == 200
        mock_fn.assert_called_once_with(eval_type_filter="security")

    def test_empty_state(self, client):
        with patch("eval.pipeline.regression.check_all_regressions", return_value=[]):
            resp = client.get("/admin/evals/regressions")

        assert resp.status_code == 200
        body = resp.json()
        assert body["reports"] == []
        assert body["has_regressions"] is False


# ---------------------------------------------------------------------------
# GET /admin/evals/prompts
# ---------------------------------------------------------------------------


class TestListPrompts:
    def test_returns_prompt_list(self, client):
        with patch("src.services.prompt_service.get_active_prompt_versions", return_value={"system": 2, "judge": 1}):
            resp = client.get("/admin/evals/prompts")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["prompts"]) == 2
        # Sorted by name
        assert body["prompts"][0]["name"] == "judge"
        assert body["prompts"][1]["name"] == "system"

    def test_empty_prompts(self, client):
        with patch("src.services.prompt_service.get_active_prompt_versions", return_value={}):
            resp = client.get("/admin/evals/prompts")

        assert resp.status_code == 200
        assert resp.json()["prompts"] == []


# ---------------------------------------------------------------------------
# POST /admin/evals/promote/check
# ---------------------------------------------------------------------------


class TestPromotionCheck:
    def test_gate_allowed(self, client):
        with patch("eval.pipeline.promotion.check_promotion_gate", return_value=FakePromotionResult()):
            resp = client.post("/admin/evals/promote/check", json={
                "prompt_name": "system",
                "from_alias": "experiment",
                "to_alias": "production",
            })

        assert resp.status_code == 200
        body = resp.json()
        assert body["allowed"] is True
        assert len(body["eval_results"]) == 1
        assert body["blocking_evals"] == []

    def test_gate_blocked(self, client):
        result = FakePromotionResult(
            allowed=False,
            blocking_evals=["quality"],
        )
        with patch("eval.pipeline.promotion.check_promotion_gate", return_value=result):
            resp = client.post("/admin/evals/promote/check", json={
                "prompt_name": "system",
            })

        assert resp.status_code == 200
        assert resp.json()["allowed"] is False
        assert "quality" in resp.json()["blocking_evals"]


# ---------------------------------------------------------------------------
# POST /admin/evals/promote/execute
# ---------------------------------------------------------------------------


class TestPromotionExecute:
    def test_succeeds_when_gate_passes(self, client):
        with (
            patch("eval.pipeline.promotion.check_promotion_gate", return_value=FakePromotionResult()),
            patch("eval.pipeline.promotion.execute_promotion", return_value=FakeAuditRecord()),
        ):
            resp = client.post("/admin/evals/promote/execute", json={
                "prompt_name": "system",
                "to_alias": "production",
                "version": 2,
                "force": False,
                "reason": "",
            })

        assert resp.status_code == 200
        body = resp.json()
        assert body["action"] == "promote"
        assert body["prompt_name"] == "system"

    def test_returns_403_when_blocked(self, client):
        blocked = FakePromotionResult(allowed=False, blocking_evals=["quality"])
        with patch("eval.pipeline.promotion.check_promotion_gate", return_value=blocked):
            resp = client.post("/admin/evals/promote/execute", json={
                "prompt_name": "system",
                "to_alias": "production",
                "version": 2,
                "force": False,
                "reason": "",
            })

        assert resp.status_code == 403

    def test_force_promotion_bypasses_gate(self, client):
        with patch("eval.pipeline.promotion.execute_promotion", return_value=FakeAuditRecord(reason="urgent fix")):
            resp = client.post("/admin/evals/promote/execute", json={
                "prompt_name": "system",
                "to_alias": "production",
                "version": 2,
                "force": True,
                "reason": "urgent fix",
            })

        assert resp.status_code == 200
        assert resp.json()["action"] == "promote"


# ---------------------------------------------------------------------------
# POST /admin/evals/run & GET /admin/evals/run/status
# ---------------------------------------------------------------------------


class TestEvalRun:
    def test_start_run_returns_202(self, client):
        with (
            patch("eval.pipeline_config.CORE_EVAL_DATASETS", ["eval/golden_dataset.json"]),
            patch("src.api.eval_dashboard._run_eval_suite_background", new_callable=AsyncMock),
            patch("asyncio.create_task"),
        ):
            # Reset state before test
            import src.api.eval_dashboard as mod
            mod._eval_run_state = None

            resp = client.post("/admin/evals/run", json={"suite": "core"})

        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "running"
        assert body["suite"] == "core"

    def test_returns_409_when_already_running(self, client):
        import src.api.eval_dashboard as mod
        mod._eval_run_state = {"status": "running", "run_id": "old"}

        resp = client.post("/admin/evals/run", json={"suite": "core"})
        assert resp.status_code == 409

        # Clean up
        mod._eval_run_state = None

    def test_get_status_returns_null_when_no_run(self, client):
        import src.api.eval_dashboard as mod
        mod._eval_run_state = None

        resp = client.get("/admin/evals/run/status")
        assert resp.status_code == 200
        assert resp.json() is None

    def test_get_status_returns_current_state(self, client):
        import src.api.eval_dashboard as mod
        now = datetime.now(timezone.utc)
        mod._eval_run_state = {
            "run_id": "test-123",
            "suite": "core",
            "status": "completed",
            "total": 5,
            "completed": 5,
            "results": [{"dataset_path": "eval/golden_dataset.json", "exit_code": 0, "passed": True}],
            "regression_reports": None,
            "started_at": now,
            "finished_at": now,
        }

        resp = client.get("/admin/evals/run/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["run_id"] == "test-123"
        assert body["status"] == "completed"
        assert len(body["results"]) == 1

        # Clean up
        mod._eval_run_state = None


# ---------------------------------------------------------------------------
# GET /admin/evals/rollback/info
# ---------------------------------------------------------------------------


class TestRollbackInfo:
    def test_returns_rollback_info(self, client):
        with (
            patch("src.services.prompt_service.load_prompt_version", return_value=FakePromptVersionInfo(version=3)),
            patch("eval.pipeline.rollback.find_previous_version", return_value=2),
        ):
            resp = client.get("/admin/evals/rollback/info?prompt_name=system")

        assert resp.status_code == 200
        body = resp.json()
        assert body["prompt_name"] == "system"
        assert body["current_version"] == 3
        assert body["previous_version"] == 2

    def test_returns_null_previous_for_v1(self, client):
        with (
            patch("src.services.prompt_service.load_prompt_version", return_value=FakePromptVersionInfo(version=1)),
            patch("eval.pipeline.rollback.find_previous_version", return_value=None),
        ):
            resp = client.get("/admin/evals/rollback/info?prompt_name=system")

        assert resp.status_code == 200
        assert resp.json()["previous_version"] is None


# ---------------------------------------------------------------------------
# POST /admin/evals/rollback/execute
# ---------------------------------------------------------------------------


class TestRollbackExecute:
    def test_execute_rollback_returns_audit(self, client):
        record = FakeAuditRecord(action="rollback", from_version=3, to_version=2, reason="regression fix")
        with patch("eval.pipeline.rollback.execute_rollback", return_value=record):
            resp = client.post("/admin/evals/rollback/execute", json={
                "prompt_name": "system",
                "alias": "production",
                "previous_version": 2,
                "reason": "regression fix",
            })

        assert resp.status_code == 200
        body = resp.json()
        assert body["action"] == "rollback"
        assert body["from_version"] == 3
        assert body["to_version"] == 2
        assert body["reason"] == "regression fix"
