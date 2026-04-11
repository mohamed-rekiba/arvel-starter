from __future__ import annotations

from app.http.controllers import (
    AuthController,
    HealthController,
    InfraController,
    UserController,
)
from arvel.http import Router

router = Router()

with router.group(prefix="/api"):
    router.controller(AuthController, include_resource_actions=False)
    router.controller(UserController)
    router.controller(InfraController, include_resource_actions=False)
    router.controller(HealthController, include_resource_actions=False)
