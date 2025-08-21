"""Tasks for documenting the codebase."""

from .document_codebase import document_codebase_task
from .document_codebase_directory import document_codebase_directory_task

__all__ = [
    "document_codebase_task",
    "document_codebase_directory_task",
]
