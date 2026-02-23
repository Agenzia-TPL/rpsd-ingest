# AI Development Assistant Context

This file provides context for AI development assistants (Claude Code, GitHub Copilot, etc.) working on this project.

## Project Overview
See `ai-project.md` for project description and details.

## Technology Stack
- **Language:** Python 3.13+
- **Package Manager:** uv
- **Project Structure:** uv or uv workspace with packages in `packages/` folder
- **CLI Framework:** Typer (modern, type-hint based)
- **Config management:** pydantic-settings
- **Testing:** pytest
- **Linting/Formatting:** ruff

## Development Environment
- **Containerization:** Docker + devcontainers
- **Package Management:** uv (not pip/poetry/conda)
- **Docker is NOT installed:** inside the devcontainer, do NOT try to use it!

## Coding Standards
- Follow PEP 8 for Python code style
- Use type hints where applicable
- Use ruff for formatting and linting
- Write docstrings for all public functions and classes
- Always prefer absolute import above relative ones
- Do not use workarounds such as: `# type: ignore[arg-type]`
- Do not use workarounds such as: `cast()`

## Common Development Commands (for AI assistants)
- `uv sync` - Install/update all dependencies
- `uv add <package>` - Add a dependency
- `uv run app` - Run the application (batch mode)
- `uv run app process <file>` - Run with specific input file (single-file mode)
- `uv run app --help` - Show CLI help
- `uv run pytest` - Run tests
- `uv run ruff format` - Format code
- `uv run ruff check --fix` - Auto-fix linting issues

## Project Structure (uv)
```
project-root/
├── examples/           # Example files
├── pyproject.toml      # Project configuration
├── uv.lock             # Lock file
├── src/                # Project source files
├── tests/              # Test files
└── README.md           # Project documentation
```

## Project Structure (uv workspace)
```
project-root/
├── pyproject.toml      # Workspace configuration
├── uv.lock             # Lock file
├── src/                # Workspace root source files
├── packages/           # Workspace members
│   ├── package-a/      # Individual package
│   └── package-b/      # Another package
├── tests/              # Test files
└── README.md           # Project documentation
```

## Guidelines for AI Assistants

### Optional Documentation Files

The project may include these optional documentation files. When present, AI assistants **MUST keep them updated** with relevant changes:

#### `ai-project.md` - Project Planning Document (Optional)
If this file exists:
- Treat it as a **project planning and decision document**, not implementation documentation
- It documents **problems, proposed solutions, and expected outcomes** BEFORE implementation
- When updating it after implementing features, use **planning language**:
  - "**Problem**" (present tense, not "Original Problem")
  - "**Proposed Solution**" (not "Implemented Solution")
  - "we'll do X" or "create Y" (future/intent, not past tense)
  - "**Expected outcome**" (not "Result")
- Keep entries **succinct** - this is a decision log, not detailed documentation
- This file captures **what** and **why**, not **how** (implementation details go in code/docs)
- Think of it as: "This is what I'm asking the AI to build" rather than "This is what was built"

#### `ARCHITECTURE.md` - Technical Architecture Documentation (Optional)
If this file exists:
- Documents the **system architecture** and technical design decisions
- Contains: component descriptions, data flow diagrams, class hierarchies, design patterns
- Explains **how the system works internally** (modules, layers, interactions)
- Target audience: developers who need to understand the codebase structure
- **Must be updated** when:
  - Adding new components or layers
  - Changing data flow or communication patterns
  - Modifying core abstractions or design patterns
  - Implementing features that affect system architecture
- Use **technical language** and focus on implementation details

#### `USAGE.md` - User Guide and Usage Documentation (Optional)
If this file exists:
- Documents **how to use** the application from a user's perspective
- Contains: CLI commands, configuration options, examples, workflows
- Explains **what the system does** and **how to operate it**
- Target audience: end users, operators, and administrators
- **Must be updated** when:
  - Adding new CLI commands or flags
  - Changing command behavior or options
  - Adding new features visible to users
  - Modifying configuration or environment variables
  - Changing execution modes or operational procedures
- Use **user-friendly language** and focus on practical usage

### Git Commit Policy
**🚨 CRITICAL: NEVER create git commits without EXPLICIT user permission! 🚨**

- **ALWAYS** stage changes with `git add` but STOP before committing
- **ALWAYS** show the user what will be committed using `git status` and `git diff --cached`
- **ALWAYS** present a proposed commit message for review
- **WAIT** for explicit user approval before running `git commit`
- **NEVER** assume permission based on previous commits in the same session
- If user says "commit this" or "create a commit", that counts as explicit permission
- If unclear, ASK: "Would you like me to create a commit for these changes?"

### Development Guidelines
- **IMPORTANT:** Always use `uv` commands, never `pip`, `poetry`, or `conda`
- Run `uv sync` after adding/removing dependencies
- Use `uv run pytest` to run tests after making changes
- Use `uv run ruff format` and `uv run ruff check --fix` for code quality
- For workspace projects, use `--package <member>` when targeting specific packages
- Follow existing code patterns and structure
- Consider security implications of changes
- Write comprehensive documentation

## Code Quality Requirements
- **IMPORTANT:** Generate code that passes the configured Ruff rules.
- Use modern Python type hints: `dict` instead of `Dict`, `list` instead of `List`, `str | None` instead of `Optional[str]`
- **VERY IMPORTANT:** Keep lines under 88 characters (project's line length limit)
- Sort and format imports properly (standard library, third-party, local imports in separate groups)
- Remove unused imports
- Add trailing newlines to all files
- Avoid f-strings without placeholders - use regular strings instead
- Break long lines using parentheses, multi-line strings, or temporary variables

---
*This file can be used by any AI coding assistant to understand the project context.*
*Individual developers may have their own tool-specific context files (e.g., CLAUDE.local.md)*
