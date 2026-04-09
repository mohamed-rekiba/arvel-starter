from __future__ import annotations

from arvel.http import Router

from app.http.controllers import (
    AuthController,
    HealthController,
    InfraController,
    UserController,
)

router = Router()

with router.group(prefix="/api"):
    router.controller(AuthController, include_resource_actions=False)
    router.controller(UserController)
    router.controller(InfraController, include_resource_actions=False)
    router.controller(HealthController, include_resource_actions=False)
