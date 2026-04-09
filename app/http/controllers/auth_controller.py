"""Auth controller — login, refresh, password reset, email verification, logout.

Dependencies are declared in method signatures via ``Inject()`` and
resolved from the Arvel DI container at request time.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from arvel.auth.password_reset import ResetTokenService
from arvel.auth.tokens import TokenService
from arvel.http import BaseController, HTTPException, Inject, Request, route, status
from arvel.security.contracts import HasherContract

from app.http.resources.user_resource import (
    ChangePasswordRequest,  # noqa: TC001
    ForgotPasswordRequest,  # noqa: TC001
    LoginRequest,  # noqa: TC001
    MessageResponse,
    RefreshRequest,  # noqa: TC001
    ResetPasswordRequest,  # noqa: TC001
    TokenResponse,
    VerifyEmailRequest,  # noqa: TC001
)
from app.models.user import User

logger = logging.getLogger(__name__)


class AuthController(BaseController):
    prefix = "/auth"
    tags = ("auth",)
    description = "Authentication endpoints."

    @route.post(
        "/login",
        response_model=TokenResponse,
        summary="Login and issue tokens",
        operation_id="auth_login",
    )
    async def login(
        self,
        payload: LoginRequest,
        token_service: TokenService = Inject(TokenService),
        hasher: HasherContract = Inject(HasherContract),
    ) -> TokenResponse:
        user = (
            await User.query()
            .where(User.email == payload.email)
            .order_by(User.id)
            .first()
        )
        if user is None or not hasher.check(payload.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        pair = token_service.create_token_pair(user.email)
        return TokenResponse(**pair)

    @route.post(
        "/refresh",
        response_model=TokenResponse,
        summary="Refresh access token",
        operation_id="auth_refresh",
    )
    async def refresh(
        self,
        payload: RefreshRequest,
        token_service: TokenService = Inject(TokenService),
    ) -> TokenResponse:
        try:
            claims = token_service.decode_token(
                payload.refresh_token, expected_type="refresh"
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        subject = claims["sub"]
        pair = token_service.create_token_pair(subject)
        return TokenResponse(**pair)

    @route.post(
        "/forgot-password",
        response_model=MessageResponse,
        summary="Request a password reset token",
        operation_id="auth_forgot_password",
    )
    async def forgot_password(
        self,
        payload: ForgotPasswordRequest,
        reset_service: ResetTokenService = Inject(ResetTokenService),
    ) -> MessageResponse:
        user = (
            await User.query()
            .where(User.email == payload.email)
            .order_by(User.id)
            .first()
        )
        if user is not None:
            token = reset_service.create_reset_token(str(user.id))
            logger.info(
                "Password reset token generated for user_id=%s token=%s",
                user.id,
                token,
            )

        return MessageResponse(
            message="If that email exists, a reset link has been sent."
        )

    @route.post(
        "/reset-password",
        response_model=MessageResponse,
        summary="Reset password using a reset token",
        operation_id="auth_reset_password",
    )
    async def reset_password(
        self,
        payload: ResetPasswordRequest,
        reset_service: ResetTokenService = Inject(ResetTokenService),
        hasher: HasherContract = Inject(HasherContract),
    ) -> MessageResponse:
        user = (
            await User.query()
            .where(User.email == payload.email)
            .order_by(User.id)
            .first()
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token",
            )

        try:
            reset_service.validate_reset_token(payload.token, str(user.id))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        user.password = hasher.make(payload.password)
        await user.save()
        return MessageResponse(message="Password has been reset successfully.")

    @route.post(
        "/change-password",
        response_model=MessageResponse,
        summary="Change password (authenticated)",
        operation_id="auth_change_password",
    )
    async def change_password(
        self,
        request: Request,
        payload: ChangePasswordRequest,
        hasher: HasherContract = Inject(HasherContract),
    ) -> MessageResponse:
        auth_context = request.state.auth_context
        subject = auth_context.sub

        user = await User.query().where(User.email == subject).order_by(User.id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not hasher.check(payload.current_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        user.password = hasher.make(payload.new_password)
        await user.save()
        return MessageResponse(message="Password changed successfully.")

    @route.post(
        "/verify-email/send",
        response_model=MessageResponse,
        summary="Send email verification token (authenticated)",
        operation_id="auth_send_verification",
    )
    async def send_verification(
        self,
        request: Request,
        reset_service: ResetTokenService = Inject(ResetTokenService),
    ) -> MessageResponse:
        auth_context = request.state.auth_context
        subject = auth_context.sub

        user = await User.query().where(User.email == subject).order_by(User.id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.email_verified_at is not None:
            return MessageResponse(message="Email is already verified.")

        token = reset_service.create_verification_token(str(user.id))
        logger.info(
            "Verification token generated for user_id=%s token=%s",
            user.id,
            token,
        )

        return MessageResponse(message="Verification email has been sent.")

    @route.post(
        "/verify-email",
        response_model=MessageResponse,
        summary="Verify email address using a verification token",
        operation_id="auth_verify_email",
    )
    async def verify_email(
        self,
        payload: VerifyEmailRequest,
        reset_service: ResetTokenService = Inject(ResetTokenService),
    ) -> MessageResponse:
        user = (
            await User.query()
            .where(User.email == payload.email)
            .order_by(User.id)
            .first()
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token",
            )

        if user.email_verified_at is not None:
            return MessageResponse(message="Email is already verified.")

        try:
            reset_service.validate_verification_token(payload.token, str(user.id))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        user.email_verified_at = datetime.now(UTC)
        await user.save()
        return MessageResponse(message="Email verified successfully.")

    @route.post(
        "/logout",
        response_model=MessageResponse,
        summary="Logout (invalidate session)",
        operation_id="auth_logout",
    )
    async def logout(
        self,
        request: Request,
    ) -> MessageResponse:
        _ = request.state.auth_context
        return MessageResponse(message="Successfully logged out.")
