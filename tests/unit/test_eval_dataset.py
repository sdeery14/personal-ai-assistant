"""
Tests for eval/dataset.py - Dataset loading and validation.

These tests verify:
- Valid dataset loading
- Schema validation (version, cases count, field requirements)
- Error handling for missing/malformed files
- Edge cases (min/max cases, duplicate IDs)
"""

import json
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile

from eval.dataset import (
    DatasetError,
    get_case_by_id,
    get_dataset_info,
    load_dataset,
    validate_dataset_file,
)
from eval.models import GoldenDataset


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def valid_dataset_dict():
    """Minimal valid dataset with 5 cases."""
    return {
        "version": "1.0.0",
        "description": "Test dataset",
        "cases": [
            {
                "id": f"case-{i:03d}",
                "user_prompt": f"Test question {i}?",
                "rubric": f"The answer should be correct for case {i}.",
            }
            for i in range(1, 6)  # 5 cases (minimum)
        ],
    }


@pytest.fixture
def valid_dataset_file(valid_dataset_dict, tmp_path):
    """Create a temporary valid dataset file."""
    file_path = tmp_path / "valid_dataset.json"
    with open(file_path, "w") as f:
        json.dump(valid_dataset_dict, f)
    return file_path


@pytest.fixture
def dataset_with_tags(valid_dataset_dict, tmp_path):
    """Dataset with tags and context fields."""
    valid_dataset_dict["cases"][0]["context"] = "Simple test case"
    valid_dataset_dict["cases"][0]["tags"] = ["basic", "math"]
    valid_dataset_dict["cases"][1]["tags"] = ["basic"]
    file_path = tmp_path / "tagged_dataset.json"
    with open(file_path, "w") as f:
        json.dump(valid_dataset_dict, f)
    return file_path


# =============================================================================
# Test: Valid Dataset Loading
# =============================================================================


class TestLoadDatasetValid:
    """Tests for successful dataset loading."""

    def test_load_valid_dataset(self, valid_dataset_file):
        """Should load and return a GoldenDataset instance."""
        dataset = load_dataset(valid_dataset_file)
        assert isinstance(dataset, GoldenDataset)
        assert dataset.version == "1.0.0"
        assert len(dataset.cases) == 5

    def test_load_dataset_with_string_path(self, valid_dataset_file):
        """Should accept string path as well as Path object."""
        dataset = load_dataset(str(valid_dataset_file))
        assert isinstance(dataset, GoldenDataset)

    def test_load_dataset_with_optional_fields(self, dataset_with_tags):
        """Should correctly load optional fields (context, tags)."""
        dataset = load_dataset(dataset_with_tags)
        assert dataset.cases[0].context == "Simple test case"
        assert dataset.cases[0].tags == ["basic", "math"]
        assert dataset.cases[1].tags == ["basic"]
        assert dataset.cases[2].context is None
        assert dataset.cases[2].tags is None


# =============================================================================
# Test: File Not Found / Read Errors
# =============================================================================


class TestLoadDatasetFileErrors:
    """Tests for file access errors."""

    def test_file_not_found(self, tmp_path):
        """Should raise DatasetError for missing file."""
        missing_path = tmp_path / "nonexistent.json"
        with pytest.raises(DatasetError) as exc_info:
            load_dataset(missing_path)
        assert "not found" in str(exc_info.value).lower()

    def test_path_is_directory(self, tmp_path):
        """Should raise DatasetError for directory path."""
        with pytest.raises(DatasetError) as exc_info:
            load_dataset(tmp_path)
        assert "not a file" in str(exc_info.value).lower()

    def test_invalid_json(self, tmp_path):
        """Should raise DatasetError for malformed JSON."""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{invalid json}")
        with pytest.raises(DatasetError) as exc_info:
            load_dataset(bad_json)
        assert "invalid json" in str(exc_info.value).lower()


# =============================================================================
# Test: Schema Validation - Version
# =============================================================================


class TestValidationVersion:
    """Tests for version field validation."""

    def test_missing_version(self, valid_dataset_dict, tmp_path):
        """Should reject dataset without version."""
        del valid_dataset_dict["version"]
        file_path = tmp_path / "no_version.json"
        with open(file_path, "w") as f:
            json.dump(valid_dataset_dict, f)

        with pytest.raises(DatasetError) as exc_info:
            load_dataset(file_path)
        assert "version" in str(exc_info.value).lower()

    @pytest.mark.parametrize(
        "invalid_version",
        [
            "1.0",  # Missing patch
            "v1.0.0",  # Has prefix
            "1.0.0.0",  # Too many parts
            "1.a.0",  # Non-numeric
            "",  # Empty
        ],
    )
    def test_invalid_version_format(
        self, valid_dataset_dict, tmp_path, invalid_version
    ):
        """Should reject invalid semver formats."""
        valid_dataset_dict["version"] = invalid_version
        file_path = tmp_path / "bad_version.json"
        with open(file_path, "w") as f:
            json.dump(valid_dataset_dict, f)

        with pytest.raises(DatasetError):
            load_dataset(file_path)


