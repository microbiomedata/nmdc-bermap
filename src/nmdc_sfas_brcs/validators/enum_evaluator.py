"""
Enum evaluator for validating ontology mappings in LinkML schemas.

This module validates that ontology term mappings (meanings) in enum definitions
match the expected labels from the ontology.

Uses OAK (Ontology Access Kit) as the abstraction layer for all ontology access.
"""

import re
import logging
import csv
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Set

from pydantic import BaseModel, Field, ConfigDict
from linkml_runtime.utils.schemaview import SchemaView
from linkml_runtime.linkml_model import EnumDefinition, PermissibleValue

try:
    from oaklib import get_adapter
    HAS_OAK = True
except ImportError:
    HAS_OAK = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationConfig(BaseModel):
    """Configuration for validation."""

    model_config = ConfigDict(extra="forbid")

    oak_adapter_string: str = Field(
        default="sqlite:obo:",
        description="OAK adapter string (e.g., sqlite:obo:, ols:, bioportal:)",
    )
    strict_mode: bool = Field(default=False, description="Treat warnings as errors")
    cache_labels: bool = Field(
        default=True, description="Cache ontology labels to avoid redundant lookups"
    )
    oak_config_path: Optional[Path] = Field(
        default=None, description="Path to OAK configuration YAML file"
    )
    cache_dir: Path = Field(
        default=Path("cache"), description="Directory for storing cached terms"
    )


class ValidationIssue(BaseModel):
    """Represents a single validation issue."""

    model_config = ConfigDict(extra="forbid")

    enum_name: str
    value_name: str
    severity: str = Field(pattern="^(ERROR|WARNING|INFO)$")
    message: str
    meaning: Optional[str] = None
    expected_label: Optional[str] = None
    actual_label: Optional[str] = None


class ValidationResult(BaseModel):
    """Results from validating a schema."""

    model_config = ConfigDict(extra="forbid")

    schema_path: Optional[Path] = None
    issues: List[ValidationIssue] = Field(default_factory=list)
    total_enums_checked: int = 0
    total_values_checked: int = 0
    total_mappings_checked: int = 0

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return any(i.severity == "ERROR" for i in self.issues)

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return any(i.severity == "WARNING" for i in self.issues)

    def print_summary(self):
        """Print a summary of validation results."""
        print(f"\nValidation Summary:")
        print(f"  Enums checked: {self.total_enums_checked}")
        print(f"  Values checked: {self.total_values_checked}")
        print(f"  Mappings checked: {self.total_mappings_checked}")

        errors = [i for i in self.issues if i.severity == "ERROR"]
        warnings = [i for i in self.issues if i.severity == "WARNING"]
        info = [i for i in self.issues if i.severity == "INFO"]

        print(f"  Errors: {len(errors)}")
        print(f"  Warnings: {len(warnings)}")
        print(f"  Info: {len(info)}")


