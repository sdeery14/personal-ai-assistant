"""
MLflow Evaluation Dataset management.

Provides helpers to register golden datasets as MLflow Evaluation Datasets
using a get-or-create pattern with deterministic naming.
"""

from pathlib import Path
from typing import Any

import mlflow
from mlflow.genai.datasets import create_dataset, search_datasets

from eval.models import (
    GoldenDataset,
    GraphExtractionGoldenDataset,
    MemoryGoldenDataset,
    MemoryWriteGoldenDataset,
    WeatherGoldenDataset,
)

# Map of dataset JSON filename stems to logical dataset type names
DATASET_TYPE_MAP = {
    "golden_dataset": "quality",
    "security_golden_dataset": "security",
    "memory_golden_dataset": "memory-retrieval",
    "memory_write_golden_dataset": "memory-write",
    "weather_golden_dataset": "weather",
    "graph_extraction_golden_dataset": "graph-extraction",
}


def _resolve_dataset_type(dataset_path: str | Path) -> str:
    """Derive a logical dataset type name from the file path."""
    stem = Path(dataset_path).stem
    return DATASET_TYPE_MAP.get(stem, stem)


def _make_dataset_name(dataset_type: str, version: str) -> str:
    """Build deterministic dataset name: '{type}-v{version}'."""
    return f"{dataset_type}-v{version}"


def get_experiment_id(experiment_name: str) -> str:
    """Get or create an MLflow experiment and return its ID as a string."""
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        return mlflow.create_experiment(experiment_name)
    return experiment.experiment_id


def get_or_create_dataset(
    dataset_path: str | Path,
    version: str,
    experiment_id: str,
    records: list[dict[str, Any]],
) -> Any:
    """
    Get existing or create new MLflow Evaluation Dataset.

    Uses deterministic naming so repeated runs with the same dataset version
    reuse the same MLflow dataset rather than creating duplicates.

    Args:
        dataset_path: Path to the source JSON file (for type inference).
        version: Dataset version from the JSON file.
        experiment_id: MLflow experiment ID to associate the dataset with.
        records: List of dicts with 'inputs' and optional 'expectations' keys.

    Returns:
        The MLflow EvaluationDataset object.
    """
    dataset_type = _resolve_dataset_type(dataset_path)
    name = _make_dataset_name(dataset_type, version)

    # Try to find existing dataset with this name
    existing = search_datasets(
        filter_string=f"name = '{name}'",
        experiment_ids=[experiment_id],
    )
    if existing:
        return existing[0]

    # Create new dataset
    ds = create_dataset(
        name=name,
        experiment_id=[experiment_id],
        tags={
            "version": version,
            "source_file": Path(dataset_path).name,
            "dataset_type": dataset_type,
        },
    )

    # Only include inputs/expectations in records (strip internal fields)
    clean_records = []
    for r in records:
        clean = {}
        if "inputs" in r:
            clean["inputs"] = r["inputs"]
        if "expectations" in r:
            clean["expectations"] = r["expectations"]
        clean_records.append(clean)

    ds.merge_records(clean_records)
    return ds


def prepare_quality_records(dataset: GoldenDataset) -> list[dict[str, Any]]:
    """Convert quality/security GoldenDataset to MLflow record format."""
    return [
        {
            "inputs": {"question": case.user_prompt},
            "expectations": {"rubric": case.rubric},
        }
        for case in dataset.cases
    ]


def prepare_memory_retrieval_records(
    dataset: MemoryGoldenDataset,
) -> list[dict[str, Any]]:
    """Convert memory retrieval dataset to MLflow record format."""
    return [
        {
            "inputs": {"query": case.query, "user_id": case.user_id},
            "expectations": {
                "expected_retrievals": case.expected_retrievals,
                "rubric": case.rubric,
            },
        }
        for case in dataset.cases
    ]


def prepare_memory_write_records(
    dataset: MemoryWriteGoldenDataset,
) -> list[dict[str, Any]]:
    """Convert memory write dataset to MLflow record format (inputs + expectations only)."""
    records = []
    for case in dataset.cases:
        last_user_msg = None
        for msg in case.conversation:
            if msg["role"] == "user":
                last_user_msg = msg["content"]
        if not last_user_msg:
            continue
        save_keywords = [
            ea.content_keywords
            for ea in case.expected_actions
            if ea.action == "save"
        ]
        records.append({
            "inputs": {"message": last_user_msg},
            "expectations": {
                "rubric": case.rubric,
                "save_keywords": save_keywords,
            },
        })
    return records


def prepare_weather_records(
    dataset: WeatherGoldenDataset,
) -> list[dict[str, Any]]:
    """Convert weather dataset to MLflow record format."""
    return [
        {
            "inputs": {"query": case.query},
            "expectations": {
                "expected_behavior": case.expected_behavior,
                "expected_fields": case.expected_fields,
                "expected_error_keywords": case.expected_error_keywords,
                "rubric": case.rubric,
            },
        }
        for case in dataset.cases
    ]


def prepare_graph_extraction_records(
    dataset: GraphExtractionGoldenDataset,
) -> list[dict[str, Any]]:
    """Convert graph extraction dataset to MLflow record format."""
    return [
        {
            "inputs": {"message": case.user_prompt},
            "expectations": {
                "rubric": case.rubric,
                "entity_keywords": [e.keywords for e in case.expected_entities],
                "relationship_keywords": [
                    {
                        "type": r.type,
                        "source_keywords": r.source_keywords,
                        "target_keywords": r.target_keywords,
                    }
                    for r in case.expected_relationships
                ],
            },
        }
        for case in dataset.cases
    ]
