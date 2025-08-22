"""Task for documenting a single directory."""

from typing import Optional

from ai_pipeline_core import pipeline_task
from ai_pipeline_core.llm import AIMessages, ModelOptions, generate_structured
from ai_pipeline_core.logging import get_pipeline_logger
from ai_pipeline_core.prompt_manager import PromptManager
from pydantic import BaseModel, Field

from ai_documentation_writer.documents.flow.codebase_documentation import (
    DirectoryAnalysis,
    FileAnalysis,
    SingleDirectoryAnalysis,
)
from ai_documentation_writer.flow_options import ProjectFlowOptions


class DirectoryAndFilesAnalysis(BaseModel):
    """Combined file summaries and directory analysis for small directories."""

    file_summaries: list[FileAnalysis] = Field(
        description="List of file analyses for all files in the directory"
    )
    directory_analysis: Optional[SingleDirectoryAnalysis] = Field(
        description=(
            "Optional comprehensive analysis of the directory structure and architecture. "
            "Should be provided only when explicitly requested by the user"
        )
    )


logger = get_pipeline_logger(__name__)
prompt_manager = PromptManager(__file__)


def create_file_batches(
    files_in_dir: dict[str, str],
    max_files: int,
    max_chars: int,
) -> list[dict[str, str]]:
    """Create batches of files respecting size limits.

    Args:
        files_in_dir: Dictionary of file paths to contents in this directory
        max_files: Maximum files per batch
        max_chars: Maximum total characters per batch

    Returns:
        List of dictionaries, each containing a batch of files
    """
    batches = []
    current_batch = {}
    current_chars = 0

    for file_path, content in files_in_dir.items():
        file_chars = len(content)

        if file_chars == 0:
            continue  # Skip empty files

        # Check if adding this file would exceed limits
        if current_batch and (
            len(current_batch) >= max_files or current_chars + file_chars > max_chars
        ):
            # Save current batch and start new one
            batches.append(current_batch)
            current_batch = {}
            current_chars = 0

        # Add file to current batch
        current_batch[file_path] = content
        current_chars += file_chars

    # Add remaining batch if not empty
    if current_batch:
        batches.append(current_batch)

    return batches


def file_summaries_to_ai_message(summaries: list[FileAnalysis]) -> str:
    """Convert FileAnalysis list to an AI message format.

    Creates a structured message with file summaries for context.
    """
    if not summaries:
        return ""

    message_parts = ["## Previously Analyzed Files in This Directory\n"]

    for summary in summaries:
        message_parts.append(f"### {summary.file_path}")
        message_parts.append(f"**Summary:** {summary.summary}")
        if summary.key_elements:
            message_parts.append(f"**Key Elements:** {', '.join(summary.key_elements)}")
        message_parts.append("")  # Empty line for spacing

    return "\n".join(message_parts)


def directory_summaries_to_ai_messages(summaries: list[DirectoryAnalysis]) -> AIMessages:
    """Convert DirectoryAnalysis list to AIMessages format.

    Creates structured messages with subdirectory summaries for context.
    """
    if not summaries:
        return AIMessages([])

    messages = []

    for summary in summaries:
        message_parts = [f"## SUBDIRECTORY: {summary.path}\n"]
        message_parts.append(f"**Summary:** {summary.summary}\n")

        # Add file summaries if present
        if summary.file_summaries:
            message_parts.append("**Files in this subdirectory:**")
            for file_summary in summary.file_summaries:
                message_parts.append(f"  - {file_summary.file_path}: {file_summary.summary}")
            message_parts.append("")

        # Add nested subdirectory summaries if present
        if summary.subdirectory_summaries:
            message_parts.append("**Nested subdirectories:**")
            for subdir in summary.subdirectory_summaries:
                message_parts.append(f"  - {subdir.path}: {subdir.summary}")
            message_parts.append("")

        messages.append("\n".join(message_parts))

    return AIMessages(messages)


