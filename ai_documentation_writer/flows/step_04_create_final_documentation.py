"""Flow for creating final documentation from codebase analysis."""

from ai_pipeline_core.documents import DocumentList
from ai_pipeline_core.flow import FlowConfig
from ai_pipeline_core.logging import get_pipeline_logger
from ai_pipeline_core.tracing import trace
from prefect import flow

from ai_documentation_writer.documents.flow.codebase_documentation import (
    CodebaseDocumentationDocument,
)
from ai_documentation_writer.documents.flow.final_documentation import (
    FinalDocumentationDocument,
)
from ai_documentation_writer.documents.flow.project_initial_description import (
    ProjectInitialDescriptionDocument,
)
from ai_documentation_writer.flow_options import FlowOptions
from ai_documentation_writer.tasks.create_final_documentation import (
    create_final_documentation_task,
)

logger = get_pipeline_logger(__name__)


class CreateFinalDocumentationConfig(FlowConfig):
    """Configuration for create final documentation flow."""

    INPUT_DOCUMENT_TYPES = [CodebaseDocumentationDocument, ProjectInitialDescriptionDocument]
    OUTPUT_DOCUMENT_TYPE = FinalDocumentationDocument


@flow(flow_run_name="create_final_documentation-{project_name}")
@trace
async def create_final_documentation(
    project_name: str, documents: DocumentList, flow_options: FlowOptions = FlowOptions()
) -> DocumentList:
    """Create final documentation from codebase analysis.

    Args:
        project_name: Name of the project
        documents: Input documents containing codebase documentation and initial description
        flow_options: Flow configuration

    Returns:
        DocumentList containing the final documentation
    """
    logger.info(f"Starting final documentation creation for: {project_name}")

    # Get input documents
    input_docs = CreateFinalDocumentationConfig.get_input_documents(documents)

    # Get the required documents
    codebase_docs = input_docs.filter_by_type(CodebaseDocumentationDocument)
    if not codebase_docs:
        raise ValueError("CodebaseDocumentationDocument not found in input documents")
    codebase_doc: CodebaseDocumentationDocument = codebase_docs[0]  # type: ignore

    initial_description_docs = input_docs.filter_by_type(ProjectInitialDescriptionDocument)
    if not initial_description_docs:
        raise ValueError("ProjectInitialDescriptionDocument not found in input documents")
    initial_description_doc: ProjectInitialDescriptionDocument = initial_description_docs[0]  # type: ignore

    # Create final documentation
    final_docs = await create_final_documentation_task(
        codebase_doc=codebase_doc,
        initial_description_doc=initial_description_doc,
        flow_options=flow_options,
    )

    # Create output documents - explicitly cast to satisfy type checker
    output_docs = DocumentList(list(final_docs))  # type: ignore[arg-type]

    # Validate output documents
    CreateFinalDocumentationConfig.validate_output_documents(output_docs)

    logger.info(f"Successfully created {len(final_docs)} final documentation files")
    return output_docs
