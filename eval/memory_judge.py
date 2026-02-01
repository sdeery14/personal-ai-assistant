"""
Memory retrieval evaluation judge.

This module provides functions to evaluate memory retrieval quality:
- Recall@K: What fraction of expected items were retrieved
- Precision@K: What fraction of retrieved items were relevant
- Cross-user violation detection: Security check for user isolation
"""

from typing import Optional


class MemoryJudge:
    """Judge for evaluating memory retrieval quality."""

    def __init__(self, k: int = 5):
        """
        Initialize the memory judge.

        Args:
            k: The K value for recall@K and precision@K calculations.
        """
        self.k = k

    def evaluate_recall(
        self,
        retrieved: list[str],
        expected: list[str],
        k: Optional[int] = None,
    ) -> float:
        """
        Compute recall@K for memory retrieval.

        Recall = (number of expected items found in top K retrieved) / (total expected items)

        Args:
            retrieved: List of retrieved memory contents (in ranked order).
            expected: List of expected keywords/phrases that should be found.
            k: Override for K value (defaults to self.k).

        Returns:
            Recall score between 0.0 and 1.0.
        """
        if not expected:
            # No expected items means perfect recall (nothing to find)
            return 1.0

        k = k or self.k
        top_k_retrieved = retrieved[:k]

        # Count how many expected items appear in top K
        found_count = 0
        for expected_item in expected:
            expected_lower = expected_item.lower()
            for retrieved_item in top_k_retrieved:
                if expected_lower in retrieved_item.lower():
                    found_count += 1
                    break  # Found this expected item, move to next

        return found_count / len(expected)

    def evaluate_precision(
        self,
        retrieved: list[str],
        expected: list[str],
        k: Optional[int] = None,
    ) -> float:
        """
        Compute precision@K for memory retrieval.

        Precision = (number of retrieved items containing expected content) / K

        For memory retrieval, we consider a retrieved item "relevant" if it
        contains any of the expected keywords/phrases.

        Args:
            retrieved: List of retrieved memory contents (in ranked order).
            expected: List of expected keywords/phrases that indicate relevance.
            k: Override for K value (defaults to self.k).

        Returns:
            Precision score between 0.0 and 1.0.
        """
        if not retrieved:
            # No retrieved items means 0 precision (nothing retrieved)
            return 0.0 if expected else 1.0

        if not expected:
            # No expected items - edge case, treat all as relevant
            return 1.0

        k = k or self.k
        top_k_retrieved = retrieved[:k]

        # Count how many retrieved items are relevant
        relevant_count = 0
        for retrieved_item in top_k_retrieved:
            retrieved_lower = retrieved_item.lower()
            for expected_item in expected:
                if expected_item.lower() in retrieved_lower:
                    relevant_count += 1
                    break  # This item is relevant, move to next

        # Precision is relevant / total retrieved (up to K)
        return relevant_count / len(top_k_retrieved)

    def check_cross_user_violation(
        self,
        retrieved_user_ids: list[str],
        expected_user_id: str,
    ) -> bool:
        """
        Check if any retrieved memories belong to a different user.

        This is a CRITICAL security check. Memory retrieval must be
        strictly scoped to the requesting user's data.

        Args:
            retrieved_user_ids: List of user_ids from retrieved memories.
            expected_user_id: The user_id that made the query.

        Returns:
            True if there is a cross-user violation (SECURITY FAILURE).
            False if all retrieved memories belong to the expected user.
        """
        for user_id in retrieved_user_ids:
            if user_id != expected_user_id:
                return True  # VIOLATION: found memory from wrong user
        return False


def evaluate_recall(
    retrieved: list[str],
    expected: list[str],
    k: int = 5,
) -> float:
    """
    Convenience function for recall@K evaluation.

    Args:
        retrieved: List of retrieved memory contents (in ranked order).
        expected: List of expected keywords/phrases that should be found.
        k: The K value for top-K evaluation.

    Returns:
        Recall score between 0.0 and 1.0.
    """
    judge = MemoryJudge(k=k)
    return judge.evaluate_recall(retrieved, expected)


def evaluate_precision(
    retrieved: list[str],
    expected: list[str],
    k: int = 5,
) -> float:
    """
    Convenience function for precision@K evaluation.

    Args:
        retrieved: List of retrieved memory contents (in ranked order).
        expected: List of expected keywords/phrases that indicate relevance.
        k: The K value for top-K evaluation.

    Returns:
        Precision score between 0.0 and 1.0.
    """
    judge = MemoryJudge(k=k)
    return judge.evaluate_precision(retrieved, expected)


def check_cross_user_violation(
    retrieved_user_ids: list[str],
    expected_user_id: str,
) -> bool:
    """
    Convenience function for cross-user violation check.

    Args:
        retrieved_user_ids: List of user_ids from retrieved memories.
        expected_user_id: The user_id that made the query.

    Returns:
        True if there is a cross-user violation (SECURITY FAILURE).
        False if all retrieved memories belong to the expected user.
    """
    judge = MemoryJudge()
    return judge.check_cross_user_violation(retrieved_user_ids, expected_user_id)
