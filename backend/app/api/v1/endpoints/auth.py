from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.user import (
    ChangePassword,
    Token,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.services.auth_service import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


class RefreshTokenRequest:
    pass


@router.post(
    "/register",
    response_model=SuccessResponse,
)
def register(
    data: UserCreate,
    db: Session = Depends(get_db),
):
    user = AuthService.register(db, data)

    return SuccessResponse(
        message="User registered successfully",
        data=UserOut.model_validate(user),
    )


@router.post(
    "/login",
    response_model=Token,
)
def login(
    data: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    return AuthService.login(
        db,
        data.email,
        data.password,
        request,
    )


@router.post(
    "/refresh",
    response_model=Token,
)
def refresh(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    return AuthService.refresh(
        db,
        refresh_token,
    )


@router.post(
    "/logout",
    response_model=SuccessResponse,
)
def logout(
    refresh_token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    AuthService.logout(
        db,
        refresh_token,
        current_user,
    )

    return SuccessResponse(
        message="Logged out successfully",
    )


@router.get(
    "/me",
    response_model=UserOut,
)
def me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.post(
    "/change-password",
    response_model=SuccessResponse,
)
def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    AuthService.change_password(
        db,
        current_user,
        data.current_password,
        data.new_password,
    )

    return SuccessResponse(
        message="Password changed successfully",
    )