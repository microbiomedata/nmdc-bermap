#!/usr/bin/env python3
"""
Fetch datasets from the BRC API and save each as an individual YAML file.

The BRC API at https://api.bioenergy.org/api/datasets/ provides metadata
for datasets from the four Bioenergy Research Centers (GLBRC, JBEI, CABBI, CBI).

Usage:
    python fetch_brc_datasets.py [--center CENTER] [--output-dir DIR] [--limit N]
"""

import argparse
import json
import re
from pathlib import Path

import requests
import yaml


BRC_API_BASE = "https://api.bioenergy.org/api/datasets/"

# Map BRC names to their standard identifiers
BRC_MAPPING = {
    "GLBRC": "glbrc",
    "JBEI": "jbei",
    "CABBI": "cabbi",
    "CBI": "cbi",
}


def fetch_datasets(center: str | None = None, limit: int | None = None) -> list[dict]:
    """
    Fetch datasets from the BRC API.

    Args:
        center: Optional BRC center to filter by (GLBRC, JBEI, CABBI, CBI)
        limit: Optional limit on number of datasets to fetch

    Returns:
        List of dataset dictionaries
    """
    params = {}
    if center:
        params["center"] = center
    if limit:
        params["limit"] = limit

    response = requests.get(BRC_API_BASE, params=params)
    response.raise_for_status()
    return response.json()


def sanitize_filename(name: str) -> str:
    """Convert a string to a safe filename."""
    # Replace spaces and special chars with underscores
    safe = re.sub(r'[^\w\-]', '_', name)
    # Collapse multiple underscores
    safe = re.sub(r'_+', '_', safe)
    # Remove leading/trailing underscores
    safe = safe.strip('_')
    # Truncate to reasonable length
    return safe[:80].lower()


def save_dataset(dataset: dict, output_dir: Path) -> Path:
    """
    Save a single dataset to a YAML file.

    Args:
        dataset: Dataset dictionary from the API
        output_dir: Directory to save the file

    Returns:
        Path to the saved file
    """
    # Try multiple fields for a unique identifier
    dataset_id = (
        dataset.get("id") or
        dataset.get("identifier") or
        dataset.get("datasetName") or
        "unknown"
    )
    # Sanitize and create filename
    filename = f"{sanitize_filename(dataset_id)}.yaml"

    filepath = output_dir / filename

    # Handle potential filename collisions by appending a counter
    counter = 1
    original_filepath = filepath
    while filepath.exists():
        stem = original_filepath.stem
        filepath = output_dir / f"{stem}_{counter}.yaml"
        counter += 1

    with open(filepath, 'w') as f:
        yaml.dump(dataset, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Fetch BRC datasets and save as individual YAML files"
    )
    parser.add_argument(
        "--center", "-c",
        choices=["GLBRC", "JBEI", "CABBI", "CBI"],
        help="Filter by BRC center"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path("db/brc_datasets"),
        help="Output directory for dataset files (default: db/brc_datasets)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Limit number of datasets to fetch"
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Print summary statistics"
    )

    args = parser.parse_args()

    # Create output directory structure
    if args.center:
        output_dir = args.output_dir / args.center.lower()
    else:
        output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching datasets from BRC API...")
    if args.center:
        print(f"  Center: {args.center}")
    if args.limit:
        print(f"  Limit: {args.limit}")

    datasets = fetch_datasets(center=args.center, limit=args.limit)
    print(f"  Found {len(datasets)} datasets")

    # If fetching all centers, organize by center subdirectories
    if not args.center:
        # Group datasets by BRC
        by_center = {}
        for ds in datasets:
            center = ds.get("brc", "unknown")
            if center not in by_center:
                by_center[center] = []
            by_center[center].append(ds)

        # Save each center's datasets in its own subdirectory
        saved_count = 0
        for center, center_datasets in by_center.items():
            center_dir = args.output_dir / center.lower()
            center_dir.mkdir(parents=True, exist_ok=True)

            for ds in center_datasets:
                save_dataset(ds, center_dir)
                saved_count += 1

            print(f"  Saved {len(center_datasets)} {center} datasets to {center_dir}")

        if args.summary:
            print_summary(datasets)
    else:
        # Save all to the specified directory
        for ds in datasets:
            save_dataset(ds, output_dir)
        print(f"  Saved {len(datasets)} datasets to {output_dir}")

        if args.summary:
            print_summary(datasets)


def print_summary(datasets: list[dict]):
    """Print summary statistics about the datasets."""
    print("\n=== Dataset Summary ===")

    # Count by center
    by_center = {}
    for ds in datasets:
        center = ds.get("brc", "unknown")
        by_center[center] = by_center.get(center, 0) + 1

    print("\nBy Center:")
    for center, count in sorted(by_center.items()):
        print(f"  {center}: {count}")

    # Count by dataset type
    by_type = {}
    for ds in datasets:
        ds_type = ds.get("datasetType", "unknown")
        by_type[ds_type] = by_type.get(ds_type, 0) + 1

    print("\nBy Dataset Type:")
    for ds_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {ds_type}: {count}")

    # Count datasets with related DOIs
    with_doi = sum(1 for ds in datasets if any(
        item.get("relatedItemIdentifier")
        for item in ds.get("relatedItem", [])
        if item.get("relatedItemIdentifier")
    ))
    print(f"\nDatasets with DOI references: {with_doi}/{len(datasets)}")

    # Count by species (top 10)
    species_counts = {}
    for ds in datasets:
        for sp in ds.get("species", []):
            name = sp.get("scientificName", "unknown")
            species_counts[name] = species_counts.get(name, 0) + 1

    print("\nTop 10 Species:")
    for name, count in sorted(species_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
