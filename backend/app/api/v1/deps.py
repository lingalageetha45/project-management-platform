from typing import List, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccessDeniedError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.security import verify_token
from app.db.session import get_db
from app.models.organization import Organization, OrganizationMember
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.models.user import SystemRole, User


security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate the current user using a valid access token."""

    if not credentials:
        raise UnauthorizedError("Authentication required.")

    user_id = verify_token(
        credentials.credentials,
        expected_type="access",
    )

    if not user_id:
        raise UnauthorizedError("Invalid or expired access token.")

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise UnauthorizedError("Invalid access token.")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise UnauthorizedError("User not found.")

    if not user.is_active:
        raise UnauthorizedError("Account is inactive.")

    return user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the authenticated user to be a system super admin."""

    if not current_user.is_superuser:
        raise AccessDeniedError("Super admin privileges required.")

    return current_user


def get_user_org_membership(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationMember:
    """Return an active organization membership."""

    organization = (
        db.query(Organization)
        .filter(
            Organization.id == org_id,
            Organization.is_active.is_(True),
        )
        .first()
    )

    if not organization:
        raise NotFoundError("Active organization")

    if current_user.is_superuser:
        return OrganizationMember(
            organization_id=org_id,
            user_id=current_user.id,
            role=SystemRole.SUPER_ADMIN.value,
            is_active=True,
        )

    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active.is_(True),
        )
        .first()
    )

    if not membership:
        raise AccessDeniedError(
            "You do not belong to this organization."
        )

    return membership


def require_org_role(allowed_roles: List[str]):
    """Require one of the allowed organization-level roles."""

    def checker(
        membership: OrganizationMember = Depends(
            get_user_org_membership
        ),
    ) -> OrganizationMember:
        if (
            membership.role not in allowed_roles
            and membership.role != SystemRole.SUPER_ADMIN.value
        ):
            raise AccessDeniedError(
                f"Required roles: {', '.join(allowed_roles)}"
            )

        return membership

    return checker


def get_project_with_access(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    """
    Enforce organization and project-level access.

    Super admins can access any existing project.
    Organization admins can access projects in their active organization.
    Other users need active organization membership and project membership.
    """

    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

    if not project:
        raise NotFoundError("Project")

    if current_user.is_superuser:
        return project

    organization = (
        db.query(Organization)
        .filter(
            Organization.id == project.organization_id,
            Organization.is_active.is_(True),
        )
        .first()
    )

    if not organization:
        raise NotFoundError("Active organization")

    organization_membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == project.organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active.is_(True),
        )
        .first()
    )

    if not organization_membership:
        raise AccessDeniedError(
            "You do not have access to this project."
        )

    # Organization admins can access projects in their own organization.
    if (
        organization_membership.role
        == SystemRole.ORGANIZATION_ADMIN.value
    ):
        return project

    project_membership = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == current_user.id,
        )
        .first()
    )

    if not project_membership:
        raise AccessDeniedError(
            "You are not a member of this project."
        )

    return project


def get_task_with_access(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    """Enforce task access through its parent project."""

    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if not task:
        raise NotFoundError("Task")

    get_project_with_access(
        project_id=task.project_id,
        current_user=current_user,
        db=db,
    )

    return task