# Starter Project Test Suite Design

**Date**: 2026-04-09
**Approach**: Option A — Mirror framework's layered pattern with full-app integration

## Problem

The arvel-starter project has `pyproject.toml` and `Makefile` wired for tests, but no `tests/` directory exists. CI fails without tests.

## Chosen Approach

Full integration testing: boot the real Arvel app with SQLite and framework fakes for infrastructure services. Each test runs inside a transaction that rolls back.

## Structure

```
tests/
├── conftest.py                    # Root: clean_env, auto-markers, app factory with fakes
├── _fixtures/
│   └── factory.py                 # UserFactory using framework's ModelFactory
├── data/
│   ├── conftest.py                # SQLite file DB, rollback session, transaction fixture
│   ├── test_user_model.py         # User model metadata, fillable, soft deletes, hierarchy
│   ├── test_user_repository.py    # UserRepository CRUD, find_by_email
│   └── test_user_observer.py      # Email normalization, event dispatch, search
├── http/
│   ├── conftest.py                # Full-app TestClient, auth helpers
│   ├── test_auth_endpoints.py     # Login, refresh, password, verify, logout
│   ├── test_user_endpoints.py     # Index, create, show, /me, hierarchy
│   ├── test_infra_endpoints.py    # Cache, lock, storage
│   └── test_health_endpoint.py    # Health check
├── validation/
│   └── test_user_create_form.py   # FormRequest rules, uniqueness
├── events/
│   └── test_user_created.py       # Event structure
└── integration/
    └── conftest.py                # Skip markers for live services
```

## Key Decisions

1. **SQLite for all DB tests** — matches framework's test pattern, no Docker needed for unit/HTTP tests
2. **Framework fakes for infrastructure** — CacheFake, LockFake, StorageFake, etc.
3. **Transaction rollback isolation** — each test gets a clean slate
4. **`acting_as()` for auth** — framework's TestClient handles X-User-ID injection
5. **Markers**: `db` auto-applied to data tests, `integration` for live services

## Non-Goals

- Performance benchmarks
- Load testing
- Multi-database (Postgres/MySQL) matrix — that's for CI with Docker
