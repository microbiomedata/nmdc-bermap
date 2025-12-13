#!/usr/bin/env python3
"""Load sfas-brcs data into Neo4j."""

import json
import yaml
from pathlib import Path
from neo4j import GraphDatabase

# Paths
DB_PATH = Path(__file__).parent.parent / "db" / "sfas-brcs.yaml"

# Neo4j config
URI = "bolt://localhost:7687"
AUTH = None  # No auth


def flatten_for_neo4j(obj: dict) -> dict:
    """Flatten nested dicts/lists to JSON strings for Neo4j compatibility."""
    result = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            result[k] = json.dumps(v)
        elif isinstance(v, list):
            if v and isinstance(v[0], dict):
                result[k] = json.dumps(v)
            else:
                result[k] = v  # Neo4j handles simple lists
        else:
            result[k] = v
    return result


def insert_nodes(tx, label: str, nodes: list[dict]):
    """Insert nodes with a specific label."""
    for node in nodes:
        props = flatten_for_neo4j(node)
        # Build property string dynamically
        prop_str = ", ".join(f"{k}: ${k}" for k in props.keys())
        query = f"CREATE (n:{label} {{{prop_str}}})"
        tx.run(query, **props)


def main():
    # Load source data
    with open(DB_PATH) as f:
        data = yaml.safe_load(f)

    # Connect to Neo4j
    driver = GraphDatabase.driver(URI, auth=AUTH)

    # Clear existing data
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("Cleared existing data")

    # Label mapping
    collections = {
        "bioenergy_research_centers": "BioenergyResearchCenter",
        "genomic_science_sfas": "GenomicScienceSFA",
        "environmental_system_science_sfas": "EnvironmentalScienceSFA",
        "user_facilities": "UserFacility",
    }

    # Insert nodes with labels
    with driver.session() as session:
        for key, label in collections.items():
            if key in data and data[key]:
                session.execute_write(insert_nodes, label, data[key])
                print(f"Inserted {len(data[key])} {label} nodes")

    # Verify counts
    with driver.session() as session:
        result = session.run(
            "MATCH (n) RETURN labels(n)[0] as label, count(*) as count"
        )
        print("\nNode counts:")
        for record in result:
            print(f"  {record['label']}: {record['count']}")

    driver.close()
    print("\nNeo4j browser available at http://localhost:7474")
    print("Try: MATCH (n) RETURN n LIMIT 25")

if __name__ == "__main__":
    main()
