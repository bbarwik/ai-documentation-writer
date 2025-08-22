"""Flow for documenting the entire codebase."""

from ai_pipeline_core import DocumentList, FlowConfig, get_pipeline_logger, pipeline_flow

from ai_documentation_writer.documents.flow.codebase_documentation import (
    CodebaseDocumentationDocument,
)
from ai_documentation_writer.documents.flow.project_files import ProjectFilesDocument
from ai_documentation_writer.documents.flow.project_initial_description import (
    ProjectInitialDescriptionDocument,
)
from ai_documentation_writer.flow_options import ProjectFlowOptions
from ai_documentation_writer.tasks.document_codebase import document_codebase_task

logger = get_pipeline_logger(__name__)


class DocumentCodebaseConfig(FlowConfig):
    """Configuration for document codebase flow."""

    INPUT_DOCUMENT_TYPES = [ProjectFilesDocument, ProjectInitialDescriptionDocument]
    OUTPUT_DOCUMENT_TYPE = CodebaseDocumentationDocument


@pipeline_flow
async def document_codebase(
    project_name: str, documents: DocumentList, flow_options: ProjectFlowOptions
) -> DocumentList:
    """Document the entire codebase with file and directory summaries.

    Args:
        project_name: Name of the project
        documents: Input documents containing project files and initial description
        flow_options: Flow configuration

    Returns:
        DocumentList containing the codebase documentation
    """
    logger.info(f"Starting codebase documentation for: {project_name}")

    # Get input documents
    input_docs = DocumentCodebaseConfig.get_input_documents(documents)

    # Get the required documents
    project_files_docs = input_docs.filter_by_type(ProjectFilesDocument)
    if not project_files_docs:
        raise ValueError("ProjectFilesDocument not found in input documents")
    project_files_doc: ProjectFilesDocument = project_files_docs[0]  # type: ignore

    initial_description_docs = input_docs.filter_by_type(ProjectInitialDescriptionDocument)
    if not initial_description_docs:
        raise ValueError("ProjectInitialDescriptionDocument not found in input documents")
    initial_description_doc: ProjectInitialDescriptionDocument = initial_description_docs[0]  # type: ignore

    # Document the codebase
    codebase_doc = await document_codebase_task(
        project_files_doc=project_files_doc,
        initial_description_doc=initial_description_doc,
        flow_options=flow_options,
    )

    # Create output documents
    output_docs = DocumentList([codebase_doc])

    # Validate output documents
    DocumentCodebaseConfig.validate_output_documents(output_docs)

    logger.info(f"Successfully documented codebase: {codebase_doc.name}")
    return output_docs
