# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Documentation Writer is an automated tool that generates comprehensive documentation for any Git repository or local codebase. It uses AI to analyze code structure, understand functionality, and produce professional documentation including README, DOCUMENTATION, and DEVELOPER_GUIDE files.

### Key Components
- **ai-pipeline-core**: The foundational framework providing async AI pipeline orchestration
- **Prefect**: Workflow orchestration for managing the documentation generation pipeline
- **LiteLLM**: Model abstraction layer for AI interactions
- **FlowOptions**: Configuration system for model selection and flow parameters

### Current Project Structure
```
ai_documentation_writer/
├── documents/          # Pydantic document models
│   └── flow/          # Persistent flow documents
│       ├── user_input.py                    # User input configuration
│       ├── project_files.py                 # Selected project files with content
│       ├── project_initial_description.py   # AI-generated project overview
│       └── codebase_documentation.py        # File/directory summaries
├── tasks/             # Processing tasks (contain PromptManager)
│   ├── prepare_project_files/
│   │   ├── clone_repository.py     # Git clone or local copy
│   │   └── select_files.py         # Intelligent file selection
│   ├── filter_project_files/       # AI-powered file filtering
│   │   ├── filter_project_files.py
│   │   └── models.py               # Pydantic models for structured output
│   ├── generate_initial_description/
│   │   ├── generate_initial_description.py  # Iterative AI analysis
│   │   ├── models.py                        # SelectedFiles, FileInfo models
│   │   └── prompts/                         # Jinja2 templates
│   └── document_codebase/
│       ├── document_codebase.py             # Main documentation task
│       ├── document_codebase_directory.py   # Directory-level processing
│       └── models.py                        # FileSummary, DirectorySummary
├── flows/             # Prefect flow orchestration (no PromptManager)
│   ├── step_01_prepare_project_files.py     # Stage 1: File preparation
│   ├── step_02_generate_initial_description.py  # Stage 2: Initial analysis
│   └── step_03_document_codebase.py         # Stage 3: Full documentation
├── flow_options.py    # Configuration for model selection and batch processing
└── __main__.py        # CLI entry point with argument parsing
```

### Important Design Patterns

1. **PromptManager**: Used ONLY in tasks, never in flows
   - Each task has its own PromptManager instance
   - Templates stored as .jinja2 files in task's prompts/ directory
   - Example: `prompt_manager = PromptManager(__file__)`

2. **FlowOptions**: Passed to all flows for runtime configuration
   - Model selection: core_model, small_model, supporting_models
   - Batch limits: batch_max_chars (200K), batch_max_files (50)
   - Feature flags: enable_file_filtering

3. **Document System**: All data flows through typed Document classes
   - FlowDocument base class for persistent documents
   - Each document has canonical_name() for directory structure
   - Documents support JSON, text, and Pydantic model serialization

4. **Async Everything**: All I/O operations are async
   - Tasks decorated with @task and @trace
   - Flows decorated with @flow and @trace
   - Use asyncio.gather() for parallel processing

5. **Iterative AI Analysis**: Multi-round exploration pattern
   - Used in generate_initial_description_task
   - AI selects files to analyze in each iteration
   - Conversation history accumulated across rounds
   - Maximum 5 iterations with early stopping

6. **Batch Processing**: Efficient handling of large codebases
   - Files grouped into batches by size and count
   - Parallel processing of batches with asyncio
   - Results aggregated and structured hierarchically

### Key Dependencies

1. **ai-pipeline-core**: Foundation framework providing:
   - Document system with FlowDocument base class
   - LLM abstraction with generate() and generate_structured()
   - PromptManager for template management
   - Logging and tracing infrastructure
   - AIMessages for conversation management

2. **Prefect**: Workflow orchestration
   - Flow and task decorators
   - Retry logic and error handling
   - Observability and monitoring

3. **LiteLLM**: Model abstraction layer
   - Unified interface for multiple AI providers
   - Model routing and fallback
   - Cost tracking and rate limiting

4. **LMNR (Laminar)**: Optional tracing and observability
   - Span tracking for AI operations
   - Performance monitoring
   - Debug visualization

