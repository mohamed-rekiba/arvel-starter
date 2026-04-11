# Contributing to Arvel Starter

Thanks for considering a contribution! This guide covers everything you need to
get up and running.

## Prerequisites

| Tool             | Version        |
| ---------------- | -------------- |
| Python           | >= 3.14        |
| [uv]             | >= 0.11        |
| Docker + Compose | latest stable  |

[uv]: https://docs.astral.sh/uv/

## Getting Started

```bash
git clone https://github.com/mohamed-rekiba/arvel-starter.git
cd arvel-starter
cp .env.example .env
make sync
make serve
```

The app starts at <http://localhost:8000>.

## Development Workflow

### Branching

1. Create a branch from `main`:
   ```bash
   git checkout -b feat/short-description
   ```
2. Use [Conventional Commits] for all commit messages:
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation only
   - `refactor:` code change that neither fixes a bug nor adds a feature
   - `test:` adding or updating tests
   - `chore:` maintenance (deps, CI, tooling)

[Conventional Commits]: https://www.conventionalcommits.org/

### Code Quality

Run the full quality gate before pushing:

```bash
make check        # lint + typecheck + tests
```

Or run individual steps:

```bash
make lint         # ruff check + format check
make typecheck    # ty check
make test         # pytest
make format       # auto-format with ruff
```

### Testing

- All tests live in `tests/`.
- Unit tests run against an in-memory SQLite database -- no Docker required.
- Integration tests (marked `@pytest.mark.integration`) require Docker services.

```bash
make test-unit          # fast, no Docker
make test-integration   # requires Docker
make coverage           # with coverage report (80% minimum)
```

### Database Migrations

```bash
make migrate      # run pending migrations
make seed         # seed the database
make fresh        # drop + recreate + migrate + seed (dev/testing only)
```

## Pull Requests

1. Push your branch and open a PR against `main`.
2. Fill in the PR template -- describe **what** changed and **why**.
3. Ensure CI passes (lint, typecheck, tests).
4. Keep PRs focused -- one logical change per PR.
5. Respond to review feedback promptly.

## Code Style

- **Formatter/linter:** [Ruff] -- config in `ruff.toml`.
- **Type checker:** [ty] -- strict mode.
- No wildcard imports. Keep imports sorted (Ruff handles this).
- Prefer explicit types on function signatures.

[Ruff]: https://docs.astral.sh/ruff/
[ty]: https://docs.astral.sh/ty/

## Project Layout

```
app/
├── http/controllers/    # route handlers
├── http/requests/       # request validation
├── http/resources/      # response serialization
├── jobs/                # background jobs
├── listeners/           # event listeners
├── models/              # ORM models
├── observers/           # model observers
├── providers/           # service providers
└── repositories/        # data access layer
config/                  # typed settings modules
database/
├── factories/           # test factories
├── migrations/          # Alembic migrations
└── seeders/             # database seeders
routes/                  # route definitions
tests/                   # test suite
```

## Reporting Issues

Use the [GitHub issue tracker](https://github.com/mohamed-rekiba/arvel-starter/issues).
Include:

- Steps to reproduce
- Expected vs. actual behavior
- Python version, OS, and relevant logs

## License

By contributing you agree that your contributions will be licensed under the
same license as the project.
