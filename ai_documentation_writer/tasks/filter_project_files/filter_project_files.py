"""Filter project files to remove unnecessary content for documentation analysis."""

import re
from pathlib import Path

from ai_pipeline_core import pipeline_task
from ai_pipeline_core.llm import AIMessages, ModelOptions, generate_structured
from ai_pipeline_core.logging import get_pipeline_logger
from ai_pipeline_core.prompt_manager import PromptManager

from ai_documentation_writer.flow_options import ProjectFlowOptions

from .models import FileFilterDecision

logger = get_pipeline_logger(__name__)
prompt_manager = PromptManager(__file__)


def prepare_file_statistics(files_dict: dict[str, str]) -> dict[str, tuple[int, str]]:
    """Get sample content from large or encoded files for AI analysis.

    Returns dict mapping file paths to sample content (5 line-based chunks:
    first 30, last 30, and 3x middle 30 lines, each line truncated at 200 chars).
    """
    file_samples: dict[str, tuple[int, str]] = {}

    for path, content in files_dict.items():
        # Include files that are large or have encoded data
        if len(content) > 10_000 or has_likely_encoded_data(content):
            lines = content.splitlines()
            total_lines = len(lines)

            chunk_size = 30
            chunks = []

            # First 30 lines
            first_chunk = lines[:chunk_size]
            truncated = "\n".join(first_chunk)
            if len(truncated) > 200:
                truncated = truncated[:200] + "..."
            chunks.append(f"// Lines 1-{len(truncated.splitlines())}\n" + truncated)

            # Calculate positions for middle chunks
            fractions = []
            if total_lines > 50:
                fractions.append(0.5)
            if total_lines > 150:
                fractions.extend([0.25, 0.75])

            for fraction in sorted(fractions):
                start_idx = int(total_lines * fraction)
                end_idx = min(start_idx + chunk_size, total_lines)
                middle_chunk = lines[start_idx:end_idx]
                truncated = "\n".join(middle_chunk)
                if len(truncated) > 200:
                    truncated = truncated[:200] + "..."
                chunks.append(
                    f"// Lines {start_idx + 1}-{start_idx + len(truncated.splitlines())}\n"
                    + truncated
                )

            # Last 30 lines
            if total_lines > 10:
                last_start = max(total_lines - chunk_size, 0)
                last_chunk = lines[last_start:]
                truncated = "\n".join(last_chunk)
                if len(truncated) > 200:
                    truncated = truncated[:200] + "..."
                chunks.append(
                    f"// Lines {last_start + 1}-{last_start + len(truncated.splitlines())}\n"
                    + truncated
                )

            # Join chunks with double newline for clarity
            file_samples[path] = (len(content), "\n\n".join(chunks))

    return file_samples


def has_likely_encoded_data(content: str) -> bool:
    """Detect if content has likely encoded data (base64, hex, escaped sequences)."""
    if not content or len(content) < 1000:
        return False

    # Check for large blocks of base64 (>500 continuous characters)
    # Base64 blocks typically don't have spaces or common punctuation
    base64_pattern = r"[A-Za-z0-9+/]{500,}={0,2}"
    if re.search(base64_pattern, content):
        return True

    # Check for large hex blocks (>500 continuous hex characters)
    hex_pattern = r"[0-9a-fA-F]{500,}"
    if re.search(hex_pattern, content):
        return True

    # Check for blocks with many escaped characters
    # Look for patterns like \x00, \n, \r, \0, etc.
    escaped_pattern = r"(\\x[0-9a-fA-F]{2}|\\[0-7]{1,3}|\\[nrt0]){50,}"
    if re.search(escaped_pattern, content):
        return True

    return False


