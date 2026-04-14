# Deferred Plan: Full REUSE/SPDX compliance

**Status:** Deferred — decided against cluttering non-source files with
headers for now. Revisit when the project is closer to final publication.

## Context

Full REUSE compliance (FSFE REUSE Specification 3.3) requires every tracked
file to be covered by an SPDX declaration. This is more thorough than adding
headers only to source files, but also more invasive: Dockerfiles, YAML
configs, Markdown docs, shell scripts, lock files, and JSON configs all need
coverage.

The current state of the repo (partial compliance):
- All Python source files under `src/` have SPDX headers. ✓
- `LICENSE` exists at repo root. ✓
- Non-source files (configs, docs, CI workflows, etc.) have no coverage. ✗
- `LICENSES/` directory does not exist. ✗
- `REUSE.toml` does not exist. ✗

## What full compliance requires

### 1. Add `reuse` as a dev dependency

```
uv add --dev reuse
```

This installs it via `uv sync` in all environments (devcontainer, CI, local).
No Dockerfile change needed.

### 2. Create `LICENSES/EUPL-1.2.txt`

Copy the full text from the existing root `LICENSE` file into
`LICENSES/EUPL-1.2.txt`. REUSE requires licence texts under `LICENSES/`
named by their SPDX identifier. Keep the root `LICENSE` for GitHub display.

### 3. Create `REUSE.toml` (repo root)

Covers all tracked files that cannot carry inline comment headers (JSON files,
lock files, binary files, Markdown docs):

```toml
# SPDX-FileCopyrightText: 2026 AGENZIA TPL BACINO CITTA' METROPOLITANA MILANO, MONZA E BRIANZA, LODI, PAVIA
# SPDX-License-Identifier: EUPL-1.2

version = 1

[[annotations]]
path = [
    "LICENSE",
    "uv.lock",
    ".python-version",
    "README.md",
    "CONTRIBUTING.md",
    "ai-context.md",
    "ai-project.md",
    "ai-scripts/README-ai-assistants.md",
    "ai-skills/README.md",
    "ai-skills/open-source-it-pa/SKILL.md",
    ".devcontainer/devcontainer.json",
    ".vscode/launch.json",
    ".vscode/settings.json",
]
SPDX-FileCopyrightText = "2026 AGENZIA TPL BACINO CITTA' METROPOLITANA MILANO, MONZA E BRIANZA, LODI, PAVIA"
SPDX-License-Identifier = "EUPL-1.2"
```

### 4. Add inline SPDX headers to remaining commentable files

Files that support `#` comments and need inline headers added:

- `pyproject.toml`
- `Dockerfile`
- `.devcontainer/Dockerfile`
- `docker-compose.yml`
- `.devcontainer/docker-compose-base.yml`
- `.devcontainer/docker-compose-run.yml`
- `.devcontainer/docker-compose.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/secrets-audit.yml`
- `.github/workflows/tag-release.yml`
- `.env.development`
- `.env.production`
- `entrypoint.sh` (after shebang)
- `ai-scripts/setup-claude-code.sh` (after shebang)
- `ai-scripts/setup-github-copilot.sh` (after shebang)
- `.gitignore`

Header to prepend:
```
# SPDX-FileCopyrightText: 2026 AGENZIA TPL BACINO CITTA' METROPOLITANA MILANO, MONZA E BRIANZA, LODI, PAVIA
# SPDX-License-Identifier: EUPL-1.2
```

**Shell scripts:** the shebang (`#!/bin/bash` etc.) must remain on line 1.
Insert the SPDX headers on lines 2–3.

### 5. Add CI workflow `.github/workflows/reuse.yml`

```yaml
# SPDX-FileCopyrightText: 2026 AGENZIA TPL BACINO CITTA' METROPOLITANA MILANO, MONZA E BRIANZA, LODI, PAVIA
# SPDX-License-Identifier: EUPL-1.2
name: REUSE Compliance

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  reuse-lint:
    name: REUSE Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: fsfe/reuse-action@v4
```

`fsfe/reuse-action` is self-contained: it does not need Python or uv installed.

## Verification

```bash
uv sync --dev
uv run reuse lint   # must print "Congratulations! Your project is compliant
                    # with version 3.3 of the REUSE Specification :-)"
```

## References

- REUSE tool: https://github.com/fsfe/reuse-tool
- REUSE Specification 3.3: https://reuse.software/spec-3.3/
- fsfe/reuse-action: https://github.com/fsfe/reuse-action
- Italian PA open source guidelines (Annex A):
  https://docs.italia.it/italia/developers-italia/gl-acquisition-and-reuse-software-for-pa-docs/en/stabile/attachments/annex-A-Guide-to-publishing-software-as-open-source.html
