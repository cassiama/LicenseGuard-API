# Dockerfile mostly taken from the official uv docs: https://docs.astral.sh/uv/guides/integration/fastapi/#deployment

FROM python:3.13.6-slim-bookworm AS base

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.8.9 /uv /uvx /bin/

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

# Use the project venv binaries on the PATH
ENV PATH="/app/.venv/bin:${PATH}"

# Run the application.
CMD ["/app/.venv/bin/fastapi", "run", "src/api/app.py", "--port", "80", "--host", "0.0.0.0"]