def apply_filters(
    files_dict: dict[str, str], filter_decision: FileFilterDecision
) -> dict[str, str]:
    """Apply filtering decisions to files dictionary."""
    filtered = {}
    excluded_count = 0

    for path, content in files_dict.items():
        should_exclude = False

        # Check exclude patterns
        if filter_decision.exclude_patterns:
            for pattern in filter_decision.exclude_patterns:
                if Path(path).match(pattern):
                    should_exclude = True
                    break

        # Check exclude directories
        if not should_exclude and filter_decision.exclude_directories:
            for dir_path in filter_decision.exclude_directories:
                # Normalize paths for comparison
                normalized_dir = dir_path.rstrip("/") + "/"
                normalized_path = path if path.startswith("/") else "/" + path
                if normalized_path.startswith(normalized_dir) or path.startswith(dir_path + "/"):
                    should_exclude = True
                    break

        # Check specific files
        if not should_exclude and path in filter_decision.exclude_specific_files:
            should_exclude = True

        if should_exclude:
            excluded_count += 1
        else:
            filtered[path] = content

    logger.info(f"Excluded {excluded_count} files based on filter decisions")
    return filtered


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable format (up to MB)."""
    size_float = float(size_bytes)
    for unit in ["B", "KB", "MB"]:
        if size_float < 1024.0:
            return f"{size_float:.1f}{unit}"
        size_float /= 1024.0
    # If we get here, it's still in MB (files won't be > 100MB)
    return f"{size_float:.1f}MB"


@pipeline_task
async def filter_project_files_task(
    file_tree: str,
    files_dict: dict[str, str],
    max_all_files_size: int,
    flow_options: ProjectFlowOptions,
) -> dict[str, str]:
    """Filter out unnecessary files using AI analysis."""
    original_count = len(files_dict)
    original_size = sum(len(content) for content in files_dict.values())

    logger.info(
        f"Starting file filtering for {original_count} files ({format_size(original_size)} total)"
    )

    # Step 1: Prepare file samples for analysis
    file_samples = prepare_file_statistics(files_dict)

    # Log statistics
    logger.info("File analysis statistics:")
    logger.info(f"  - Files requiring review: {len(file_samples)}")
    logger.info(f"  - Total files: {original_count}")
    logger.info(f"  - Total size: {format_size(original_size)}")
    logger.info(f"  - Max size: {format_size(max_all_files_size)}")

    # Step 2: Create messages following security guidelines from CLAUDE.md
    # File content as separate messages to prevent injection
    messages = []

    # Add file samples as separate messages (not in prompt)
    for file_path, (file_size, sample_content) in file_samples.items():
        file_message = (
            f"# CHUNKS OF FILE: {file_path} (size: {format_size(file_size)})\n\n{sample_content}"
        )
        messages.append(file_message)

    # Step 3: Create prompt with only file list (no content)
    filter_prompt = prompt_manager.get(
        "identify_files_to_exclude.jinja2",
        file_tree=file_tree,
        files_to_review=file_samples,
        total_files=original_count,
        total_size=original_size,
        max_all_files_size=max_all_files_size,
        format_size=format_size,
    )

    # Add prompt after file samples
    messages.append(filter_prompt)

    # Step 4: Get AI filtering decision
    filter_response = await generate_structured(
        model=flow_options.core_model,  # type: ignore[arg-type]
        response_format=FileFilterDecision,
        messages=AIMessages(messages),  # All messages in order
        options=ModelOptions(reasoning_effort="high"),
    )

    filter_decision = filter_response.parsed

    logger.info("AI filtering decision:")
    logger.info(f"  Reasoning: {filter_decision.reasoning}")
    logger.info(f"  Exclude patterns: {filter_decision.exclude_patterns}")
    logger.info(f"  Exclude directories: {filter_decision.exclude_directories}")
    logger.info(f"  Specific files: {len(filter_decision.exclude_specific_files)} files")

    # Step 4: Apply filters
    filtered_files = apply_filters(files_dict, filter_decision)

    # Calculate statistics
    filtered_count = len(filtered_files)
    filtered_size = sum(len(content) for content in filtered_files.values())
    reduction_percent = (
        ((original_size - filtered_size) / original_size * 100) if original_size > 0 else 0
    )

    logger.info("File filtering complete:")
    logger.info(f"  - Original: {original_count} files ({format_size(original_size)})")
    logger.info(f"  - Filtered: {filtered_count} files ({format_size(filtered_size)})")
    logger.info(f"  - Removed: {original_count - filtered_count} files")
    logger.info(f"  - Size reduction: {reduction_percent:.1f}%")

    return filtered_files
