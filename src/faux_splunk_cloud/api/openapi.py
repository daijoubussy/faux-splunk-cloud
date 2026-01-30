"""
OpenAPI schema generation and export.

FastAPI automatically generates OpenAPI schemas from code.
This module provides utilities for exporting the schema for
Backstage integration and external documentation.
"""

import json
from pathlib import Path

from faux_splunk_cloud.api.app import create_app


def get_openapi_schema() -> dict:
    """
    Get the OpenAPI schema generated from code.

    Returns:
        The OpenAPI schema as a dictionary.
    """
    app = create_app()
    return app.openapi()


def export_openapi_schema(output_path: Path | str) -> None:
    """
    Export the OpenAPI schema to a file.

    This is useful for:
    - Backstage API catalog integration
    - Static documentation generation
    - SDK generation

    Args:
        output_path: Path to write the schema (JSON or YAML)
    """
    output_path = Path(output_path)
    schema = get_openapi_schema()

    if output_path.suffix in (".yaml", ".yml"):
        import yaml

        with open(output_path, "w") as f:
            yaml.dump(schema, f, default_flow_style=False, sort_keys=False)
    else:
        with open(output_path, "w") as f:
            json.dump(schema, f, indent=2)


def generate_backstage_api_definition() -> str:
    """
    Generate the API definition for Backstage catalog.

    Returns:
        YAML string for Backstage API entity.
    """
    import yaml

    schema = get_openapi_schema()

    backstage_api = {
        "apiVersion": "backstage.io/v1alpha1",
        "kind": "API",
        "metadata": {
            "name": "faux-splunk-cloud-api",
            "title": schema.get("info", {}).get("title", "Faux Splunk Cloud API"),
            "description": schema.get("info", {}).get("description", ""),
            "tags": ["splunk", "acs", "openapi"],
        },
        "spec": {
            "type": "openapi",
            "lifecycle": "experimental",
            "owner": "platform-team",
            "definition": schema,
        },
    }

    return yaml.dump(backstage_api, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":
    # CLI for exporting schema
    import sys

    if len(sys.argv) > 1:
        export_openapi_schema(sys.argv[1])
        print(f"Exported OpenAPI schema to {sys.argv[1]}")
    else:
        # Print to stdout
        print(json.dumps(get_openapi_schema(), indent=2))
