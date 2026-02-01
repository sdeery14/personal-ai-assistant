"""Unit tests for memory retrieval judge."""

import pytest

from eval.memory_judge import (
    MemoryJudge,
    check_cross_user_violation,
    evaluate_precision,
    evaluate_recall,
)


class TestEvaluateRecall:
    """Tests for recall@K calculation."""

    def test_evaluate_recall_correct_calculation(self):
        """T124: Verify recall formula is correct."""
        retrieved = [
            "User prefers uv over pip",
            "Project uses FastAPI",
            "Testing with pytest",
        ]
        expected = ["uv", "FastAPI"]

        recall = evaluate_recall(retrieved, expected, k=5)

        # Both expected items found in top 5
        assert recall == 1.0

    def test_evaluate_recall_partial_match(self):
        """Test recall when only some expected items are found."""
        retrieved = [
            "User prefers uv over pip",
            "Project uses Docker",
            "Redis for caching",
        ]
        expected = ["uv", "FastAPI", "pytest"]

        recall = evaluate_recall(retrieved, expected, k=5)

        # Only 1 of 3 expected items found
        assert recall == pytest.approx(1 / 3)

    def test_evaluate_recall_no_matches(self):
        """Test recall when no expected items are found."""
        retrieved = [
            "Unrelated content",
            "More unrelated stuff",
        ]
        expected = ["uv", "FastAPI"]

        recall = evaluate_recall(retrieved, expected, k=5)

        assert recall == 0.0

    def test_evaluate_recall_empty_expected(self):
        """Test recall when no items are expected."""
        retrieved = ["Some content"]
        expected = []

        recall = evaluate_recall(retrieved, expected, k=5)

        # Nothing to find means perfect recall
        assert recall == 1.0

    def test_evaluate_recall_empty_retrieved(self):
        """Test recall when nothing is retrieved."""
        retrieved = []
        expected = ["uv", "FastAPI"]

        recall = evaluate_recall(retrieved, expected, k=5)

        assert recall == 0.0

    def test_evaluate_recall_respects_k(self):
        """Test that recall only considers top K results."""
        retrieved = [
            "Irrelevant 1",
            "Irrelevant 2",
            "Irrelevant 3",
            "Irrelevant 4",
            "Irrelevant 5",
            "User prefers uv over pip",  # Position 6, outside top 5
        ]
        expected = ["uv"]

        recall = evaluate_recall(retrieved, expected, k=5)

        # uv is at position 6, outside top 5
        assert recall == 0.0

    def test_evaluate_recall_case_insensitive(self):
        """Test that matching is case insensitive."""
        retrieved = ["User prefers UV over PIP"]
        expected = ["uv", "pip"]

        recall = evaluate_recall(retrieved, expected, k=5)

        assert recall == 1.0


class TestEvaluatePrecision:
    """Tests for precision@K calculation."""

    def test_evaluate_precision_correct_calculation(self):
        """T125: Verify precision formula is correct."""
        retrieved = [
            "User prefers uv over pip",
            "Project uses FastAPI",
            "Testing with pytest",
        ]
        expected = ["uv", "FastAPI"]

        precision = evaluate_precision(retrieved, expected, k=5)

        # 2 of 3 retrieved items are relevant
        assert precision == pytest.approx(2 / 3)

    def test_evaluate_precision_all_relevant(self):
        """Test precision when all retrieved items are relevant."""
        retrieved = [
            "User prefers uv",
            "FastAPI is used",
        ]
        expected = ["uv", "FastAPI"]

        precision = evaluate_precision(retrieved, expected, k=5)

        assert precision == 1.0

    def test_evaluate_precision_none_relevant(self):
        """Test precision when no retrieved items are relevant."""
        retrieved = [
            "Unrelated content",
            "More unrelated stuff",
        ]
        expected = ["uv", "FastAPI"]

        precision = evaluate_precision(retrieved, expected, k=5)

        assert precision == 0.0

    def test_evaluate_precision_empty_retrieved(self):
        """Test precision when nothing is retrieved."""
        retrieved = []
        expected = ["uv"]

        precision = evaluate_precision(retrieved, expected, k=5)

        assert precision == 0.0

    def test_evaluate_precision_empty_expected(self):
        """Test precision when no items are expected."""
        retrieved = ["Some content"]
        expected = []

        precision = evaluate_precision(retrieved, expected, k=5)

        # Edge case: no expectations means all are "relevant"
        assert precision == 1.0

    def test_evaluate_precision_respects_k(self):
        """Test that precision only considers top K results."""
        retrieved = [
            "Irrelevant 1",
            "Irrelevant 2",
            "Irrelevant 3",
            "Irrelevant 4",
            "Irrelevant 5",
            "User prefers uv",  # Position 6, outside top 5
        ]
        expected = ["uv"]

        precision = evaluate_precision(retrieved, expected, k=5)

        # Only looking at top 5, which are all irrelevant
        assert precision == 0.0


class TestCrossUserViolation:
    """Tests for cross-user security violation detection."""

    def test_cross_user_violation_detected(self):
        """T126: Verify detection of cross-user violations."""
        retrieved_user_ids = ["test-user", "other-user", "test-user"]
        expected_user_id = "test-user"

        violation = check_cross_user_violation(retrieved_user_ids, expected_user_id)

        assert violation is True

    def test_cross_user_violation_not_detected(self):
        """Test no violation when all memories belong to correct user."""
        retrieved_user_ids = ["test-user", "test-user", "test-user"]
        expected_user_id = "test-user"

        violation = check_cross_user_violation(retrieved_user_ids, expected_user_id)

        assert violation is False

    def test_cross_user_violation_empty_retrieved(self):
        """Test no violation when no memories retrieved."""
        retrieved_user_ids = []
        expected_user_id = "test-user"

        violation = check_cross_user_violation(retrieved_user_ids, expected_user_id)

        assert violation is False

    def test_cross_user_violation_all_wrong_user(self):
        """Test violation when all memories belong to wrong user."""
        retrieved_user_ids = ["other-user", "other-user"]
        expected_user_id = "test-user"

        violation = check_cross_user_violation(retrieved_user_ids, expected_user_id)

        assert violation is True


class TestMemoryJudgeClass:
    """Tests for MemoryJudge class."""

    def test_judge_default_k(self):
        """Test judge uses default k=5."""
        judge = MemoryJudge()

        assert judge.k == 5

    def test_judge_custom_k(self):
        """Test judge accepts custom k value."""
        judge = MemoryJudge(k=10)

        assert judge.k == 10

    def test_judge_recall_method(self):
        """Test judge's recall method."""
        judge = MemoryJudge(k=3)
        retrieved = ["uv content", "FastAPI content", "pytest content"]
        expected = ["uv", "FastAPI"]

        recall = judge.evaluate_recall(retrieved, expected)

        assert recall == 1.0

    def test_judge_precision_method(self):
        """Test judge's precision method."""
        judge = MemoryJudge(k=3)
        retrieved = ["uv content", "unrelated", "FastAPI content"]
        expected = ["uv", "FastAPI"]

        precision = judge.evaluate_precision(retrieved, expected)

        assert precision == pytest.approx(2 / 3)

    def test_judge_cross_user_method(self):
        """Test judge's cross-user violation method."""
        judge = MemoryJudge()

        assert judge.check_cross_user_violation(["user-a"], "user-b") is True
        assert judge.check_cross_user_violation(["user-a"], "user-a") is False
