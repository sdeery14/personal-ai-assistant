"""
Tests for eval/judge.py - Judge output structure validation.

These tests verify:
- Judge creation with correct configuration
- Score interpretation (pass/fail threshold)
- Score labels
- Judge output structure (NOT actual score values, which are non-deterministic)
"""

import pytest
from typing import Literal

from eval.judge import (
    PASS_THRESHOLD,
    SCORE_LABELS,
    create_quality_judge,
    score_to_label,
    score_to_passed,
)


# =============================================================================
# Test: Score Interpretation Functions
# =============================================================================


class TestScoreToPass:
    """Tests for score_to_passed function."""

    @pytest.mark.parametrize(
        "score,expected_passed",
        [
            (5, True),  # Excellent -> PASS
            (4, True),  # Good -> PASS
            (3, False),  # Acceptable -> FAIL
            (2, False),  # Poor -> FAIL
            (1, False),  # Unacceptable -> FAIL
        ],
    )
    def test_score_to_passed(self, score, expected_passed):
        """Should correctly convert score to pass/fail."""
        result = score_to_passed(score)
        assert result == expected_passed

    def test_pass_threshold_is_4(self):
        """PASS_THRESHOLD should be 4 (scores 4+ pass)."""
        assert PASS_THRESHOLD == 4


class TestScoreLabels:
    """Tests for score label mapping."""

    def test_all_scores_have_labels(self):
        """All valid scores (1-5) should have labels."""
        for score in range(1, 6):
            assert score in SCORE_LABELS
            assert isinstance(SCORE_LABELS[score], str)
            assert len(SCORE_LABELS[score]) > 0

    @pytest.mark.parametrize(
        "score,expected_label",
        [
            (1, "Unacceptable"),
            (2, "Poor"),
            (3, "Acceptable"),
            (4, "Good"),
            (5, "Excellent"),
        ],
    )
    def test_score_to_label(self, score, expected_label):
        """Should return correct label for each score."""
        result = score_to_label(score)
        assert result == expected_label

    def test_score_to_label_unknown(self):
        """Should return 'Unknown' for invalid scores."""
        result = score_to_label(99)
        assert result == "Unknown"


# =============================================================================
# Test: Judge Creation (Structure, not behavior)
# =============================================================================


class TestJudgeCreation:
    """Tests for judge creation and configuration."""

    def test_create_quality_judge_returns_judge(self, monkeypatch):
        """Should create a judge object without errors."""
        # Mock the settings to avoid needing actual env vars
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1")

        # Reset settings singleton to pick up new env
        from eval.config import reset_settings

        reset_settings()

        judge = create_quality_judge()

        # Verify judge is created (exact type depends on MLflow internals)
        assert judge is not None

    def test_judge_has_correct_name(self, monkeypatch):
        """Judge should be named 'quality'."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1")

        from eval.config import reset_settings

        reset_settings()

        judge = create_quality_judge()

        # The judge name should be accessible
        assert hasattr(judge, "name") or hasattr(judge, "_name")
        # Get name from whichever attribute exists
        name = getattr(judge, "name", None) or getattr(judge, "_name", None)
        assert name == "quality"


# =============================================================================
# Test: Judge Instructions Template
# =============================================================================


class TestJudgeInstructions:
    """Tests for judge instructions template structure."""

    def test_instructions_include_required_placeholders(self, monkeypatch):
        """Judge instructions should include MLflow template placeholders."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1")

        from eval.config import reset_settings
        reset_settings()

        judge = create_quality_judge()

        # Get instructions from judge (attribute name may vary)
        instructions = getattr(judge, "instructions", None) or getattr(
            judge, "_instructions", None
        )

        if instructions:
            # Verify template placeholders exist (MLflow 3.x uses top-level vars)
            assert "{{ inputs }}" in instructions
            assert "{{ outputs }}" in instructions
            assert "{{ expectations }}" in instructions

    def test_instructions_include_scoring_scale(self, monkeypatch):
        """Judge instructions should define the 1-5 scoring scale."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1")

        from eval.config import reset_settings
        reset_settings()

        judge = create_quality_judge()

        instructions = getattr(judge, "instructions", None) or getattr(
            judge, "_instructions", None
        )

        if instructions:
            # Verify all score levels are mentioned
            assert "5" in instructions and "Excellent" in instructions
            assert "4" in instructions and "Good" in instructions
            assert "3" in instructions and "Acceptable" in instructions
            assert "2" in instructions and "Poor" in instructions
            assert "1" in instructions and "Unacceptable" in instructions


# =============================================================================
# Test: Feedback Value Type
# =============================================================================


class TestFeedbackValueType:
    """Tests for judge feedback value type configuration."""

    def test_feedback_type_is_literal_1_to_5(self, monkeypatch):
        """Judge should use Literal['1', '2', '3', '4', '5'] as feedback type."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1")

        from eval.config import reset_settings

        reset_settings()

        judge = create_quality_judge()

        # Get feedback_value_type from judge
        feedback_type = getattr(judge, "feedback_value_type", None) or getattr(
            judge, "_feedback_value_type", None
        )

        if feedback_type:
            # Check that it's a Literal type with values "1" through "5"
            # The actual check depends on how Literal is represented
            type_str = str(feedback_type)
            for val in ["1", "2", "3", "4", "5"]:
                assert (
                    val in type_str or feedback_type == Literal["1", "2", "3", "4", "5"]
                )


# =============================================================================
# Test: Integration with EvalResult Model
# =============================================================================


class TestJudgeEvalResultIntegration:
    """Tests for judge output compatibility with EvalResult model."""

    def test_score_values_are_valid_for_eval_result(self):
        """All possible judge scores should be valid for EvalResult model."""
        from eval.models import EvalResult

        for score in range(1, 6):
            # Should not raise ValidationError
            result = EvalResult(
                case_id="test-001",
                user_prompt="Test question?",
                assistant_response="Test response.",
                score=score,
                passed=score >= 4,
                justification="Test justification.",
                duration_ms=1000,
            )
            assert result.score == score
            assert result.passed == (score >= 4)

    def test_invalid_scores_rejected_by_eval_result(self):
        """Scores outside 1-5 should be rejected by EvalResult model."""
        from eval.models import EvalResult
        from pydantic import ValidationError

        for invalid_score in [0, 6, -1, 100]:
            with pytest.raises(ValidationError):
                EvalResult(
                    case_id="test-001",
                    user_prompt="Test question?",
                    assistant_response="Test response.",
                    score=invalid_score,
                    passed=False,
                    justification="Test justification.",
                    duration_ms=1000,
                )
