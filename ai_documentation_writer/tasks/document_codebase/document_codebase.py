"""Task for documenting the entire codebase with file and directory summaries."""

import asyncio
from collections import defaultdict
from pathlib import Path

from ai_pipeline_core.llm import AIMessages
from ai_pipeline_core.logging import get_pipeline_logger
from ai_pipeline_core.prompt_manager import PromptManager
from ai_pipeline_core.tracing import trace
from prefect import task

from ai_documentation_writer.documents.flow.codebase_documentation import (
    CodebaseDocumentationDocument,
    CodebaseDocumentationEnum,
    DirectoryAnalysis,
)
from ai_documentation_writer.documents.flow.project_files import (
    ProjectFilesData,
    ProjectFilesDocument,
)
from ai_documentation_writer.documents.flow.project_initial_description import (
    ProjectInitialDescriptionDocument,
)
from ai_documentation_writer.flow_options import FlowOptions

from .document_codebase_directory import document_codebase_directory_task

logger = get_pipeline_logger(__name__)
prompt_manager = PromptManager(__file__)


def organize_files_by_directory(files: dict[str, str]) -> dict[str, dict[str, str]]:
    """Organize files by their parent directory.

    Args:
        files: Dictionary mapping file paths to contents

    Returns:
        Dictionary mapping directory paths to dict of file paths->contents in that directory
    """
    dir_files: dict[str, dict[str, str]] = defaultdict(dict)

    for file_path, content in files.items():
        path = Path(file_path)
        # Get parent directory, use "." for root files
        parent = str(path.parent) if path.parent != Path(".") else "."
        dir_files[parent][file_path] = content

    return dict(dir_files)


def get_directory_depth(path: str) -> int:
    """Get the depth of a directory path."""
    if path == ".":
        return 0
    return len(Path(path).parts)


def get_directories_by_depth(dir_files: dict[str, dict[str, str]]) -> dict[int, list[str]]:
    """Group directories by their depth level.

    Returns directories organized by depth, with deepest first.
    """
    depth_dirs: defaultdict[int, list[str]] = defaultdict(list)

    for dir_path in dir_files.keys():
        depth = get_directory_depth(dir_path)
        depth_dirs[depth].append(dir_path)

    return dict(depth_dirs)


@task
@trace
async def document_codebase_task(
    project_files_doc: ProjectFilesDocument,
    initial_description_doc: ProjectInitialDescriptionDocument,
    flow_options: FlowOptions,
) -> CodebaseDocumentationDocument:
    """Document the entire codebase with detailed file and directory summaries.

    Args:
        project_files_doc: Document containing all project files
        initial_description_doc: Initial project description for context
        flow_options: Flow configuration options

    Returns:
        CodebaseDocumentationDocument with comprehensive documentation
    """
    logger.info("Starting codebase documentation")

    # Extract data
    project_data = project_files_doc.as_pydantic_model(ProjectFilesData)
    initial_description = initial_description_doc.as_text()

    # Prepare common context with file tree and initial description
    common_context_prompt = prompt_manager.get(
        "document_codebase.jinja2",
        file_tree=project_data.file_tree,
        initial_description=initial_description,
    )
    common_context = AIMessages([common_context_prompt])

    logger.info("Prepared common context for all analysis tasks")

    # Organize files by directory
    dir_files = organize_files_by_directory(project_data.files)
    logger.info(f"Found {len(dir_files)} directories to process")

    # Get directories by depth (deepest first)
    depth_dirs = get_directories_by_depth(dir_files)
    max_depth = max(depth_dirs.keys()) if depth_dirs else 0

    # Storage for all summaries by path
    all_directory_summaries: dict[str, DirectoryAnalysis] = {}

    # Process directories from deepest to shallowest
    for depth in range(max_depth, -1, -1):
        directories = sorted(depth_dirs[depth])
        logger.info(f"Processing {len(directories)} directories at depth {depth} in parallel")

        # Create tasks for all directories at this depth level
        directory_tasks = []
        for dir_path in directories:
            files_in_dir = dir_files[dir_path]

            # Get subdirectory summaries if any
            subdir_summaries: list[DirectoryAnalysis] = []
            for other_dir, other_summary in all_directory_summaries.items():
                other_path = Path(other_dir)
                if other_path.parent == Path(dir_path):
                    subdir_summaries.append(other_summary)

            # Create task for this directory
            task = document_codebase_directory_task(
                dir_path=dir_path,
                files_in_dir=files_in_dir,
                subdirectory_summaries=subdir_summaries,
                common_context=common_context,
                flow_options=flow_options,
            )
            directory_tasks.append(task)

        # Process all directories at this depth level in parallel
        directory_summaries = await asyncio.gather(*directory_tasks)

        # Store results
        for summary in directory_summaries:
            all_directory_summaries[summary.path] = summary

        logger.info(f"Completed all directories at depth {depth}")

    # Get the root directory summary which should contain everything
    assert "." in all_directory_summaries, "Root directory summary not found"
    root_summary: DirectoryAnalysis = all_directory_summaries["."]  # type: ignore

    logger.info(
        f"Documentation complete: {len(project_data.files)} files, "
        f"{len(all_directory_summaries)} directories"
    )

    return CodebaseDocumentationDocument.create_as_json(
        name=CodebaseDocumentationEnum.CODEBASE_DOCUMENTATION.value,
        description="Comprehensive documentation of all files and directories",
        data=root_summary,
    )
