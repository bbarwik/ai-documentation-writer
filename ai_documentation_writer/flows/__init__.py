"""Flow modules for documentation generation pipeline."""

from .step_01_prepare_project_files import PrepareProjectFilesConfig, prepare_project_files
from .step_02_generate_initial_description import (
    GenerateInitialDescriptionConfig,
    generate_initial_description,
)
from .step_03_document_codebase import DocumentCodebaseConfig, document_codebase
from .step_04_create_final_documentation import (
    CreateFinalDocumentationConfig,
    create_final_documentation,
)

FLOW_CONFIGS = [
    PrepareProjectFilesConfig,
    GenerateInitialDescriptionConfig,
    DocumentCodebaseConfig,
    CreateFinalDocumentationConfig,
]

FLOWS = [
    prepare_project_files,
    generate_initial_description,
    document_codebase,
    create_final_documentation,
]

assert len(FLOW_CONFIGS) == len(FLOWS)

__all__ = [
    "PrepareProjectFilesConfig",
    "prepare_project_files",
    "GenerateInitialDescriptionConfig",
    "generate_initial_description",
    "DocumentCodebaseConfig",
    "document_codebase",
    "CreateFinalDocumentationConfig",
    "create_final_documentation",
    "FLOW_CONFIGS",
    "FLOWS",
]
