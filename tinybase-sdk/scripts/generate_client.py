#!/usr/bin/env python
"""Regenerate OpenAPI client from TinyBase API spec."""

import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests


def main():
    sdk_dir = Path(__file__).parent.parent
    project_root = sdk_dir.parent
    client_dir = sdk_dir / "src" / "tinybase_sdk" / "client"
    config_file = sdk_dir / "openapi-client-config.yaml"

    # Start TinyBase server temporarily
    print("Starting TinyBase server for client generation...")
    server = subprocess.Popen(
        ["uv", "run", "tinybase", "serve", "--port", "8001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root,
    )

    try:
        # Wait for server to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:8001/health", timeout=1)
                if response.status_code == 200:
                    break
            except Exception:
                time.sleep(0.5)
        else:
            server.terminate()
            raise RuntimeError("TinyBase server failed to start")

        # Clear existing generated client
        if client_dir.exists():
            shutil.rmtree(client_dir)

        # Generate new client from OpenAPI spec
        print("Generating OpenAPI client...")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "openapi_python_client",
                "generate",
                "--url",
                "http://localhost:8001/openapi.json",
                "--output-path",
                str(client_dir),
                "--config",
                str(config_file),
            ],
            check=True,
        )

        print(f"✓ Client generated at {client_dir}")
    finally:
        # Stop server
        server.terminate()
        server.wait()


if __name__ == "__main__":
    main()
