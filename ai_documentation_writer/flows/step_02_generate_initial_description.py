"""Flow for generating initial project description."""

from ai_pipeline_core.documents import DocumentList
from ai_pipeline_core.flow import FlowConfig
from ai_pipeline_core.logging import get_pipeline_logger
from ai_pipeline_core.tracing import trace
from prefect import flow

from ai_documentation_writer.documents.flow.project_files import ProjectFilesDocument
from ai_documentation_writer.documents.flow.project_initial_description import (
    ProjectInitialDescriptionDocument,
)
from ai_documentation_writer.flow_options import FlowOptions
from ai_documentation_writer.tasks.generate_initial_description import (
    generate_initial_description_task,
)

logger = get_pipeline_logger(__name__)


class GenerateInitialDescriptionConfig(FlowConfig):
    """Configuration for generate initial description flow."""

    INPUT_DOCUMENT_TYPES = [ProjectFilesDocument]
    OUTPUT_DOCUMENT_TYPE = ProjectInitialDescriptionDocument


@flow(flow_run_name="generate_initial_description-{project_name}")
@trace
async def generate_initial_description(
    project_name: str, documents: DocumentList, flow_options: FlowOptions = FlowOptions()
) -> DocumentList:
    """Generate initial project description using AI analysis.

    Args:
        project_name: Name of the project
        documents: Input documents containing project files
        flow_options: Flow configuration

    Returns:
        DocumentList containing the initial project description
    """
    logger.info(f"Starting initial description generation for: {project_name}")

    # Get input documents
    input_docs = GenerateInitialDescriptionConfig.get_input_documents(documents)

    # Get the project files document
    project_files_docs = input_docs.filter_by_type(ProjectFilesDocument)
    if not project_files_docs:
        raise ValueError("ProjectFilesDocument not found in input documents")
    project_files_doc: ProjectFilesDocument = project_files_docs[0]  # type: ignore

    # Generate initial description
    initial_description_doc = await generate_initial_description_task(
        project_files_doc=project_files_doc,
        flow_options=flow_options,
    )

    # Create output documents
    output_docs = DocumentList([initial_description_doc])

    # Validate output documents
    GenerateInitialDescriptionConfig.validate_output_documents(output_docs)

    logger.info(f"Successfully generated initial description: {initial_description_doc.name}")
    return output_docs
