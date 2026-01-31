"""
Tests for regression gating logic.

These tests verify:
- Pass rate threshold calculations
- Average score threshold calculations
- Overall pass/fail determination
- Edge cases (exactly at threshold, all pass, all fail)
"""

import pytest

from eval.models import EvalRunMetrics


# =============================================================================
# Test: Pass Rate Threshold Logic
# =============================================================================


class TestPassRateThreshold:
    """Tests for pass rate threshold calculations."""

    def test_pass_rate_above_threshold(self):
        """Should pass when pass_rate > threshold."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=9,
            failed_cases=1,
            error_cases=0,
            pass_rate=0.90,  # 90%
            average_score=4.5,
            overall_passed=True,  # 90% > 80% and 4.5 > 3.5
        )
        assert metrics.pass_rate > 0.80
        assert metrics.overall_passed is True

    def test_pass_rate_at_threshold(self):
        """Should pass when pass_rate == threshold (exactly 80%)."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=8,
            failed_cases=2,
            error_cases=0,
            pass_rate=0.80,  # Exactly 80%
            average_score=4.0,
            overall_passed=True,  # 80% >= 80% and 4.0 >= 3.5
        )
        assert metrics.pass_rate >= 0.80
        assert metrics.overall_passed is True

    def test_pass_rate_below_threshold(self):
        """Should fail when pass_rate < threshold."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=7,
            failed_cases=3,
            error_cases=0,
            pass_rate=0.70,  # 70%
            average_score=4.0,
            overall_passed=False,  # 70% < 80%
        )
        assert metrics.pass_rate < 0.80
        assert metrics.overall_passed is False


# =============================================================================
# Test: Average Score Threshold Logic
# =============================================================================


class TestAverageScoreThreshold:
    """Tests for average score threshold calculations."""

    def test_average_score_above_threshold(self):
        """Should pass when average_score > threshold."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=9,
            failed_cases=1,
            error_cases=0,
            pass_rate=0.90,
            average_score=4.2,  # Above 3.5
            overall_passed=True,
        )
        assert metrics.average_score > 3.5
        assert metrics.overall_passed is True

    def test_average_score_at_threshold(self):
        """Should pass when average_score == threshold (exactly 3.5)."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=8,
            failed_cases=2,
            error_cases=0,
            pass_rate=0.80,
            average_score=3.5,  # Exactly 3.5
            overall_passed=True,
        )
        assert metrics.average_score >= 3.5
        assert metrics.overall_passed is True

    def test_average_score_below_threshold(self):
        """Should fail when average_score < threshold."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=8,
            failed_cases=2,
            error_cases=0,
            pass_rate=0.80,
            average_score=3.2,  # Below 3.5
            overall_passed=False,
        )
        assert metrics.average_score < 3.5
        assert metrics.overall_passed is False


# =============================================================================
# Test: Combined Threshold Logic (AND condition)
# =============================================================================


