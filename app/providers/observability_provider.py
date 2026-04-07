"""Starter-level observability wiring — middleware and i18n bootstrap.

The framework's ``ObservabilityProvider`` handles logging configuration and
the ``/health`` endpoint.  This provider adds app-level ASGI middleware.

Middleware ordering (outermost → innermost, Starlette convention: last
``add_middleware`` call = outermost):

  AccessLogMiddleware → LocaleMiddleware → RequestIdMiddleware → app
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from arvel.foundation.config import get_module_settings
from arvel.foundation.provider import ServiceProvider
from arvel.i18n import set_translator
from arvel.i18n.middleware import LocaleMiddleware
from arvel.i18n.translator import Translator
from arvel.observability.access_log import AccessLogMiddleware
from arvel.observability.config import ObservabilitySettings
from arvel.observability.request_id import RequestIdMiddleware

if TYPE_CHECKING:
    from arvel.foundation.application import Application


class StarterObservabilityProvider(ServiceProvider):
    """Adds RequestIdMiddleware, LocaleMiddleware, AccessLogMiddleware, and Translator."""

    priority: int = 8

    async def boot(self, app: Application) -> None:
        fastapi_app = app.asgi_app()

        try:
            obs_settings = get_module_settings(app.config, ObservabilitySettings)
        except Exception:
            obs_settings = ObservabilitySettings()

        fastapi_app.add_middleware(RequestIdMiddleware)
        fastapi_app.add_middleware(LocaleMiddleware, default_locale="en")

        if obs_settings.access_log_enabled:
            fastapi_app.add_middleware(AccessLogMiddleware)

        translator = Translator(default_locale="en", fallback_locale="en")
        lang_dir = Path(app.config.base_path) / "lang"
        for module_name in ("validation", "messages"):
            translator.load_module(module_name, lang_dir)
        set_translator(translator)
