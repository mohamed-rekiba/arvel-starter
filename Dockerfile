# ── Base stage ──────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl ca-certificates openssh-client && \
    rm -rf /var/lib/apt/lists/*

# ── Build stage ──────────────────────────────────────────
FROM base AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install dependencies (SSH agent forwarded for private Git deps)
COPY uv.lock pyproject.toml README.md .
RUN uv sync --locked

# Copy full source and sync the project
COPY . .

EXPOSE 8000

# ── Development stage (used by docker-compose) ──────────
FROM builder AS dev

CMD ["uv", "run", "arvel", "serve", "--host", "0.0.0.0", "--port", "8000"]

# ── Production stage ─────────────────────────────────────
FROM builder AS production

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["python", "-m", "uvicorn", "bootstrap.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
