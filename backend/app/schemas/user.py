from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError("Full name must contain at least 2 characters.")

        return value


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must contain at least 8 characters.")

        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter.")

        if not any(char.islower() for char in value):
            raise ValueError("Password must contain at least one lowercase letter.")

        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one number.")

        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    is_active: Optional[bool] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        value = value.strip()

        if len(value) < 2:
            raise ValueError("Full name must contain at least 2 characters.")

        return value


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must contain at least 8 characters.")

        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter.")

        if not any(char.islower() for char in value):
            raise ValueError("Password must contain at least one lowercase letter.")

        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one number.")

        return value


class UserOut(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None