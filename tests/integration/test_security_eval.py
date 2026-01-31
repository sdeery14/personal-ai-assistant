"""
Integration test for full security evaluation run.

This test verifies the complete security evaluation flow:
- Load security dataset
- Run evaluation with guardrails enabled
- Verify security metrics are computed and logged to MLflow
- Check exit code reflects security gate result
"""

import subprocess
import pytest
from pathlib import Path


class TestSecurityEvaluation:
    """Integration test for security evaluation (T051)."""

    def test_full_security_eval_run(self):
        """T051: Run full security eval and verify MLflow metrics logged."""
        # Run security evaluation
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "eval",
                "--dataset",
                "eval/security_golden_dataset.json",
                "--workers",
                "1",
            ],
            capture_output=True,
            text=True,
            env={"MLFLOW_GENAI_EVAL_SKIP_TRACE_VALIDATION": "True"},
        )

        # Check output contains security metrics
        output = result.stdout + result.stderr
        assert "Security dataset detected" in output or "SECURITY METRICS" in output
        assert "Block Rate" in output
        assert "False Positive Rate" in output
        assert "Top 10 Critical Miss" in output
        assert "SECURITY GATE" in output

        # Exit code should be 0 or 1 (not error codes like 2)
        # 0 = passed, 1 = failed (both are valid outcomes)
        assert result.returncode in [0, 1], \
            f"Expected exit code 0 or 1, got {result.returncode}"

        # If gate failed, verify failure reason is present
        if result.returncode == 1:
            assert "FAIL" in output
            # Should have one of the failure reasons
            assert any(
                reason in output
                for reason in [
                    "Block rate",
                    "False positive",
                    "Top 10 critical",
                ]
            )

    def test_security_eval_creates_mlflow_artifacts(self):
        """Verify security evaluation creates MLflow artifacts."""
        # This is a lighter test that just checks the eval runs without
        # making assertions about specific metrics values
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "eval",
                "--dataset",
                "eval/security_golden_dataset.json",
                "--workers",
                "1",
            ],
            capture_output=True,
            text=True,
            env={"MLFLOW_GENAI_EVAL_SKIP_TRACE_VALIDATION": "True"},
        )

        # Check that MLflow run ID is mentioned
        output = result.stdout + result.stderr
        assert "MLflow Run ID" in output or "Run ID" in output

        # Check dataset was loaded
        assert "15" in output  # 15 cases in security dataset

    def test_security_eval_with_verbose_flag(self):
        """Verify verbose output shows per-case results."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "eval",
                "--dataset",
                "eval/security_golden_dataset.json",
                "--verbose",
                "--workers",
                "1",
            ],
            capture_output=True,
            text=True,
            env={"MLFLOW_GENAI_EVAL_SKIP_TRACE_VALIDATION": "True"},
        )

        output = result.stdout + result.stderr

        # Verbose should show case IDs
        assert any(
            case_type in output
            for case_type in [
                "prompt-injection",
                "disallowed-content",
                "secret-extraction",
                "benign-edge",
            ]
        )

        # Should show PASS/FAIL per case
        assert "PASS" in output or "FAIL" in output
