# AI Documentation Writer (Preview Release)

> ⚠️ **Preview Release**: This is an early preview version (v0.1.0). While functional, expect breaking changes in future releases.

Automatically generate comprehensive documentation for any Git repository or local codebase using AI-powered analysis and structured document generation.

## Features

- 🤖 **AI-Powered Analysis**: Multi-stage AI analysis using configurable models (Gemini 2.5 Pro/Flash by default)
- 📁 **Universal Support**: Works with Git repositories (HTTP/HTTPS/SSH) and local directories
- 🔄 **Modular Pipeline**: 3-stage resumable pipeline (Prepare Files → Generate Description → Document Codebase)
- 📊 **Full Observability**: Built-in Prefect orchestration with LMNR tracing support
- ⚙️ **Flexible Configuration**: FlowOptions system for model selection and batch processing control
- 📝 **Comprehensive Output**: Generates detailed file/directory summaries and project documentation
- 🚀 **Production Ready**: Async architecture, strong typing with Pydantic, and comprehensive error handling
- 🎯 **Smart File Filtering**: AI-powered file selection for relevant code documentation

## Quick Start

### Installation

```bash
pip install ai-documentation-writer
```

### Prerequisites

1. **LiteLLM Proxy** - Required for AI model abstraction:

```yaml
# litellm-config.yml
model_list:
  - model_name: gpt-5
    litellm_params:
      model: openai/gpt-4o
      api_key: your-api-key
  - model_name: gpt-5-mini
    litellm_params:
      model: openai/gpt-4o-mini
      api_key: your-api-key
  - model_name: gemini-2.5-pro
    litellm_params:
      model: gemini/gemini-2.0-pro-exp-0111
      api_key: your-api-key
```

Run the proxy:
```bash
docker run -d --name litellm-proxy -p 4000:4000 \
  -v $(pwd)/litellm-config.yml:/app/config.yaml \
  ghcr.io/berriai/litellm:main --config /app/config.yaml
```

2. **Environment Configuration**:

```bash
# .env file
OPENAI_BASE_URL=http://localhost:4000/v1
OPENAI_API_KEY=your-litellm-key
```

### Usage

```bash
# Git repository
doc-writer https://github.com/user/repo ./output

# Local directory
doc-writer /path/to/project ./output

# With custom instructions
doc-writer /path/to/project ./output --instructions "Focus on API documentation"

# Resume from specific stage
doc-writer /path/to/project ./output --start 2
```

## Pipeline Stages

### Stage 1: Prepare Project Files
- Clones Git repository or copies local directory
- Intelligently selects relevant text files for documentation
- Filters out binary files, dependencies, and build artifacts
- Creates structured file tree with size information

### Stage 2: Generate Initial Description
- Iteratively analyzes project files using AI
- Builds comprehensive understanding through multiple exploration rounds
- Extracts key architectural patterns and design decisions
- Produces detailed project overview with technical insights

### Stage 3: Document Codebase
- Processes files in batches for efficient AI analysis
- Generates detailed summaries for each file and directory
- Creates hierarchical documentation structure
- Produces comprehensive codebase documentation with full context

## Output Structure

```
output/
├── user_input_document/
│   └── user_input.json           # Initial configuration
├── project_files_document/
│   └── project_files.json         # Selected files with content
├── project_initial_description_document/
│   └── initial_description.md     # AI-generated project overview
└── codebase_documentation_document/
    └── codebase_documentation.json # Comprehensive file/directory summaries
```

Each document is a self-contained artifact that can be:
- Used as input for subsequent stages
- Exported for external processing
- Versioned and tracked in git

## Development

### Setup

```bash
git clone https://github.com/bbarwik/ai-documentation-writer.git
cd ai-documentation-writer

# Install with development dependencies
make install-dev  # or: pip install -e ".[dev]" && pre-commit install
```

### Testing

```bash
make test          # Run all tests
make test-cov      # With coverage
make lint          # Run linting
make format        # Auto-format code
make typecheck     # Type checking
```

### Architecture

The project implements a clean, layered architecture:

#### Core Components

- **Documents** (`documents/flow/`): Strongly-typed Pydantic models representing data at each stage
  - `UserInputDocument`: User configuration and instructions
  - `ProjectFilesDocument`: Selected project files with content
  - `ProjectInitialDescriptionDocument`: AI-generated project overview
  - `CodebaseDocumentationDocument`: Complete file/directory documentation

- **Tasks** (`tasks/`): Atomic processing units that contain business logic
  - Each task has its own PromptManager for template management
  - Tasks are pure async functions with full type hints
  - Examples: `clone_repository_task`, `generate_initial_description_task`

- **Flows** (`flows/`): Prefect-orchestrated pipelines
  - Compose tasks into larger workflows
  - Handle document validation and persistence
  - No direct PromptManager usage (separation of concerns)

