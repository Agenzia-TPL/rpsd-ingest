FROM python:3.13-slim-bookworm

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Pull only the packages/ subdirectory from rpsd-commons (named build context).
# Excludes .git/ and other root files to avoid leaking credentials into image layers.
COPY --from=rpsd-commons packages/ /rpsd-commons/packages/

# Copy dependency files first (for better layer caching)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies only (cached unless pyproject.toml/uv.lock change)
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code (changes here don't invalidate dependency cache)
COPY src/ ./src/

# Now install the local project (builds webinner with src/ available)
RUN uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Copy entrypoint script
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Set entrypoint (command comes from docker-compose.yml)
ENTRYPOINT ["./entrypoint.sh"]
