FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Setup a non-root user
RUN groupadd --system --gid 999 nonroot && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Install dependencies (without project, for caching)
RUN --mount=type=cache,target=/root/.cache/uv --mount=type=bind,source=uv.lock,target=uv.lock --mount=type=bind,source=pyproject.toml,target=pyproject.toml uv sync --locked --no-install-project --no-dev

# Add project source
COPY . /app

# Make sure the entrypoint script is executable
RUN chmod +x /app/entrypoint.sh

# Install the project dependencies as root, then change ownership to nonroot
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev

# Change ownership of the app directory to nonroot user so it can run the application
RUN chown -R nonroot:nonroot /app

# Place executables in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Reset entrypoint
ENTRYPOINT []

# Use non-root user
USER nonroot

CMD ["/app/entrypoint.sh"]