from __future__ import annotations

from pathlib import Path

from arvel.foundation.application import Application

global root_path
root_path = Path(__file__).resolve().parent.parent


def create_app() -> Application:
    return Application.configure(root_path)
