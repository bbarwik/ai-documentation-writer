"""CLI entry point for AI Documentation Writer."""

from typing import cast

from ai_pipeline_core import DocumentList, FlowOptions
from ai_pipeline_core.simple_runner import run_cli

from .documents.flow.user_input import UserInputData, UserInputDocument
from .flow_options import ProjectFlowOptions
from .flows import FLOW_CONFIGS, FLOWS


def initialize_project(options: FlowOptions) -> tuple[str, DocumentList]:
    """Initialize project with user input document.

    Creates the UserInputDocument that tracks the user's configuration.
    This maintains compatibility with the original data flow.
    """
    # Cast to ProjectFlowOptions
    project_options = cast(ProjectFlowOptions, options)

    # Create user input document from flow options
    user_input_data = UserInputData(
        target=project_options.target,
        branch=project_options.branch,
        tag=project_options.tag,
        instructions=project_options.instructions,
    )

    user_input_doc = UserInputDocument.create_as_json(
        name="user_input.json",
        description="User input configuration",
        data=user_input_data,
    )

    # Return project name (derived from target) and initial documents
    # The simple_runner will use the working directory name as project name
    return "", DocumentList([user_input_doc])


def main():
    """Main CLI entry point."""
    run_cli(
        flows=FLOWS,
        flow_configs=FLOW_CONFIGS,
        options_cls=ProjectFlowOptions,
        initializer=initialize_project,
        trace_name="ai-documentation-writer",
    )


if __name__ == "__main__":
    main()
