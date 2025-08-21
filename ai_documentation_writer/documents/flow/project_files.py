"""Project files document for storing selected text files from the repository."""

from enum import StrEnum
from typing import Any

from ai_pipeline_core.documents import FlowDocument
from pydantic import BaseModel, Field


class ProjectFilesEnum(StrEnum):
    """File names for project files documents."""

    PROJECT_FILES = "project_files.json"


class ProjectFilesData(BaseModel):
    """Data structure for project files."""

    files: dict[str, str] = Field(
        default_factory=dict, description="Dictionary mapping relative file paths to file contents"
    )

    @property
    def total_files(self) -> int:
        """Total number of files in the project."""
        return len(self.files)

    @property
    def total_size(self) -> int:
        """Total size of all files in bytes."""
        return sum(len(content.encode("utf-8")) for content in self.files.values())

    @property
    def file_tree(self) -> str:
        """Generate a file tree with directory and file sizes."""
        # Build tree structure with sizes
        tree: dict[str, Any] = {}
        file_sizes: dict[str, int] = {}

        # Store file sizes
        for path, content in self.files.items():
            file_sizes[path] = len(content.encode("utf-8"))

        # Build tree and calculate directory sizes
        dir_sizes: dict[str, int] = {}
        for path, size in file_sizes.items():
            parts = path.split("/")
            current = tree

            # Update all parent directory sizes
            for i in range(len(parts)):
                dir_path = "/".join(parts[: i + 1])
                dir_sizes[dir_path] = dir_sizes.get(dir_path, 0) + size

            # Build tree structure
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = size  # Store raw size for now

        # Build output lines
        lines: list[str] = []

        def render(node: dict[str, Any], path: str = "", prefix: str = "") -> None:
            items = sorted(node.items())
            for i, (name, value) in enumerate(items):
                is_last = i == len(items) - 1
                current_path = f"{path}/{name}" if path else name

                if isinstance(value, dict):  # Directory
                    size = dir_sizes.get(current_path, 0)
                    lines.append(f"{prefix}{'└── ' if is_last else '├── '}{name}/ ({size:,} bytes)")
                    render(value, current_path, prefix + ("    " if is_last else "│   "))
                else:  # File
                    lines.append(f"{prefix}{'└── ' if is_last else '├── '}{name} ({value:,} bytes)")

        render(tree)
        return "\n".join(lines)


class ProjectFilesDocument(FlowDocument):
    """Document containing selected text files from the project."""

    FILES = ProjectFilesEnum
