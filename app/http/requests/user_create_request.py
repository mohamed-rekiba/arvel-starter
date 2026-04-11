"""UserCreateFormRequest — Arvel FormRequest with DB-aware validation rules.

Demonstrates:
- ``authorize()`` gating
- ``Unique`` DB rule for email uniqueness
- Custom ``messages()`` for i18n-ready error text
- ``after_validation()`` hook for data transformation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from arvel.i18n import trans
from arvel.validation import FormRequest, Unique

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from arvel.validation.rule import AsyncRule, Rule


class _Required:
    """Simple 'required' rule — value must be non-empty."""

    def passes(self, attribute: str, value: Any, data: dict[str, Any]) -> bool:
        return value is not None and str(value).strip() != ""

    def message(self) -> str:
        return trans("validation.required", field="this field")


class _MinLength:
    """Minimum string length rule."""

    def __init__(self, min_len: int) -> None:
        self._min_len = min_len

    def passes(self, attribute: str, value: Any, data: dict[str, Any]) -> bool:
        if value is None:
            return False
        return len(str(value)) >= self._min_len

    def message(self) -> str:
        return f"Must be at least {self._min_len} characters."


class _MaxLength:
    """Maximum string length rule."""

    def __init__(self, max_len: int) -> None:
        self._max_len = max_len

    def passes(self, attribute: str, value: Any, data: dict[str, Any]) -> bool:
        if value is None:
            return True
        return len(str(value)) <= self._max_len

    def message(self) -> str:
        return f"Must be at most {self._max_len} characters."


class UserCreateFormRequest(FormRequest):
    """Validates user creation with DB-aware uniqueness check on email."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    def authorize(self, request: Any) -> bool:
        return True

    def rules(self) -> dict[str, list[Rule | AsyncRule]]:
        email_rules: list[Rule | AsyncRule] = [
            _Required(),
            _MinLength(3),
            _MaxLength(255),
        ]
        if self._session is not None:
            email_rules.append(Unique("users", "email", session=self._session))
        return {
            "name": [_Required(), _MinLength(1), _MaxLength(100)],
            "email": email_rules,
            "password": [_Required(), _MinLength(8), _MaxLength(255)],
        }

    def messages(self) -> dict[str, str]:
        return {
            "name._Required": trans("validation.required", field="name"),
            "email._Required": trans("validation.required", field="email"),
            "email.Unique": trans("validation.unique", field="email"),
            "password._Required": trans("validation.required", field="password"),
        }

    def after_validation(self, data: dict[str, Any]) -> dict[str, Any]:
        if "email" in data and isinstance(data["email"], str):
            data["email"] = data["email"].strip().lower()
        return data
