FROM ghcr.io/astral-sh/uv:alpine3.22

# Setup a non-root user
RUN addgroup -S nonroot && adduser -S nonroot -G nonroot -h /home/nonroot

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Add project source
COPY . /app

# Change ownership of the app directory to nonroot user so it can run the application
RUN chown -R nonroot:nonroot /app

# Make sure the entrypoint script is executable
RUN chmod +x /app/scripts/entrypoint.sh
RUN chmod +x /app/scripts/deploy.sh

# Use non-root user
USER nonroot

RUN mkdir -p /app/website/static


# Install the project dependencies as root, then change ownership to nonroot
RUN --mount=type=cache,target=/root/.cache/uv --mount=type=bind,source=uv.lock,target=uv.lock --mount=type=bind,source=pyproject.toml,target=pyproject.toml uv sync --locked --no-install-project --no-dev

# Place executables in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Reset entrypoint
ENTRYPOINT []


CMD ["/app/scripts/entrypoint.sh"]
