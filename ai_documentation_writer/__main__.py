"""CLI entry point for AI Documentation Writer."""

import argparse
import asyncio
import sys
from dataclasses import fields
from pathlib import Path
from typing import Any

from ai_pipeline_core.documents import DocumentList, FlowDocument
from ai_pipeline_core.logging import get_pipeline_logger, setup_logging
from lmnr import Laminar
from prefect.testing.utilities import prefect_test_harness

from .documents.flow.user_input import UserInputData, UserInputDocument
from .flow_options import FlowOptions
from .flows import FLOW_CONFIGS, FLOWS

# Setup logging
setup_logging()
logger = get_pipeline_logger(__name__)


def is_git_url(url: str) -> bool:
    """Check if the URL is a git URL."""
    if url.startswith(("git@", "git://", "ssh://", "file://")):
        return True
    return any(
        host in url for host in ["github.com", "gitlab.com", "bitbucket.org"]
    ) or url.endswith(".git")


def load_documents_from_directory(
    base_dir: Path, document_types: list[type[FlowDocument]]
) -> DocumentList:
    """Load documents from directory structure."""
    documents = DocumentList()

    for doc_class in document_types:
        dir_name = doc_class.canonical_name()
        type_dir = base_dir / dir_name

        if not type_dir.exists():
            continue

        logger.info(f"Loading documents from {type_dir}")

        for file_path in type_dir.iterdir():
            if not file_path.is_file() or file_path.name.endswith(".description.md"):
                continue

            try:
                doc = doc_class(name=file_path.name, content=file_path.read_bytes())
                documents.append(doc)
                logger.info(f"  Loaded: {file_path.name}")
            except Exception as e:
                logger.error(f"  Failed to load {file_path.name}: {e}")

    return documents


def save_documents_to_directory(base_dir: Path, documents: DocumentList) -> None:
    """Save documents to directory structure."""
    for document in documents:
        document_dir = base_dir / document.canonical_name()
        document_dir.mkdir(parents=True, exist_ok=True)

        file_path = document_dir / document.name
        file_path.write_bytes(document.content)
        logger.info(f"Saved: {file_path}")


async def run_flows(
    base_dir: Path, start_index: int, end_index: int, flow_options: FlowOptions
) -> None:
    """Run flows in sequence."""
    project_name = base_dir.name

    for i in range(start_index, end_index + 1):
        flow = FLOWS[i]
        flow_config = FLOW_CONFIGS[i]
        flow_name = flow.__name__  # type: ignore[attr-defined]

        logger.info(f"--- Running Flow {i + 1}/{len(FLOWS)}: {flow_name} ---")

        try:
            # Load input documents
            documents = load_documents_from_directory(base_dir, flow_config.INPUT_DOCUMENT_TYPES)

            if not documents:
                logger.error(f"Missing input documents for flow {flow_name}. Aborting.")
                return

            # Run flow
            result = await flow(project_name, documents, flow_options)

            # Validate and save output
            flow_config.validate_output_documents(result)
            save_documents_to_directory(base_dir, result)

            # Also save input documents that may have been created
            save_documents_to_directory(base_dir, documents)

            logger.info(f"--- Completed Flow: {flow_name} ---")

        except Exception as e:
            logger.error(f"--- Flow {flow_name} Failed: {e} ---", exc_info=True)
            raise


def create_flow_options_from_args(args: argparse.Namespace) -> FlowOptions:
    """Create FlowOptions from CLI arguments."""
    flow_kwargs: dict[str, Any] = {}

    for field in fields(FlowOptions):
        if hasattr(args, field.name) and getattr(args, field.name) is not None:
            flow_kwargs[field.name] = getattr(args, field.name)

    return FlowOptions(**flow_kwargs)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI Documentation Writer - Automatically generate documentation for codebases"
    )

    # Required arguments
    parser.add_argument("target", help="Target source: Git repository URL or local directory path")
    parser.add_argument("output_dir", help="Directory to save documentation and intermediate files")

    # Optional arguments
    parser.add_argument("--branch", help="Branch name for git repositories")
    parser.add_argument("--tag", help="Tag name for git repositories")
    parser.add_argument("--instructions", help="High-level instructions for the AI")

    # Flow control
    parser.add_argument(
        "--start", type=int, default=1, help=f"Starting flow (1-{len(FLOWS)}, default: 1)"
    )
    parser.add_argument(
        "--end",
        type=int,
        default=len(FLOWS),
        help=f"Ending flow (1-{len(FLOWS)}, default: {len(FLOWS)})",
    )

    # FlowOptions parameters
    parser.add_argument("--core-model", dest="core_model", help="Override core model")
    parser.add_argument("--small-model", dest="small_model", help="Override small model")
    parser.add_argument(
        "--supporting-models",
        dest="supporting_models",
        nargs="+",
        help="Override supporting models",
    )
    parser.add_argument(
        "--batch-max-chars", dest="batch_max_chars", type=int, help="Maximum characters per batch"
    )
    parser.add_argument(
        "--batch-max-files", dest="batch_max_files", type=int, help="Maximum files per batch"
    )

    args = parser.parse_args()

    # Validate flow indices (convert to 0-based)
    start_index = args.start - 1
    end_index = args.end - 1

    if not (0 <= start_index < len(FLOWS)):
        logger.error(f"Start flow must be between 1 and {len(FLOWS)}")
        sys.exit(1)

    if not (0 <= end_index < len(FLOWS)):
        logger.error(f"End flow must be between 1 and {len(FLOWS)}")
        sys.exit(1)

    if start_index > end_index:
        logger.error("Start flow must come before or equal to end flow")
        sys.exit(1)

    # Validate target
    target_path = Path(args.target)
    if target_path.exists() and target_path.is_dir():
        logger.info(f"Using local directory: {target_path.absolute()}")
        target = str(target_path.absolute())
    elif is_git_url(args.target):
        logger.info(f"Using git repository: {args.target}")
        target = args.target
    else:
        if not args.target.startswith(("http://", "https://", "git://", "git@", "ssh://")):
            logger.error(f"Local directory does not exist: {args.target}")
        else:
            logger.error(f"Invalid git URL: {args.target}")
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create initial user input document
    user_input_data = UserInputData(
        target=target,
        branch=args.branch,
        tag=args.tag,
        instructions=args.instructions,
    )

    initial_doc = UserInputDocument.create_as_json(
        name="user_input.json",
        description="User input configuration",
        data=user_input_data,
    )

    save_documents_to_directory(output_dir, DocumentList([initial_doc]))

    logger.info(f"Starting documentation generation for {target}")
    logger.info(f"Output will be saved to: {output_dir}")
    logger.info(f"Running flows {args.start} to {args.end}")

    # Create flow options
    flow_options = create_flow_options_from_args(args)

    # Run flows
    with prefect_test_harness():
        try:
            with Laminar.start_as_current_span("ai_documentation_writer", input=vars(args)):
                asyncio.run(run_flows(output_dir, start_index, end_index, flow_options))
                logger.info("✅ Pipeline completed successfully!")
                logger.info(f"Documentation saved to: {output_dir}")
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