class EnumEvaluator:
    """Evaluator for validating ontology mappings in enums."""

    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        Initialize the evaluator.

        Args:
            config: Validation configuration
        """
        self.config = config or ValidationConfig()
        self._label_cache: Optional[Dict[str, Optional[str]]] = (
            {} if self.config.cache_labels else None
        )
        self._per_prefix_adapters: Dict = {}
        self._oak_config = self._load_oak_config()
        self._prefix_caches: Dict[str, Dict[str, str]] = {}
        self._warned_prefixes: Set[str] = set()
        self._initialize_oak()

    def _load_oak_config(self) -> Dict[str, str]:
        """Load OAK configuration from YAML file."""
        config_path = self.config.oak_config_path
        if not config_path:
            config_path = Path(__file__).parent / "oak_config.yaml"

        if not config_path.exists():
            logger.warning(f"OAK config file not found: {config_path}")
            return {}

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
            adapters = config_data.get("ontology_adapters", {})
            return {k.lower(): v for k, v in adapters.items()}

    def _get_cache_file(self, prefix: str) -> Path:
        """Get the cache file path for a given prefix."""
        cache_dir = self.config.cache_dir / prefix.lower()
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "terms.csv"

    def _load_cache(self, prefix: str) -> Dict[str, str]:
        """Load cached terms for a prefix."""
        cache_file = self._get_cache_file(prefix)
        cache: Dict[str, str] = {}

        if cache_file.exists():
            with open(cache_file, "r", newline="") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) >= 2:
                        cache[row[0]] = row[1]

        return cache

    def _save_to_cache(self, prefix: str, curie: str, label: Optional[str]):
        """Save a term to cache."""
        if prefix.lower() not in self._oak_config:
            return

        cache_file = self._get_cache_file(prefix)

        existing_cache: Set[str] = set()
        if cache_file.exists():
            with open(cache_file, "r", newline="") as f:
                reader = csv.reader(f)
                next(reader)
                for row in reader:
                    if len(row) >= 1:
                        existing_cache.add(row[0])

        if curie in existing_cache:
            return

        if not cache_file.exists():
            with open(cache_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["curie", "label", "retrieved_at"])

        with open(cache_file, "a", newline="") as f:
            writer = csv.writer(f)
            timestamp = datetime.now().isoformat()
            writer.writerow([curie, label or "", timestamp])

    def _initialize_oak(self):
        """Initialize OAK adapters dynamically based on usage."""
        if not HAS_OAK:
            logger.warning("OAK is not installed. Install with: pip install oaklib")
            return

        if self.config.oak_adapter_string == "sqlite:obo:":
            logger.info("Using dynamic SemSQL adapter selection based on CURIE prefix")
            return

        self._per_prefix_adapters["_default"] = get_adapter(
            self.config.oak_adapter_string
        )
        logger.info(f"Initialized OAK adapter: {self.config.oak_adapter_string}")

    def get_ontology_label(self, curie: str) -> Optional[str]:
        """Get the label for an ontology term using OAK."""
        if self._label_cache is not None and curie in self._label_cache:
            return self._label_cache[curie]

        prefix = curie.split(":")[0] if ":" in curie else None
        if not prefix:
            return None

        prefix_lower = prefix.lower()

        if prefix_lower in self._prefix_caches:
            if curie in self._prefix_caches[prefix_lower]:
                label = self._prefix_caches[prefix_lower][curie]
                if self._label_cache is not None:
                    self._label_cache[curie] = label
                return label if label else None

        label = None
        adapter = None

        if prefix_lower in self._oak_config and prefix_lower not in self._prefix_caches:
            self._prefix_caches[prefix_lower] = self._load_cache(prefix)
            if curie in self._prefix_caches[prefix_lower]:
                label = self._prefix_caches[prefix_lower][curie]
                if self._label_cache is not None:
                    self._label_cache[curie] = label
                return label if label else None

        if prefix_lower in self._oak_config:
            adapter_string = self._oak_config[prefix_lower]

            if not adapter_string:
                logger.debug(
                    f"Skipping validation for {prefix} (empty adapter string in config)"
                )
                self._per_prefix_adapters[prefix_lower] = None
                return None

            if prefix_lower not in self._per_prefix_adapters:
                self._per_prefix_adapters[prefix_lower] = get_adapter(adapter_string)
                logger.info(f"Created configured adapter for {prefix} ontology")

            adapter = self._per_prefix_adapters.get(prefix_lower)
        elif self.config.oak_adapter_string == "sqlite:obo:" and prefix:
            if prefix_lower not in self._per_prefix_adapters:
                adapter_string = f"sqlite:obo:{prefix_lower}"
                self._per_prefix_adapters[prefix_lower] = get_adapter(adapter_string)
                logger.info(f"Created adapter for {prefix} ontology")

            adapter = self._per_prefix_adapters.get(prefix_lower)
        else:
            adapter = self._per_prefix_adapters.get("_default")

        if adapter:
            label = adapter.label(curie)

        if self._label_cache is not None:
            self._label_cache[curie] = label

        if prefix_lower in self._oak_config:
            self._save_to_cache(prefix, curie, label)
            if prefix_lower in self._prefix_caches:
                self._prefix_caches[prefix_lower][curie] = label or ""

        return label

    def is_prefix_configured(self, prefix: str) -> bool:
        """Check if a prefix is configured for strict validation."""
        prefix_lower = prefix.lower()
        return prefix_lower in self._oak_config and bool(
            self._oak_config[prefix_lower]
        )

    def normalize_string(self, s: str) -> str:
        """Normalize a string for comparison."""
        if not s:
            return ""
        s = re.sub(r"[^a-zA-Z0-9\s]", " ", s)
        s = re.sub(r"\s+", " ", s)
        return s.strip().lower()

    def extract_aliases(self, pv: PermissibleValue, value_name: str) -> Set[str]:
        """Extract all possible aliases for a permissible value."""
        aliases = {value_name}

        if pv.title:
            aliases.add(pv.title)

        if pv.aliases:
            aliases.update(pv.aliases)

        if hasattr(pv, "structured_aliases") and pv.structured_aliases:
            for struct_alias in pv.structured_aliases:
                if hasattr(struct_alias, "literal_form") and struct_alias.literal_form:
                    aliases.add(struct_alias.literal_form)

        if pv.annotations:
            for key in ["label", "display_name", "preferred_name", "synonym"]:
                if key in pv.annotations:
                    val = pv.annotations[key]
                    if val and hasattr(val, "value"):
                        aliases.add(str(val.value))
                    elif val:
                        aliases.add(str(val))

        return aliases

    def validate_enum(
        self, enum_def: EnumDefinition, enum_name: str
    ) -> List[ValidationIssue]:
        """Validate a single enum definition."""
        issues = []

        if not enum_def.permissible_values:
            return issues

        for value_name, pv in enum_def.permissible_values.items():
            meaning = pv.meaning
            if not meaning:
                continue

            prefix = meaning.split(":")[0] if ":" in meaning else None
            if (
                prefix
                and prefix.lower() in self._oak_config
                and not self._oak_config[prefix.lower()]
            ):
                logger.debug(
                    f"Skipping validation for {meaning} (empty adapter string in config)"
                )
                continue

            actual_label = self.get_ontology_label(meaning)
            expected_labels = self.extract_aliases(pv, value_name)
            normalized_expected = {
                self.normalize_string(label) for label in expected_labels
            }
            normalized_actual = (
                self.normalize_string(actual_label) if actual_label else None
            )

            if actual_label is None:
                prefix = meaning.split(":")[0] if ":" in meaning else None
                if prefix and self.is_prefix_configured(prefix):
                    severity = "ERROR"
                    message = (
                        f"Could not retrieve label for configured ontology term {meaning}"
                    )
                else:
                    severity = "INFO"
                    message = f"Could not retrieve label for {meaning}"

                issue = ValidationIssue(
                    enum_name=enum_name,
                    value_name=value_name,
                    severity=severity,
                    message=message,
                    meaning=meaning,
                )
                issues.append(issue)
            elif normalized_actual not in normalized_expected:
                prefix = meaning.split(":")[0] if ":" in meaning else None
                is_configured = prefix and self.is_prefix_configured(prefix)
                severity = (
                    "ERROR" if (self.config.strict_mode or is_configured) else "WARNING"
                )
                issue = ValidationIssue(
                    enum_name=enum_name,
                    value_name=value_name,
                    severity=severity,
                    message=f"Ontology label mismatch: expected one of {expected_labels}, got '{actual_label}'",
                    meaning=meaning,
                    expected_label=value_name,
                    actual_label=actual_label,
                )
                issues.append(issue)

        return issues

    def validate_schema(self, schema_path: Path) -> ValidationResult:
        """Validate all enums in a schema."""
        result = ValidationResult(schema_path=schema_path)

        sv = SchemaView(str(schema_path))

        for enum_name, enum_def in sv.all_enums().items():
            result.total_enums_checked += 1

            if enum_def.permissible_values:
                result.total_values_checked += len(enum_def.permissible_values)

                for pv in enum_def.permissible_values.values():
                    if pv.meaning:
                        result.total_mappings_checked += 1

                issues = self.validate_enum(enum_def, enum_name)
                result.issues.extend(issues)

        return result

    def report_unknown_prefixes(self) -> None:
        """Report unknown ontology prefixes encountered during validation."""
        if self._warned_prefixes:
            print(f"\nUnknown ontology prefixes encountered:")
            print(
                "   Consider adding these to oak_config.yaml if they are valid ontologies:"
            )
            for prefix in sorted(self._warned_prefixes):
                print(f"   - {prefix.upper()}: sqlite:obo:{prefix}")


def main():
    """Main function for CLI usage."""
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Validate LinkML enum ontology mappings"
    )
    parser.add_argument("path", type=Path, help="Path to schema file or directory")
    parser.add_argument(
        "--adapter",
        default="sqlite:obo:",
        help="OAK adapter string (e.g., sqlite:obo:, ols:, bioportal:)",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as errors"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable label caching"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )

    args = parser.parse_args()

    config = ValidationConfig(
        oak_adapter_string=args.adapter,
        strict_mode=args.strict,
        cache_labels=not args.no_cache,
    )

    if args.verbose:
        logging.basicConfig(level=logging.INFO, force=True)
    else:
        logging.basicConfig(level=logging.CRITICAL, force=True)
        for logger_name in [
            "oaklib",
            "root",
            "pystow",
            "linkml_runtime",
            "urllib3",
            "httpx",
            "httpcore",
        ]:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        os.environ["PYSTOW_NO_PROGRESS"] = "1"

    evaluator = EnumEvaluator(config)

    if not HAS_OAK:
        print("Error: OAK is not installed. Please install with: pip install oaklib")
        return 1

    if args.path.is_file():
        result = evaluator.validate_schema(args.path)

        if not result.has_errors() and not result.has_warnings():
            if args.verbose:
                result.print_summary()
            else:
                print("OK")
            evaluator.report_unknown_prefixes()
            return 0
        else:
            if args.verbose:
                result.print_summary()
                for issue in result.issues:
                    print(f"\n{issue.severity}: {issue.enum_name}.{issue.value_name}")
                    print(f"  {issue.message}")
                    if issue.meaning:
                        print(f"  CURIE: {issue.meaning}")
            else:
                errors = [i for i in result.issues if i.severity == "ERROR"]
                warnings = [i for i in result.issues if i.severity == "WARNING"]

                if errors:
                    print(f"Validation failed with {len(errors)} error(s)\n")
                    print("ERRORS:")
                    for issue in errors:
                        print(
                            f"  - {args.path.name}:{issue.enum_name}.{issue.value_name}: {issue.message}"
                        )
                        if issue.meaning:
                            print(f"    Fix: Check CURIE {issue.meaning}")

                if warnings and not args.strict:
                    print(f"\n{len(warnings)} warning(s):")
                    for issue in warnings[:100]:
                        id_info = f" [{issue.meaning}]" if issue.meaning else ""
                        print(
                            f"  - {issue.enum_name}.{issue.value_name}{id_info}: {issue.message}"
                        )
                    if len(warnings) > 100:
                        print(f"  ... and {len(warnings) - 100} more warnings")

            evaluator.report_unknown_prefixes()
            return (
                1
                if result.has_errors() or (args.strict and result.has_warnings())
                else 0
            )

    elif args.path.is_dir():
        all_results = []
        schema_files = sorted(
            [f for f in args.path.rglob("*.yaml") if "linkml_model" not in str(f)]
        )

        if args.verbose:
            print(f"Validating {len(schema_files)} schema files...\n")

        for schema_file in schema_files:
            if args.verbose:
                print(f"Validating {schema_file.name}...")

            result = evaluator.validate_schema(schema_file)
            result.schema_path = schema_file
            all_results.append(result)

            if args.verbose:
                result.print_summary()

        total_errors = sum(
            len([i for i in r.issues if i.severity == "ERROR"]) for r in all_results
        )
        total_warnings = sum(
            len([i for i in r.issues if i.severity == "WARNING"]) for r in all_results
        )

        if total_errors == 0 and total_warnings == 0:
            if args.verbose:
                print(f"\nAll {len(schema_files)} schemas validated successfully!")
            else:
                print("OK")
            evaluator.report_unknown_prefixes()
            return 0
        else:
            if not args.verbose:
                if total_errors > 0:
                    print(
                        f"Validation failed with {total_errors} error(s) in {sum(1 for r in all_results if r.has_errors())} file(s)\n"
                    )
                    print("ERRORS:")
                    for result in all_results:
                        errors = [i for i in result.issues if i.severity == "ERROR"]
                        if errors:
                            for issue in errors:
                                schema_name = (
                                    result.schema_path.name
                                    if result.schema_path
                                    else "unknown"
                                )
                                print(
                                    f"  - {schema_name}:{issue.enum_name}.{issue.value_name}: {issue.message}"
                                )
                                if issue.meaning:
                                    print(f"    Fix: Check CURIE {issue.meaning}")

                if total_warnings > 0 and not args.strict:
                    print(
                        f"\n{total_warnings} warning(s) in {sum(1 for r in all_results if r.has_warnings())} file(s)"
                    )
            else:
                print(
                    f"\nOverall: {total_errors} errors, {total_warnings} warnings in {len(schema_files)} files"
                )

            evaluator.report_unknown_prefixes()
            return (
                1
                if total_errors > 0 or (args.strict and total_warnings > 0)
                else 0
            )
    else:
        print(f"Error: {args.path} is not a file or directory")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
