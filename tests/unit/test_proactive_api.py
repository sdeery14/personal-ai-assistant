"""Unit tests for proactive API endpoints."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.proactive import router
from src.models.user import User


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = "testuser"
    user.is_admin = False
    return user


@pytest.fixture
def mock_service():
    return AsyncMock()


@pytest.fixture
def app(mock_user):
    from fastapi import FastAPI
    from src.api.dependencies import get_current_user

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestGetSettings:
    def test_returns_default_settings(self, client, mock_service):
        mock_service.get_or_create_settings.return_value = {
            "global_level": 0.7,
            "suppressed_types": json.dumps([]),
            "boosted_types": json.dumps([]),
            "user_override": None,
            "is_onboarded": False,
        }

        with patch(
            "src.api.proactive.ProactiveService",
            return_value=mock_service,
        ):
            response = client.get("/proactive/settings")

        assert response.status_code == 200
        data = response.json()
        assert data["global_level"] == 0.7
        assert data["suppressed_types"] == []
        assert data["boosted_types"] == []
        assert data["is_onboarded"] is False

    def test_returns_customized_settings(self, client, mock_service):
        mock_service.get_or_create_settings.return_value = {
            "global_level": 0.3,
            "suppressed_types": json.dumps(["weather_briefing"]),
            "boosted_types": json.dumps(["meeting_prep"]),
            "user_override": "less",
            "is_onboarded": True,
        }

        with patch(
            "src.api.proactive.ProactiveService",
            return_value=mock_service,
        ):
            response = client.get("/proactive/settings")

        assert response.status_code == 200
        data = response.json()
        assert data["global_level"] == 0.3
        assert "weather_briefing" in data["suppressed_types"]
        assert data["user_override"] == "less"


class TestGetProfile:
    def test_returns_aggregated_profile(self, client, mock_service):
        mock_service.get_user_profile.return_value = {
            "facts": [{"content": "Engineer", "type": "fact", "confidence": 0.95}],
            "preferences": [{"content": "Dark mode", "type": "preference", "confidence": 0.9}],
            "patterns": [{"description": "Morning weather", "occurrence_count": 5, "acted_on": False}],
            "key_relationships": [{"entity": "Sarah", "relationship": "WORKS_WITH", "mentions": 8}],
            "proactiveness": {"global_level": 0.7, "engaged_categories": [], "suppressed_categories": []},
        }

        with patch(
            "src.api.proactive.ProactiveService",
            return_value=mock_service,
        ):
            response = client.get("/proactive/profile")

        assert response.status_code == 200
        data = response.json()
        assert len(data["facts"]) == 1
        assert len(data["preferences"]) == 1
        assert len(data["patterns"]) == 1
        assert data["proactiveness"]["global_level"] == 0.7

    def test_returns_empty_profile_for_new_user(self, client, mock_service):
        mock_service.get_user_profile.return_value = {
            "facts": [],
            "preferences": [],
            "patterns": [],
            "key_relationships": [],
            "proactiveness": {"global_level": 0.7, "engaged_categories": [], "suppressed_categories": []},
        }

        with patch(
            "src.api.proactive.ProactiveService",
            return_value=mock_service,
        ):
            response = client.get("/proactive/profile")

        assert response.status_code == 200
        data = response.json()
        assert data["facts"] == []
        assert data["preferences"] == []
