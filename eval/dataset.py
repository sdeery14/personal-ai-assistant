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

from eval.alfred_models import (
    MemoryInformedGoldenDataset,
    MultiCapGoldenDataset,
    ReturningGreetingGoldenDataset,
    RoutingGoldenDataset,
    ToneGoldenDataset,
)
from eval.models import (
    GoldenDataset,
    GraphExtractionGoldenDataset,
    GraphExtractionTestCase,
    MemoryGoldenDataset,
    MemoryTestCase,
    MemoryWriteGoldenDataset,
    MemoryWriteTestCase,
    TestCase,
    WeatherGoldenDataset,
    WeatherTestCase,
)
from eval.onboarding_models import OnboardingGoldenDataset


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


# Weather-specific dataset loading functions


def load_weather_dataset(path: str | Path) -> WeatherGoldenDataset:
    """
    Load and validate a weather evaluation dataset from a JSON file.

    Args:
        path: Path to the weather golden dataset JSON file.

    Returns:
        Validated WeatherGoldenDataset instance.

    Raises:
        DatasetError: If the file cannot be read or validation fails.
    """
    path = Path(path)

    # Check file exists
    if not path.exists():
        raise DatasetError(f"Weather dataset file not found: {path}")

    if not path.is_file():
        raise DatasetError(f"Weather dataset path is not a file: {path}")

    # Read JSON
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DatasetError(f"Invalid JSON in weather dataset file: {e}")
    except OSError as e:
        raise DatasetError(f"Failed to read weather dataset file: {e}")

    # Validate required fields
    if "cases" not in data:
        raise DatasetError("Weather dataset missing required field: 'cases'")

    for idx, case in enumerate(data.get("cases", [])):
        required_fields = ["id", "query", "expected_behavior", "rubric"]
        missing = [f for f in required_fields if f not in case]
        if missing:
            raise DatasetError(
                f"Weather dataset case {idx} missing required fields: {missing}"
            )

    # Validate with Pydantic
    try:
        dataset = WeatherGoldenDataset.model_validate(data)
    except ValidationError as e:
        errors = _format_validation_errors(e)
        raise DatasetError(f"Weather dataset validation failed:\n{errors}")

    return dataset


def validate_weather_dataset_file(path: str | Path) -> tuple[bool, str | None]:
    """
    Validate a weather dataset file without raising exceptions.

    Args:
        path: Path to the weather golden dataset JSON file.

    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is None.
    """
    try:
        load_weather_dataset(path)
        return True, None
    except DatasetError as e:
        return False, str(e)


def get_weather_dataset_info(dataset: WeatherGoldenDataset) -> dict[str, Any]:
    """
    Get summary information about a weather dataset.

    Args:
        dataset: Validated WeatherGoldenDataset instance.

    Returns:
        Dictionary with dataset info.
    """
    # Collect all tags
    all_tags: set[str] = set()
    for case in dataset.cases:
        all_tags.update(case.tags)

    # Count by expected behavior
    success_cases = sum(1 for c in dataset.cases if c.expected_behavior == "success")
    error_cases = sum(1 for c in dataset.cases if c.expected_behavior == "error")
    clarification_cases = sum(
        1 for c in dataset.cases if c.expected_behavior == "clarification"
    )

    return {
        "version": dataset.version,
        "description": dataset.description,
        "case_count": len(dataset.cases),
        "success_cases": success_cases,
        "error_cases": error_cases,
        "clarification_cases": clarification_cases,
        "tags": sorted(all_tags),
        "case_ids": [case.id for case in dataset.cases],
    }


def get_weather_case_by_id(
    dataset: WeatherGoldenDataset, case_id: str
) -> WeatherTestCase | None:
    """
    Get a specific weather test case by ID.

    Args:
        dataset: Validated WeatherGoldenDataset instance.
        case_id: The case ID to find.

    Returns:
        WeatherTestCase if found, None otherwise.
    """
    for case in dataset.cases:
        if case.id == case_id:
            return case
    return None


def is_weather_dataset(path: str | Path) -> bool:
    """
    Check if a dataset file is a weather dataset.

    Args:
        path: Path to the dataset file.

    Returns:
        True if the file appears to be a weather dataset.
    """
    path = Path(path)

    # Check filename
    if "weather" in path.name.lower():
        return True

    # Check content for weather-specific fields
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cases = data.get("cases", [])
        if cases and "expected_behavior" in cases[0] and "expected_fields" in cases[0]:
            return True
    except (json.JSONDecodeError, OSError, KeyError):
        pass

    return False


# Memory Write dataset loading functions (Feature 006)


def is_memory_write_dataset(path: str | Path) -> bool:
    """Check if a dataset file is a memory write evaluation dataset.

    Args:
        path: Path to the dataset file.

    Returns:
        True if the file appears to be a memory write dataset.
    """
    path = Path(path)

    # Check filename
    if "memory_write" in path.name.lower():
        return True

    # Check content for memory write-specific fields
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cases = data.get("cases", [])
        if cases and "expected_actions" in cases[0] and "conversation" in cases[0]:
            return True
    except (json.JSONDecodeError, OSError, KeyError):
        pass

    return False


