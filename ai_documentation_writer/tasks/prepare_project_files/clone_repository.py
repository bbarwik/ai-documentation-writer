"""Task for cloning a git repository."""

import asyncio
from pathlib import Path

from ai_pipeline_core import get_pipeline_logger, pipeline_task

from ai_documentation_writer.documents.flow.user_input import UserInputData

logger = get_pipeline_logger(__name__)


@pipeline_task
async def clone_repository_task(
    user_input: UserInputData,
    temp_dir: Path,
) -> Path:
    """Clone a git repository to a temporary directory.

    Args:
        user_input: User input data containing target repository
        temp_dir: Temporary directory to clone into

    Returns:
        Path to the cloned repository directory
    """
    # Check if target is already a local directory
    target_path = Path(user_input.target)
    if target_path.exists() and target_path.is_dir():
        logger.info(f"Using local directory: {target_path}")
        return target_path

    # Clone git repository
    logger.info(f"Cloning repository: {user_input.target}")

    # Prepare clone directory
    repo_dir = temp_dir / "repository"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Build git clone command
    clone_cmd = ["git", "clone", "--depth", "1"]

    if user_input.branch:
        clone_cmd.extend(["--branch", user_input.branch])
    elif user_input.tag:
        clone_cmd.extend(["--branch", user_input.tag])

    clone_cmd.extend([user_input.target, str(repo_dir)])

    # Execute git clone
    process = await asyncio.create_subprocess_exec(
        *clone_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode() if stderr else "Unknown error"
        raise RuntimeError(f"Failed to clone repository: {error_msg}")

    logger.info(f"Successfully cloned repository to {repo_dir}")

    return repo_dir
