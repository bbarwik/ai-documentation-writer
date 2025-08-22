"""Task for generating initial project description using AI."""

from ai_pipeline_core import pipeline_task
from ai_pipeline_core.llm import (
    AIMessages,
    ModelOptions,
    generate,
    generate_structured,
)
from ai_pipeline_core.logging import get_pipeline_logger
from ai_pipeline_core.prompt_manager import PromptManager

from ai_documentation_writer.documents.flow.project_files import (
    ProjectFilesData,
    ProjectFilesDocument,
)
from ai_documentation_writer.documents.flow.project_initial_description import (
    ProjectInitialDescriptionDocument,
    ProjectInitialDescriptionEnum,
)
from ai_documentation_writer.flow_options import ProjectFlowOptions

from .models import SelectedFiles

logger = get_pipeline_logger(__name__)
prompt_manager = PromptManager(__file__)

MAX_ITERATIONS = 5


@pipeline_task
async def generate_initial_description_task(
    project_files_doc: ProjectFilesDocument,
    flow_options: ProjectFlowOptions,
) -> ProjectInitialDescriptionDocument:
    """Generate initial project description using iterative AI analysis.

    Args:
        project_files_doc: Document containing project files
        flow_options: Flow configuration options

    Returns:
        ProjectInitialDescriptionDocument with comprehensive project description
    """
    logger.info("Starting initial description generation")

    # Extract project files data
    project_data = project_files_doc.as_pydantic_model(ProjectFilesData)

    # Get file tree from property
    file_tree = project_data.file_tree

    # Initialize AI messages with project structure
    initial_prompt = prompt_manager.get(
        "initial_analysis.jinja2",
        file_tree=file_tree,
        total_files=project_data.total_files,
        total_size=project_data.total_size,
        batch_max_files=flow_options.batch_max_files,
        batch_max_chars=flow_options.batch_max_chars,
    )

    ai_messages = AIMessages([initial_prompt])

    # Iterative file exploration
    for iteration in range(MAX_ITERATIONS):
        logger.info(f"Starting iteration {iteration + 1}/{MAX_ITERATIONS}")

        # Ask AI to select files
        select_prompt = prompt_manager.get(
            "select_files.jinja2",
            batch_max_files=flow_options.batch_max_files,
            batch_max_chars=flow_options.batch_max_chars,
        )
        ai_messages.append(select_prompt)

        # Get structured file selection
        selection_response = await generate_structured(
            model=flow_options.small_model,  # type: ignore
            response_format=SelectedFiles,
            context=ai_messages,
            messages=AIMessages(["Select the next batch of files to analyze."]),
            options=ModelOptions(
                reasoning_effort="high",
            ),
        )

        selected_files = selection_response.parsed
        ai_messages.append(selection_response)

        # Check if AI wants to stop
        if not selected_files.files:
            logger.info(
                f"AI decided to stop at iteration {iteration + 1}: {selected_files.reasoning}"
            )
            break

        logger.info(f"Selected {len(selected_files.files)} files to analyze")

        # Gather selected file contents
        files_to_read: dict[str, str] = {}
        total_chars = 0

        for file_info in selected_files.files:
            if file_info.path in project_data.files:
                content = project_data.files[file_info.path]
                file_chars = len(content)

                # Check size limits
                if total_chars + file_chars > flow_options.batch_max_chars:
                    logger.warning(f"Reached character limit, skipping {file_info.path}")
                    break

                files_to_read[file_info.path] = content
                total_chars += file_chars

                if len(files_to_read) >= flow_options.batch_max_files:
                    logger.warning(f"Reached file limit of {flow_options.batch_max_files}")
                    break

        if not files_to_read:
            logger.warning("No valid files selected, moving to next iteration")
            continue

        # Generate analysis prompt with file contents
        analyze_prompt = prompt_manager.get(
            "analyze_files.jinja2",
            files=list(files_to_read.keys()),
        )

        # Files list
        files_to_read_list: list[str] = []
        for file_path, content in files_to_read.items():
            files_to_read_list.append(f"# FILE: {file_path}\n---\n{content}")

        # Analyze the files
        analysis_response = await generate(
            model=flow_options.small_model,  # type: ignore
            context=ai_messages,
            messages=AIMessages([*files_to_read_list, analyze_prompt]),
        )

        ai_messages.append(analysis_response)
        logger.info(f"Completed analysis for iteration {iteration + 1}")

    # Generate final comprehensive description
    logger.info("Generating final comprehensive description")

    final_prompt = prompt_manager.get("generate_final_description.jinja2")

    final_response = await generate(
        model=flow_options.core_model,  # type: ignore
        context=ai_messages,
        messages=final_prompt,
        options=ModelOptions(
            reasoning_effort="high",
        ),
    )

    # Create and return the document
    return ProjectInitialDescriptionDocument(
        name=ProjectInitialDescriptionEnum.INITIAL_DESCRIPTION.value,
        content=final_response.content.encode("utf-8"),
        description="AI-generated comprehensive initial project description",
    )
