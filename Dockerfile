FROM astral/uv:0.8-python3.13-alpine

RUN apk add --no-cache \
    build-base \
    postgresql-dev \
    python3-dev \
    libffi-dev \
    musl-dev \
    linux-headers

# Setup a non-root user
RUN addgroup -S nonroot && adduser -S nonroot -G nonroot -h /home/nonroot

WORKDIR /app

# Enable bytecode compilation
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Add project source
COPY . /app

# RUN apk add --no-cache postgresql-dev

# Install the project dependencies as root, then change ownership to nonroot
RUN uv venv  .venv

RUN uv sync --locked --no-dev


# Change ownership of the app directory to nonroot user so it can run the application
RUN chown -R nonroot:nonroot /app

# Make sure the entrypoint script is executable
RUN chmod +x /app/scripts/entrypoint.sh
RUN chmod +x /app/scripts/deploy.sh

# Use non-root user
USER nonroot

RUN mkdir -p /app/website/static


# Place executables in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Reset entrypoint
ENTRYPOINT []


CMD ["/app/scripts/entrypoint.sh"]
