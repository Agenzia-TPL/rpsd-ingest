# AI Project analysis

## Name

Rapsodia Ingest

## Overview

Ingest component of the Rapsodia project.

Uses packages from the rpsd-commons component:
- rpsd-transport
- rpsd-storage
- rpsd-flow

It's heavily inspired by its **FastAPI Ingest Example**. 

## Retrieve Flow configurations from Config

**Problem:** `resolve_flow_deployment` in `main.py` needs to select the correct Prefect Flow for each incoming message. The mapping from `(who, what)` to a flow name should come from the Config service, not be hard-coded.

**Proposed solution:** Add an async `fetch_flow_profile(who, what)` function that calls the Config service and returns the flow name to invoke. The feature is opt-in: if `EXCHANGE_AGREEMENT__FLOW_PROFILE_URL` is not set, the existing `settings.flow.deployment` fallback is used unchanged.

**Settings:** Add `ExchangeAgreementSettings` (nested under `exchange_agreement`) with a single optional field:

    EXCHANGE_AGREEMENT__FLOW_PROFILE_URL=http://rpsd-config:8000/exchange_agreement/api/v1/contracts/{contract_code}/flow-profile

**Contract code validation:** Validate `who` against `^[A-Z]+-\d+$` before building the URL, then URL-encode with `quote()` to prevent injection. Reject with `ValueError` if the pattern doesn't match.

**HTTP call:** Use `httpx.AsyncClient` (timeout 10 s). A 404 means unknown contract → reject the message with `ValueError`. Any other non-2xx raises via `raise_for_status()`.

**Response model:** Parse the response into typed Pydantic models (`ContractFlowProfileResponse`, `FlowProfile`, `FlowProfileOptions`, `DataIngestionEntry`) defined in `models/exchange_agreement.py`, mirroring the schema from `rpsd-config`.

**Validation logic:**
1. If `flow_profile` is `None` on the response → reject (no profile assigned).
2. Look up `what` in `flow_profile.options.data_ingestion` → reject if not present.
3. Check `entry.active` → reject if `False`.
4. Return `entry.flow` as the deployment name.

**Integration in `/ingest`:** Call `fetch_flow_profile` right after `carrier.receive()`. If it returns a flow name, use it as `config_deployment`; this takes priority over `settings.flow.deployment` when invoking the Prefect flow. All `ValueError`s from this function bubble up as HTTP 400 responses.

**Expected outcome:** Every ingested message is validated against the Config service. Unknown contracts, unsupported content types, and inactive flows are rejected before storage. When the env var is absent the service behaves exactly as before.

---

## Project Structure

```
project-root/
├── pyproject.toml      # Project configuration
├── uv.lock             # Lock file
├── src/                # Project source files
│   └── rpsd_ingest/    # Application package
├── tests/              # Test files
└── README.md           # Project documentation
```

## Project-Specific Guidelines

- This service ingests data into the Rapsodia platform; changes may affect downstream services
  that consume ingested data
- Follow the existing application structure under `src/rpsd_ingest/`
- Use `--package rpsd-ingest` when targeting this package in uv workspace commands, if applicable

---

## Technology Stack

- **Language:** Python 3.13+
- **Framework:** Django (REST API) + Django-ninja (async API support)
- **Package Manager:** uv (not pip/poetry/conda)
- **Production server:** Gunicorn (process manager) + UvicornWorker (ASGI)
- **Testing:** pytest
- **Linting/Formatting:** ruff

## Development Environment

- **Containerization:** Docker + devcontainers

## Common Development Commands

- `uv sync` - Install/update all dependencies
- `uv add <package>` - Add a dependency
- `uv run pytest` - Run tests
- `uv run ruff format` - Format code
- `uv run ruff check --fix` - Auto-fix linting issues
- `uv run python` - Execute Python code on the fly
- `uv run devserver` - Run Django dev server with configured host/port (devcontainer)

See `USAGE.md` for running with Docker (integration tests, staging, production).

## Development Guidelines

- **IMPORTANT:** Always use `uv` commands, never `pip`, `poetry`, or `conda`
- Run `uv sync` after adding/removing dependencies
- Use `uv run pytest` to run tests after making changes
- Use `uv run ruff format` and `uv run ruff check --fix` for code quality
- For workspace projects, use `--package <member>` when targeting specific packages

## Coding Standards

- Follow PEP 8 for Python code style
- Use type hints where applicable
- Use ruff for formatting and linting
- Write docstrings for all public functions and classes
- Always prefer absolute imports over relative ones
- Do not use workarounds such as `# type: ignore[arg-type]`
- Do not use workarounds such as `cast()`
- Use Pydantic Settings (not python-decouple or python-dotenv) for full type inference

## Code Quality Requirements

- Generate code that passes the configured Ruff rules
- Use modern Python type hints: `dict` not `Dict`, `list` not `List`, `str | None` not `Optional[str]`
- Keep lines under 88 characters (project's line length limit)
- Sort and format imports properly (standard library, third-party, local imports in separate groups)
- Remove unused imports
- Add trailing newlines to all files
- Avoid f-strings without placeholders — use regular strings instead
- Break long lines using parentheses, multi-line strings, or temporary variables

---
*For generic AI assistant guidelines and behavior, see `ai-context.md`.*
