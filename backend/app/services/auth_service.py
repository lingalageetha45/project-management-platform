from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.audit_service import log_action


class AuthService:

    @staticmethod
    def register(db: Session, data: UserCreate) -> User:
        email = data.email.lower().strip()

        existing_user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if existing_user:
            raise ConflictError(
                "Email already registered.",
                code="EMAIL_EXISTS",
            )

        user = User(
            email=email,
            full_name=data.full_name.strip(),
            hashed_password=get_password_hash(data.password),
            is_active=True,
            is_superuser=False,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def login(
        db: Session,
        email: str,
        password: str,
        request=None,
    ) -> dict:

        user = (
            db.query(User)
            .filter(User.email == email.lower().strip())
            .first()
        )

        if not user:
            raise UnauthorizedError(
                "Invalid email or password."
            )

        if not verify_password(
            password,
            user.hashed_password,
        ):
            raise UnauthorizedError(
                "Invalid email or password."
            )

        if not user.is_active:
            raise UnauthorizedError(
                "Account is inactive."
            )

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )

        db_token = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=expires_at,
            is_revoked=False,
        )

        db.add(db_token)

        user.last_login = datetime.now(timezone.utc)

        db.commit()

        log_action(
            db,
            user_id=user.id,
            action="LOGIN",
            entity_type="user",
            entity_id=user.id,
            ip_address=(
                request.client.host
                if request and request.client
                else None
            ),
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    @staticmethod
    def refresh(
        db: Session,
        refresh_token: str,
    ) -> dict:

        user_id = verify_token(
            refresh_token,
            expected_type="refresh",
        )

        if not user_id:
            raise UnauthorizedError(
                "Invalid or expired refresh token."
            )

        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            raise UnauthorizedError(
                "Invalid refresh token."
            )

        stored_token = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token == refresh_token,
            )
            .first()
        )

        if not stored_token:
            raise UnauthorizedError(
                "Refresh token not found."
            )

        if stored_token.is_revoked:
            raise UnauthorizedError(
                "Refresh token has already been revoked."
            )

        now = datetime.now(timezone.utc)

        expires_at = stored_token.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc
            )

        if expires_at < now:
            stored_token.is_revoked = True
            db.commit()

            raise UnauthorizedError(
                "Refresh token has expired."
            )

        if stored_token.user_id != user_id:
            raise UnauthorizedError(
                "Invalid refresh token."
            )

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:
            raise UnauthorizedError(
                "User not found."
            )

        if not user.is_active:
            raise UnauthorizedError(
                "Account is inactive."
            )

        # Rotate the refresh token.
        stored_token.is_revoked = True

        new_access_token = create_access_token(user.id)
        new_refresh_token = create_refresh_token(user.id)

        new_expires_at = (
            now
            + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )

        new_token = RefreshToken(
            user_id=user.id,
            token=new_refresh_token,
            expires_at=new_expires_at,
            is_revoked=False,
        )

        db.add(new_token)
        db.commit()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    @staticmethod
    def logout(
        db: Session,
        refresh_token: str,
        user: User,
    ) -> None:

        stored_token = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token == refresh_token,
                RefreshToken.user_id == user.id,
            )
            .first()
        )

        if stored_token:
            stored_token.is_revoked = True
            db.commit()

    @staticmethod
    def change_password(
        db: Session,
        user: User,
        current: str,
        new: str,
    ) -> None:

        if not verify_password(
            current,
            user.hashed_password,
        ):
            raise ValidationError(
                "Current password is incorrect.",
                code="INVALID_PASSWORD",
            )

        if current == new:
            raise ValidationError(
                "New password must be different from the current password.",
                code="PASSWORD_UNCHANGED",
            )

        user.hashed_password = get_password_hash(new)

        # Revoke all existing refresh tokens.
        (
            db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user.id,
                RefreshToken.is_revoked == False,
            )
            .update(
                {
                    RefreshToken.is_revoked: True,
                },
                synchronize_session=False,
            )
        )

        db.commit()