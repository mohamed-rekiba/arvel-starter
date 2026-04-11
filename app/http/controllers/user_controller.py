"""User controller — demonstrates the full data + infrastructure + search stack.

Dependencies are declared in method signatures via ``Inject()`` and
resolved from the Arvel DI container at request time.
Auth-protected endpoints rely on ``AuthGuardMiddleware`` to set
``request.state.auth_context`` before the handler runs.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.http.requests.user_create_request import UserCreateFormRequest
from app.http.resources.user_resource import (
    ApiErrorResponse,
    HierarchyNode,
    HierarchyResponse,
    NotifyResponse,
    PaginatedUserResponse,
    PaginationMeta,
    ProfileImageUploadResponse,
    SearchHitResource,
    SearchResponse,
    UserCreateRequest,  # noqa: TC001
    UserProfileResource,
    UserResource,
)
from app.models.user import User
from app.notifications.welcome_notification import WelcomeNotification
from arvel.data import PaginatedResult
from arvel.http import (
    BaseController,
    File,
    HTTPException,
    Inject,
    Path,
    Query,
    Request,  # noqa: TC001
    UploadFile,  # noqa: TC001
    route,
    status,
)
from arvel.lock.contracts import LockContract
from arvel.media.contracts import MediaContract
from arvel.notifications.dispatcher import NotificationDispatcher
from arvel.search.contracts import SearchEngine
from arvel.storage.contracts import StorageContract

if TYPE_CHECKING:
    from arvel.data import TreeNode

logger = logging.getLogger(__name__)


class UserController(BaseController):
    description = "User management endpoints."
    tags = ("users",)
    prefix = "/users"

    @route.get(
        "",
        response_model=PaginatedUserResponse,
        summary="List users (paginated)",
        operation_id="users_index",
    )
    async def index(
        self,
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1, le=100),
    ) -> PaginatedUserResponse:
        logger.info("index query: %s", page, per_page)
        total = await User.count()
        offset = (page - 1) * per_page
        users = await User.query().order_by(User.id).limit(per_page).offset(offset).all()
        paginated = PaginatedResult(
            data=list(users),
            total=total,
            page=page,
            per_page=per_page,
        )
        logger.info("index response")
        return PaginatedUserResponse(
            data=[UserResource(id=u.id, name=u.name) for u in paginated.data],
            pagination=PaginationMeta(
                total=paginated.total,
                page=paginated.page,
                per_page=paginated.per_page,
                last_page=paginated.last_page,
                has_more=paginated.has_more,
            ),
        )

    @route.post(
        "/",
        response_model=UserResource,
        status_code=201,
        responses={422: {"description": "Validation error"}},
        summary="Create user",
        description="Creates a user from the typed request body.",
        operation_id="users_create",
    )
    async def store(self, payload: UserCreateRequest) -> UserResource:
        user = await User.create(payload.model_dump())
        return UserResource(id=user.id, name=user.name)

    @route.post(
        "/validated",
        response_model=UserResource,
        status_code=201,
        responses={422: {"description": "Validation error"}},
        summary="Create user with FormRequest validation",
        description="Validates via Arvel FormRequest (Unique email, length rules) before creating.",
        operation_id="users_create_validated",
    )
    async def store_validated(self, request: Request) -> UserResource:
        body = await request.json()
        form = UserCreateFormRequest()
        validated = await form.validate_request(request=request, data=body)
        user = await User.create(validated)
        return UserResource(id=user.id, name=user.name)

    @route.get(
        "/id/{id}",
        response_model=UserResource,
        responses={404: {"description": "User not found", "model": ApiErrorResponse}},
        summary="Get user by id",
        description="Returns a typed user resource for the given identifier.",
        operation_id="users_show",
    )
    async def show(self, user_id: int = Path(alias="id", ge=1)) -> UserResource:
        user = await User.find_or_none(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResource(id=user.id, name=user.name)

    @route.get(
        "/me",
        response_model=UserProfileResource,
        summary="Get current user profile",
        operation_id="users_me",
    )
    async def me(self, request: Request) -> UserProfileResource:
        auth_context = request.state.auth_context
        subject = auth_context.sub
        user = await User.query().where(User.email == subject).order_by(User.id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return UserProfileResource(id=user.id, email=user.email)

    @route.post(
        "/me/profile-image",
        response_model=ProfileImageUploadResponse,
        summary="Upload profile image via MediaContract",
        operation_id="users_upload_profile_image",
    )
    async def upload_profile_image(
        self,
        request: Request,
        file: UploadFile = File(..., description="Image file to upload"),
        media: MediaContract = Inject(MediaContract),
        storage: StorageContract = Inject(StorageContract),
    ) -> ProfileImageUploadResponse:
        auth_context = request.state.auth_context
        content_type = file.content_type or ""
        if not content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image payload",
            )

        subject = auth_context.sub
        file_bytes = await file.read()
        user = await User.query().where(User.email == subject).order_by(User.id).first()

        if user is not None:
            item = await media.add(
                user,
                file_bytes,
                f"profile-{user.id}.webp",
                collection="profile_images",
                content_type=content_type,
            )
            url = await storage.url(item.path)
        else:
            path = f"media/profile/{subject}.webp"
            await storage.put(path, file_bytes, content_type=content_type)
            url = await storage.url(path)
        return ProfileImageUploadResponse(url=url)

    @route.post(
        "/{id}/notify",
        response_model=NotifyResponse,
        summary="Trigger user notification (with lock for idempotency)",
        operation_id="users_notify",
    )
    async def notify(
        self,
        user_id: int = Path(alias="id", ge=1),
        lock: LockContract = Inject(LockContract),
        notification_dispatcher: NotificationDispatcher = Inject(NotificationDispatcher),
    ) -> NotifyResponse:
        lock_key = f"notify:user:{user_id}"
        acquired = await lock.acquire(lock_key, ttl=10)
        if not acquired:
            return NotifyResponse(status="skipped", channel="lock_held")
        try:
            user = await User.find_or_none(user_id)
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")

            await notification_dispatcher.send(user, WelcomeNotification(name=user.name))
            return NotifyResponse(status="sent", channel="mail")
        finally:
            await lock.release(lock_key)

    @route.get(
        "/search",
        response_model=SearchResponse,
        summary="Full-text search users via SearchEngine",
        operation_id="users_search",
    )
    async def search(
        self,
        q: str = Query(min_length=1, max_length=200),
        limit: int = Query(default=20, ge=1, le=100),
        engine: SearchEngine = Inject(SearchEngine),
    ) -> SearchResponse:
        index_name = User.search_index_name()
        result = await engine.search(index_name, q, limit=limit)

        hits: list[SearchHitResource] = []
        for hit in result.hits:
            user = await User.find_or_none(int(hit.id))
            if user is not None:
                hits.append(
                    SearchHitResource(
                        id=user.id,
                        name=user.name,
                        email=user.email,
                        score=hit.score,
                    )
                )
        return SearchResponse(query=q, hits=hits, total=result.total)

    @route.get(
        "/{id}/hierarchy",
        response_model=HierarchyResponse,
        summary="Get recursive hierarchy",
        operation_id="users_hierarchy",
    )
    async def hierarchy(self, user_id: int = Path(alias="id", ge=1)) -> HierarchyResponse:
        tree_nodes: list[TreeNode[User]] = (
            await User.query().descendants(user_id, max_depth=10).all_as_tree()
        )
        if not tree_nodes:
            return HierarchyResponse(root=None, nodes=[])

        def _convert(tn: TreeNode[User]) -> HierarchyNode:
            return HierarchyNode(
                id=tn.data.get("id", 0),
                name=tn.data.get("name"),
                depth=tn.depth,
                children=[_convert(c) for c in tn.children],
            )

        nodes = [_convert(tn) for tn in tree_nodes]
        root_node = nodes[0] if nodes else None
        return HierarchyResponse(root=root_node, nodes=nodes)
