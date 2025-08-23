# Dockerfile mostly taken from the official uv docs: https://docs.astral.sh/uv/guides/integration/fastapi/#deployment

FROM python:3.13.6-slim-bookworm@sha256:9b8102b7b3a61db24fe58f335b526173e5aeaaf7d13b2fbfb514e20f84f5e386 AS base

# Add OCI labels so GHCR links back to the repo.
LABEL org.opencontainers.image.source="https://github.com/cassiama/LicenseGuard-API" \
      org.opencontainers.image.description="LicenseGuard API server"
# TODO: add licensing info, once you have decided on a license!

# Install uv.
COPY --from=ghcr.io/astral-sh/uv@sha256:cda9608307dbbfc1769f3b6b1f9abf5f1360de0be720f544d29a7ae2863c47ef /uv /uvx /bin/

# Copy the project metadata first to leverage build cache.
COPY pyproject.toml uv.lock ./

# Install the application dependencies.
WORKDIR /src
RUN uv sync --frozen --no-cache

# Copy the rest of the application code.
COPY . .

# Use the project venv binaries on the PATH.
ENV PATH="/src/.venv/bin:${PATH}"

# Run the application.
CMD ["/src/.venv/bin/fastapi", "run", "src/srv/app.py", "--port", "80", "--host", "0.0.0.0"]