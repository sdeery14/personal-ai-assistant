"""Unit tests for weather evaluation dataset (T091-T092)."""

import json
import tempfile
from pathlib import Path

import pytest

from eval.dataset import (
    DatasetError,
    get_weather_case_by_id,
    get_weather_dataset_info,
    is_weather_dataset,
    load_weather_dataset,
    validate_weather_dataset_file,
)
from eval.models import WeatherGoldenDataset, WeatherTestCase


class TestLoadWeatherDataset:
    """Tests for weather dataset loading (T091)."""

    def test_load_weather_dataset_parses_json(self):
        """Test that weather dataset loads and parses correctly."""
        dataset = load_weather_dataset("eval/weather_golden_dataset.json")

        assert isinstance(dataset, WeatherGoldenDataset)
        assert dataset.version == "1.0.0"
        assert len(dataset.cases) >= 5

    def test_load_weather_dataset_file_not_found(self):
        """Test error when file doesn't exist."""
        with pytest.raises(DatasetError, match="file not found"):
            load_weather_dataset("nonexistent.json")

    def test_load_weather_dataset_invalid_json(self):
        """Test error when JSON is invalid."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{invalid json")
            temp_path = f.name

        try:
            with pytest.raises(DatasetError, match="Invalid JSON"):
                load_weather_dataset(temp_path)
        finally:
            Path(temp_path).unlink()


class TestWeatherDatasetSchemaValidation:
    """Tests for weather dataset schema validation (T092)."""

    def test_dataset_requires_version(self):
        """Test that version field is required."""
        data = {
            "description": "Test",
            "cases": [
                {
                    "id": "test-001",
                    "query": "What's the weather?",
                    "expected_behavior": "success",
                    "rubric": "Should return weather data",
                }
            ]
            * 5,
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            with pytest.raises(DatasetError, match="validation failed"):
                load_weather_dataset(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_dataset_requires_cases(self):
        """Test that cases array is required."""
        data = {"version": "1.0.0", "description": "Test"}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            with pytest.raises(DatasetError, match="missing required field"):
                load_weather_dataset(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_case_requires_expected_behavior(self):
        """Test that expected_behavior is required for each case."""
        data = {
            "version": "1.0.0",
            "cases": [
                {"id": "test-001", "query": "Weather?", "rubric": "Test rubric"}
            ]
            * 5,
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            with pytest.raises(DatasetError, match="missing required fields"):
                load_weather_dataset(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_expected_behavior_must_be_valid(self):
        """Test that expected_behavior must be success|error|clarification."""
        data = {
            "version": "1.0.0",
            "cases": [
                {
                    "id": "test-001",
                    "query": "Weather?",
                    "expected_behavior": "invalid",
                    "rubric": "Test rubric that is long enough",
                }
            ]
            * 5,
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            with pytest.raises(DatasetError, match="validation failed"):
                load_weather_dataset(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_case_ids_must_be_unique(self):
        """Test that case IDs must be unique."""
        data = {
            "version": "1.0.0",
            "cases": [
                {
                    "id": "duplicate-001",
                    "query": f"Weather query {i}?",
                    "expected_behavior": "success",
                    "rubric": "Test rubric that is long enough",
                }
                for i in range(5)
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            with pytest.raises(DatasetError, match="unique"):
                load_weather_dataset(temp_path)
        finally:
            Path(temp_path).unlink()


class TestWeatherDatasetHelpers:
    """Tests for weather dataset helper functions."""

    def test_validate_weather_dataset_file_valid(self):
        """Test validation returns True for valid file."""
        is_valid, error = validate_weather_dataset_file(
            "eval/weather_golden_dataset.json"
        )
        assert is_valid is True
        assert error is None

    def test_validate_weather_dataset_file_invalid(self):
        """Test validation returns False for invalid file."""
        is_valid, error = validate_weather_dataset_file("nonexistent.json")
        assert is_valid is False
        assert error is not None

    def test_get_weather_dataset_info(self):
        """Test dataset info extraction."""
        dataset = load_weather_dataset("eval/weather_golden_dataset.json")
        info = get_weather_dataset_info(dataset)

        assert "version" in info
        assert "case_count" in info
        assert "success_cases" in info
        assert "error_cases" in info
        assert "clarification_cases" in info
        assert "tags" in info
        assert info["case_count"] == len(dataset.cases)

    def test_get_weather_case_by_id_found(self):
        """Test finding a case by ID."""
        dataset = load_weather_dataset("eval/weather_golden_dataset.json")
        case = get_weather_case_by_id(dataset, "weather-001")

        assert case is not None
        assert isinstance(case, WeatherTestCase)
        assert case.id == "weather-001"

    def test_get_weather_case_by_id_not_found(self):
        """Test None returned for non-existent ID."""
        dataset = load_weather_dataset("eval/weather_golden_dataset.json")
        case = get_weather_case_by_id(dataset, "nonexistent")

        assert case is None

    def test_is_weather_dataset_by_filename(self):
        """Test weather dataset detection by filename."""
        assert is_weather_dataset("eval/weather_golden_dataset.json") is True
        assert is_weather_dataset("eval/golden_dataset.json") is False

    def test_is_weather_dataset_by_content(self):
        """Test weather dataset detection by content."""
        # The actual weather dataset should be detected
        assert is_weather_dataset("eval/weather_golden_dataset.json") is True