# =============================================================================
# Test: Schema Validation - Cases Count
# =============================================================================


class TestValidationCasesCount:
    """Tests for cases array size validation."""

    def test_too_few_cases(self, valid_dataset_dict, tmp_path):
        """Should reject dataset with fewer than 5 cases."""
        valid_dataset_dict["cases"] = valid_dataset_dict["cases"][:4]
        file_path = tmp_path / "too_few.json"
        with open(file_path, "w") as f:
            json.dump(valid_dataset_dict, f)

        with pytest.raises(DatasetError) as exc_info:
            load_dataset(file_path)
        assert "validation" in str(exc_info.value).lower()

    def test_too_many_cases(self, valid_dataset_dict, tmp_path):
        """Should reject dataset with more than 20 cases."""
        # Add cases to exceed limit
        for i in range(21):
            valid_dataset_dict["cases"].append(
                {
                    "id": f"extra-{i:03d}",
                    "user_prompt": f"Extra question {i}?",
                    "rubric": f"Extra rubric {i}.",
                }
            )
        file_path = tmp_path / "too_many.json"
        with open(file_path, "w") as f:
            json.dump(valid_dataset_dict, f)

        with pytest.raises(DatasetError):
            load_dataset(file_path)

    def test_maximum_valid_cases(self, tmp_path):
        """Should accept dataset with exactly 20 cases."""
        dataset = {
            "version": "1.0.0",
            "cases": [
                {
                    "id": f"case-{i:03d}",
                    "user_prompt": f"Question {i}?",
                    "rubric": f"Rubric for case {i}.",
                }
                for i in range(1, 21)  # 20 cases (maximum)
            ],
        }
        file_path = tmp_path / "max_cases.json"
        with open(file_path, "w") as f:
            json.dump(dataset, f)

        result = load_dataset(file_path)
        assert len(result.cases) == 20


# =============================================================================
# Test: Schema Validation - Case Fields
# =============================================================================


class TestValidationCaseFields:
    """Tests for individual case field validation."""

    def test_missing_id(self, valid_dataset_dict, tmp_path):
        """Should reject case without id."""
        del valid_dataset_dict["cases"][0]["id"]
        file_path = tmp_path / "no_id.json"
        with open(file_path, "w") as f:
            json.dump(valid_dataset_dict, f)

        with pytest.raises(DatasetError):
            load_dataset(file_path)

    def test_invalid_id_format(self, valid_dataset_dict, tmp_path):
        """Should reject case with invalid id format."""
        valid_dataset_dict["cases"][0]["id"] = "Case_001"  # Uppercase and underscore
        file_path = tmp_path / "bad_id.json"
        with open(file_path, "w") as f:
            json.dump(valid_dataset_dict, f)

        with pytest.raises(DatasetError):
            load_dataset(file_path)

    def test_duplicate_ids(self, valid_dataset_dict, tmp_path):
        """Should reject dataset with duplicate case IDs."""
        valid_dataset_dict["cases"][1]["id"] = valid_dataset_dict["cases"][0]["id"]
        file_path = tmp_path / "dup_ids.json"
        with open(file_path, "w") as f:
            json.dump(valid_dataset_dict, f)

        with pytest.raises(DatasetError) as exc_info:
            load_dataset(file_path)
        assert "unique" in str(exc_info.value).lower()

    def test_rubric_too_short(self, valid_dataset_dict, tmp_path):
        """Should reject rubric shorter than 10 characters."""
        valid_dataset_dict["cases"][0]["rubric"] = "Short"  # Only 5 chars
        file_path = tmp_path / "short_rubric.json"
        with open(file_path, "w") as f:
            json.dump(valid_dataset_dict, f)

        with pytest.raises(DatasetError):
            load_dataset(file_path)


# =============================================================================
# Test: Helper Functions
# =============================================================================


class TestHelperFunctions:
    """Tests for dataset helper functions."""

    def test_validate_dataset_file_valid(self, valid_dataset_file):
        """Should return (True, None) for valid file."""
        is_valid, error = validate_dataset_file(valid_dataset_file)
        assert is_valid is True
        assert error is None

    def test_validate_dataset_file_invalid(self, tmp_path):
        """Should return (False, error_message) for invalid file."""
        missing = tmp_path / "missing.json"
        is_valid, error = validate_dataset_file(missing)
        assert is_valid is False
        assert error is not None
        assert "not found" in error.lower()

    def test_get_dataset_info(self, valid_dataset_file):
        """Should return summary info about dataset."""
        dataset = load_dataset(valid_dataset_file)
        info = get_dataset_info(dataset)

        assert info["version"] == "1.0.0"
        assert info["case_count"] == 5
        assert "case_ids" in info
        assert len(info["case_ids"]) == 5

    def test_get_dataset_info_with_tags(self, dataset_with_tags):
        """Should collect all unique tags from dataset."""
        dataset = load_dataset(dataset_with_tags)
        info = get_dataset_info(dataset)

        assert "basic" in info["tags"]
        assert "math" in info["tags"]
        assert len(info["tags"]) == 2

    def test_get_case_by_id_found(self, valid_dataset_file):
        """Should return case when ID exists."""
        dataset = load_dataset(valid_dataset_file)
        case = get_case_by_id(dataset, "case-001")

        assert case is not None
        assert case.id == "case-001"

    def test_get_case_by_id_not_found(self, valid_dataset_file):
        """Should return None when ID doesn't exist."""
        dataset = load_dataset(valid_dataset_file)
        case = get_case_by_id(dataset, "nonexistent")

        assert case is None


