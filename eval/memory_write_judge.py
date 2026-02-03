"""
Memory write evaluation judge.

This module provides functions to evaluate memory write quality:
- Extraction precision: What fraction of actual writes were expected
- Extraction recall: What fraction of expected writes were made
- False positive counting: Unwanted writes
"""


class MemoryWriteJudge:
    """Judge for evaluating memory write/extraction quality."""

    def evaluate_extraction_precision(
        self,
        actual_writes: list[str],
        expected_keywords: list[list[str]],
    ) -> float:
        """Compute precision of memory extraction.

        Precision = (actual writes that match expected) / (total actual writes)

        A write is considered matching if it contains any keyword from any
        expected action's keyword list.

        Args:
            actual_writes: List of actual memory contents written
            expected_keywords: List of keyword lists from expected actions

        Returns:
            Precision score between 0.0 and 1.0
        """
        if not actual_writes:
            return 1.0 if not expected_keywords else 0.0

        # Flatten all expected keywords
        all_expected = set()
        for kw_list in expected_keywords:
            for kw in kw_list:
                all_expected.add(kw.lower())

        if not all_expected:
            # No expected keywords - any write is a false positive
            return 0.0

        matching = 0
        for write in actual_writes:
            write_lower = write.lower()
            if any(kw in write_lower for kw in all_expected):
                matching += 1

        return matching / len(actual_writes)

    def evaluate_extraction_recall(
        self,
        actual_writes: list[str],
        expected_keywords: list[list[str]],
    ) -> float:
        """Compute recall of memory extraction.

        Recall = (expected actions that have a matching write) / (total expected actions)

        An expected action is considered found if any actual write contains
        at least one keyword from that action's keyword list.

        Args:
            actual_writes: List of actual memory contents written
            expected_keywords: List of keyword lists from expected actions

        Returns:
            Recall score between 0.0 and 1.0
        """
        if not expected_keywords:
            return 1.0

        found = 0
        for kw_list in expected_keywords:
            if not kw_list:
                continue
            # Check if any actual write contains at least one keyword
            for write in actual_writes:
                write_lower = write.lower()
                if any(kw.lower() in write_lower for kw in kw_list):
                    found += 1
                    break

        return found / len(expected_keywords)

    def count_false_positives(
        self,
        actual_writes: list[str],
        expected_keywords: list[list[str]],
    ) -> int:
        """Count false positive writes (writes with no matching expected action).

        Args:
            actual_writes: List of actual memory contents written
            expected_keywords: List of keyword lists from expected actions

        Returns:
            Number of false positive writes
        """
        if not actual_writes:
            return 0

        # Flatten all expected keywords
        all_expected = set()
        for kw_list in expected_keywords:
            for kw in kw_list:
                all_expected.add(kw.lower())

        false_positives = 0
        for write in actual_writes:
            write_lower = write.lower()
            if not any(kw in write_lower for kw in all_expected):
                false_positives += 1

        return false_positives


# Convenience functions

def evaluate_extraction_precision(
    actual_writes: list[str],
    expected_keywords: list[list[str]],
) -> float:
    """Convenience function for extraction precision evaluation."""
    judge = MemoryWriteJudge()
    return judge.evaluate_extraction_precision(actual_writes, expected_keywords)


def evaluate_extraction_recall(
    actual_writes: list[str],
    expected_keywords: list[list[str]],
) -> float:
    """Convenience function for extraction recall evaluation."""
    judge = MemoryWriteJudge()
    return judge.evaluate_extraction_recall(actual_writes, expected_keywords)


def count_false_positives(
    actual_writes: list[str],
    expected_keywords: list[list[str]],
) -> int:
    """Convenience function for false positive counting."""
    judge = MemoryWriteJudge()
    return judge.count_false_positives(actual_writes, expected_keywords)