@pipeline_task
async def document_codebase_directory_task(
    dir_path: str,
    files_in_dir: dict[str, str],
    subdirectory_summaries: list[DirectoryAnalysis],
    common_context: AIMessages,
    flow_options: ProjectFlowOptions,
) -> DirectoryAnalysis:
    """Document a single directory with its files and subdirectories.

    Args:
        dir_path: Path to the directory
        files_in_dir: Dictionary of file paths to contents in this directory
        subdirectory_summaries: List of DirectoryAnalysis objects for immediate subdirectories
        common_context: Common context containing file tree and initial description
        flow_options: Flow configuration options

    Returns:
        DirectoryAnalysis for the directory
    """
    logger.info(f"Processing directory: {dir_path}")

    batches = create_file_batches(
        files_in_dir,
        flow_options.batch_max_files,
        flow_options.batch_max_chars,
    )

    if len(batches) == 0:
        if len(subdirectory_summaries) > 0:
            batches.append({})
        else:
            logger.info(f"Directory {dir_path} is empty")
            return DirectoryAnalysis(
                path=dir_path,
                summary="Directory is empty",
                main_components=[],
                patterns=[],
                documentation_usage="Empty directory with no content to document",
                file_summaries=[],
                subdirectory_summaries=subdirectory_summaries,
            )

    context = AIMessages(
        [*common_context, *directory_summaries_to_ai_messages(subdirectory_summaries)]
    )
    file_summaries: list[FileAnalysis] = []

    logger.info(f"Processing {len(files_in_dir)} files in {len(batches)} batch(es)")
    for batch_idx, batch_files in enumerate(batches, 1):
        logger.info(f"Processing batch {batch_idx}/{len(batches)}")
        is_last_batch = batch_idx == len(batches)

        batch_file_messages: list[str] = []
        for file_path, content in batch_files.items():
            batch_file_messages.append(f"# FILE: {file_path}\n---\n{content}")

        # Generate combined prompt for both file and directory analysis
        combined_prompt = prompt_manager.get(
            "document_codebase_directory.jinja2",
            directory_path=dir_path,
            file_paths=list(batch_files.keys()),
            is_last_batch=is_last_batch,
        )

        # Combine file messages with analysis prompt (files first, then instructions)
        analysis_response = await generate_structured(
            model=flow_options.small_model,  # type: ignore
            response_format=DirectoryAndFilesAnalysis,
            context=context,
            messages=AIMessages([*batch_file_messages, combined_prompt]),
            options=ModelOptions(reasoning_effort="high"),
        )
        analysis: DirectoryAndFilesAnalysis = analysis_response.parsed
        if is_last_batch and not analysis.directory_analysis:
            logger.error(
                "Directory analysis is required for the last batch, but it is not provided"
            )
            raise ValueError("Directory analysis is required for the last batch")
        elif not is_last_batch and analysis.directory_analysis:
            logger.error(
                "Directory analysis is not allowed for non-last batches, but it is provided"
            )
            raise ValueError("Directory analysis is not allowed for non-last batches")

        new_file_summaries: list[FileAnalysis] = analysis.file_summaries
        context.append(file_summaries_to_ai_message(new_file_summaries))
        file_summaries.extend(new_file_summaries)

        if analysis.directory_analysis:
            # Create DirectoryAnalysis from SingleDirectoryAnalysis
            # Use dir_path parameter to ensure correct path (AI might not set it correctly)
            return DirectoryAnalysis(
                path=dir_path,
                summary=analysis.directory_analysis.summary,
                main_components=analysis.directory_analysis.main_components,
                patterns=analysis.directory_analysis.patterns,
                documentation_usage=analysis.directory_analysis.documentation_usage,
                file_summaries=file_summaries,
                subdirectory_summaries=subdirectory_summaries,
            )

    raise ValueError("No directory analysis found, it should not happen")
