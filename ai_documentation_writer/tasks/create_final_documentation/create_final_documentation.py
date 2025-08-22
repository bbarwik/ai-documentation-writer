"""Task for creating final documentation from codebase analysis."""

from ai_pipeline_core import pipeline_task
from ai_pipeline_core.llm import AIMessages, ModelOptions, generate
from ai_pipeline_core.logging import get_pipeline_logger
from ai_pipeline_core.prompt_manager import PromptManager

from ai_documentation_writer.documents.flow.codebase_documentation import (
    CodebaseDocumentationDocument,
    DirectoryAnalysis,
    FileAnalysis,
)
from ai_documentation_writer.documents.flow.final_documentation import (
    FinalDocumentationDocument,
    FinalDocumentationEnum,
)
from ai_documentation_writer.documents.flow.project_initial_description import (
    ProjectInitialDescriptionDocument,
)
from ai_documentation_writer.flow_options import ProjectFlowOptions

logger = get_pipeline_logger(__name__)
prompt_manager = PromptManager(__file__)


def extract_all_file_summaries(directory_analysis: DirectoryAnalysis) -> list[FileAnalysis]:
    """Recursively extract all file summaries from a DirectoryAnalysis.

    Args:
        directory_analysis: The root directory analysis

    Returns:
        List of all FileAnalysis objects from the entire tree
    """
    all_files = []

    # Add files from current directory
    all_files.extend(directory_analysis.file_summaries)

    # Recursively process subdirectories
    for subdirectory in directory_analysis.subdirectory_summaries:
        all_files.extend(extract_all_file_summaries(subdirectory))

    return all_files


def build_file_tree_markdown(directory_analysis: DirectoryAnalysis, indent: int = 0) -> str:
    """Build a markdown representation of the file tree structure.

    Args:
        directory_analysis: The root directory analysis
        indent: Current indentation level

    Returns:
        Markdown formatted file tree
    """
    lines = []
    prefix = "  " * indent

    # Add current directory
    if indent == 0:
        lines.append("```")
        lines.append(f"{directory_analysis.path}/")
    else:
        lines.append(f"{prefix}├── {directory_analysis.path.split('/')[-1]}/")

    # Add files in this directory
    for file_summary in directory_analysis.file_summaries:
        file_name = file_summary.file_path.split("/")[-1]
        lines.append(f"{prefix}│   ├── {file_name}")

    # Add subdirectories
    for subdir in directory_analysis.subdirectory_summaries:
        subdir_lines = build_file_tree_markdown(subdir, indent + 1)
        # Skip the first line (```) for subdirectories
        subdir_lines = subdir_lines.replace("```\n", "").replace("\n```", "")
        lines.append(subdir_lines)

    if indent == 0:
        lines.append("```")

    return "\n".join(lines)


