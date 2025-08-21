"""Tests for ProjectFilesData file tree with directory sizes."""

from ai_documentation_writer.documents.flow.project_files import ProjectFilesData


class TestProjectFilesTree:
    """Test file tree generation with directory sizes."""

    def test_file_tree_with_single_file(self):
        """Test tree generation with a single file."""
        data = ProjectFilesData(files={"main.py": "print('hello')"})
        tree = data.file_tree

        assert "main.py (14 bytes)" in tree
        assert "/" not in tree  # No directories

    def test_file_tree_with_directory_sizes(self):
        """Test that directories show cumulative sizes."""
        files = {
            "src/main.py": "x" * 100,  # 100 bytes
            "src/utils.py": "y" * 50,  # 50 bytes
            "tests/test_main.py": "z" * 200,  # 200 bytes
        }
        data = ProjectFilesData(files=files)
        tree = data.file_tree

        # Check directory sizes (should include all files within)
        assert "src/ (150 bytes)" in tree  # 100 + 50
        assert "tests/ (200 bytes)" in tree

        # Check individual file sizes
        assert "main.py (100 bytes)" in tree
        assert "utils.py (50 bytes)" in tree
        assert "test_main.py (200 bytes)" in tree

    def test_file_tree_with_nested_directories(self):
        """Test nested directory size calculation."""
        files = {
            "app/models/user.py": "a" * 100,
            "app/models/post.py": "b" * 150,
            "app/views/index.py": "c" * 200,
            "app/config.py": "d" * 50,
        }
        data = ProjectFilesData(files=files)
        tree = data.file_tree

        # app/ should contain all files (100 + 150 + 200 + 50 = 500)
        assert "app/ (500 bytes)" in tree

        # app/models/ should contain only its files (100 + 150 = 250)
        assert "models/ (250 bytes)" in tree

        # app/views/ should contain only its file (200)
        assert "views/ (200 bytes)" in tree

        # Individual files
        assert "user.py (100 bytes)" in tree
        assert "post.py (150 bytes)" in tree
        assert "index.py (200 bytes)" in tree
        assert "config.py (50 bytes)" in tree

    def test_file_tree_structure(self):
        """Test tree structure with proper indentation."""
        files = {
            "README.md": "# Project",
            "src/main.py": "main",
            "src/lib/helper.py": "help",
        }
        data = ProjectFilesData(files=files)
        tree = data.file_tree
        lines = tree.split("\n")

        # Check structure - Updated to match actual output
        assert any("README.md" in line and "├──" in line for line in lines)
        assert any("src/" in line and "└──" in line for line in lines)
        assert any("    " in line and "main.py" in line for line in lines)
        assert any("    " in line and "lib/" in line for line in lines)
        assert any("    " in line and "helper.py" in line for line in lines)

    def test_empty_files(self):
        """Test handling of empty files."""
        files = {
            "empty.txt": "",
            "dir/also_empty.py": "",
        }
        data = ProjectFilesData(files=files)
        tree = data.file_tree

        # Empty files should show 0 bytes
        assert "empty.txt (0 bytes)" in tree
        assert "also_empty.py (0 bytes)" in tree
        assert "dir/ (0 bytes)" in tree  # Directory with only empty files

    def test_utf8_encoding_sizes(self):
        """Test that sizes are calculated in UTF-8 bytes."""
        files = {
            "ascii.txt": "hello",  # 5 bytes
            "emoji.txt": "👋",  # 4 bytes in UTF-8
            "unicode.txt": "café",  # 5 bytes in UTF-8 (é is 2 bytes)
        }
        data = ProjectFilesData(files=files)
        tree = data.file_tree

        assert "ascii.txt (5 bytes)" in tree
        assert "emoji.txt (4 bytes)" in tree
        assert "unicode.txt (5 bytes)" in tree
