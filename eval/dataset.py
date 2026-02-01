"""
Golden dataset loading and validation.

This module provides functions to load, validate, and work with the golden
dataset used for evaluation. It uses JSON Schema validation to ensure data
integrity.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from eval.models import GoldenDataset, MemoryGoldenDataset, MemoryTestCase, TestCase


class DatasetError(Exception):
    """Raised when dataset loading or validation fails."""

    pass


def load_dataset(path: str | Path) -> GoldenDataset:
    """
    Load and validate a golden dataset from a JSON file.

    Args:
        path: Path to the golden dataset JSON file.

    Returns:
        Validated GoldenDataset instance.

    Raises:
        DatasetError: If the file cannot be read or validation fails.
    """
    path = Path(path)

    # Check file exists
    if not path.exists():
        raise DatasetError(f"Dataset file not found: {path}")

    if not path.is_file():
        raise DatasetError(f"Dataset path is not a file: {path}")

    # Read JSON
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DatasetError(f"Invalid JSON in dataset file: {e}")
    except OSError as e:
        raise DatasetError(f"Failed to read dataset file: {e}")

    # Validate with Pydantic
    try:
        dataset = GoldenDataset.model_validate(data)
    except ValidationError as e:
        errors = _format_validation_errors(e)
        raise DatasetError(f"Dataset validation failed:\n{errors}")

    return dataset


def _format_validation_errors(error: ValidationError) -> str:
    """Format Pydantic validation errors for readable output."""
    lines = []
    for err in error.errors():
        loc = " -> ".join(str(x) for x in err["loc"])
        msg = err["msg"]
        lines.append(f"  - {loc}: {msg}")
    return "\n".join(lines)


def validate_dataset_file(path: str | Path) -> tuple[bool, str | None]:
    """
    Validate a dataset file without raising exceptions.

    Args:
        path: Path to the golden dataset JSON file.

    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is None.
    """
    try:
        load_dataset(path)
        return True, None
    except DatasetError as e:
        return False, str(e)


def get_dataset_info(dataset: GoldenDataset) -> dict[str, Any]:
    """
    Get summary information about a dataset.

    Args:
        dataset: Validated GoldenDataset instance.

    Returns:
        Dictionary with dataset info (version, count, tags, etc.).
    """
    all_tags: set[str] = set()
    for case in dataset.cases:
        if case.tags:
            all_tags.update(case.tags)

    return {
        "version": dataset.version,
        "description": dataset.description,
        "case_count": len(dataset.cases),
        "tags": sorted(all_tags),
        "case_ids": [case.id for case in dataset.cases],
    }


def get_case_by_id(dataset: GoldenDataset, case_id: str) -> TestCase | None:
    """
    Get a specific test case by ID.

    Args:
        dataset: Validated GoldenDataset instance.
        case_id: The case ID to find.

    Returns:
        TestCase if found, None otherwise.
    """
    for case in dataset.cases:
        if case.id == case_id:
            return case
    return None


# Memory-specific dataset loading functions


def load_memory_dataset(path: str | Path) -> MemoryGoldenDataset:
    """
    Load and validate a memory evaluation dataset from a JSON file.

    Args:
        path: Path to the memory golden dataset JSON file.

    Returns:
        Validated MemoryGoldenDataset instance.

    Raises:
        DatasetError: If the file cannot be read or validation fails.
    """
    path = Path(path)

    # Check file exists
    if not path.exists():
        raise DatasetError(f"Memory dataset file not found: {path}")

    if not path.is_file():
        raise DatasetError(f"Memory dataset path is not a file: {path}")

    # Read JSON
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DatasetError(f"Invalid JSON in memory dataset file: {e}")
    except OSError as e:
        raise DatasetError(f"Failed to read memory dataset file: {e}")

    # Validate required fields
    if "cases" not in data:
        raise DatasetError("Memory dataset missing required field: 'cases'")

    for idx, case in enumerate(data.get("cases", [])):
        required_fields = ["id", "query", "user_id", "expected_retrievals", "rubric"]
        missing = [f for f in required_fields if f not in case]
        if missing:
            raise DatasetError(
                f"Memory dataset case {idx} missing required fields: {missing}"
            )

    # Validate with Pydantic
    try:
        dataset = MemoryGoldenDataset.model_validate(data)
    except ValidationError as e:
        errors = _format_validation_errors(e)
        raise DatasetError(f"Memory dataset validation failed:\n{errors}")

    return dataset


def validate_memory_dataset_file(path: str | Path) -> tuple[bool, str | None]:
    """
    Validate a memory dataset file without raising exceptions.

    Args:
        path: Path to the memory golden dataset JSON file.

    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is None.
    """
    try:
        load_memory_dataset(path)
        return True, None
    except DatasetError as e:
        return False, str(e)


def get_memory_dataset_info(dataset: MemoryGoldenDataset) -> dict[str, Any]:
    """
    Get summary information about a memory dataset.

    Args:
        dataset: Validated MemoryGoldenDataset instance.

    Returns:
        Dictionary with dataset info.
    """
    # Count case types
    recall_cases = sum(1 for c in dataset.cases if c.id.startswith("recall-"))
    precision_cases = sum(1 for c in dataset.cases if c.id.startswith("precision-"))
    edge_cases = sum(1 for c in dataset.cases if c.id.startswith("edge-"))
    security_cases = sum(1 for c in dataset.cases if c.id.startswith("security-"))

    return {
        "version": dataset.version,
        "description": dataset.description,
        "case_count": len(dataset.cases),
        "recall_cases": recall_cases,
        "precision_cases": precision_cases,
        "edge_cases": edge_cases,
        "security_cases": security_cases,
        "case_ids": [case.id for case in dataset.cases],
    }


def get_memory_case_by_id(
    dataset: MemoryGoldenDataset, case_id: str
) -> MemoryTestCase | None:
    """
    Get a specific memory test case by ID.

    Args:
        dataset: Validated MemoryGoldenDataset instance.
        case_id: The case ID to find.

    Returns:
        MemoryTestCase if found, None otherwise.
    """
    for case in dataset.cases:
        if case.id == case_id:
            return case
    return None
