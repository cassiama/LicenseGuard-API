# Dockerfile mostly taken from the official uv docs: https://docs.astral.sh/uv/guides/integration/fastapi/#deployment

FROM python:3.13.6-slim-bookworm@sha256:9b8102b7b3a61db24fe58f335b526173e5aeaaf7d13b2fbfb514e20f84f5e386 AS base

# Add OCI labels so GHCR links back to the repo.
LABEL org.opencontainers.image.source="https://github.com/cassiama/LicenseGuard-API" \
      org.opencontainers.image.description="LicenseGuard API server"
# TODO: add licensing info, once you have decided on a license!

# minimal ODBC runtime for pyodbc/aioodbc (Debian/Ubuntu base)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg2 unixodbc \
  && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
    > /etc/apt/sources.list.d/microsoft-prod.list \
  && apt-get update \
  && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
  && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv@sha256:cda9608307dbbfc1769f3b6b1f9abf5f1360de0be720f544d29a7ae2863c47ef /uv /uvx /bin/

# Set the working dir before copying project metadata.
WORKDIR /api

# Create non-root user & group (system account, no shell).
RUN set -eux; \
    groupadd -r app && useradd -r -g app -d /api -s /usr/sbin/nologin app; \
    chown -R app:app /api

# Give the user permissions for, potentially, a "/api/data" directory.
RUN install -d -o app -g app -m 0770 /api/data

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

# Set the user to be the non-root user we created (following best practices from here: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html).
USER app:app

# Set the entrypoint and default command. By default, run the application.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["serve"]