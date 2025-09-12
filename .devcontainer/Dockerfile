# See here for image contents: https://github.com/devcontainers/images/blob/main/src/python/.devcontainer/Dockerfile

# [Choice] Python version (use -bookworm or -bullseye variants on local arm64/Apple Silicon): 3, 3.13, 3.12, 3.11, 3.10, 3.9, 3-bookworm, 3.13-bookworm, 3.12-bookworm, 3.11-bookworm, 3.10-bookworm, 3.9-bookworm, 3-bullseye, 3.13-bullseye, 3.12-bullseye, 3.11-bullseye, 3.10-bullseye, 3.9-bullseye, 3-buster, 3.12-buster, 3.11-buster, 3.10-buster, 3.9-buster

# Stage 1: Build
ARG VARIANT="3.13-bookworm"
FROM mcr.microsoft.com/devcontainers/python:1-${VARIANT} AS build

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Stage 2: Base
FROM build AS base

# Install dependencies, but not the project itself (do NOT install "dev" requirements here)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable --no-dev

# Stage 3a: Development
FROM base AS development

# Install development dependencies, but not the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable --dev

