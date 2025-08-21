"""Flow options configuration for documentation generation."""

from dataclasses import dataclass, field

from ai_pipeline_core.llm import ModelName

DEFAULT_CORE_MODEL: ModelName | str = "gemini-2.5-pro"
DEFAULT_SMALL_MODEL: ModelName | str = "gemini-2.5-flash"
DEFAULT_SUPPORTING_MODELS: list[ModelName | str] = ["gemini-2.5-flash"]


@dataclass
class FlowOptions:
    """Options to be provided to each flow.

    Attributes:
        core_model: Primary model for complex tasks
        small_model: Lightweight model for simple tasks
        supporting_models: Additional models for planning and reviewing
        batch_max_chars: Maximum total characters in a batch for summarization
        batch_max_files: Maximum number of files in a batch for summarization
        enable_file_filtering: Enable AI-powered file filtering for large projects
    """

    core_model: ModelName | str = DEFAULT_CORE_MODEL
    small_model: ModelName | str = DEFAULT_SMALL_MODEL
    supporting_models: list[ModelName | str] = field(
        default_factory=lambda: DEFAULT_SUPPORTING_MODELS.copy()
    )
    batch_max_chars: int = 200_000  # 200K characters max per batch
    batch_max_files: int = 50  # Maximum 50 files per batch

    # File filtering options
    enable_file_filtering: bool = True
