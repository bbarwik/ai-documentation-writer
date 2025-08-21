"""Tasks for the AI Documentation Writer pipeline."""

from .document_codebase.document_codebase import document_codebase_task
from .generate_initial_description.generate_initial_description import (
    generate_initial_description_task,
)
from .prepare_project_files.clone_repository import clone_repository_task
from .prepare_project_files.select_files import select_project_files_task

__all__ = [
    # Prepare project files
    "clone_repository_task",
    "select_project_files_task",
    # Generate initial description
    "generate_initial_description_task",
    # Document codebase
    "document_codebase_task",
]