def load_memory_write_dataset(path: str | Path) -> MemoryWriteGoldenDataset:
    """Load and validate a memory write evaluation dataset from a JSON file.

    Args:
        path: Path to the memory write golden dataset JSON file.

    Returns:
        Validated MemoryWriteGoldenDataset instance.

    Raises:
        DatasetError: If the file cannot be read or validation fails.
    """
    path = Path(path)

    if not path.exists():
        raise DatasetError(f"Memory write dataset file not found: {path}")

    if not path.is_file():
        raise DatasetError(f"Memory write dataset path is not a file: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DatasetError(f"Invalid JSON in memory write dataset file: {e}")
    except OSError as e:
        raise DatasetError(f"Failed to read memory write dataset file: {e}")

    if "cases" not in data:
        raise DatasetError("Memory write dataset missing required field: 'cases'")

    for idx, case in enumerate(data.get("cases", [])):
        required_fields = ["id", "conversation", "expected_actions", "rubric"]
        missing = [f for f in required_fields if f not in case]
        if missing:
            raise DatasetError(
                f"Memory write dataset case {idx} missing required fields: {missing}"
            )

    try:
        dataset = MemoryWriteGoldenDataset.model_validate(data)
    except ValidationError as e:
        errors = _format_validation_errors(e)
        raise DatasetError(f"Memory write dataset validation failed:\n{errors}")

    return dataset


def get_memory_write_case_by_id(
    dataset: MemoryWriteGoldenDataset, case_id: str
) -> MemoryWriteTestCase | None:
    """Get a specific memory write test case by ID."""
    for case in dataset.cases:
        if case.id == case_id:
            return case
    return None


# Graph Extraction dataset loading functions (Feature 007)


def is_graph_extraction_dataset(path: str | Path) -> bool:
    """Check if a dataset file is a graph extraction evaluation dataset.

    Args:
        path: Path to the dataset file.

    Returns:
        True if the file appears to be a graph extraction dataset.
    """
    path = Path(path)

    # Check filename
    if "graph_extraction" in path.name.lower():
        return True

    # Check content for graph-specific fields
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cases = data.get("cases", [])
        if cases and "expected_entities" in cases[0] and "expected_relationships" in cases[0]:
            return True
    except (json.JSONDecodeError, OSError, KeyError):
        pass

    return False


def load_graph_extraction_dataset(path: str | Path) -> GraphExtractionGoldenDataset:
    """Load and validate a graph extraction evaluation dataset from a JSON file.

    Args:
        path: Path to the graph extraction golden dataset JSON file.

    Returns:
        Validated GraphExtractionGoldenDataset instance.

    Raises:
        DatasetError: If the file cannot be read or validation fails.
    """
    path = Path(path)

    if not path.exists():
        raise DatasetError(f"Graph extraction dataset file not found: {path}")

    if not path.is_file():
        raise DatasetError(f"Graph extraction dataset path is not a file: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DatasetError(f"Invalid JSON in graph extraction dataset file: {e}")
    except OSError as e:
        raise DatasetError(f"Failed to read graph extraction dataset file: {e}")

    if "cases" not in data:
        raise DatasetError("Graph extraction dataset missing required field: 'cases'")

    for idx, case in enumerate(data.get("cases", [])):
        required_fields = ["id", "user_prompt", "rubric"]
        missing = [f for f in required_fields if f not in case]
        if missing:
            raise DatasetError(
                f"Graph extraction dataset case {idx} missing required fields: {missing}"
            )

    try:
        dataset = GraphExtractionGoldenDataset.model_validate(data)
    except ValidationError as e:
        errors = _format_validation_errors(e)
        raise DatasetError(f"Graph extraction dataset validation failed:\n{errors}")

    return dataset


def get_graph_extraction_case_by_id(
    dataset: GraphExtractionGoldenDataset, case_id: str
) -> GraphExtractionTestCase | None:
    """Get a specific graph extraction test case by ID."""
    for case in dataset.cases:
        if case.id == case_id:
            return case
    return None


# Onboarding dataset loading functions (Feature 011)


def is_onboarding_dataset(path: str | Path) -> bool:
    """Check if a dataset file is an onboarding evaluation dataset.

    Args:
        path: Path to the dataset file.

    Returns:
        True if the file appears to be an onboarding dataset.
    """
    path = Path(path)

    # Check filename
    if "onboarding" in path.name.lower():
        return True

    # Check content for onboarding-specific fields
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cases = data.get("cases", [])
        if cases and "user_turns" in cases[0] and "persona" in cases[0]:
            return True
    except (json.JSONDecodeError, OSError, KeyError):
        pass

    return False


def load_onboarding_dataset(path: str | Path) -> OnboardingGoldenDataset:
    """Load and validate an onboarding evaluation dataset from a JSON file.

    Args:
        path: Path to the onboarding golden dataset JSON file.

    Returns:
        Validated OnboardingGoldenDataset instance.

    Raises:
        DatasetError: If the file cannot be read or validation fails.
    """
    path = Path(path)

    if not path.exists():
        raise DatasetError(f"Onboarding dataset file not found: {path}")

    if not path.is_file():
        raise DatasetError(f"Onboarding dataset path is not a file: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DatasetError(f"Invalid JSON in onboarding dataset file: {e}")
    except OSError as e:
        raise DatasetError(f"Failed to read onboarding dataset file: {e}")

    if "cases" not in data:
        raise DatasetError("Onboarding dataset missing required field: 'cases'")

    for idx, case in enumerate(data.get("cases", [])):
        required_fields = ["id", "persona", "user_turns", "expectations", "rubric"]
        missing = [f for f in required_fields if f not in case]
        if missing:
            raise DatasetError(
                f"Onboarding dataset case {idx} missing required fields: {missing}"
            )

    try:
        dataset = OnboardingGoldenDataset.model_validate(data)
    except ValidationError as e:
        errors = _format_validation_errors(e)
        raise DatasetError(f"Onboarding dataset validation failed:\n{errors}")

    return dataset


# ============================================================
# Alfred Eval Suite — Dataset Detection & Loading
# ============================================================


def _detect_eval_type(path: str | Path) -> str | None:
    """Detect Alfred eval type from JSON eval_type field or filename.

    Returns the eval_type string or None if not an Alfred eval.
    """
    path = Path(path)

    # Check content for eval_type field (definitive)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        eval_type = data.get("eval_type")
        if eval_type in (
            "tone", "returning_greeting", "routing",
            "memory_informed", "multi_cap",
        ):
            return eval_type
    except (json.JSONDecodeError, OSError):
        pass

    # Filename heuristics
    name = path.name.lower()
    if "tone" in name:
        return "tone"
    if "returning_greeting" in name:
        return "returning_greeting"
    if "routing" in name:
        return "routing"
    if "memory_informed" in name:
        return "memory_informed"
    if "multi_cap" in name:
        return "multi_cap"

    return None


def is_tone_dataset(path: str | Path) -> bool:
    """Check if a dataset file is a tone/personality evaluation dataset."""
    return _detect_eval_type(path) == "tone"


def is_returning_greeting_dataset(path: str | Path) -> bool:
    """Check if a dataset file is a returning user greeting evaluation dataset."""
    return _detect_eval_type(path) == "returning_greeting"


def is_routing_dataset(path: str | Path) -> bool:
    """Check if a dataset file is a routing evaluation dataset."""
    return _detect_eval_type(path) == "routing"


def is_memory_informed_dataset(path: str | Path) -> bool:
    """Check if a dataset file is a memory-informed evaluation dataset."""
    return _detect_eval_type(path) == "memory_informed"


def is_multi_cap_dataset(path: str | Path) -> bool:
    """Check if a dataset file is a multi-capability evaluation dataset."""
    return _detect_eval_type(path) == "multi_cap"


def _load_alfred_dataset(path: str | Path, model_class: type, label: str):
    """Generic loader for Alfred eval datasets."""
    path = Path(path)

    if not path.exists():
        raise DatasetError(f"{label} dataset file not found: {path}")
    if not path.is_file():
        raise DatasetError(f"{label} dataset path is not a file: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DatasetError(f"Invalid JSON in {label} dataset file: {e}")
    except OSError as e:
        raise DatasetError(f"Failed to read {label} dataset file: {e}")

    if "cases" not in data:
        raise DatasetError(f"{label} dataset missing required field: 'cases'")

    try:
        return model_class.model_validate(data)
    except ValidationError as e:
        errors = _format_validation_errors(e)
        raise DatasetError(f"{label} dataset validation failed:\n{errors}")


def load_tone_dataset(path: str | Path) -> ToneGoldenDataset:
    """Load and validate a tone/personality evaluation dataset."""
    return _load_alfred_dataset(path, ToneGoldenDataset, "Tone")


def load_returning_greeting_dataset(path: str | Path) -> ReturningGreetingGoldenDataset:
    """Load and validate a returning user greeting evaluation dataset."""
    return _load_alfred_dataset(path, ReturningGreetingGoldenDataset, "Returning greeting")


def load_routing_dataset(path: str | Path) -> RoutingGoldenDataset:
    """Load and validate a routing evaluation dataset."""
    return _load_alfred_dataset(path, RoutingGoldenDataset, "Routing")


def load_memory_informed_dataset(path: str | Path) -> MemoryInformedGoldenDataset:
    """Load and validate a memory-informed evaluation dataset."""
    return _load_alfred_dataset(path, MemoryInformedGoldenDataset, "Memory-informed")


def load_multi_cap_dataset(path: str | Path) -> MultiCapGoldenDataset:
    """Load and validate a multi-capability evaluation dataset."""
    return _load_alfred_dataset(path, MultiCapGoldenDataset, "Multi-capability")
