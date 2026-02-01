"""Unit tests for memory dataset loading and validation."""

import json
import tempfile
from pathlib import Path

import pytest

from eval.dataset import DatasetError, load_memory_dataset, validate_memory_dataset_file


class TestLoadMemoryDataset:
    """Tests for load_memory_dataset function."""

    def test_load_memory_dataset_parses_json(self):
        """T122: Verify memory dataset JSON parsing works."""
        dataset_content = {
            "version": "1.0.0",
            "description": "Test memory dataset",
            "cases": [
                {
                    "id": "test-001",
                    "query": "Test query",
                    "user_id": "test-user",
                    "setup_memories": [],
                    "expected_retrievals": ["expected"],
                    "rubric": "Test rubric for evaluation",
                },
                {
                    "id": "test-002",
                    "query": "Another query",
                    "user_id": "test-user",
                    "setup_memories": [],
                    "expected_retrievals": [],
                    "rubric": "Another rubric text here",
                },
                {
                    "id": "test-003",
                    "query": "Third query",
                    "user_id": "test-user",
                    "setup_memories": [],
                    "expected_retrievals": ["item1"],
                    "rubric": "Third rubric text here",
                },
                {
                    "id": "test-004",
                    "query": "Fourth query",
                    "user_id": "test-user",
                    "setup_memories": [],
                    "expected_retrievals": ["item2"],
                    "rubric": "Fourth rubric text here",
                },
                {
                    "id": "test-005",
                    "query": "Fifth query",
                    "user_id": "test-user",
                    "setup_memories": [],
                    "expected_retrievals": ["item3"],
                    "rubric": "Fifth rubric text here",
                },
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(dataset_content, f)
            temp_path = f.name

        try:
            dataset = load_memory_dataset(temp_path)

            assert dataset.version == "1.0.0"
            assert dataset.description == "Test memory dataset"
            assert len(dataset.cases) == 5
            assert dataset.cases[0].id == "test-001"
            assert dataset.cases[0].query == "Test query"
            assert dataset.cases[0].user_id == "test-user"
        finally:
            Path(temp_path).unlink()

    def test_memory_dataset_schema_validation_missing_query(self):
        """T123: Verify required field 'query' is checked."""
        dataset_content = {
            "version": "1.0.0",
            "cases": [
                {
                    "id": "test-001",
                    # Missing "query" field
                    "user_id": "test-user",
                    "expected_retrievals": [],
                    "rubric": "Test rubric here",
                },
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(dataset_content, f)
            temp_path = f.name

        try:
            with pytest.raises(DatasetError) as exc_info:
                load_memory_dataset(temp_path)

            assert "query" in str(exc_info.value).lower()
        finally:
            Path(temp_path).unlink()

    def test_memory_dataset_schema_validation_missing_user_id(self):
        """T123: Verify required field 'user_id' is checked."""
        dataset_content = {
            "version": "1.0.0",
            "cases": [
                {
                    "id": "test-001",
                    "query": "Test query",
                    # Missing "user_id" field
                    "expected_retrievals": [],
                    "rubric": "Test rubric here",
                },
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(dataset_content, f)
            temp_path = f.name

        try:
            with pytest.raises(DatasetError) as exc_info:
                load_memory_dataset(temp_path)

            assert "user_id" in str(exc_info.value).lower()
        finally:
            Path(temp_path).unlink()

    def test_memory_dataset_schema_validation_missing_expected_retrievals(self):
        """T123: Verify required field 'expected_retrievals' is checked."""
        dataset_content = {
            "version": "1.0.0",
            "cases": [
                {
                    "id": "test-001",
                    "query": "Test query",
                    "user_id": "test-user",
                    # Missing "expected_retrievals" field
                    "rubric": "Test rubric here",
                },
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(dataset_content, f)
            temp_path = f.name

        try:
            with pytest.raises(DatasetError) as exc_info:
                load_memory_dataset(temp_path)

            assert "expected_retrievals" in str(exc_info.value).lower()
        finally:
            Path(temp_path).unlink()

    def test_memory_dataset_file_not_found(self):
        """Verify error when file doesn't exist."""
        with pytest.raises(DatasetError) as exc_info:
            load_memory_dataset("/nonexistent/path/to/dataset.json")

        assert "not found" in str(exc_info.value).lower()

    def test_memory_dataset_invalid_json(self):
        """Verify error on invalid JSON."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{ invalid json }")
            temp_path = f.name

        try:
            with pytest.raises(DatasetError) as exc_info:
                load_memory_dataset(temp_path)

            assert "invalid json" in str(exc_info.value).lower()
        finally:
            Path(temp_path).unlink()

    def test_validate_memory_dataset_file_returns_tuple(self):
        """Verify validate function returns (bool, error_message)."""
        is_valid, error = validate_memory_dataset_file("/nonexistent/file.json")

        assert is_valid is False
        assert error is not None
        assert "not found" in error.lower()
