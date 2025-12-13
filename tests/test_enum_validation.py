"""Tests for enum permissible value validation."""

from pathlib import Path

import pytest

from nmdc_sfas_brcs.validators import EnumEvaluator, ValidationConfig

SCHEMA_PATH = Path(__file__).parent.parent / "src" / "nmdc_sfas_brcs" / "schema" / "nmdc_sfas_brcs.yaml"


@pytest.fixture
def evaluator():
    """Create an EnumEvaluator with default config."""
    config = ValidationConfig(cache_labels=True)
    return EnumEvaluator(config)


def test_schema_exists():
    """Test that the schema file exists."""
    assert SCHEMA_PATH.exists(), f"Schema not found at {SCHEMA_PATH}"


def test_validate_schema_runs(evaluator):
    """Test that validation runs without crashing."""
    result = evaluator.validate_schema(SCHEMA_PATH)
    assert result.total_enums_checked > 0
    assert result.total_values_checked > 0


def test_validate_schema_finds_mappings(evaluator):
    """Test that validation finds enum mappings to validate."""
    result = evaluator.validate_schema(SCHEMA_PATH)
    # DataType enum has several meanings defined
    assert result.total_mappings_checked > 0, "Expected to find some ontology mappings"


def test_no_errors_in_schema(evaluator):
    """Test that schema has no validation errors."""
    result = evaluator.validate_schema(SCHEMA_PATH)
    errors = [i for i in result.issues if i.severity == "ERROR"]
    assert not errors, f"Found {len(errors)} errors: {[e.message for e in errors]}"
