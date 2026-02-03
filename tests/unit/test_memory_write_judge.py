"""Unit tests for memory write evaluation judge."""

import pytest
from eval.memory_write_judge import MemoryWriteJudge


@pytest.fixture
def judge():
    """Create a MemoryWriteJudge instance."""
    return MemoryWriteJudge()


class TestExtractionPrecision:
    """Tests for extraction precision calculation."""

    def test_perfect_precision(self, judge):
        """All actual writes match expected."""
        actual = ["User's name is Sarah", "User lives in Portland"]
        expected = [["Sarah", "name"], ["Portland"]]

        result = judge.evaluate_extraction_precision(actual, expected)
        assert result == 1.0

    def test_zero_precision(self, judge):
        """No actual writes match expected."""
        actual = ["User likes cats", "User works remotely"]
        expected = [["Python", "programming"]]

        result = judge.evaluate_extraction_precision(actual, expected)
        assert result == 0.0

    def test_partial_precision(self, judge):
        """Some actual writes match expected."""
        actual = ["User's name is Sarah", "Random unrelated memory"]
        expected = [["Sarah", "name"]]

        result = judge.evaluate_extraction_precision(actual, expected)
        assert result == 0.5

    def test_empty_actual_with_expected(self, judge):
        """No writes but some expected."""
        result = judge.evaluate_extraction_precision([], [["Sarah"]])
        assert result == 0.0

    def test_empty_actual_empty_expected(self, judge):
        """No writes and nothing expected."""
        result = judge.evaluate_extraction_precision([], [])
        assert result == 1.0

    def test_writes_with_no_expected_keywords(self, judge):
        """Writes exist but no expected keywords (all are false positives)."""
        result = judge.evaluate_extraction_precision(["Some memory"], [])
        assert result == 0.0


class TestExtractionRecall:
    """Tests for extraction recall calculation."""

    def test_perfect_recall(self, judge):
        """All expected actions have matching writes."""
        actual = ["User's name is Sarah", "User lives in Portland"]
        expected = [["Sarah"], ["Portland"]]

        result = judge.evaluate_extraction_recall(actual, expected)
        assert result == 1.0

    def test_zero_recall(self, judge):
        """No expected actions have matching writes."""
        actual = ["User likes cats"]
        expected = [["Python"], ["Rust"]]

        result = judge.evaluate_extraction_recall(actual, expected)
        assert result == 0.0

    def test_partial_recall(self, judge):
        """Some expected actions have matching writes."""
        actual = ["User's name is Sarah"]
        expected = [["Sarah"], ["Portland"]]

        result = judge.evaluate_extraction_recall(actual, expected)
        assert result == 0.5

    def test_empty_expected(self, judge):
        """No expected items means perfect recall."""
        result = judge.evaluate_extraction_recall(["Some memory"], [])
        assert result == 1.0

    def test_empty_actual_with_expected(self, judge):
        """No writes but some expected."""
        result = judge.evaluate_extraction_recall([], [["Sarah"]])
        assert result == 0.0


class TestFalsePositives:
    """Tests for false positive counting."""

    def test_no_false_positives(self, judge):
        """All writes match expected."""
        actual = ["User's name is Sarah"]
        expected = [["Sarah", "name"]]

        result = judge.count_false_positives(actual, expected)
        assert result == 0

    def test_all_false_positives(self, judge):
        """No writes match expected."""
        actual = ["Random memory 1", "Random memory 2"]
        expected = [["Python"]]

        result = judge.count_false_positives(actual, expected)
        assert result == 2

    def test_mixed_false_positives(self, judge):
        """Some writes match, some don't."""
        actual = ["User's name is Sarah", "Random memory"]
        expected = [["Sarah"]]

        result = judge.count_false_positives(actual, expected)
        assert result == 1

    def test_empty_actual(self, judge):
        """No writes means no false positives."""
        result = judge.count_false_positives([], [["Sarah"]])
        assert result == 0

    def test_case_insensitive_matching(self, judge):
        """Keywords should match case-insensitively."""
        actual = ["User prefers DARK MODE"]
        expected = [["dark mode"]]

        result = judge.count_false_positives(actual, expected)
        assert result == 0
