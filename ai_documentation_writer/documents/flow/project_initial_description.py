"""Project initial description document for storing AI-generated project documentation."""

from enum import StrEnum

from ai_pipeline_core.documents import FlowDocument


class ProjectInitialDescriptionEnum(StrEnum):
    """File names for project initial description documents."""

    INITIAL_DESCRIPTION = "initial_description.md"


class ProjectInitialDescriptionDocument(FlowDocument):
    """Document containing AI-generated initial description of the project."""

    FILES = ProjectInitialDescriptionEnum
