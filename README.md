# Arvel Starter

Starter app designed to stress real framework integrations, not just a hello-world route.

## What This Template Covers

- HTTP app boot + routes
- PostgreSQL integration for relational data
- Valkey for cache + queue broker
- Mailpit for local SMTP capture
- MinIO for S3-compatible object storage

## Prerequisites

- `uv` (recommended: `0.11.3`)
- Docker + Docker Compose (for full stack)

## Local Development

```bash
cp .env.example .env
make sync
make run
```

App runs at [http://localhost:8000](http://localhost:8000).
`make run` explicitly uses `bootstrap.app:create_app` and sets `PYTHONPATH=.`
so reload subprocess imports `bootstrap` reliably.

`.env.example` defaults target the compose services (Postgres, Valkey, Mailpit, MinIO)
using `localhost` endpoints, so host-run app + compose infra works without edits.
Logging and tracing config use canonical `OBSERVABILITY_*` keys.

## API Docs (Swagger)

When the app is running, open:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- OpenAPI JSON: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

The starter ships typed API docs examples:

- `GET /api/health` with a typed `PingResponse`
- `GET /api/users`, `POST /api/users`, `GET /api/users/{id}` with typed
  request/response models and explicit operation metadata (`summary`, `tags`,
  `operation_id`, and selected response docs)

Use this pattern for new routes:

```python
from arvel.http import BaseController, route


class ItemController(BaseController):
    prefix = "/items"
    tags = ("items",)

    @route.post(
        "/",
        response_model=ItemResource,
        summary="Create item",
        operation_id="items_create",
    )
    async def store(self, payload: ItemCreateRequest) -> ItemResource:
        ...
```

This starter is wired for the current monorepo: `arvel` resolves from `../../`
via `tool.uv.sources` in `pyproject.toml`.

## Custom Typed Config (Auto-Discovery)

Arvel auto-discovers custom settings classes from `config/*.py` when a file
exports `settings_class` as a `ModuleSettings` subclass.

Example included: `config/search.py`.

Runtime access is typed and simple:

```python
from arvel.http import BaseController
from arvel.foundation.application import Application
from config.search import SearchSettings


class SearchController(BaseController):
    def __init__(self, app: Application) -> None:
        self._search = app.settings(SearchSettings)
```

You can also inject the settings from DI by type when wiring services.

## Full Stack With Docker Compose

```bash
cp .env.example .env
make compose-up
```

The compose app container overrides infra hostnames (`postgres`, `valkey`, `mailpit`,
`minio`) while keeping the same drivers and credentials.

Services:

- App: [http://localhost:8000](http://localhost:8000)
- PostgreSQL: `localhost:5432`
- Valkey: `localhost:6379`
- Mailpit UI: [http://localhost:8025](http://localhost:8025)
- MinIO API: [http://localhost:9000](http://localhost:9000)
- MinIO Console: [http://localhost:9001](http://localhost:9001)

Stop the stack:

```bash
make compose-down
```

## Quality Checks

```bash
make lint
make typecheck
make test
make check
```

## Dockerfile Targets

- `dev`: includes `uv`, optimized for iterative development
- `runtime`: slim Python production image (assumes `arvel` is installable from an index)
- `distroless`: locked-down runtime target (also assumes `arvel` is installable from an index)

Example build:

```bash
docker build --target distroless -t arvel-starter:distroless .
```
