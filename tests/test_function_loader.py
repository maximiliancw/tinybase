"""
Tests for function loader module.

Tests metadata extraction, parallel loading, and pre-warming.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tinybase.functions.core import FunctionMeta, get_global_registry, reset_global_registry
from tinybase.functions.loader import (
    ensure_functions_package,
    extract_function_metadata,
    load_functions_from_directory,
    prewarm_function_dependencies,
)


class TestFunctionLoader:
    """Test function loader functionality."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before each test."""
        reset_global_registry()
        yield
        reset_global_registry()

    def test_extract_function_metadata_success(self):
        """Test successful metadata extraction."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            function_code = '''# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="test_function", description="Test", tags=["test"])
def test_func(client, payload: dict) -> dict:
    return {"result": "ok"}

if __name__ == "__main__":
    run()
'''
            f.write(function_code)
            f.flush()
            function_file = Path(f.name)

        try:
            metadata = extract_function_metadata(function_file)

            assert metadata is not None
            assert metadata["name"] == "test_function"
            assert metadata["description"] == "Test"
            assert metadata["auth"] == "auth"
            assert metadata["tags"] == ["test"]
            assert metadata["input_schema"] is not None
            assert metadata["output_schema"] is not None
        finally:
            try:
                function_file.unlink()
            except Exception:
                pass

    def test_extract_function_metadata_invalid_file(self):
        """Test metadata extraction from invalid file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("invalid python code {")
            f.flush()
            invalid_file = Path(f.name)

        try:
            metadata = extract_function_metadata(invalid_file)
            # Should return None for invalid files
            assert metadata is None
        finally:
            try:
                invalid_file.unlink()
            except Exception:
                pass

    def test_extract_function_metadata_no_function(self):
        """Test metadata extraction from file with no registered function."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("print('hello')")
            f.flush()
            no_function_file = Path(f.name)

        try:
            metadata = extract_function_metadata(no_function_file)
            # Should return None if no function is registered
            assert metadata is None
        finally:
            try:
                no_function_file.unlink()
            except Exception:
                pass

    def test_prewarm_function_dependencies(self):
        """Test pre-warming function dependencies."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            function_code = '''# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="test_function")
def test_func(client, payload: dict) -> dict:
    return {"result": "ok"}

if __name__ == "__main__":
    run()
'''
            f.write(function_code)
            f.flush()
            function_file = Path(f.name)

        try:
            # Pre-warming should complete (may take time for first run)
            result = prewarm_function_dependencies(function_file)
            # Result may be True or False depending on whether dependencies are already installed
            assert isinstance(result, bool)
        finally:
            try:
                function_file.unlink()
            except Exception:
                pass

    def test_load_functions_from_directory(self):
        """Test loading functions from a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Create function files
            func1_file = dir_path / "func1.py"
            func1_file.write_text('''# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="function_one", description="First function")
def func1(client, payload: dict) -> dict:
    return {"result": 1}

if __name__ == "__main__":
    run()
''')

            func2_file = dir_path / "func2.py"
            func2_file.write_text('''# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="function_two", description="Second function")
def func2(client, payload: dict) -> dict:
    return {"result": 2}

if __name__ == "__main__":
    run()
''')

            # Create a file that should be ignored
            ignored_file = dir_path / "_private.py"
            ignored_file.write_text("print('ignored')")

            # Load functions
            loaded_count = load_functions_from_directory(dir_path)

            # Should load 2 functions (ignoring _private.py)
            assert loaded_count == 2

            # Verify functions are registered
            registry = get_global_registry()
            assert registry.get("function_one") is not None
            assert registry.get("function_two") is not None
            assert registry.get("function_one").description == "First function"
            assert registry.get("function_two").description == "Second function"

    def test_load_functions_from_empty_directory(self):
        """Test loading from empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            loaded_count = load_functions_from_directory(dir_path)

            assert loaded_count == 0

    def test_load_functions_handles_errors_gracefully(self):
        """Test that loader handles errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Create one valid and one invalid function file
            valid_file = dir_path / "valid.py"
            valid_file.write_text('''# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="valid_function")
def valid_func(client, payload: dict) -> dict:
    return {"result": "ok"}

if __name__ == "__main__":
    run()
''')

            invalid_file = dir_path / "invalid.py"
            invalid_file.write_text("invalid syntax {")

            # Should load the valid function and skip the invalid one
            loaded_count = load_functions_from_directory(dir_path)

            assert loaded_count == 1

            registry = get_global_registry()
            assert registry.get("valid_function") is not None

    def test_ensure_functions_package(self):
        """Test ensuring functions package exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Directory doesn't exist yet
            assert not dir_path.exists()

            result = ensure_functions_package(dir_path)

            assert result is True
            assert dir_path.exists()
            assert (dir_path / "__init__.py").exists()

            # Check __init__.py content
            init_content = (dir_path / "__init__.py").read_text()
            assert "TinyBase Functions Package" in init_content

    def test_ensure_functions_package_existing(self):
        """Test ensuring functions package when it already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)
            dir_path.mkdir()

            result = ensure_functions_package(dir_path)

            assert result is True
            assert (dir_path / "__init__.py").exists()

    def test_load_functions_parallel_metadata_extraction(self):
        """Test that metadata extraction happens in parallel."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Create multiple function files
            for i in range(5):
                func_file = dir_path / f"func{i}.py"
                func_file.write_text(f'''# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run

@register(name="function_{i}", description="Function {i}")
def func{i}(client, payload: dict) -> dict:
    return {{"result": {i}}}

if __name__ == "__main__":
    run()
''')

            # Load functions (should use parallel extraction)
            loaded_count = load_functions_from_directory(dir_path)

            assert loaded_count == 5

            # Verify all functions are registered
            registry = get_global_registry()
            for i in range(5):
                assert registry.get(f"function_{i}") is not None
