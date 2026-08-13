FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS builder

WORKDIR /app

COPY . /app

RUN UV_PROJECT_ENVIRONMENT=/usr/local \
    uv sync --project=/app --frozen --compile-bytecode --no-dev --no-editable --no-managed-python

FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

RUN useradd --create-home --shell /bin/bash nonroot

COPY --from=builder /usr/local /usr/local

COPY --from=builder /app /app

WORKDIR /app

USER nonroot

ENTRYPOINT ["python", "scripts/entrypoint.py"]
