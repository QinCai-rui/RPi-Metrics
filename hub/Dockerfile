FROM docker.io/oven/bun:1.4 AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/index.html frontend/tsconfig.json ./
COPY frontend/src ./src
RUN bun run --bun build

FROM docker.io/library/python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/opt/fleetmuster \
    PATH="/opt/fleetmuster/bin:$PATH" \
    FLEETMUSTER_DATA_DIR=/data \
    FLEETMUSTER_FRONTEND_DIR=/app/frontend
COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/fleetmuster_hub ./fleetmuster_hub
RUN uv sync --locked --no-dev --no-editable \
    && mkdir -m 700 /data \
    && touch /data/.fleetmuster \
    && chown -R 10001:10001 /data
COPY --from=frontend /frontend/dist ./frontend
USER 10001:10001
CMD ["fleetmuster-hub", "serve"]
