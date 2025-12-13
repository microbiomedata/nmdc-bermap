#!/usr/bin/env python3
"""Generate an interactive HTML browser for the SFAs and BRCs database.

Uses Jinja2 templates for maintainability. Templates are in scripts/templates/.
"""

import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR.parent / "db" / "sfas-brcs.yaml"
TEMPLATE_DIR = SCRIPT_DIR / "templates"
OUTPUT_PATH = SCRIPT_DIR.parent / "docs" / "browser.html"


def load_db() -> dict:
    """Load the YAML database."""
    with open(DB_PATH) as f:
        return yaml.safe_load(f)


def create_jinja_env() -> Environment:
    """Create and configure Jinja2 environment."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


def generate_html(db: dict) -> str:
    """Generate the HTML page from templates."""
    env = create_jinja_env()
    template = env.get_template("browser.html.j2")
    return template.render(**db)


def main():
    """Main entry point."""
    print(f"Loading database from {DB_PATH}")
    db = load_db()

    print("Generating HTML from templates...")
    html = generate_html(db)

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Writing to {OUTPUT_PATH}")
    with open(OUTPUT_PATH, "w") as f:
        f.write(html)

    print(f"Done! Open {OUTPUT_PATH} in a browser.")


if __name__ == "__main__":
    main()
