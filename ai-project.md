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

In main.oy method resolve_flow_deployment should decide which Prefect Flow to invoke to process the received file.
To that avail it has to call the Config service upon the URL specified by:

    settings.exchange_agreement.flow_profile_url

This variable is retrieved from env and is something like:

    EXCHANGE_AGREEMENT__FLOW_PROFILE_URL=http://rpsd-config:8000/exchange_agreement/api/v1/contracts/{contract_code}/flow-profile

where "contract_code" is the "who" value of the received message.

To protect from injections a safetize method could be used, such as:

import re
from urllib.parse import quote

CONTRACT_CODE_RE = re.compile(r"^[A-Z]+-\d+$")  # or whatever the actual pattern is

def flow_profile_url(contract_code: str) -> str:
    if not CONTRACT_CODE_RE.match(contract_code):
        raise ValueError(f"Invalid contract code: {contract_code}")
    return settings.exchange_agreement.flow_profile_url.format(
        contract_code=quote(contract_code, safe="")
    )

The call to rhis API must be made before line 252 of main.py, that is, right after the message is received, or even before the message is retrieved at all, because all that's needed is the "who" value.
If the API call returns an error, for example an error of unknown contract (404), the received message must be refused.
If, instead, it returns a success, it will be a response such as:
{
  "contract_code": "CTR-001",
  "flow_profile": {
    "code": "standard-it-v1",
    "name": "Standard IT v1",
    "schema_version": "1.0",
    "is_active": true,
    "description": "Profilo standard per import e retention base.",
    "options": {
      "data_ingestion": {
        "gtfs": {
          "flow": "plnd-002",
          "active": false,
          "description": "Carica GTFS con step di trasformazione."
        },
        "netex": {
          "flow": "plnd-001",
          "active": true,
          "description": "Carica il programmato da NeTEx."
        },
        "siri_pt": {
          "flow": "rltm-spt-001",
          "active": true,
          "description": "Acquisisce real time SIRI PT."
        }
      },
      "data_retention": {
        "plnd": {
          "days": 100,
          "flow": "plnd-clr-001",
          "description": "Pulizia storico programmato."
        },
        "rltm": {
          "days": 3,
          "flow": "rltm-clr-001",
          "description": "Pulizia storico real time."
        }
      },
      "planned_master": {
        "gtfs": {
          "flow": "master-002",
          "active": true,
          "description": "Importa GTFS e lo converte in NeTEx."
        },
        "netex": {
          "flow": "master-001",
          "active": true,
          "description": "Carica il programmato master in formato NeTEx."
        }
      },
      "general_profile": "it"
    }
  }
}

Here, we're interested in values inside "flow_profile"/"options"/"data_ingestion", but this path is not strictly defined yet...
Then, we have to look for a key corresponding to the "what" value of the received message, that should be one of the listed values, such as: "gtfs", "netex", "siri_pt", etc.
If the "what" value is not listed, the message must be rejected, otherwise the "flow" field contains the name of the Prefect Flow to invoke.
As a start, we just have to magae the call to Config, the check of the "who" and "what" values, we'll implement the actual invocation later.

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