### Dependencies Documentation
- `dependencies_docs/ai-pipeline-core.md` - Guide for using ai-pipeline-core framework
- `dependencies_docs/ai-pipeline-core-files.txt` - Complete source code of ai-pipeline-core

### Note
> The `dependencies_docs/` directory contains guides for AI assistants on interacting with external dependencies (Prefect, LMNR, etc.), NOT user documentation.

## Absolute Non-Negotiable Rules

1. **Minimalism Above All**
   - Less code is better code - every line must justify its existence
   - Delete code rather than comment it out
   - No defensive programming for unlikely scenarios
   - If you can't explain why a line exists, delete it
   - Do not create any new markdown file unless told to do it

2. **Python 3.12+ Only**
   - Use modern Python features exclusively
   - No `from typing import List, Dict` - use built-in types
   - No compatibility shims or version checks
   - No legacy patterns

3. **Everything Async**
   - ALL I/O operations must be async - no blocking calls allowed
   - No `requests` library - use `httpx` with async
   - No `time.sleep()` - use `asyncio.sleep()`
   - No blocking database calls

4. **Strong Typing with Pydantic**
   - Every function must have complete type hints
   - All data structures must be Pydantic models
   - Use `frozen=True` for immutable models
   - No raw dicts for configuration or data transfer

5. **Self-Documenting Code**
   - Code for experienced developers only
   - No comments explaining *what* - code must be clear
   - No verbose logging or excessive documentation
   - Function and variable names must be descriptive

6. **Consistency is Mandatory**
   - No tricks or hacks (no imports inside functions/classes)
   - Follow the established patterns exactly
   - Use the pipeline logger, never import logging directly
   - All exports must be explicit in `__all__`

## Essential Commands

```bash
# Development setup
make install-dev         # Install with dev dependencies and pre-commit hooks

# Testing
make test                # Run all tests
make test-cov           # Run tests with coverage report
pytest tests/test_documents.py::TestDocument::test_creation  # Run single test

# Code quality
make lint               # Run ruff linting
make format            # Auto-format and fix code
make typecheck         # Run basedpyright type checking
make pre-commit        # Run all pre-commit hooks

# Cleanup
make clean             # Remove all build artifacts and caches

# Running the application
python -m ai_documentation_writer <target> <output_dir> [options]
doc-writer <target> <output_dir> [options]  # After pip install
```

## Import Convention

```python
# Within same package - relative imports
from .document import Document
from .utils import helper

# Cross-package - absolute imports
from ai_pipeline_core.documents import Document
from ai_pipeline_core.llm import generate

# NEVER use parent imports (..)
```

## Critical Patterns

### Always Async
```python
# Every I/O operation must be async
async def process_document(doc: Document) -> ProcessedDocument:
    result = await generate(context, messages, options)
    return ProcessedDocument(...)
```

### Always Typed
```python
# Complete type annotations required
def calculate(x: int, y: int) -> int:
    return x + y

async def fetch_data(url: str) -> dict[str, Any]:
    ...
```

### Always Pydantic
```python
# All data structures must be Pydantic models
class Config(BaseModel):
    model: ModelName  # Use enums for constrained values
    temperature: float = Field(ge=0, le=2)

    model_config = ConfigDict(frozen=True)  # Immutable by default
```

### Never Direct Logging
```python
# Always use pipeline logger
from ai_pipeline_core.logging import get_pipeline_logger
logger = get_pipeline_logger(__name__)
```

## Forbidden Patterns (NEVER Do These)

1. **No print statements** - Use pipeline logger
2. **No global mutable state** - Use dependency injection
3. **No `sys.exit()`** - Raise exceptions
4. **No hardcoded paths** - Use settings/config
5. **No string concatenation for paths** - Use `pathlib.Path`
6. **No manual JSON parsing** - Use Pydantic
7. **No `time.sleep()`** - Use `asyncio.sleep()`
8. **No `requests` library** - Use `httpx` with async
9. **No raw SQL** - Use async ORM or query builders
10. **No magic numbers** - Use named constants
11. **No nested functions** (except decorators)
12. **No dynamic imports** - All imports at module level
13. **No monkeypatching**
14. **No metaclasses** (except Pydantic)
15. **No multiple inheritance** (except mixins)
16. **No TODO/FIXME comments** - Fix it or delete it
17. **No commented code** - Delete it
18. **No defensive programming** - Trust the types

