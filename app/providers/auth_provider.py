"""Application-level auth provider — wires TokenService, JwtGuard, AuthManager.

Assembles the framework's auth module from config and registers services
in the DI container.  Protected routes are guarded by ``AuthGuardMiddleware``
applied via a prefix-matching wrapper.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from arvel.auth.auth_manager import AuthManager
from arvel.auth.guard import AuthGuardMiddleware
from arvel.auth.guards import JwtGuard
from arvel.auth.password_reset import ResetTokenService
from arvel.auth.tokens import TokenService
from arvel.context import Context
from arvel.foundation.container import Scope
from arvel.foundation.provider import ServiceProvider
from arvel.http.exception_handler import install_exception_handlers
from arvel.http.request import RequestContainerMiddleware
from arvel.security.config import SecuritySettings
from arvel.validation.exceptions import ValidationError as ArvelValidationError
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from arvel.foundation.application import Application
    from arvel.foundation.container import ContainerBuilder
    from starlette.types import ASGIApp, Receive, Send
    from starlette.types import Scope as ASGIScope

_TEST_APP_KEY = "test-secret-key-for-starter-demo-only"  # noqa: S105

_PROTECTED_PATH_PREFIXES: tuple[str, ...] = (
    "/api/users/me",
    "/api/auth/change-password",
    "/api/auth/logout",
    "/api/auth/verify-email/send",
)


class _PrefixAuthMiddleware:
    """Apply ``AuthGuardMiddleware`` only on protected path prefixes.

    After successful authentication, seeds the ``Context`` store with
    ``user_id`` so it flows into structured logs, error responses, and
    queued jobs automatically.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        auth_manager: AuthManager,
        protected_prefixes: tuple[str, ...],
    ) -> None:
        self._app = _AuthContextMiddleware(app)
        self._guard_inner = AuthGuardMiddleware(self._app, auth_manager=auth_manager)
        self._prefixes = protected_prefixes

    async def __call__(self, scope: ASGIScope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if any(path.startswith(p) for p in self._prefixes):
            await self._guard_inner(scope, receive, send)
        else:
            await self._app(scope, receive, send)


class _AuthContextMiddleware:
    """Seeds ``Context`` with ``user_id`` from the auth guard's scope state.

    Runs *after* ``AuthGuardMiddleware`` has populated
    ``scope["state"]["auth_user_id"]``, so every downstream log line
    and error response includes the authenticated user.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: ASGIScope, receive: Receive, send: Send) -> None:
        state: dict[str, object] = scope.get("state", {})
        user_id = state.get("auth_user_id")
        if user_id is not None:
            Context.add("user_id", str(user_id))
        await self._app(scope, receive, send)


def _make_token_service() -> TokenService:
    settings = SecuritySettings()
    secret = os.environ.get("APP_KEY", "") or _TEST_APP_KEY
    return TokenService(
        secret,
        algorithm=settings.jwt_algorithm,
        access_ttl_minutes=settings.jwt_access_ttl_minutes,
        refresh_ttl_days=settings.jwt_refresh_ttl_days,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


def _make_reset_token_service() -> ResetTokenService:
    settings = SecuritySettings()
    secret = os.environ.get("APP_KEY", "") or _TEST_APP_KEY
    return ResetTokenService(
        secret,
        reset_ttl_minutes=settings.reset_token_ttl_minutes,
        verify_ttl_hours=settings.verify_token_ttl_hours,
    )


def _make_auth_manager() -> AuthManager:
    token_service = _make_token_service()
    jwt_guard = JwtGuard(token_service=token_service)
    return AuthManager(guards={"jwt": jwt_guard}, default="jwt")


def _install_validation_handler(app: FastAPI) -> None:
    """Map ``ArvelValidationError`` → 422 with field-level error details."""

    @app.exception_handler(ArvelValidationError)
    async def _handler(_request: Request, exc: ArvelValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "type": "about:blank",
                "title": "Validation Error",
                "status": 422,
                "detail": exc.detail,
                "errors": [
                    {"field": e.field, "rule": e.rule, "message": e.message}
                    for e in exc.errors
                ],
            },
            media_type="application/problem+json",
        )


class AuthProvider(ServiceProvider):
    """Wires JWT auth for the starter application."""

    priority: int = 15

    async def register(self, container: ContainerBuilder) -> None:
        container.provide_factory(TokenService, _make_token_service, scope=Scope.APP)
        container.provide_factory(
            ResetTokenService, _make_reset_token_service, scope=Scope.APP
        )
        container.provide_factory(AuthManager, _make_auth_manager, scope=Scope.APP)

    async def boot(self, app: Application) -> None:
        auth_manager = await app.container.resolve(AuthManager)
        _app = app.asgi_app()

        install_exception_handlers(_app, debug=getattr(app.config, "app_debug", False))
        _install_validation_handler(_app)

        _app.add_middleware(
            _PrefixAuthMiddleware,
            auth_manager=auth_manager,
            protected_prefixes=_PROTECTED_PATH_PREFIXES,
        )
        _app.add_middleware(RequestContainerMiddleware, container=app.container)
