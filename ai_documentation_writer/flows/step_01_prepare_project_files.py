"""Flow for preparing project files."""

import tempfile
from pathlib import Path

from ai_pipeline_core import DocumentList, FlowConfig, get_pipeline_logger, pipeline_flow

from ai_documentation_writer.documents.flow.project_files import ProjectFilesDocument
from ai_documentation_writer.documents.flow.user_input import (
    UserInputData,
    UserInputDocument,
    UserInputFiles,
)
from ai_documentation_writer.flow_options import ProjectFlowOptions
from ai_documentation_writer.tasks.prepare_project_files import (
    clone_repository_task,
    select_project_files_task,
)

logger = get_pipeline_logger(__name__)


class PrepareProjectFilesConfig(FlowConfig):
    """Configuration for prepare project files flow."""

    INPUT_DOCUMENT_TYPES = [UserInputDocument]
    OUTPUT_DOCUMENT_TYPE = ProjectFilesDocument


@pipeline_flow
async def prepare_project_files(
    project_name: str, documents: DocumentList, flow_options: ProjectFlowOptions
) -> DocumentList:
    """Prepare project files for documentation generation.

    Args:
        project_name: Name of the project
        documents: Input documents containing user input
        flow_options: Flow configuration

    Returns:
        DocumentList containing the selected project files
    """
    logger.info(f"Starting project file preparation for: {project_name}")

    # Get input documents
    input_docs = PrepareProjectFilesConfig.get_input_documents(documents)

    # Extract user input - check both UserInputDocument and flow_options
    # This maintains compatibility with both old and new patterns
    user_input_doc = input_docs.get_by_name(UserInputFiles.USER_INPUT.value)
    if user_input_doc:
        # Use document if available (maintains backward compatibility)
        user_input_data = user_input_doc.as_pydantic_model(UserInputData)
    else:
        # Fall back to flow_options (new pattern)
        user_input_data = UserInputData(
            target=flow_options.target,
            branch=flow_options.branch,
            tag=flow_options.tag,
            instructions=flow_options.instructions,
        )

    # Create temporary directory for git cloning
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Task 1: Clone repository if needed
        project_dir = await clone_repository_task(
            user_input=user_input_data,
            temp_dir=temp_path,
        )

        # Task 2: Select text files from the project
        project_files_doc = await select_project_files_task(
            project_dir=project_dir,
            user_instructions=user_input_data.instructions,
            flow_options=flow_options,
        )

    # Create output documents
    output_docs = DocumentList([project_files_doc])

    # Validate output documents
    PrepareProjectFilesConfig.validate_output_documents(output_docs)

    logger.info(f"Successfully prepared {project_files_doc.name}")
    return output_docs
