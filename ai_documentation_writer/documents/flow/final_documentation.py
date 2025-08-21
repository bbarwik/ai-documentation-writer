"""Final documentation document for storing generated documentation."""

from enum import StrEnum

from ai_pipeline_core.documents import FlowDocument


class FinalDocumentationEnum(StrEnum):
    """File names for final documentation documents."""

    README = "README.md"
    DOCUMENTATION = "DOCUMENTATION.md"
    DEVELOPER_GUIDE = "DEVELOPER_GUIDE.md"


class FinalDocumentationDocument(FlowDocument):
    """Document containing final generated documentation."""

    FILES = FinalDocumentationEnum
