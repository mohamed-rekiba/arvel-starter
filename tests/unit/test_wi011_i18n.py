"""WI-011 tests — i18n Translator (Epic 008, Story 4).

Validates Translator loading, key resolution, locale fallback, and
parameter substitution.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from pathlib import Path
from typing import Any

import pytest

from arvel.i18n.translator import Translator


async def _noop_asgi(
    scope: MutableMapping[str, Any],
    receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
    send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
) -> None:
    """No-op ASGI app for middleware tests."""


@pytest.fixture
def lang_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "lang"


@pytest.fixture
def translator(lang_dir: Path) -> Translator:
    t = Translator(default_locale="en", fallback_locale="en")
    t.load_module("validation", lang_dir)
    t.load_module("messages", lang_dir)
    return t


class TestTranslatorLoading:
    def test_load_module_from_lang_dir(self, translator: Translator) -> None:
        result = translator.get("validation.required", field="name")
        assert "name" in result
        assert "required" in result.lower()

    def test_unknown_key_returns_key_itself(self, translator: Translator) -> None:
        result = translator.get("validation.nonexistent_key")
        assert result == "validation.nonexistent_key"

    def test_unknown_module_returns_key(self, translator: Translator) -> None:
        result = translator.get("unknown_module.some_key")
        assert result == "unknown_module.some_key"

    def test_key_without_dot_returns_key(self, translator: Translator) -> None:
        result = translator.get("nodot")
        assert result == "nodot"


class TestTranslatorLocale:
    def test_default_locale_is_english(self, translator: Translator) -> None:
        assert translator.default_locale == "en"

    def test_french_translation_resolves(self, translator: Translator) -> None:
        result = translator.get("validation.required", locale="fr", field="nom")
        assert "obligatoire" in result

    def test_fallback_to_english_for_missing_locale(
        self, translator: Translator
    ) -> None:
        result = translator.get("validation.required", locale="de", field="name")
        assert "required" in result.lower()

    def test_set_default_locale(self, translator: Translator) -> None:
        translator.default_locale = "fr"
        result = translator.get("validation.required", field="nom")
        assert "obligatoire" in result
        translator.default_locale = "en"


class TestTranslatorParameters:
    def test_parameter_substitution(self, translator: Translator) -> None:
        result = translator.get("validation.required", field="email")
        assert "email" in result

    def test_multiple_parameters(self, translator: Translator) -> None:
        result = translator.get("validation.min_length", field="password", min="8")
        assert "password" in result
        assert "8" in result

    def test_missing_parameter_returns_template(self, translator: Translator) -> None:
        result = translator.get("validation.required")
        assert "{field}" in result or "field" in result.lower()


class TestTransGlobalFunction:
    def test_trans_with_configured_translator(self, translator: Translator) -> None:
        from arvel.i18n import set_translator, trans

        set_translator(translator)
        try:
            result = trans("validation.welcome")
            assert "Welcome" in result or "Arvel" in result
        finally:
            set_translator(None)

    def test_trans_without_translator_returns_key(self) -> None:
        from arvel.i18n import set_translator, trans

        set_translator(None)
        result = trans("validation.required", field="test")
        assert result == "validation.required"

    def test_trans_with_locale_override(self, translator: Translator) -> None:
        from arvel.i18n import set_translator, trans

        set_translator(translator)
        try:
            result = trans("validation.welcome", locale="fr")
            assert "Bienvenue" in result
        finally:
            set_translator(None)


class TestLocaleMiddleware:
    def test_locale_middleware_default(self) -> None:
        from arvel.i18n.middleware import LocaleMiddleware

        middleware = LocaleMiddleware(app=_noop_asgi, default_locale="en")
        assert middleware._default_locale == "en"

    def test_parse_accept_language_simple(self) -> None:
        from arvel.i18n.middleware import LocaleMiddleware

        middleware = LocaleMiddleware(app=_noop_asgi, default_locale="en")
        assert middleware._parse_accept_language("fr-FR,fr;q=0.9,en;q=0.8") == "fr"

    def test_parse_accept_language_empty(self) -> None:
        from arvel.i18n.middleware import LocaleMiddleware

        middleware = LocaleMiddleware(app=_noop_asgi, default_locale="en")
        assert middleware._parse_accept_language("") == "en"