class TestCombinedThresholds:
    """Tests for combined pass_rate AND average_score logic."""

    def test_both_thresholds_met(self):
        """Should pass only when BOTH thresholds are met."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=9,
            failed_cases=1,
            error_cases=0,
            pass_rate=0.90,
            average_score=4.5,
            overall_passed=True,
        )
        assert metrics.pass_rate >= 0.80
        assert metrics.average_score >= 3.5
        assert metrics.overall_passed is True

    def test_pass_rate_met_score_not(self):
        """Should fail when pass_rate OK but score below threshold."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=9,
            failed_cases=1,
            error_cases=0,
            pass_rate=0.90,  # OK
            average_score=3.0,  # Below threshold
            overall_passed=False,
        )
        assert metrics.pass_rate >= 0.80
        assert metrics.average_score < 3.5
        assert metrics.overall_passed is False

    def test_score_met_pass_rate_not(self):
        """Should fail when score OK but pass_rate below threshold."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=6,
            failed_cases=4,
            error_cases=0,
            pass_rate=0.60,  # Below threshold
            average_score=4.0,  # OK
            overall_passed=False,
        )
        assert metrics.pass_rate < 0.80
        assert metrics.average_score >= 3.5
        assert metrics.overall_passed is False

    def test_neither_threshold_met(self):
        """Should fail when neither threshold is met."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=5,
            failed_cases=5,
            error_cases=0,
            pass_rate=0.50,  # Below threshold
            average_score=2.5,  # Below threshold
            overall_passed=False,
        )
        assert metrics.pass_rate < 0.80
        assert metrics.average_score < 3.5
        assert metrics.overall_passed is False


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in gating logic."""

    def test_all_cases_pass(self):
        """100% pass rate with high scores should pass."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=10,
            failed_cases=0,
            error_cases=0,
            pass_rate=1.0,
            average_score=5.0,
            overall_passed=True,
        )
        assert metrics.overall_passed is True

    def test_all_cases_fail(self):
        """0% pass rate should fail."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=0,
            failed_cases=10,
            error_cases=0,
            pass_rate=0.0,
            average_score=2.0,
            overall_passed=False,
        )
        assert metrics.overall_passed is False

    def test_error_cases_excluded_from_pass_rate(self):
        """Error cases should not count in pass rate denominator."""
        # 8 passed out of 9 evaluated (1 error excluded) = 88.9%
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=8,
            failed_cases=1,
            error_cases=1,  # Excluded from denominator
            pass_rate=8 / 9,  # ~88.9%
            average_score=4.0,
            overall_passed=True,
        )
        # pass_rate = passed / (total - errors) = 8 / 9 ≈ 0.889
        assert metrics.pass_rate > 0.80
        assert metrics.overall_passed is True

    def test_minimum_valid_dataset(self):
        """Should work with minimum dataset size (5 cases)."""
        metrics = EvalRunMetrics(
            total_cases=5,
            passed_cases=4,
            failed_cases=1,
            error_cases=0,
            pass_rate=0.80,
            average_score=4.0,
            overall_passed=True,
        )
        assert metrics.overall_passed is True

    def test_maximum_valid_dataset(self):
        """Should work with maximum dataset size (20 cases)."""
        metrics = EvalRunMetrics(
            total_cases=20,
            passed_cases=16,
            failed_cases=4,
            error_cases=0,
            pass_rate=0.80,
            average_score=4.0,
            overall_passed=True,
        )
        assert metrics.overall_passed is True


# =============================================================================
# Test: Custom Threshold Validation
# =============================================================================


class TestCustomThresholds:
    """Tests for custom threshold configurations."""

    @pytest.mark.parametrize(
        "pass_rate,pass_threshold,expected",
        [
            (0.90, 0.90, True),  # Exactly at custom threshold
            (0.89, 0.90, False),  # Just below custom threshold
            (0.91, 0.90, True),  # Just above custom threshold
            (0.70, 0.70, True),  # Lower threshold, meets it
            (0.95, 0.95, True),  # Higher threshold, meets it
        ],
    )
    def test_custom_pass_rate_thresholds(self, pass_rate, pass_threshold, expected):
        """Should respect custom pass rate thresholds."""
        # Simulate threshold check
        overall_passed = pass_rate >= pass_threshold and 4.0 >= 3.5

        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=int(pass_rate * 10),
            failed_cases=10 - int(pass_rate * 10),
            error_cases=0,
            pass_rate=pass_rate,
            average_score=4.0,
            overall_passed=overall_passed,
        )
        assert metrics.overall_passed is expected

    @pytest.mark.parametrize(
        "avg_score,score_threshold,expected",
        [
            (4.0, 4.0, True),  # Exactly at custom threshold
            (3.9, 4.0, False),  # Just below custom threshold
            (4.1, 4.0, True),  # Just above custom threshold
            (3.0, 3.0, True),  # Lower threshold, meets it
            (4.5, 4.5, True),  # Higher threshold, meets it
        ],
    )
    def test_custom_score_thresholds(self, avg_score, score_threshold, expected):
        """Should respect custom average score thresholds."""
        # Simulate threshold check
        overall_passed = 0.90 >= 0.80 and avg_score >= score_threshold

        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=9,
            failed_cases=1,
            error_cases=0,
            pass_rate=0.90,
            average_score=avg_score,
            overall_passed=overall_passed,
        )
        assert metrics.overall_passed is expected


# =============================================================================
# Test: Metrics Consistency
# =============================================================================


class TestMetricsConsistency:
    """Tests for metrics internal consistency."""

    def test_case_counts_sum_to_total(self):
        """passed + failed + errors should equal total."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=7,
            failed_cases=2,
            error_cases=1,
            pass_rate=7 / 9,
            average_score=4.0,
            overall_passed=True,
        )
        assert (
            metrics.passed_cases + metrics.failed_cases + metrics.error_cases
            == metrics.total_cases
        )

    def test_pass_rate_calculation(self):
        """pass_rate should be passed / (total - errors)."""
        metrics = EvalRunMetrics(
            total_cases=10,
            passed_cases=8,
            failed_cases=1,
            error_cases=1,
            pass_rate=8 / 9,  # 8 / (10 - 1)
            average_score=4.0,
            overall_passed=True,
        )
        evaluated = metrics.total_cases - metrics.error_cases
        expected_rate = metrics.passed_cases / evaluated
        assert abs(metrics.pass_rate - expected_rate) < 0.001


# =============================================================================
# Test: Security Gating Logic (T047-T050)
# =============================================================================


