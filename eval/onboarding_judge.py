"""
Onboarding conversation quality judge.

This module provides:
- OnboardingJudge: Keyword-based recall evaluation for memory saves and entity creates
- Convenience functions for computing memory/entity recall from tool call data
"""


class OnboardingJudge:
    """Judge for evaluating onboarding conversation extraction quality."""

    def evaluate_memory_recall(
        self,
        actual_writes: list[str],
        expected_keywords: list[str],
    ) -> float:
        """Compute recall of memory extraction during onboarding.

        Recall = (expected keywords that appear in any write) / (total expected keywords)

        Args:
            actual_writes: List of actual memory contents written via save_memory calls.
            expected_keywords: List of keywords expected to appear in saved memories.

        Returns:
            Recall score between 0.0 and 1.0.
        """
        if not expected_keywords:
            return 1.0

        all_writes_lower = " ".join(w.lower() for w in actual_writes)

        found = 0
        for kw in expected_keywords:
            if kw.lower() in all_writes_lower:
                found += 1

        return found / len(expected_keywords)

    def evaluate_entity_recall(
        self,
        actual_entities: list[str],
        expected_entities: list[str],
    ) -> float:
        """Compute recall of entity creation during onboarding.

        Recall = (expected entities that were created) / (total expected entities)

        An expected entity is considered found if any actual entity name contains
        the expected name (case-insensitive).

        Args:
            actual_entities: List of entity names created via save_entity calls.
            expected_entities: List of entity names expected to be created.

        Returns:
            Recall score between 0.0 and 1.0.
        """
        if not expected_entities:
            return 1.0

        actual_lower = [e.lower() for e in actual_entities]

        found = 0
        for expected in expected_entities:
            exp_lower = expected.lower()
            if any(exp_lower in actual for actual in actual_lower):
                found += 1

        return found / len(expected_entities)


# Convenience functions

def evaluate_memory_recall(
    actual_writes: list[str],
    expected_keywords: list[str],
) -> float:
    """Convenience function for memory recall evaluation."""
    judge = OnboardingJudge()
    return judge.evaluate_memory_recall(actual_writes, expected_keywords)


def evaluate_entity_recall(
    actual_entities: list[str],
    expected_entities: list[str],
) -> float:
    """Convenience function for entity recall evaluation."""
    judge = OnboardingJudge()
    return judge.evaluate_entity_recall(actual_entities, expected_entities)
