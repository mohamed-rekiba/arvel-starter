from __future__ import annotations


from pydantic import BaseModel, Field


class ApiErrorResponse(BaseModel):
    detail: str


class UserResource(BaseModel):
    id: int
    name: str


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105


class UserProfileResource(BaseModel):
    id: int
    email: str
    profile_image_url: str | None = None


class ProfileImageUploadResponse(BaseModel):
    url: str


class NotifyResponse(BaseModel):
    status: str
    channel: str


class HierarchyNode(BaseModel):
    id: int
    name: str | None = None
    depth: int = 0
    children: list[HierarchyNode] = Field(default_factory=list)


class HierarchyResponse(BaseModel):
    root: HierarchyNode | None = None
    nodes: list[HierarchyNode] = Field(default_factory=list)


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    last_page: int
    has_more: bool


class PaginatedUserResponse(BaseModel):
    data: list[UserResource]
    pagination: PaginationMeta


class SearchHitResource(BaseModel):
    id: int
    name: str
    email: str
    score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHitResource] = Field(default_factory=list)
    total: int = 0


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1)
    email: str = Field(min_length=3, max_length=255)


class MessageResponse(BaseModel):
    message: str


class ValidationFieldError(BaseModel):
    field: str
    rule: str
    message: str


class ValidationErrorResponse(BaseModel):
    code: str = "VALIDATION_FAILED"
    message: str = "The given data was invalid."
    details: list[ValidationFieldError] = Field(default_factory=list)
