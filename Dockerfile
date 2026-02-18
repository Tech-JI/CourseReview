FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

COPY . /app

RUN UV_PROJECT_ENVIRONMENT=/usr/local \
    uv sync --project=/app --frozen --compile-bytecode --no-dev --no-editable --no-managed-python

FROM gcr.io/distroless/base-debian13:nonroot

COPY --from=builder /usr/local /usr/local

COPY --from=builder /app /app

WORKDIR /app

USER nonroot

ENTRYPOINT ["python", "/app/scripts/entrypoint.py"]
