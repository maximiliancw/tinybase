"""CLI runner for TinyBase functions."""

import json
import sys
from typing import Any
from tinybase_sdk.decorator import get_registered_function


def run():
    """Handle CLI invocation for metadata extraction or execution."""
    if "--metadata" in sys.argv:
        # Output function metadata as JSON
        func = get_registered_function()
        if func:
            metadata = {
                "name": func["name"],
                "description": func["description"],
                "auth": func["auth"],
                "tags": func["tags"],
                "input_schema": func["input_schema"],
                "output_schema": func["output_schema"],
            }
            print(json.dumps(metadata))
            sys.exit(0)
        sys.exit(1)

    # Execution mode: read context+payload from stdin
    input_data = json.loads(sys.stdin.read())
    context_data = input_data["context"]
    payload_data = input_data["payload"]

    func = get_registered_function()
    if not func:
        print(json.dumps({"error": "No function registered"}), file=sys.stderr)
        sys.exit(1)

    # Import client dynamically (will be available after generation)
    try:
        from tinybase_sdk.client import Client
    except ImportError:
        # Fallback if client not generated yet
        print(
            json.dumps({"error": "Client not generated. Run scripts/generate_client.py"}),
            file=sys.stderr,
        )
        sys.exit(1)

    # Create client with auth token
    client = Client(
        base_url=context_data["api_base_url"],
        token=context_data["auth_token"],
    )

    # Validate and execute
    try:
        input_type = func["input_type"]

        # Handle different input types
        if input_type is None:
            # No input parameter (just client)
            result = func["callable"](client)
        elif hasattr(input_type, "model_validate"):
            # Pydantic model - validate
            validated_payload = input_type.model_validate(payload_data)
            result = func["callable"](client, validated_payload)
        else:
            # Basic type - use as-is (FastAPI will handle validation)
            result = func["callable"](client, payload_data)

        # Serialize result
        if hasattr(result, "model_dump"):
            # Pydantic model
            output = result.model_dump()
        elif isinstance(result, (dict, list, str, int, float, bool, type(None))):
            # JSON-serializable types
            output = result
        else:
            # Fallback: try to convert to dict
            output = dict(result) if hasattr(result, "__dict__") else str(result)

        print(json.dumps({"status": "succeeded", "result": output}))
    except Exception as e:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
        )
        sys.exit(0)  # Exit 0 so we can parse the error JSON