@pipeline_task
async def create_final_documentation_task(
    codebase_doc: CodebaseDocumentationDocument,
    initial_description_doc: ProjectInitialDescriptionDocument,
    flow_options: ProjectFlowOptions,
) -> list[FinalDocumentationDocument]:
    """Create final documentation from codebase analysis.

    Args:
        codebase_doc: Document containing codebase analysis
        initial_description_doc: Document containing initial project description
        flow_options: Flow configuration

    Returns:
        List of FinalDocumentationDocument containing README, DOCUMENTATION, and DEVELOPER_GUIDE
    """
    logger.info("Starting final documentation generation")

    # Load the codebase analysis
    codebase_analysis = codebase_doc.as_pydantic_model(DirectoryAnalysis)

    # Extract all file summaries recursively
    all_file_summaries = extract_all_file_summaries(codebase_analysis)
    logger.info(f"Extracted {len(all_file_summaries)} file summaries from codebase analysis")

    # Build file tree representation
    file_tree = build_file_tree_markdown(codebase_analysis)

    # Load initial description
    initial_description = initial_description_doc.as_text()

    # Prepare file summaries text for context
    file_summaries_text = []
    for file_analysis in all_file_summaries:
        file_summaries_text.append(f"## {file_analysis.file_path}\n\n{file_analysis.summary}")
        if file_analysis.key_elements:
            file_summaries_text.append("\n**Key Elements:**")
            for element in file_analysis.key_elements:
                file_summaries_text.append(f"- {element}")
        if file_analysis.dependencies:
            file_summaries_text.append("\n**Dependencies:**")
            for dep in file_analysis.dependencies:
                file_summaries_text.append(f"- {dep}")
        file_summaries_text.append("")  # Empty line between files

    # Prepare directory structure information
    directory_structure = []

    def build_directory_info(dir_analysis: DirectoryAnalysis, level: int = 0):
        indent = "  " * level
        directory_structure.append(f"{indent}- **{dir_analysis.path}/**")
        directory_structure.append(f"{indent}  {dir_analysis.summary}")
        if dir_analysis.main_components:
            directory_structure.append(
                f"{indent}  Components: {', '.join(dir_analysis.main_components)}"
            )
        if dir_analysis.patterns:
            directory_structure.append(f"{indent}  Patterns: {', '.join(dir_analysis.patterns)}")
        directory_structure.append("")

        for subdir in dir_analysis.subdirectory_summaries:
            build_directory_info(subdir, level + 1)

    build_directory_info(codebase_analysis)

    # Create a shared context with ALL project information
    # This context will be cached and reused for all three documentation generations
    shared_context_prompt = prompt_manager.get(
        "shared_context.jinja2",
        initial_description=initial_description,
        file_tree=file_tree,
        root_summary=codebase_analysis.summary,
        file_summaries="\n".join(file_summaries_text),
        directory_structure="\n".join(directory_structure),
        main_components=codebase_analysis.main_components,
        patterns=codebase_analysis.patterns,
    )

    # Create the shared context that will be reused (and cached) for all AI calls
    shared_context = AIMessages([shared_context_prompt])

    # Generate README
    logger.info("Generating README.md")
    readme_instructions = prompt_manager.get("readme_instructions.jinja2")

    readme_response = await generate(
        model=flow_options.core_model,
        context=shared_context,  # Use shared context for caching
        messages=AIMessages([readme_instructions]),  # Only instructions, no data
        options=ModelOptions(reasoning_effort="high"),
    )
    readme_content = str(readme_response).strip()

    # Generate DOCUMENTATION
    logger.info("Generating DOCUMENTATION.md")
    documentation_instructions = prompt_manager.get("documentation_instructions.jinja2")

    documentation_response = await generate(
        model=flow_options.core_model,
        context=shared_context,  # Use shared context for caching
        messages=AIMessages([documentation_instructions]),  # Only instructions, no data
        options=ModelOptions(reasoning_effort="high"),
    )
    documentation_content = str(documentation_response).strip()

    # Generate DEVELOPER_GUIDE
    logger.info("Generating DEVELOPER_GUIDE.md")
    developer_guide_instructions = prompt_manager.get("developer_guide_instructions.jinja2")

    developer_guide_response = await generate(
        model=flow_options.core_model,
        context=shared_context,  # Use shared context for caching
        messages=AIMessages([developer_guide_instructions]),  # Only instructions, no data
        options=ModelOptions(reasoning_effort="high"),
    )
    developer_guide_content = str(developer_guide_response).strip()

    # Create three separate documents for each file
    readme_doc = FinalDocumentationDocument.create(
        name=FinalDocumentationEnum.README,
        description="Generated README documentation",
        content=readme_content.encode("utf-8"),
    )

    documentation_doc = FinalDocumentationDocument.create(
        name=FinalDocumentationEnum.DOCUMENTATION,
        description="Generated technical documentation",
        content=documentation_content.encode("utf-8"),
    )

    developer_guide_doc = FinalDocumentationDocument.create(
        name=FinalDocumentationEnum.DEVELOPER_GUIDE,
        description="Generated developer guide",
        content=developer_guide_content.encode("utf-8"),
    )

    logger.info("Successfully generated final documentation files")

    # Return all three documents
    return [readme_doc, documentation_doc, developer_guide_doc]
