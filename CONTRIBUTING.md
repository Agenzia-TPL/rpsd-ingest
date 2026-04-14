# Contributing to rpsd-ingest

Thank you for your interest in contributing. This document explains how to
report bugs, propose improvements, and submit code changes.

## Reporting bugs

Use [GitHub Issues](https://github.com/Agenzia-TPL/rpsd-ingest/issues) to
report bugs or request features. Before opening a new issue, search existing
ones to avoid duplicates.

When reporting a bug, please include:

- A clear description of the problem and the expected behaviour.
- Steps to reproduce the issue.
- The Python version and relevant environment variable configuration (omit any
  secrets or credentials).
- Relevant log output or error messages.

## Submitting changes

1. **Fork** the repository on GitHub.
2. **Create a branch** from `main` with a descriptive name
   (e.g. `fix-api-key-validation` or `add-siri-support`).
3. **Make your changes.** Follow the coding standards below.
4. **Run the tests** to make sure nothing is broken.
5. **Open a Pull Request** against the `main` branch with a clear description
   of what the change does and why.

Changes that add new behaviour should include tests. Changes that affect
configuration or the HTTP API should update the relevant sections of
`README.md`.

## Development setup

Follow the [installation instructions](README.md#installation) in the README.
After cloning and running `uv sync`, the full test suite can be run with:

```bash
uv run pytest
```

## Coding standards

- **Style:** follow [PEP 8](https://peps.python.org/pep-0008/).
- **Formatting and linting:** use [ruff](https://docs.astral.sh/ruff/).
  Format with `uv run ruff format` and fix linting issues with
  `uv run ruff check --fix`.
- **Type hints:** use modern Python type syntax (`str | None`, `list[str]`,
  `dict[str, int]`). Do not use `Optional`, `List`, `Dict` from `typing`.
- **Line length:** 88 characters maximum.
- **Imports:** absolute imports only; group standard library, third-party, and
  local imports in separate blocks.
- **Docstrings:** write docstrings for all public functions, classes, and
  modules.
- **SPDX headers:** every new `.py` file must start with the two SPDX
  comment lines (see existing files for the exact format).

Before opening a pull request, verify that the code passes:

```bash
uv run ruff format --check
uv run ruff check
uv run pytest
```

## Licence and Contributor License Agreement

By submitting a pull request you certify that:

1. You have the right to submit the contribution under the project licence.
2. Your contribution is your original work, or you have the necessary rights
   to submit it.
3. You grant the project maintainer (Agenzia TPL Bacino Città Metropolitana
   Milano, Monza e Brianza, Lodi, Pavia) the right to redistribute your
   contributions under any OSI-approved open source licence, including future
   versions of EUPL or compatible licences such as AGPL-3.0-or-later.

Your contributions will be licensed under the
[European Union Public Licence v. 1.2 (EUPL-1.2)](LICENSE), the same licence
that covers the rest of the project.
