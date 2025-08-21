"""Task for selecting text files from a project directory."""

import json
from pathlib import Path

from ai_pipeline_core.documents import Document
from ai_pipeline_core.logging import get_pipeline_logger
from ai_pipeline_core.tracing import trace
from prefect import task

from ai_documentation_writer.documents.flow.project_files import (
    ProjectFilesData,
    ProjectFilesDocument,
    ProjectFilesEnum,
)
from ai_documentation_writer.flow_options import FlowOptions
from ai_documentation_writer.tasks.filter_project_files import filter_project_files_task

logger = get_pipeline_logger(__name__)

# Files/directories to exclude
EXCLUDE_PATTERNS = {
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".env",
    "dist",
    "build",
    "target",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".coverage",
    "htmlcov",
    ".tox",
    ".eggs",
    "*.egg-info",
    ".DS_Store",
}


def should_exclude(path: Path) -> bool:
    """Check if a path should be excluded."""
    path_str = str(path)
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return True
    return False


def is_text_file(file_path: Path, max_size: int) -> tuple[bool, str | None]:
    """Check if a file is a text file and return its content.

    Args:
        file_path: Path to the file
        max_size: Maximum file size to process

    Returns:
        Tuple of (is_text, content) where content is None if not text
    """
    try:
        # Check file size first
        if file_path.stat().st_size > max_size:
            logger.debug(f"Skipping large file: {file_path}")
            return False, None

        # Try to read as text
        content = file_path.read_text(encoding="utf-8")

        # Check if content is JSON serializable (ensures it's text)
        try:
            json.dumps(content)
            return True, content
        except (TypeError, ValueError):
            return False, None

    except (UnicodeDecodeError, OSError) as e:
        logger.debug(f"Skipping non-text or unreadable file {file_path}: {e}")
        return False, None


@task
@trace
async def select_project_files_task(
    project_dir: Path,
    user_instructions: str | None,
    flow_options: FlowOptions,
) -> ProjectFilesDocument:
    """Select text files from a project directory.

    Args:
        project_dir: Directory containing project files
        user_instructions: Optional user instructions for file selection
        flow_options: Flow configuration options

    Returns:
        ProjectFilesDocument containing selected text files
    """
    logger.info(f"Selecting files from {project_dir}")

    # Calculate max file size (Document.MAX_CONTENT_SIZE // 4)
    # Using a reasonable default if MAX_CONTENT_SIZE is not available
    max_file_size = 1024 * 1024  # 1 MB
    max_all_files_size = Document.MAX_CONTENT_SIZE // 4

    files_data = {}
    total_size = 0

    # Walk through all files in the directory
    for file_path in project_dir.rglob("*"):
        if file_path.is_file() and not should_exclude(file_path):
            # Get relative path
            relative_path = file_path.relative_to(project_dir)
            relative_path_str = str(relative_path)

            # Check if it's a text file and get content
            is_text, content = is_text_file(file_path, max_file_size)

            if is_text and content is not None:
                files_data[relative_path_str] = content
                total_size += len(content.encode("utf-8"))
                logger.debug(f"Added file: {relative_path_str}")

    logger.info(f"Selected {len(files_data)} text files, total size: {total_size:,} bytes")

    # Apply AI filtering if enabled
    if flow_options.enable_file_filtering and len(files_data) > 0:
        for i in range(3):
            size_mb = total_size / 1_000_000
            logger.info(
                f"[{i + 1}/3] Applying AI filtering to {len(files_data)} files ({size_mb:.1f}MB)"
            )

            # Generate file tree for AI analysis
            temp_project_data = ProjectFilesData(files=files_data)
            file_tree = temp_project_data.file_tree

            # Apply AI filtering
            files_data = await filter_project_files_task(
                file_tree=file_tree,
                files_dict=files_data,
                max_all_files_size=max_all_files_size,
                flow_options=flow_options,
            )

            # Update total size after filtering
            total_size = sum(len(content.encode("utf-8")) for content in files_data.values())
            logger.info(
                f"[{i + 1}/3] After filtering: {len(files_data)} files, {total_size:,} bytes"
            )
            if total_size < max_all_files_size:
                max_mb = max_all_files_size / 1_000_000
                logger.info(
                    f"[{i + 1}/3] Total size is less than {max_mb:.1f}MB, stopping filtering"
                )
                break
            else:
                max_mb = max_all_files_size / 1_000_000
                logger.info(f"[{i + 1}/3] Total size is greater than {max_mb:.1f}MB, continuing")

    # Create ProjectFilesData
    project_data = ProjectFilesData(files=files_data)

    # Create and return ProjectFilesDocument using Document.create_as_json
    return ProjectFilesDocument.create_as_json(
        name=ProjectFilesEnum.PROJECT_FILES.value,
        description=f"Selected text files from {project_dir.name}",
        data=project_data,
    )
