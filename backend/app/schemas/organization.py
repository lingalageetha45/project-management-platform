from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from app.models.user import SystemRole
from app.schemas.user import UserOut


MANAGEABLE_ORGANIZATION_ROLES = {
    SystemRole.ORGANIZATION_ADMIN.value,
    SystemRole.PROJECT_MANAGER.value,
    SystemRole.TEAM_MEMBER.value,
    SystemRole.VIEWER.value,
}


class OrganizationBase(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError(
                "Organization name must contain at least 2 characters."
            )

        return value

    @field_validator("description")
    @classmethod
    def validate_description(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        return value


class OrganizationCreate(OrganizationBase):
    slug: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=90,
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None

        value = value.strip().lower()

        if not value:
            return None

        allowed = set(
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789-_"
        )

        if any(character not in allowed for character in value):
            raise ValueError(
                "Slug may contain only lowercase letters, "
                "numbers, hyphens, and underscores."
            )

        return value


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=255,
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None

        value = value.strip()

        if len(value) < 2:
            raise ValueError(
                "Organization name must contain at least 2 characters."
            )

        return value

    @field_validator("description")
    @classmethod
    def validate_description(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        return value


class OrganizationOut(OrganizationBase):
    id: int
    slug: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class MemberAdd(BaseModel):
    email: EmailStr
    role: str = Field(
        default=SystemRole.TEAM_MEMBER.value,
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in MANAGEABLE_ORGANIZATION_ROLES:
            raise ValueError(
                "Invalid organization member role."
            )

        return value


class MemberRoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in MANAGEABLE_ORGANIZATION_ROLES:
            raise ValueError(
                "Invalid organization member role."
            )

        return value


class OrganizationMemberOut(BaseModel):
    id: int
    user: UserOut
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )