"""Tests for the filter_project_files task."""

import pytest

from ai_documentation_writer.flow_options import ProjectFlowOptions
from ai_documentation_writer.tasks.filter_project_files.filter_project_files import (
    apply_filters,
    format_size,
    has_likely_encoded_data,
    prepare_file_statistics,
)
from ai_documentation_writer.tasks.filter_project_files.models import FileFilterDecision


class TestFilterHelperFunctions:
    """Test helper functions for file filtering."""

    def test_format_size(self):
        """Test size formatting function."""
        assert format_size(0) == "0.0B"
        assert format_size(512) == "512.0B"
        assert format_size(1024) == "1.0KB"
        assert format_size(1536) == "1.5KB"
        assert format_size(1048576) == "1.0MB"
        assert format_size(10485760) == "10.0MB"
        # Files won't be larger than 100MB
        assert format_size(104857600) == "100.0MB"

    def test_has_likely_encoded_data(self):
        """Test encoded data detection."""
        # Test large base64 block (>500 continuous chars, content must be >1000 chars total)
        # 1240 chars total
        base64_content = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789" * 20
        assert has_likely_encoded_data(base64_content) is True

        # Test small base64 that should NOT be detected
        small_base64 = "import base64\ndata = base64.b64encode(b'hello')"
        assert has_likely_encoded_data(small_base64) is False

        # Test large hex block (must be >1000 chars total)
        hex_content = "0123456789abcdef" * 65  # 1040 hex chars
        assert has_likely_encoded_data(hex_content) is True

        # Test escaped characters block (50+ occurrences, must be >1000 chars total)
        escaped_content = r"data = b'" + r"\x00\x01\x02\x03" * 250 + "'"  # Over 1000 chars
        assert has_likely_encoded_data(escaped_content) is True

        # Test normal code
        assert has_likely_encoded_data("def hello_world():\n    print('Hello')" * 20) is False
        assert has_likely_encoded_data("import os\nimport sys\nimport base64" * 20) is False

        # Test empty content
        assert has_likely_encoded_data("") is False

    def test_prepare_file_statistics(self):
        """Test file sample preparation."""
        # Create test files with different characteristics
        files = {
            "src/main.py": "import os\n" * 100,  # Small file (1000 chars, not >10KB)
            "tests/fixtures/data.json": "\n".join(
                [f"line {i}: " + "x" * 250 for i in range(200)]
            ),  # Large file with 200 lines
            "tests/cassettes/api.yaml": "x" * 500 + "A" * 600,  # Has encoded data
            "vendor/lib.js": "console.log('vendor');\n" * 50,  # Small file
            "docs/README.md": "\n".join(
                [f"# Documentation line {i}" for i in range(1000)]
            ),  # Large file with many lines
        }

        samples = prepare_file_statistics(files)

        # Should include large files
        assert "tests/fixtures/data.json" in samples
        assert "docs/README.md" in samples

        # Should include files with encoded data
        assert "tests/cassettes/api.yaml" in samples

        # Should not include small files without encoded data
        assert "src/main.py" not in samples
        assert "vendor/lib.js" not in samples

        # Check sample structure for a large file with many lines
        _, json_sample = samples["tests/fixtures/data.json"]

        # Should have line markers
        assert "// Lines" in json_sample

        # Check that lines are truncated at 200 chars
        sample_lines = json_sample.split("\n")
        for line in sample_lines:
            if not line.startswith("// Lines"):
                # Data lines should be max 203 chars (200 + "...")
                assert len(line) <= 203

        # For files with many lines, should have 5 chunks
        chunk_markers = [line for line in sample_lines if line.startswith("// Lines")]
        assert len(chunk_markers) == 5  # Should have 5 chunks

    def test_apply_filters(self):
        """Test filter application."""
        files = {
            "src/main.py": "import os",
            "src/utils.py": "def helper():",
            "tests/test_main.py": "def test():",
            "tests/fixtures/data.yaml": "data: value",
            "tests/cassettes/api.yaml": "recording",
            "vendor/lib.js": "console.log()",
            "node_modules/pkg/index.js": "module.exports",
            "docs/README.md": "# Documentation",
            ".cache/data": "cached",
        }

        filter_decision = FileFilterDecision(
            reasoning="Filtering test fixtures and vendor files",
            exclude_patterns=["**/*.yaml", ".cache/**"],
            exclude_directories=["node_modules", "vendor"],
            exclude_specific_files=["tests/test_main.py"],
        )

        filtered = apply_filters(files, filter_decision)

        # Check what's kept
        assert "src/main.py" in filtered
        assert "src/utils.py" in filtered
        assert "docs/README.md" in filtered

        # Check what's excluded
        assert "tests/fixtures/data.yaml" not in filtered  # Pattern match
        assert "tests/cassettes/api.yaml" not in filtered  # Pattern match
        assert "vendor/lib.js" not in filtered  # Directory match
        assert "node_modules/pkg/index.js" not in filtered  # Directory match
        assert "tests/test_main.py" not in filtered  # Specific file
        assert ".cache/data" not in filtered  # Pattern match

        # Check count
        assert len(filtered) == 3


@pytest.mark.asyncio
class TestFilterProjectFilesTask:
    """Test the main filter_project_files_task."""

    @pytest.mark.skip(reason="Skipping for first release - requires AI model interaction")
    async def test_filter_identifies_test_fixtures(self):
        """Test that filter correctly identifies test fixture files."""
        from ai_documentation_writer.tasks.filter_project_files import filter_project_files_task

        files = {
            "src/main.py": "import os\nclass Main:\n    pass",
            "src/utils.py": "def helper():\n    return True",
            "tests/cassettes/test_api.yaml": "x" * 500 + "A" * 700,  # Large base64-like block
            "tests/fixtures/large_data.json": '{"data": "' + "x" * 50000 + '"}',
            "tests/test_main.py": "def test_main():\n    assert True",
            "package.json": '{"name": "project"}',
            "README.md": "# Project\nThis is a test project",
        }

        file_tree = """
src/
├── main.py
├── utils.py
tests/
├── cassettes/
│   └── test_api.yaml
├── fixtures/
│   └── large_data.json
├── test_main.py
package.json
README.md
        """.strip()

        flow_options = ProjectFlowOptions(
            target="test-project",
            enable_file_filtering=True,
        )

        filtered = await filter_project_files_task(
            file_tree=file_tree,
            files_dict=files,
            max_all_files_size=100_000_000,  # 100MB
            flow_options=flow_options,
        )

        # Core files should be preserved
        assert "src/main.py" in filtered
        assert "src/utils.py" in filtered
        assert "package.json" in filtered
        assert "README.md" in filtered

        # Test file should be preserved
        assert "tests/test_main.py" in filtered

        # Fixtures should be filtered out
        assert "tests/cassettes/test_api.yaml" not in filtered
        assert "tests/fixtures/large_data.json" not in filtered

    @pytest.mark.skip(reason="Skipping for first release - requires AI model interaction")
    async def test_filter_handles_large_projects(self):
        """Test filtering with many files."""
        from ai_documentation_writer.tasks.filter_project_files import filter_project_files_task

        # Create a large file set
        files = {}

        # Add source files
        for i in range(100):
            files[f"src/module_{i}.py"] = f"class Module{i}:\n    pass"

        # Add test fixtures with binary data (large base64 blocks)
        for i in range(50):
            files[f"tests/fixtures/data_{i}.yaml"] = "x" * 500 + "B" * 600  # Large base64 block

        # Add vendor files
        for i in range(30):
            files[f"vendor/lib_{i}.js"] = "console.log();"

        # Add docs
        files["README.md"] = "# Documentation"
        files["docs/guide.md"] = "## User Guide"

        file_tree = "src/\ntests/\nvendor/\ndocs/\nREADME.md"

        flow_options = ProjectFlowOptions(
            target="test-project",
            enable_file_filtering=True,
        )

        filtered = await filter_project_files_task(
            file_tree=file_tree,
            files_dict=files,
            max_all_files_size=100_000_000,  # 100MB
            flow_options=flow_options,
        )

        # Should keep source files and docs
        assert any("src/" in path for path in filtered)
        assert "README.md" in filtered
        assert "docs/guide.md" in filtered

        # Should filter out fixtures and vendor
        assert not any("tests/fixtures/" in path for path in filtered)
        assert not any("vendor/" in path for path in filtered)

        # Should be significantly smaller
        assert len(filtered) < len(files) * 0.7  # At least 30% reduction
