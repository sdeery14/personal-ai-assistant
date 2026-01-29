"""
Integration tests for eval/runner.py - End-to-end evaluation flow.

These tests verify:
- Full evaluation flow with mocked APIs
- MLflow integration (requires no running server for mocked tests)
- Error handling and retries
- Result aggregation and metrics calculation
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from eval.dataset import DatasetError, load_dataset
from eval.models import EvalRunMetrics, GoldenDataset
from eval.runner import (
    EvaluationResult,
    _prepare_eval_data,
    _process_eval_results,
    format_summary,
    run_evaluation,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def minimal_dataset_file(tmp_path):
    """Create a minimal valid dataset with 5 cases."""
    dataset = {
        "version": "1.0.0",
        "description": "Test dataset",
        "cases": [
            {
                "id": f"test-{i:03d}",
                "user_prompt": f"Test question {i}?",
                "rubric": f"Should correctly answer question {i}.",
            }
            for i in range(1, 6)
        ],
    }
    file_path = tmp_path / "test_dataset.json"
    with open(file_path, "w") as f:
        json.dump(dataset, f)
    return file_path


@pytest.fixture
def mock_settings(monkeypatch):
    """Set up mock environment for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1")
    monkeypatch.setenv("EVAL_JUDGE_MODEL", "gpt-4.1")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

    from eval.config import reset_settings

    reset_settings()


# =============================================================================
# Test: Dataset Preparation
# =============================================================================


class TestDatasetPreparation:
    """Tests for _prepare_eval_data function."""

    def test_prepare_eval_data_structure(self, minimal_dataset_file):
        """Should convert dataset to MLflow-compatible format."""
        dataset = load_dataset(minimal_dataset_file)
        eval_data = _prepare_eval_data(dataset)

        assert len(eval_data) == 5

        for item in eval_data:
            assert "inputs" in item
            assert "expectations" in item
            assert "_case_id" in item
            assert "question" in item["inputs"]
            assert "rubric" in item["expectations"]

    def test_prepare_eval_data_preserves_content(self, minimal_dataset_file):
        """Should preserve original content in converted format."""
        dataset = load_dataset(minimal_dataset_file)
        eval_data = _prepare_eval_data(dataset)

        first_case = dataset.cases[0]
        first_data = eval_data[0]

        assert first_data["inputs"]["question"] == first_case.user_prompt
        assert first_data["expectations"]["rubric"] == first_case.rubric
        assert first_data["_case_id"] == first_case.id


# =============================================================================
# Test: Dry Run Mode
# =============================================================================


class TestDryRunMode:
    """Tests for dry run (validation only) mode."""

    def test_dry_run_validates_dataset(self, minimal_dataset_file, mock_settings):
        """Dry run should validate dataset without running evaluation."""
        result = run_evaluation(
            dataset_path=minimal_dataset_file,
            dry_run=True,
        )

        assert isinstance(result, EvaluationResult)
        assert result.metrics.total_cases == 5
        assert result.mlflow_run_id is None  # No MLflow run in dry run
        assert result.results == []  # No results in dry run

    def test_dry_run_rejects_invalid_dataset(self, tmp_path, mock_settings):
        """Dry run should fail for invalid dataset."""
        # Create invalid dataset (too few cases)
        invalid = tmp_path / "invalid.json"
        invalid.write_text('{"version": "1.0.0", "cases": []}')

        with pytest.raises(DatasetError):
            run_evaluation(dataset_path=invalid, dry_run=True)


# =============================================================================
# Test: Result Processing
# =============================================================================


class TestResultProcessing:
    """Tests for _process_eval_results function."""

    def test_process_results_calculates_metrics(self, minimal_dataset_file):
        """Should calculate correct aggregate metrics."""
        import pandas as pd

        dataset = load_dataset(minimal_dataset_file)

        # Mock MLflow eval results
        mock_results = MagicMock()
        mock_results.tables = {
            "eval_results_table": pd.DataFrame(
                {
                    "quality/value": ["5", "4", "4", "3", "5"],  # 4 pass, 1 fail
                    "outputs/response": ["resp1", "resp2", "resp3", "resp4", "resp5"],
                    "quality/rationale": ["good"] * 5,
                }
            )
        }

        results, metrics = _process_eval_results(
            eval_results=mock_results,
            dataset=dataset,
            pass_threshold=0.80,
            score_threshold=3.5,
        )

        assert len(results) == 5
        assert metrics.passed_cases == 4  # Scores 4, 4, 5, 5 pass; score 3 fails
        assert metrics.failed_cases == 1
        assert metrics.average_score == (5 + 4 + 4 + 3 + 5) / 5  # 4.2
        assert metrics.pass_rate == 0.80  # 4/5

    def test_process_results_handles_errors(self, minimal_dataset_file):
        """Should mark cases as errors when processing fails."""
        import pandas as pd

        dataset = load_dataset(minimal_dataset_file)

        # Mock results with one case that will cause an error
        mock_results = MagicMock()
        mock_results.tables = {
            "eval_results_table": pd.DataFrame(
                {
                    "quality/value": [
                        "5",
                        "invalid",
                        "4",
                        "4",
                        "5",
                    ],  # Second is invalid
                    "outputs/response": ["resp1", "resp2", "resp3", "resp4", "resp5"],
                    "quality/rationale": ["good"] * 5,
                }
            )
        }

        results, metrics = _process_eval_results(
            eval_results=mock_results,
            dataset=dataset,
            pass_threshold=0.80,
            score_threshold=3.5,
        )

        # Should have processed 5 cases, with 1 error
        assert len(results) == 5
        assert metrics.error_cases == 1


