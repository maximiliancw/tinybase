#!/usr/bin/env python3
"""Export OpenAPI spec from FastAPI app."""
import json
import sys
from pathlib import Path


def main():
    from tinybase.api.app import create_app

    app = create_app()
    spec = app.openapi()

    output_path = Path(__file__).parent.parent / "openapi" / "openapi.json"

    if "--check" in sys.argv:
        # Compare with existing
        if not output_path.exists():
            print(f"OpenAPI spec not found at {output_path}")
            sys.exit(1)
        existing = json.loads(output_path.read_text())
        if existing != spec:
            print("OpenAPI spec out of date!")
            sys.exit(1)
        print("OpenAPI spec is up to date")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec, indent=2, sort_keys=True))
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