## Testing Approach

- All tests must be async
- Use `@trace(test=True)` for test tracing
- Mock external services
- Test with proper Document types, not raw data
- Coverage target: >80%

## When Making Changes

1. **Before writing any code, ask**: "Can this be done with less code?"
2. **Before adding a line, ask**: "Can I justify why this exists?"
3. Run `make lint` and `make typecheck` before committing
4. Let pre-commit hooks auto-fix formatting
5. If you can't explain it to another developer in one sentence, rewrite it
6. If the function is longer than 20 lines, it's probably doing too much
7. **Final check**: Could you delete this code? If maybe, then yes - delete it

## LLM Interaction Patterns - Security & Quality Guidelines

### Core Principle: Defensive Prompt Engineering

When constructing prompts for LLM interactions, apply defensive engineering practices that prevent prompt injection, ensure output quality, and maintain structural integrity. These patterns are derived from the `generate_initial_description` task implementation and represent battle-tested approaches.

### File Content Provision Strategy

#### **DO: Separate File Content from Instructions**

```python
# CORRECT: Files as separate messages, instructions reference them
files_list = []
for path, content in files.items():
    files_list.append(f"# FILE: {path}\n\n---\n{content}")

# Files injected first, then instructions
messages = AIMessages([*files_list, analysis_prompt])
```

**Motivation**: This separation creates a security boundary preventing malicious content within files from corrupting instruction execution. File content cannot override or modify your prompts.

#### **DON'T: Embed File Content Within Instructions**

```python
# WRONG: Vulnerable to prompt injection
prompt = f"""
Analyze these files:
{file_content}
Now provide your analysis...
"""
```

**Risk**: Malicious file content could contain "Ignore previous instructions" or markdown that restructures your prompt hierarchy.

### Markdown Hierarchy Control - Critical Security Pattern

#### **CRITICAL: Header Hierarchy for Prompt Injection Prevention**

**The Problem**: Template variables like `{{ initial_description }}` or `{{ file_tree }}` often contain markdown with `##` and `###` headers. If your prompt instructions also use `##` and `###`, the injected content can corrupt your prompt structure and potentially override instructions.

**The Solution**: Use inverse header hierarchy:
- **Prompt instructions**: Use top-level `#` headers for YOUR instructions
- **AI responses**: Restrict to `##` and below
- **Template variables**: Already contain `##` and `###` headers

#### **DO: Use Top-Level Headers (#) for Prompt Instructions**

```python
# CORRECT: Instructions use #, template variables use ##/###
prompt = """
# Analysis Task

You are analyzing the following project:

{{ initial_description }}  <!-- This contains ## and ### headers -->

# Requirements

Analyze the codebase and provide detailed documentation.

# Output Constraints

Use markdown formatting limited to:
- Headers starting from ## (no top-level #)
- Lists and sublists
- Code blocks (no ASCII diagrams)
"""
```

**Why This Works**:
1. Your instructions with `#` headers maintain highest priority
2. Template variables with `##/###` remain subordinate
3. AI output restricted to `##` and below cannot override instructions
4. Clear hierarchical boundaries prevent prompt injection

#### **DON'T: Use Same Header Level as Template Variables**

```python
# WRONG: Instructions use ## like template variables
prompt = """
## Analysis Task  <!-- DANGEROUS: Same level as injected content -->

{{ initial_description }}  <!-- Contains ## headers that can interfere -->

## Requirements  <!-- Can be overridden by ## in initial_description -->
"""
```

**Risk**: When `initial_description` contains `## Architecture` or `## Overview`, it becomes indistinguishable from your instruction headers, potentially:
- Confusing the AI about what are instructions vs. context
- Allowing injected content to override subsequent instructions
- Breaking the logical structure of your prompt

#### **Example: Secure Prompt Template Structure**

