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

from eval.models import GoldenDataset, TestCase


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