- **FlowOptions**: Configuration system for runtime parameters
  - Model selection (core_model, small_model, supporting_models)
  - Batch processing limits (batch_max_chars, batch_max_files)
  - Feature flags (enable_file_filtering)

#### Design Principles

- **Async-First**: All I/O operations are async (no blocking calls)
- **Type Safety**: Complete type hints with Pydantic validation
- **Minimal Code**: Every line must justify its existence
- **No Defensive Programming**: Trust the types, fail fast
- **Clear Boundaries**: Strict separation between flows, tasks, and documents

## Configuration

### FlowOptions

Configure AI models and processing parameters:

```python
from ai_documentation_writer.flow_options import FlowOptions

options = FlowOptions(
    core_model="gemini-2.5-pro",         # Primary model for complex analysis
    small_model="gemini-2.5-flash",      # Fast model for simple tasks
    supporting_models=["gemini-2.5-flash"],  # Additional models for planning
    batch_max_chars=200_000,              # Max characters per batch (default: 200K)
    batch_max_files=50,                   # Max files per batch (default: 50)
    enable_file_filtering=True            # Enable AI-powered file selection
)
```

### CLI Options

```bash
# Override default models
doc-writer /path/to/project ./output \
  --core-model gpt-4o \
  --small-model gpt-4o-mini \
  --supporting-models claude-3-sonnet gemini-2.5-pro

# Adjust batch processing
doc-writer /path/to/project ./output \
  --batch-max-chars 100000 \
  --batch-max-files 25

# Resume from specific stage (1-3)
doc-writer /path/to/project ./output --start 2 --end 3
```

## Implementation Details

### Document System

All data flows through strongly-typed Document classes:

```python
# Flow documents persist between stages
class ProjectFilesDocument(FlowDocument):
    """Contains selected project files with content."""

# Documents are versioned and self-describing
doc = ProjectFilesDocument.create_as_json(
    name="project_files.json",
    description="Selected text files from the repository",
    data=ProjectFilesData(files={...})
)
```

### Prompt Engineering

The project implements defensive prompt engineering patterns:

- **Header Hierarchy**: Instructions use `#`, AI output uses `##`/`###`
- **File Separation**: Files provided as separate messages to prevent injection
- **Structured Output**: Pydantic models for predictable AI responses
- **Context Accumulation**: Conversation history maintained across iterations

### Batch Processing

Efficient handling of large codebases:

```python
# Files are processed in configurable batches
batches = create_file_batches(
    files=project_files,
    max_chars=flow_options.batch_max_chars,
    max_files=flow_options.batch_max_files
)

# Parallel processing with asyncio
results = await asyncio.gather(
    *[process_batch(batch) for batch in batches]
)
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Git not found | Install Git or use local directory path |
| Clone failed | Check network, verify URL, or download manually |
| Model errors | Ensure LiteLLM proxy is running with correct config |
| Out of memory | Reduce batch sizes with `--batch-max-chars` |
| Slow processing | Use faster model with `--small-model gemini-2.5-flash` |

## Advanced Usage

### Custom Instructions

Provide specific documentation requirements:

```bash
doc-writer /path/to/project ./output \
  --instructions "Focus on API endpoints and data models. Include examples for each function."
```

### Integration with CI/CD

```yaml
# GitHub Actions example
- name: Generate Documentation
  run: |
    pip install ai-documentation-writer
    doc-writer . ./docs --instructions "Update based on latest changes"

- name: Commit Documentation
  run: |
    git add docs/
    git commit -m "docs: auto-generated documentation"
    git push
```

### Programmatic Usage

```python
import asyncio
from pathlib import Path
from ai_documentation_writer.flows import prepare_project_files
from ai_documentation_writer.flow_options import FlowOptions
from ai_documentation_writer.documents.flow.user_input import UserInputDocument
from ai_pipeline_core.documents import DocumentList

async def generate_docs():
    # Create input document
    user_input = UserInputDocument.create_as_json(
        name="user_input.json",
        description="Configuration",
        data={"target": "/path/to/project"}
    )

    # Run flow
    result = await prepare_project_files(
        project_name="my-project",
        documents=DocumentList([user_input]),
        flow_options=FlowOptions()
    )

    return result

asyncio.run(generate_docs())
```

## License

MIT License - see LICENSE file for details.

## Credits

Built on [ai-pipeline-core](https://github.com/bbarwik/ai-pipeline-core) for robust async AI pipeline orchestration.

## Contributing

Contributions are welcome! Please ensure:
- All tests pass (`make test`)
- Code is formatted (`make format`)
- Type hints are complete (`make typecheck`)
- Coverage meets minimum requirements (`make test-cov`)
