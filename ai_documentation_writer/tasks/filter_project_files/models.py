"""Pydantic models for file filtering decisions."""

from pydantic import BaseModel, Field


class FileFilterDecision(BaseModel):
    """Decision about which files to exclude from documentation analysis."""

    reasoning: str = Field(description="Detailed explanation of filtering strategy")

    exclude_patterns: list[str] = Field(
        description="Glob patterns for files to exclude",
        examples=["**/*.yaml", "**/cassettes/**", "**/fixtures/**"],
        default_factory=list,
    )

    exclude_directories: list[str] = Field(
        description="Directory paths to exclude entirely",
        examples=["tests/fixtures", "vendor", "node_modules"],
        default_factory=list,
    )

    exclude_specific_files: list[str] = Field(
        description="Specific file paths to exclude", default_factory=list
    )
