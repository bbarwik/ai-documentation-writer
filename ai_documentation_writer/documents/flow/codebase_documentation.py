"""Codebase documentation document for storing file and directory summaries."""

from enum import StrEnum

from ai_pipeline_core.documents import FlowDocument
from pydantic import BaseModel, Field


class CodebaseDocumentationEnum(StrEnum):
    """File names for codebase documentation documents."""

    CODEBASE_DOCUMENTATION = "codebase_documentation.json"


class FileAnalysis(BaseModel):
    """Analysis of a single file."""

    file_path: str = Field(description="The relative path to the file being analyzed")
    summary: str = Field(
        description="Comprehensive summary of the file's purpose, functionality and contents"
    )
    key_elements: list[str] = Field(
        default_factory=list,
        description="Key functions, classes, variables, exports or other important elements",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Key dependencies or imports used by this file",
    )
    documentation_usage: str = Field(
        description=(
            "Detailed analysis of how this file should be used when generating documentation"
        )
    )


class SingleDirectoryAnalysis(BaseModel):
    """Analysis of a single directory without nested content - used for AI model interaction."""

    path: str = Field(description="Relative path to the directory")
    summary: str = Field(
        description="Detailed summary of the directory's purpose, architecture and contents"
    )
    main_components: list[str] = Field(
        default_factory=list,
        description="Main components or modules in this directory",
    )
    patterns: list[str] = Field(
        default_factory=list,
        description="Design patterns or architectural patterns observed",
    )
    documentation_usage: str = Field(
        description=(
            "Detailed analysis of how important this directory is and how it should be used "
            "when generating documentation of the codebase"
        )
    )


class DirectoryAnalysis(SingleDirectoryAnalysis):
    """Comprehensive analysis of a directory including its nested contents."""

    file_summaries: list[FileAnalysis] = Field(
        default_factory=list, description="Analyses of files in this directory"
    )
    subdirectory_summaries: list["DirectoryAnalysis"] = Field(
        default_factory=list,
        description="Nested analyses of subdirectories",
    )


class CodebaseDocumentationDocument(FlowDocument):
    """Document containing comprehensive codebase documentation."""

    FILES = CodebaseDocumentationEnum
