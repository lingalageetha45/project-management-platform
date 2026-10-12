from datetime import date, datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.project import ProjectStatus
from app.models.user import SystemRole


PROJECT_MEMBER_ROLES = {
    SystemRole.PROJECT_MANAGER.value,
    SystemRole.TEAM_MEMBER.value,
    SystemRole.VIEWER.value,
}


class ProjectBase(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
    )

    description: Optional[str] = Field(
        default=None,
        max_length=5000,
    )

    start_date: Optional[date] = None

    due_date: Optional[date] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Project name cannot be empty.")

        return value

    @field_validator("description")
    @classmethod
    def validate_description(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is not None:
            value = value.strip()

            if not value:
                return None

        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.start_date is not None
            and self.due_date is not None
            and self.due_date < self.start_date
        ):
            raise ValueError(
                "Due date cannot be earlier than start date."
            )

        return self


class ProjectCreate(ProjectBase):
    organization_id: int = Field(
        ...,
        gt=0,
    )

    status: ProjectStatus = ProjectStatus.PLANNING


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    description: Optional[str] = Field(
        default=None,
        max_length=5000,
    )

    status: Optional[ProjectStatus] = None

    start_date: Optional[date] = None

    due_date: Optional[date] = None

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is not None:
            value = value.strip()

            if not value:
                raise ValueError(
                    "Project name cannot be empty."
                )

        return value

    @field_validator("description")
    @classmethod
    def validate_description(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is not None:
            value = value.strip()

            if not value:
                return None

        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.start_date is not None
            and self.due_date is not None
            and self.due_date < self.start_date
        ):
            raise ValueError(
                "Due date cannot be earlier than start date."
            )

        return self


class ProjectOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    name: str
    description: Optional[str]
    organization_id: int
    owner_id: int
    status: ProjectStatus
    start_date: Optional[date]
    due_date: Optional[date]
    created_at: datetime
    updated_at: datetime


class ProjectMemberAdd(BaseModel):
    user_id: int = Field(
        ...,
        gt=0,
    )

    role: str = Field(
        default=SystemRole.TEAM_MEMBER.value,
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in PROJECT_MEMBER_ROLES:
            raise ValueError(
                "Invalid project member role."
            )

        return value


class ProjectMemberRoleUpdate(BaseModel):
    role: str = Field(
        ...,
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in PROJECT_MEMBER_ROLES:
            raise ValueError(
                "Invalid project member role."
            )

        return value