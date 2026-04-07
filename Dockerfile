# ==============================================================================
# Arvel Starter — multi-stage Dockerfile
#
# Build context MUST be the monorepo root (py-framework/) so the local
# arvel dependency at src/arvel/ is available.
#
# Targets:
#   dev      — full toolchain, hot-reload, dev dependencies
#   runtime  — slim production image (bookworm)
#   distroless — minimal attack surface, non-root (recommended for prod)
#
# Build (from arvel-starter/):
#   docker compose up --build
#   docker compose build app
#
# Standalone (from monorepo root):
#   docker build -f repos/arvel-starter/Dockerfile --target dev -t arvel-starter:dev .
#   docker build -f repos/arvel-starter/Dockerfile --target runtime -t arvel-starter:runtime .
# ==============================================================================

# --------------- uv binary ----------------------------------------------------
FROM ghcr.io/astral-sh/uv:0.11.3 AS uv

# --------------- Base: shared Python + system deps ----------------------------
FROM python:3.14.3-slim-bookworm AS base

COPY --from=uv /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Mirror monorepo layout so [tool.uv.sources] path = "../../" resolves correctly.
# arvel-starter pyproject.toml lives at /monorepo/repos/arvel-starter/
# arvel framework lives at /monorepo/ (../../ from the starter)
WORKDIR /monorepo

# Copy framework source (the local path dependency)
COPY pyproject.toml ./pyproject.toml
COPY src/arvel/ ./src/arvel/

# Copy starter project files needed for dependency resolution
WORKDIR /monorepo/repos/arvel-starter
COPY repos/arvel-starter/pyproject.toml repos/arvel-starter/uv.lock repos/arvel-starter/README.md ./

RUN uv sync --frozen --no-dev

# Copy full starter source
COPY repos/arvel-starter/ .

# --------------- Dev: full toolchain + hot-reload -----------------------------
FROM base AS dev

RUN uv sync --frozen

ENV APP_ENV=development \
    APP_DEBUG=true

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "bootstrap.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --------------- Runtime: slim production image -------------------------------
FROM base AS runtime

ENV APP_ENV=production \
    APP_DEBUG=false

RUN addgroup --system app && adduser --system --ingroup app app
USER app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "bootstrap.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# --------------- Distroless: minimal attack surface ---------------------------
FROM gcr.io/distroless/python3-debian12:nonroot AS distroless

WORKDIR /app
COPY --from=runtime /monorepo/repos/arvel-starter /app
COPY --from=runtime /usr/local/lib/python3.14 /usr/local/lib/python3.14
COPY --from=runtime /usr/local/bin/uvicorn /usr/local/bin/uvicorn

ENV APP_ENV=production \
    APP_DEBUG=false

EXPOSE 8000

ENTRYPOINT ["python", "-m", "uvicorn", "bootstrap.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
