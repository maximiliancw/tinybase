"""
Tests for function loader module.

Tests metadata extraction, parallel loading, and pre-warming.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from tinybase.functions.core import get_function_registry, reset_function_registry
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
        reset_function_registry()
        yield
        reset_function_registry()

    def test_extract_function_metadata_success(self):
        """Test successful metadata extraction."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            function_code = """# /// script
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
"""
            f.write(function_code)
            f.flush()
            function_file = Path(f.name)

        try:
            with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                # Mock successful metadata extraction
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = '{"name": "test_function", "description": "Test", "auth": "auth", "tags": ["test"], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                mock_result.stderr = ""
                mock_subprocess.return_value = mock_result

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
            with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                # Mock failed subprocess execution
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = "Syntax error"
                mock_subprocess.return_value = mock_result

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
            with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                # Mock subprocess that exits with code 1 (no function registered)
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = "No function registered"
                mock_subprocess.return_value = mock_result

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
            function_code = """# /// script
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
"""
            f.write(function_code)
            f.flush()
            function_file = Path(f.name)

        try:
            with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                # Mock successful dependency pre-warming
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = ""
                mock_result.stderr = ""
                mock_subprocess.return_value = mock_result

                result = prewarm_function_dependencies(function_file)
                assert result is True
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
            func1_file.write_text("""# /// script
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
""")

            func2_file = dir_path / "func2.py"
            func2_file.write_text("""# /// script
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
""")

            # Create a file that should be ignored
            ignored_file = dir_path / "_private.py"
            ignored_file.write_text("print('ignored')")

            # Mock subprocess calls for metadata extraction
            with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                with patch("tinybase.functions.pool.get_pool") as mock_get_pool:
                    mock_pool = MagicMock()
                    mock_get_pool.return_value = mock_pool

                    def mock_subprocess_side_effect(cmd, *args, **kwargs):
                        mock_result = MagicMock()
                        # Check if this is metadata extraction (--metadata flag)
                        if isinstance(cmd, list) and "--metadata" in cmd:
                            # Determine which function based on file path (cmd[3] or cmd[-2])
                            file_path = str(cmd[3]) if len(cmd) > 3 else ""
                            if "func1" in file_path:
                                mock_result.stdout = '{"name": "function_one", "description": "First function", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                            elif "func2" in file_path:
                                mock_result.stdout = '{"name": "function_two", "description": "Second function", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                            else:
                                mock_result.stdout = "{}"
                            mock_result.returncode = 0
                            mock_result.stderr = ""
                        else:
                            # For prewarm (uv sync)
                            mock_result.returncode = 0
                            mock_result.stdout = ""
                            mock_result.stderr = ""
                        return mock_result

                    mock_subprocess.side_effect = mock_subprocess_side_effect

                    # Load functions
                    loaded_count = load_functions_from_directory(dir_path)

                    # Should load 2 functions (ignoring _private.py)
                    assert loaded_count == 2

                    # Verify functions are registered
                    registry = get_function_registry()
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
        """Test that loader handles errors gracefully and skips invalid files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Create a valid SDK function with proper script block
            valid_file = dir_path / "my_function.py"
            valid_file.write_text("""# /// script
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
""")

            # Create file with syntax error - should be skipped
            invalid_syntax = dir_path / "broken.py"
            invalid_syntax.write_text("invalid syntax {")

            # Create file without tinybase-sdk dependency - should be skipped
            no_sdk = dir_path / "no_sdk.py"
            no_sdk.write_text("""# /// script
# dependencies = [
#   "requests",
# ]
# ///

print("No SDK")
""")

            # Mock subprocess calls
            with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                with patch("tinybase.functions.pool.get_pool") as mock_get_pool:
                    mock_pool = MagicMock()
                    mock_get_pool.return_value = mock_pool

                    def mock_subprocess_side_effect(cmd, *args, **kwargs):
                        mock_result = MagicMock()
                        if isinstance(cmd, list) and "--metadata" in cmd:
                            file_path = str(cmd[3]) if len(cmd) > 3 else ""
                            if "my_function.py" in file_path:
                                # Valid function with SDK
                                mock_result.stdout = '{"name": "valid_function", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                mock_result.returncode = 0
                            elif "broken.py" in file_path:
                                # Syntax error
                                mock_result.returncode = 1
                                mock_result.stderr = "SyntaxError: invalid syntax"
                                mock_result.stdout = ""
                            elif "no_sdk.py" in file_path:
                                # No SDK = no function registered
                                mock_result.returncode = 1
                                mock_result.stderr = "No function registered"
                                mock_result.stdout = ""
                            else:
                                mock_result.returncode = 1
                                mock_result.stderr = "Unknown error"
                                mock_result.stdout = ""
                        else:
                            # For prewarm
                            mock_result.returncode = 0
                            mock_result.stdout = ""
                            mock_result.stderr = ""
                        return mock_result

                    mock_subprocess.side_effect = mock_subprocess_side_effect

                    # Should load only the valid function and skip the invalid ones
                    loaded_count = load_functions_from_directory(dir_path)

                    assert loaded_count == 1

                    registry = get_function_registry()
                    assert registry.get("valid_function") is not None

    def test_load_functions_excludes_underscore_files(self):
        """Test that files starting with underscore are excluded from loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Create __init__.py - should be excluded
            init_file = dir_path / "__init__.py"
            init_file.write_text('"""Package init"""')

            # Create _helper.py - should be excluded
            helper_file = dir_path / "_helper.py"
            helper_file.write_text("""# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register

