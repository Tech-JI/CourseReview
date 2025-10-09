# --- STAGE 1: Builder ---
FROM debian:13-slim AS builder

WORKDIR /app

COPY . /app

RUN --mount=type=bind,source=.,target=/app \
    --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/usr/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    <<EOF

    set -Eeux

    uv python install 3.13 --install-dir=/tmp/python

    (cd /tmp/python/* && tar -cf- .) | (cd /usr/local && tar -xf-)
    rm -r /tmp/python

    export UV_PROJECT_ENVIRONMENT=/usr/local
    uv sync --project=/app --frozen --compile-bytecode --no-dev --no-editable --no-managed-python
EOF

FROM gcr.io/distroless/base-debian13:nonroot

ARG CHIPSET_ARCH=x86_64-linux-gnu

COPY --from=builder /lib/${CHIPSET_ARCH}/libz.so.1 /lib/${CHIPSET_ARCH}/

COPY --from=builder /usr/local /usr/local

COPY --from=builder /app /app

WORKDIR /app

USER nonroot

ENTRYPOINT ["python", "/app/scripts/entrypoint.py"]