# =============================================================================
# Test: Summary Formatting
# =============================================================================


class TestSummaryFormatting:
    """Tests for format_summary function."""

    def test_format_summary_pass(self, mock_settings):
        """Should format passing summary correctly."""
        from eval.config import get_eval_settings

        settings = get_eval_settings()

        result = EvaluationResult(
            metrics=EvalRunMetrics(
                total_cases=10,
                passed_cases=9,
                failed_cases=1,
                error_cases=0,
                pass_rate=0.90,
                average_score=4.5,
                overall_passed=True,
            ),
            results=[],
            mlflow_run_id="abc123",
            dataset_version="1.0.0",
        )

        summary = format_summary(result, settings)

        assert "PASS" in summary
        assert "90" in summary  # Pass rate
        assert "4.5" in summary  # Average score
        assert "abc123" in summary  # Run ID

    def test_format_summary_fail_with_reasons(self, mock_settings):
        """Should include failure reasons in summary."""
        from eval.config import get_eval_settings

        settings = get_eval_settings()

        result = EvaluationResult(
            metrics=EvalRunMetrics(
                total_cases=10,
                passed_cases=6,
                failed_cases=4,
                error_cases=0,
                pass_rate=0.60,
                average_score=3.2,
                overall_passed=False,
            ),
            results=[],
            mlflow_run_id="def456",
            dataset_version="1.0.0",
        )

        summary = format_summary(result, settings)

        assert "FAIL" in summary
        assert "60" in summary  # Pass rate
        assert "3.2" in summary  # Average score


# =============================================================================
# Test: Full Integration (Mocked API)
# =============================================================================


class TestFullIntegration:
    """Full integration tests with mocked external calls."""

    @patch("eval.runner.genai_evaluate")
    @patch("eval.runner.get_response")
    @patch("mlflow.start_run")
    @patch("mlflow.set_experiment")
    @patch("mlflow.set_tracking_uri")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metrics")
    @patch("mlflow.log_artifact")
    def test_full_evaluation_flow(
        self,
        mock_log_artifact,
        mock_log_metrics,
        mock_log_params,
        mock_set_uri,
        mock_set_exp,
        mock_start_run,
        mock_get_response,
        mock_genai_eval,
        minimal_dataset_file,
        mock_settings,
    ):
        """Should complete full evaluation flow with mocked APIs."""
        import pandas as pd

        # Mock MLflow run context
        mock_run = MagicMock()
        mock_run.info.run_id = "test-run-123"
        mock_start_run.return_value.__enter__ = MagicMock(return_value=mock_run)
        mock_start_run.return_value.__exit__ = MagicMock(return_value=False)

        # Mock assistant responses
        mock_get_response.return_value = "Test response"

        # Mock genai_evaluate results
        mock_eval_result = MagicMock()
        mock_eval_result.tables = {
            "eval_results_table": pd.DataFrame(
                {
                    "quality/value": ["5", "4", "5", "4", "5"],
                    "outputs/response": ["resp"] * 5,
                    "quality/rationale": ["good"] * 5,
                }
            )
        }
        mock_genai_eval.return_value = mock_eval_result

        # Run evaluation
        result = run_evaluation(
            dataset_path=minimal_dataset_file,
            verbose=False,
        )

        # Verify result
        assert isinstance(result, EvaluationResult)
        assert result.mlflow_run_id == "test-run-123"
        assert result.metrics.total_cases == 5
        assert result.metrics.overall_passed is True

        # Verify MLflow calls
        mock_set_uri.assert_called_once()
        mock_set_exp.assert_called_once()
        mock_log_params.assert_called_once()
        mock_log_metrics.assert_called_once()


# =============================================================================
# Test: Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in evaluation."""

    def test_missing_dataset_file(self, mock_settings):
        """Should raise DatasetError for missing dataset."""
        with pytest.raises(DatasetError) as exc_info:
            run_evaluation(dataset_path="nonexistent.json")
        assert "not found" in str(exc_info.value).lower()

    def test_invalid_dataset_format(self, tmp_path, mock_settings):
        """Should raise DatasetError for invalid JSON."""
        invalid = tmp_path / "invalid.json"
        invalid.write_text("{not valid json")

        with pytest.raises(DatasetError) as exc_info:
            run_evaluation(dataset_path=invalid)
        assert "invalid json" in str(exc_info.value).lower()
