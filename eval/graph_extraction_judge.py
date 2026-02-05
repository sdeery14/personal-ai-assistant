"""
Graph extraction evaluation judge.

This module provides functions to evaluate knowledge graph extraction quality:
- Entity extraction precision: What fraction of extracted entities were expected
- Entity extraction recall: What fraction of expected entities were extracted
- Relationship extraction precision: What fraction of extracted relationships were expected
- Relationship extraction recall: What fraction of expected relationships were extracted
- False positive counting: Unwanted entity/relationship extractions
"""


class GraphExtractionJudge:
    """Judge for evaluating knowledge graph extraction quality."""

    def evaluate_entity_precision(
        self,
        actual_entities: list[dict],
        expected_keywords: list[list[str]],
    ) -> float:
        """Compute precision of entity extraction.

        Precision = (actual entities matching expected) / (total actual entities)

        An entity matches if its name contains any keyword from any expected
        entity's keyword list.

        Args:
            actual_entities: List of dicts with 'name' and 'entity_type' from tool calls
            expected_keywords: List of keyword lists from expected entities

        Returns:
            Precision score between 0.0 and 1.0
        """
        if not actual_entities:
            return 1.0 if not expected_keywords else 0.0

        all_expected = set()
        for kw_list in expected_keywords:
            for kw in kw_list:
                all_expected.add(kw.lower())

        if not all_expected:
            return 0.0

        matching = 0
        for entity in actual_entities:
            name_lower = entity.get("name", "").lower()
            if any(kw in name_lower for kw in all_expected):
                matching += 1

        return matching / len(actual_entities)

    def evaluate_entity_recall(
        self,
        actual_entities: list[dict],
        expected_keywords: list[list[str]],
    ) -> float:
        """Compute recall of entity extraction.

        Recall = (expected entities that have a matching extraction) / (total expected)

        An expected entity is found if any actual entity's name contains
        at least one keyword from that entity's keyword list.

        Args:
            actual_entities: List of dicts with 'name' and 'entity_type' from tool calls
            expected_keywords: List of keyword lists from expected entities

        Returns:
            Recall score between 0.0 and 1.0
        """
        if not expected_keywords:
            return 1.0

        found = 0
        for kw_list in expected_keywords:
            if not kw_list:
                continue
            for entity in actual_entities:
                name_lower = entity.get("name", "").lower()
                if any(kw.lower() in name_lower for kw in kw_list):
                    found += 1
                    break

        return found / len(expected_keywords)

    def evaluate_relationship_precision(
        self,
        actual_relationships: list[dict],
        expected_keywords: list[dict],
    ) -> float:
        """Compute precision of relationship extraction.

        Precision = (actual relationships matching expected) / (total actual)

        A relationship matches if its type matches and source/target names
        contain expected keywords.

        Args:
            actual_relationships: List of dicts with relationship_type, source, target
            expected_keywords: List of dicts with type, source_keywords, target_keywords

        Returns:
            Precision score between 0.0 and 1.0
        """
        if not actual_relationships:
            return 1.0 if not expected_keywords else 0.0

        if not expected_keywords:
            return 0.0

        matching = 0
        for rel in actual_relationships:
            rel_type = rel.get("relationship_type", "").upper()
            source = rel.get("source_entity_name", "").lower()
            target = rel.get("target_entity_name", "").lower()

            for expected in expected_keywords:
                exp_type = expected.get("type", "").upper()
                exp_source_kws = [k.lower() for k in expected.get("source_keywords", [])]
                exp_target_kws = [k.lower() for k in expected.get("target_keywords", [])]

                type_match = rel_type == exp_type
                source_match = any(kw in source for kw in exp_source_kws) if exp_source_kws else True
                target_match = any(kw in target for kw in exp_target_kws) if exp_target_kws else True

                if type_match and source_match and target_match:
                    matching += 1
                    break

        return matching / len(actual_relationships)

    def evaluate_relationship_recall(
        self,
        actual_relationships: list[dict],
        expected_keywords: list[dict],
    ) -> float:
        """Compute recall of relationship extraction.

        Recall = (expected relationships found) / (total expected)

        Args:
            actual_relationships: List of dicts with relationship_type, source, target
            expected_keywords: List of dicts with type, source_keywords, target_keywords

        Returns:
            Recall score between 0.0 and 1.0
        """
        if not expected_keywords:
            return 1.0

        found = 0
        for expected in expected_keywords:
            exp_type = expected.get("type", "").upper()
            exp_source_kws = [k.lower() for k in expected.get("source_keywords", [])]
            exp_target_kws = [k.lower() for k in expected.get("target_keywords", [])]

            for rel in actual_relationships:
                rel_type = rel.get("relationship_type", "").upper()
                source = rel.get("source_entity_name", "").lower()
                target = rel.get("target_entity_name", "").lower()

                type_match = rel_type == exp_type
                source_match = any(kw in source for kw in exp_source_kws) if exp_source_kws else True
                target_match = any(kw in target for kw in exp_target_kws) if exp_target_kws else True

                if type_match and source_match and target_match:
                    found += 1
                    break

        return found / len(expected_keywords)

    def count_entity_false_positives(
        self,
        actual_entities: list[dict],
        expected_keywords: list[list[str]],
    ) -> int:
        """Count false positive entity extractions.

        Args:
            actual_entities: List of dicts with 'name' from tool calls
            expected_keywords: List of keyword lists from expected entities

        Returns:
            Number of false positive entity extractions
        """
        if not actual_entities:
            return 0

        all_expected = set()
        for kw_list in expected_keywords:
            for kw in kw_list:
                all_expected.add(kw.lower())

        false_positives = 0
        for entity in actual_entities:
            name_lower = entity.get("name", "").lower()
            if not any(kw in name_lower for kw in all_expected):
                false_positives += 1

        return false_positives

    def count_relationship_false_positives(
        self,
        actual_relationships: list[dict],
        expected_keywords: list[dict],
    ) -> int:
        """Count false positive relationship extractions.

        Args:
            actual_relationships: List of dicts with relationship_type, source, target
            expected_keywords: List of dicts with type, source_keywords, target_keywords

        Returns:
            Number of false positive relationship extractions
        """
        if not actual_relationships:
            return 0

        false_positives = 0
        for rel in actual_relationships:
            rel_type = rel.get("relationship_type", "").upper()
            source = rel.get("source_entity_name", "").lower()
            target = rel.get("target_entity_name", "").lower()

            matched = False
            for expected in expected_keywords:
                exp_type = expected.get("type", "").upper()
                exp_source_kws = [k.lower() for k in expected.get("source_keywords", [])]
                exp_target_kws = [k.lower() for k in expected.get("target_keywords", [])]

                type_match = rel_type == exp_type
                source_match = any(kw in source for kw in exp_source_kws) if exp_source_kws else True
                target_match = any(kw in target for kw in exp_target_kws) if exp_target_kws else True

                if type_match and source_match and target_match:
                    matched = True
                    break

            if not matched:
                false_positives += 1

        return false_positives


# Convenience functions

def evaluate_entity_precision(
    actual_entities: list[dict],
    expected_keywords: list[list[str]],
) -> float:
    """Convenience function for entity precision evaluation."""
    judge = GraphExtractionJudge()
    return judge.evaluate_entity_precision(actual_entities, expected_keywords)


def evaluate_entity_recall(
    actual_entities: list[dict],
    expected_keywords: list[list[str]],
) -> float:
    """Convenience function for entity recall evaluation."""
    judge = GraphExtractionJudge()
    return judge.evaluate_entity_recall(actual_entities, expected_keywords)


def evaluate_relationship_precision(
    actual_relationships: list[dict],
    expected_keywords: list[dict],
) -> float:
    """Convenience function for relationship precision evaluation."""
    judge = GraphExtractionJudge()
    return judge.evaluate_relationship_precision(actual_relationships, expected_keywords)


def evaluate_relationship_recall(
    actual_relationships: list[dict],
    expected_keywords: list[dict],
) -> float:
    """Convenience function for relationship recall evaluation."""
    judge = GraphExtractionJudge()
    return judge.evaluate_relationship_recall(actual_relationships, expected_keywords)