# =============================================================================
# Security Dataset Tests (T042-T046)
# =============================================================================


@pytest.fixture
def security_dataset_path():
    """Path to the security golden dataset."""
    return Path("eval/security_golden_dataset.json")


@pytest.fixture
def security_dataset(security_dataset_path):
    """Load the security dataset for testing."""
    return load_dataset(str(security_dataset_path))


class TestSecurityDataset:
    """Tests for security golden dataset validation (User Story 3)."""

    def test_load_security_dataset(self, security_dataset_path):
        """T042: Verify security dataset JSON parses correctly."""
        # Should not raise any exceptions
        dataset = load_dataset(str(security_dataset_path))
        
        # Verify it's a valid GoldenDataset
        assert isinstance(dataset, GoldenDataset)
        assert dataset.version
        assert dataset.description
        assert len(dataset.cases) > 0

    def test_dataset_schema_validation(self, security_dataset):
        """T043: Verify required security fields are present."""
        # All cases should have security-specific fields
        for case in security_dataset.cases:
            # Required base fields
            assert case.id, f"Case missing id: {case}"
            assert case.user_prompt, f"Case {case.id} missing user_prompt"
            assert case.rubric, f"Case {case.id} missing rubric"
            
            # Required security fields
            assert case.expected_behavior in ["block", "allow"], \
                f"Case {case.id} has invalid expected_behavior: {case.expected_behavior}"
            assert case.severity in ["critical", "high", "medium", "low"], \
                f"Case {case.id} has invalid severity: {case.severity}"
            assert case.attack_type, f"Case {case.id} missing attack_type"

    def test_severity_distribution(self, security_dataset):
        """T044: Verify ≥10 critical/high severity cases."""
        critical_high_cases = [
            case for case in security_dataset.cases
            if case.severity in ["critical", "high"]
        ]
        
        assert len(critical_high_cases) >= 10, \
            f"Expected ≥10 critical/high cases, got {len(critical_high_cases)}"

    def test_attack_type_coverage(self, security_dataset):
        """T045: Verify 5 attack categories covered."""
        # Expected attack types per spec
        expected_types = {
            "prompt_injection",
            "disallowed_content",
            "secret_extraction",
            "social_engineering",
            "jailbreak"
        }
        
        # Get unique attack types from dataset (excluding benign cases)
        adversarial_cases = [
            case for case in security_dataset.cases
            if case.expected_behavior == "block"
        ]
        actual_types = {case.attack_type for case in adversarial_cases}
        
        # Verify all expected types are covered
        missing_types = expected_types - actual_types
        assert not missing_types, \
            f"Missing attack types: {missing_types}. Found: {actual_types}"

    def test_expected_behavior_distribution(self, security_dataset):
        """T046: Verify ~80% block / ~20% allow distribution."""
        total_cases = len(security_dataset.cases)
        block_cases = [
            case for case in security_dataset.cases
            if case.expected_behavior == "block"
        ]
        allow_cases = [
            case for case in security_dataset.cases
            if case.expected_behavior == "allow"
        ]
        
        block_percentage = len(block_cases) / total_cases
        allow_percentage = len(allow_cases) / total_cases
        
        # Allow some flexibility: 70-90% block, 10-30% allow
        assert 0.70 <= block_percentage <= 0.90, \
            f"Block cases should be 70-90%, got {block_percentage:.1%}"
        assert 0.10 <= allow_percentage <= 0.30, \
            f"Allow cases should be 10-30%, got {allow_percentage:.1%}"

    def test_dataset_minimum_size(self, security_dataset):
        """Verify dataset has minimum viable size."""
        assert len(security_dataset.cases) >= 15, \
            f"Expected ≥15 cases for meaningful evaluation, got {len(security_dataset.cases)}"

    def test_benign_cases_present(self, security_dataset):
        """Verify benign cases exist to test false positives."""
        benign_cases = [
            case for case in security_dataset.cases
            if case.expected_behavior == "allow"
        ]
        
        assert len(benign_cases) >= 3, \
            f"Need at least 3 benign cases to test false positives, got {len(benign_cases)}"
