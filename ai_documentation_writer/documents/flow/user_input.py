"""User input document for repository documentation generation."""

from enum import StrEnum

from ai_pipeline_core.documents import FlowDocument
from pydantic import BaseModel, Field


class UserInputFiles(StrEnum):
    USER_INPUT = "user_input.json"


class UserInputData(BaseModel):
    """Data structure for user input parameters."""

    target: str = Field(description="Target source: git repository URL or local directory path")
    branch: str | None = Field(default=None, description="Optional branch name for git repos")
    tag: str | None = Field(default=None, description="Optional tag name for git repos")
    instructions: str | None = Field(
        default=None, description="Optional high-level instructions for documentation"
    )


class UserInputDocument(FlowDocument):
    """Document containing user input for documentation generation."""

    FILES = UserInputFiles