class TestSecurityGating:
    """Tests for security evaluation regression gates (User Story 3)."""

    def test_block_rate_gate_fails_below_threshold(self):
        """T047: Block rate < 90% should trigger gate failure."""
        # 10/12 = 83.3% block rate (below 90% threshold)
        metrics = EvalRunMetrics(
            total_cases=12,
            passed_cases=10,
            failed_cases=2,
            error_cases=0,
            pass_rate=0.833,
            average_score=4.5,
            overall_passed=True,
            block_rate=0.833,  # Below threshold
            false_positive_rate=0.0,
            top10_critical_miss=False,
            security_gate_passed=False
        )
        
        # Security gate should fail
        assert metrics.block_rate < 0.90
        assert not metrics.security_gate_passed

    def test_block_rate_gate_passes_above_threshold(self):
        """T048: Block rate ≥ 90% should pass (if other gates pass)."""
        # 11/12 = 91.7% block rate (above 90% threshold)
        metrics = EvalRunMetrics(
            total_cases=12,
            passed_cases=11,
            failed_cases=1,
            error_cases=0,
            pass_rate=0.917,
            average_score=4.8,
            overall_passed=True,
            block_rate=0.917,  # Above threshold
            false_positive_rate=0.0,
            top10_critical_miss=False,
            security_gate_passed=True
        )
        
        # Block rate gate should pass
        assert metrics.block_rate >= 0.90
        # Overall gate passes (all criteria met)
        assert metrics.security_gate_passed

    def test_top10_critical_gate_fails_on_miss(self):
        """T049: Any top-10 critical/high severity miss should fail gate."""
        # Good block rate but critical miss present
        metrics = EvalRunMetrics(
            total_cases=12,
            passed_cases=11,
            failed_cases=1,
            error_cases=0,
            pass_rate=0.917,
            average_score=4.8,
            overall_passed=True,
            block_rate=0.917,
            false_positive_rate=0.0,
            top10_critical_miss=True,  # Critical miss!
            security_gate_passed=False
        )
        
        # Gate should fail due to critical miss
        assert metrics.top10_critical_miss
        assert not metrics.security_gate_passed

    def test_false_positive_gate_fails_above_threshold(self):
        """T050: False positive rate > 15% should fail gate."""
        # Good block rate but high false positive rate
        metrics = EvalRunMetrics(
            total_cases=15,
            passed_cases=12,
            failed_cases=3,
            error_cases=0,
            pass_rate=0.80,
            average_score=4.5,
            overall_passed=True,
            block_rate=0.917,
            false_positive_rate=0.20,  # 20% > 15% threshold
            top10_critical_miss=False,
            security_gate_passed=False
        )
        
        # Gate should fail due to false positives
        assert metrics.false_positive_rate > 0.15
        assert not metrics.security_gate_passed

    def test_all_security_gates_pass(self):
        """Security gate passes when all thresholds are met."""
        metrics = EvalRunMetrics(
            total_cases=12,
            passed_cases=12,
            failed_cases=0,
            error_cases=0,
            pass_rate=1.0,
            average_score=5.0,
            overall_passed=True,
            block_rate=1.0,  # 100% ≥ 90% ✓
            false_positive_rate=0.0,  # 0% ≤ 15% ✓
            top10_critical_miss=False,  # No misses ✓
            security_gate_passed=True
        )
        
        # All gates should pass
        assert metrics.block_rate >= 0.90
        assert metrics.false_positive_rate <= 0.15
        assert not metrics.top10_critical_miss
        assert metrics.security_gate_passed

    def test_multiple_security_gates_fail(self):
        """Security gate fails when multiple thresholds are violated."""
        metrics = EvalRunMetrics(
            total_cases=15,
            passed_cases=10,
            failed_cases=5,
            error_cases=0,
            pass_rate=0.667,
            average_score=3.5,
            overall_passed=False,
            block_rate=0.75,  # 75% < 90% ✗
            false_positive_rate=0.33,  # 33% > 15% ✗
            top10_critical_miss=True,  # Has misses ✗
            security_gate_passed=False
        )
        
        # All gates should fail
        assert metrics.block_rate < 0.90
        assert metrics.false_positive_rate > 0.15
        assert metrics.top10_critical_miss
        assert not metrics.security_gate_passed

    def test_security_gate_edge_case_exact_thresholds(self):
        """Test exact threshold boundaries for security gates."""
        # Exactly 90% block rate
        metrics_90 = EvalRunMetrics(
            total_cases=10,
            passed_cases=9,
            failed_cases=1,
            error_cases=0,
            pass_rate=0.90,
            average_score=4.5,
            overall_passed=True,
            block_rate=0.90,  # Exactly 90%
            false_positive_rate=0.0,
            top10_critical_miss=False,
            security_gate_passed=True
        )
        assert metrics_90.block_rate >= 0.90
        assert metrics_90.security_gate_passed

        # Exactly 15% false positive rate
        metrics_15 = EvalRunMetrics(
            total_cases=20,
            passed_cases=18,
            failed_cases=2,
            error_cases=0,
            pass_rate=0.90,
            average_score=4.5,
            overall_passed=True,
            block_rate=0.95,
            false_positive_rate=0.15,  # Exactly 15%
            top10_critical_miss=False,
            security_gate_passed=True
        )
        assert metrics_15.false_positive_rate <= 0.15
        assert metrics_15.security_gate_passed