```jinja2
# Project Analysis Task

You will analyze a software project with the following structure:

# Current Project State

{{ file_tree }}  <!-- Safe: Contains formatted tree, no headers -->

# Project Description

{{ initial_description }}  <!-- Safe: ## and ### headers remain subordinate -->

# Your Instructions

1. Analyze the architecture
2. Identify design patterns
3. Document key components

# Output Requirements

Your response must:
- Start with ## for your main sections
- Use ### for subsections
- Never use # (top-level headers)

# Quality Standards

Write for senior engineers only.
Token cost is not a concern.
```

**Security Boundaries Created**:
- Level 1 (#): Your instructions only
- Level 2 (##): Template variables and AI output
- Level 3+ (###): Subsections in both

### Output Quality Instructions

#### **DO: Calibrate for Technical Audience**

```python
prompt_manager.get("analysis.jinja2",
    audience_instructions="""
    Write for highly experienced developers (10+ years).
    No basic explanations or obvious observations.
    Focus on architectural decisions and non-trivial patterns.
    Assume deep familiarity with software engineering concepts.
    """)
```

**Motivation**: Maximizes information density by eliminating pedagogical overhead. Forces substantive technical analysis rather than tutorial-style explanations.

#### **DON'T: Use Generic Audience Instructions**

```python
# WRONG: Produces verbose, low-density output
prompt = "Explain this code clearly"
```

### Word Count Specifications

#### **DO: Specify Explicit Word Ranges**

```python
prompt = """
Provide a detailed analysis (minimum 1000 words, maximum 10000 words).
Focus on depth over brevity - token cost is not a concern.
"""
```

**Motivation**: Minimum word count prevents superficial summaries. Maximum allows comprehensive analysis. Explicit "cost is not a concern" removes implicit brevity optimization.

#### **DON'T: Leave Output Length Ambiguous**

```python
# WRONG: Often results in brief, surface-level responses
prompt = "Analyze these files"
```

### Context Permanence Warnings

#### **DO: Create Urgency for Comprehensive Analysis**

```python
prompt = """
The file contents won't be available again after this message.
Extract ALL relevant information in this single analysis.
"""
```

**Motivation**: Psychological framing that triggers more thorough processing. Prevents assumption of information permanence.

### Structured Output Requirements

#### **DO: Use Pydantic Models for Predictable Outputs**

```python
class FileSelection(BaseModel):
    reasoning: str = Field(description="Why these files were selected")
    files: list[FileInfo] = Field(description="Files to analyze")

response = await generate_structured(
    model=model,
    response_format=FileSelection,
    messages=messages
)
```

**Motivation**: Type-safe, predictable outputs that can be programmatically processed. Eliminates parsing errors and ensures consistent structure.

### Conversation History Management

#### **DO: Accumulate Context for Complex Analysis**

```python
ai_messages = AIMessages([initial_context])
for iteration in range(MAX_ITERATIONS):
    # Add new analysis to conversation history
    response = await generate(context=ai_messages, messages=new_prompt)
    ai_messages.append(response)
```

**Motivation**: Maintains analytical continuity across iterations. No insights are lost between steps.

### Security-First Prompt Construction

#### **DO: Explicitly Prohibit Unwanted Behaviors**

```python
prompt = """
Do NOT include:
- Personal opinions or speculation
- External links or references
- Graphical representations or ASCII art
- Meta-commentary about the task
Start your response directly with the analysis.
"""
```

**Motivation**: Prevents token waste on unwanted content types and maintains focus on substantive analysis.

### Implementation Checklist

When creating LLM interaction tasks, verify:

1. ✅ **Prompt instructions use # headers, template variables use ##/###**
2. ✅ Files provided as separate messages, not embedded in prompts
3. ✅ AI output restricted to ## headers and below (no top-level #)
4. ✅ Template variables isolated from instruction headers
5. ✅ Explicit word count ranges specified
6. ✅ Audience sophistication level calibrated
7. ✅ Output format constraints clearly defined
8. ✅ Pydantic models used for structured outputs
9. ✅ "No cost concern" explicitly stated for comprehensive analysis
10. ✅ Unwanted behaviors explicitly prohibited
11. ✅ File boundaries marked with clear delimiters
12. ✅ Conversation history properly accumulated for multi-step tasks

### Anti-Patterns to Avoid

1. ❌ **Using ## or ### for prompt instructions (same level as template variables)**
2. ❌ Concatenating file content directly into prompt strings
3. ❌ Allowing AI to use top-level # headers (reserved for instructions)
4. ❌ Mixing instruction headers with content headers at same level
5. ❌ Allowing unrestricted markdown formatting
6. ❌ Omitting explicit word count requirements
7. ❌ Using generic "explain this" instructions
8. ❌ Trusting AI to maintain context without explicit history
9. ❌ Mixing instructions with file content in same message
10. ❌ Requesting ASCII diagrams or graphical representations
11. ❌ Leaving output structure ambiguous
12. ❌ Assuming brevity without explicit instruction

### Example: Secure Multi-File Analysis Pattern

```python
# Step 1: Initialize context with proper hierarchy
context_prompt = """
# Project Context

The following analysis includes:

{{ file_tree }}  # Template variable with no headers

{{ initial_description }}  # Template variable with ## and ### headers
"""

# Step 2: Separate file injection
file_messages = [f"# FILE: {p}\n\n---\n{c}" for p, c in files.items()]

# Step 3: Analysis prompt with # headers for instructions
analysis_prompt = """
# Analysis Task

Analyze the provided files (listed above).

# Requirements

- Minimum 2000 words of technical analysis
- Focus on architecture and design patterns
- Write for senior engineers only

# Output Constraints

Your response must:
- Use ## for main sections (no top-level #)
- Use ### for subsections
- No ASCII art or diagrams
- Start directly with the analysis
"""

# Step 4: Structured response collection
messages = AIMessages([*file_messages, analysis_prompt])
response = await generate(context=context, messages=messages)
```

**Key Security Features**:
1. Instructions use `#` headers (highest priority)
2. Template variables contain `##/###` (subordinate)
3. AI output restricted to `##` and below
4. Files separated from instructions
5. Clear hierarchical boundaries prevent injection

## Final Rule

**The best code is no code. The second best is minimal, clear, typed, async code that does exactly what's needed and nothing more.**

If you're unsure whether to add code, don't add it.

## Project-Specific Patterns

### Task Implementation Template

```python
# tasks/my_task/my_task.py
from ai_pipeline_core.logging import get_pipeline_logger
from ai_pipeline_core.prompt_manager import PromptManager
from ai_pipeline_core.tracing import trace
from prefect import task

logger = get_pipeline_logger(__name__)
prompt_manager = PromptManager(__file__)

@task
@trace
async def my_task(
    input_doc: SomeDocument,
    flow_options: FlowOptions,
) -> OutputDocument:
    """Task description."""
    logger.info("Starting task")

    # Extract data
    data = input_doc.as_pydantic_model(SomeData)

    # Get prompt template
    prompt = prompt_manager.get(
        "template.jinja2",
        variable=data.field
    )

    # AI interaction
    response = await generate(
        model=flow_options.core_model,
        messages=AIMessages([prompt]),
        options=ModelOptions(reasoning_effort="high")
    )

    # Return document
    return OutputDocument.create_as_json(
        name="output.json",
        description="Output description",
        data=result
    )
```

### Flow Implementation Template

```python
# flows/step_XX_flow_name.py
from ai_pipeline_core.documents import DocumentList
from ai_pipeline_core.flow import FlowConfig
from ai_pipeline_core.tracing import trace
from prefect import flow

class MyFlowConfig(FlowConfig):
    INPUT_DOCUMENT_TYPES = [InputDocument1, InputDocument2]
    OUTPUT_DOCUMENT_TYPE = OutputDocument

@flow(name="my_flow")
@trace
async def my_flow(
    project_name: str,
    documents: DocumentList,
    flow_options: FlowOptions = FlowOptions()
) -> DocumentList:
    """Flow description."""
    # Get input documents
    input_docs = MyFlowConfig.get_input_documents(documents)

    # Run tasks
    result = await my_task(input_docs[0], flow_options)

    # Create output
    output_docs = DocumentList([result])

    # Validate
    MyFlowConfig.validate_output_documents(output_docs)

    return output_docs
```
