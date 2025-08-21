"""Pydantic models for structured outputs in generate_initial_description task."""

from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """Information about a file to be read."""

    path: str = Field(description="Relative path to the file")
    size: int = Field(description="Size of the file in bytes")


class SelectedFiles(BaseModel):
    """Model for AI to select files to read in the current iteration."""

    reasoning: str = Field(description="Brief reasoning for selecting files or deciding to finish")
    files: list[FileInfo] = Field(
        default_factory=list,
        description="List of files to read in this iteration. Return empty list to finish.",
    )
