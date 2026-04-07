"""WI-011 tests — DX files (Epic 008, Stories 5-6).

Validates that Dockerfile, docker-compose.yml, and CI workflow exist
with correct structure.
"""

from __future__ import annotations

from pathlib import Path


def _starter_root() -> Path:
    return Path(__file__).resolve().parents[2]


class TestDockerfile:
    def test_dockerfile_exists(self) -> None:
        assert (_starter_root() / "Dockerfile").exists()

    def test_dockerfile_has_dev_target(self) -> None:
        content = (_starter_root() / "Dockerfile").read_text()
        assert "FROM" in content
        assert "AS dev" in content

    def test_dockerfile_has_runtime_target(self) -> None:
        content = (_starter_root() / "Dockerfile").read_text()
        assert "AS runtime" in content

    def test_dockerfile_has_distroless_target(self) -> None:
        content = (_starter_root() / "Dockerfile").read_text()
        assert "AS distroless" in content

    def test_distroless_uses_nonroot(self) -> None:
        content = (_starter_root() / "Dockerfile").read_text()
        assert "nonroot" in content


class TestDockerCompose:
    def test_docker_compose_exists(self) -> None:
        assert (_starter_root() / "docker-compose.yml").exists()

    def test_compose_has_app_service(self) -> None:
        content = (_starter_root() / "docker-compose.yml").read_text()
        assert "app:" in content

    def test_compose_has_postgres(self) -> None:
        content = (_starter_root() / "docker-compose.yml").read_text()
        assert "postgres:" in content

    def test_compose_has_valkey(self) -> None:
        content = (_starter_root() / "docker-compose.yml").read_text()
        assert "valkey:" in content

    def test_compose_has_mailpit(self) -> None:
        content = (_starter_root() / "docker-compose.yml").read_text()
        assert "mailpit:" in content

    def test_compose_has_minio(self) -> None:
        content = (_starter_root() / "docker-compose.yml").read_text()
        assert "minio:" in content

    def test_compose_has_minio_init_bucket_setup(self) -> None:
        content = (_starter_root() / "docker-compose.yml").read_text()
        assert "minio-init:" in content
        assert "mc mb" in content
        assert "arvel-dev" in content

    def test_compose_has_meilisearch(self) -> None:
        content = (_starter_root() / "docker-compose.yml").read_text()
        assert "meilisearch:" in content
        assert "MEILI_MASTER_KEY" in content

    def test_compose_app_uses_meilisearch_for_search(self) -> None:
        content = (_starter_root() / "docker-compose.yml").read_text()
        assert "SEARCH_DRIVER: meilisearch" in content
        assert "SEARCH_MEILISEARCH_URL" in content

    def test_compose_marks_dev_only_credentials(self) -> None:
        content = (_starter_root() / "docker-compose.yml").read_text()
        assert "DEV ONLY" in content


class TestCIWorkflow:
    def test_ci_workflow_exists(self) -> None:
        assert (_starter_root() / ".github" / "workflows" / "ci.yml").exists()

    def test_ci_includes_ruff_check(self) -> None:
        content = (_starter_root() / ".github" / "workflows" / "ci.yml").read_text()
        assert "ruff check" in content

    def test_ci_includes_ruff_format(self) -> None:
        content = (_starter_root() / ".github" / "workflows" / "ci.yml").read_text()
        assert "ruff format" in content

    def test_ci_includes_pytest(self) -> None:
        content = (_starter_root() / ".github" / "workflows" / "ci.yml").read_text()
        assert "pytest" in content

    def test_ci_no_secrets_required(self) -> None:
        content = (_starter_root() / ".github" / "workflows" / "ci.yml").read_text()
        assert "DB_DRIVER: sqlite" in content
