"""Flow options configuration for documentation generation."""

from ai_pipeline_core import FlowOptions, ModelName
from pydantic import Field


class ProjectFlowOptions(FlowOptions):
    """Options to be provided to each flow in the documentation writer pipeline.

    Extends the base FlowOptions with project-specific configuration.
    """

    # Required project fields
    target: str = Field(description="Target source: Git repository URL or local directory path")
    branch: str | None = Field(default=None, description="Branch name for git repositories")
    tag: str | None = Field(default=None, description="Tag name for git repositories")
    instructions: str | None = Field(default=None, description="High-level instructions for the AI")

    # Override defaults from base class
    core_model: ModelName | str = Field(default="gemini-2.5-pro")
    small_model: ModelName | str = Field(default="gemini-2.5-flash")

    # Additional configuration
    supporting_models: list[ModelName | str] = Field(
        default_factory=lambda: ["gemini-2.5-flash"],
        description="Additional models for planning and reviewing",
    )
    batch_max_chars: int = Field(
        default=200_000,
        description="Maximum total characters in a batch for summarization",
    )
    batch_max_files: int = Field(
        default=50,
        description="Maximum number of files in a batch for summarization",
    )
    enable_file_filtering: bool = Field(
        default=True,
        description="Enable AI-powered file filtering for large projects",
    )