@register(name="should_not_load")
def helper(client, payload: dict) -> dict:
    return {"result": "ok"}
""")

            # Create normal function file - should be loaded
            func_file = dir_path / "my_function.py"
            func_file.write_text("""# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from tinybase_sdk import register

@register(name="my_function")
def my_func(client, payload: dict) -> dict:
    return {"result": "ok"}
""")

            with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                with patch("tinybase.functions.pool.get_pool") as mock_get_pool:
                    mock_pool = MagicMock()
                    mock_get_pool.return_value = mock_pool

                    def mock_subprocess_side_effect(cmd, *args, **kwargs):
                        mock_result = MagicMock()
                        if isinstance(cmd, list) and "--metadata" in cmd:
                            file_path = str(cmd[3]) if len(cmd) > 3 else ""
                            # Only my_function.py should be processed
                            if "my_function.py" in file_path:
                                mock_result.stdout = '{"name": "my_function", "auth": "auth", "tags": [], "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}'
                                mock_result.returncode = 0
                            else:
                                # __init__.py and _helper.py should never reach here
                                raise AssertionError(f"File {file_path} should not be processed")
                        else:
                            mock_result.returncode = 0
                            mock_result.stdout = ""
                            mock_result.stderr = ""
                        return mock_result

                    mock_subprocess.side_effect = mock_subprocess_side_effect

                    loaded_count = load_functions_from_directory(dir_path)

                    # Only my_function.py should be loaded
                    assert loaded_count == 1

                    registry = get_function_registry()
                    assert registry.get("my_function") is not None
                    assert registry.get("should_not_load") is None

    def test_ensure_functions_package(self):
        """Test ensuring functions package exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # TemporaryDirectory creates the directory, so it exists
            assert dir_path.exists()

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
            # Directory already exists from TemporaryDirectory

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
                func_file.write_text(f"""# /// script
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
""")

            # Mock subprocess calls
            with patch("tinybase.functions.loader.subprocess.run") as mock_subprocess:
                with patch("tinybase.functions.pool.get_pool") as mock_get_pool:
                    mock_pool = MagicMock()
                    mock_get_pool.return_value = mock_pool

                    def mock_subprocess_side_effect(cmd, *args, **kwargs):
                        mock_result = MagicMock()
                        if isinstance(cmd, list) and "--metadata" in cmd:
                            file_path = str(cmd[3]) if len(cmd) > 3 else ""
                            # Extract function number from path
                            func_num = None
                            for j in range(5):
                                if f"func{j}" in file_path:
                                    func_num = j
                                    break
                            if func_num is not None:
                                mock_result.stdout = f'{{"name": "function_{func_num}", "description": "Function {func_num}", "auth": "auth", "tags": [], "input_schema": {{"type": "object"}}, "output_schema": {{"type": "object"}}}}'
                                mock_result.returncode = 0
                            else:
                                mock_result.returncode = 1
                            mock_result.stderr = ""
                        else:
                            # For prewarm
                            mock_result.returncode = 0
                            mock_result.stdout = ""
                            mock_result.stderr = ""
                        return mock_result

                    mock_subprocess.side_effect = mock_subprocess_side_effect

                    # Load functions (should use parallel extraction)
                    loaded_count = load_functions_from_directory(dir_path)

                    assert loaded_count == 5

                    # Verify all functions are registered
                    registry = get_function_registry()
                    for i in range(5):
                        assert registry.get(f"function_{i}") is not None
