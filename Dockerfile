# Dockerfile mostly taken from the official uv docs: https://docs.astral.sh/uv/guides/integration/fastapi/#deployment

FROM python:3.13.6-slim-bookworm@sha256:9b8102b7b3a61db24fe58f335b526173e5aeaaf7d13b2fbfb514e20f84f5e386 AS base

# Add OCI labels so GHCR links back to the repo.
LABEL org.opencontainers.image.source="https://github.com/cassiama/LicenseGuard-API" \
      org.opencontainers.image.description="LicenseGuard API server"
# TODO: add licensing info, once you have decided on a license!

# Install uv.
COPY --from=ghcr.io/astral-sh/uv@sha256:cda9608307dbbfc1769f3b6b1f9abf5f1360de0be720f544d29a7ae2863c47ef /uv /uvx /bin/

# Set the working dir before copying project metadata.
WORKDIR /api

# Create non-root user & group (system account, no shell).
RUN set -eux; \
    groupadd -r app && useradd -r -g app -d /api -s /usr/sbin/nologin app; \
    chown -R app:app /api

# Copy the project metadata first to leverage build cache.
COPY pyproject.toml uv.lock ./

# Install the application dependencies.
RUN uv sync --frozen --no-cache

# Copy the app source code and the Alembic files.
COPY --chown=app:app src/ /api/src/
COPY --chown=app:app alembic.ini /api/
COPY --chown=app:app migrations/ /api/migrations/

# Copy the entrypoint script to the PATH and make it executable.
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Use the project venv binaries on the PATH.
ENV PATH="/api/.venv/bin:${PATH}"

# Set the entrypoint and default command. By default, run the application.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["serve"]