from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    get_current_user,
    get_project_with_access,
)
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberRoleUpdate,
    ProjectOut,
    ProjectUpdate,
)
from app.services.project_service import ProjectService


router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


@router.post(
    "",
    response_model=SuccessResponse,
)
def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a project.

    ProjectService enforces:
    - organization membership
    - organization admin/project manager role
    - tenant isolation
    """

    project = ProjectService.create(
        db,
        data.model_dump(),
        current_user,
    )

    return SuccessResponse(
        message="Project created successfully.",
        data=ProjectOut.model_validate(project),
    )


@router.get(
    "",
    response_model=SuccessResponse,
)
def list_projects(
    organization_id: Optional[int] = Query(
        default=None,
        gt=0,
        description="Filter projects by organization.",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List projects accessible to the current user.
    """

    projects = ProjectService.list_for_user(
        db,
        current_user,
        organization_id,
    )

    return SuccessResponse(
        data=[
            ProjectOut.model_validate(project)
            for project in projects
        ]
    )


@router.get(
    "/{project_id}",
    response_model=SuccessResponse,
)
def get_project(
    project: Project = Depends(get_project_with_access),
):
    """
    Get a project.

    Access is enforced through get_project_with_access.
    """

    return SuccessResponse(
        data=ProjectOut.model_validate(project)
    )


@router.patch(
    "/{project_id}",
    response_model=SuccessResponse,
)
def update_project(
    data: ProjectUpdate,
    project: Project = Depends(get_project_with_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update project details or status.
    """

    updated_project = ProjectService.update(
        db,
        project,
        data.model_dump(exclude_unset=True),
        current_user,
    )

    return SuccessResponse(
        message="Project updated successfully.",
        data=ProjectOut.model_validate(updated_project),
    )


@router.post(
    "/{project_id}/members",
    response_model=SuccessResponse,
)
def add_project_member(
    data: ProjectMemberAdd,
    project: Project = Depends(get_project_with_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a user to a project.
    """

    project_member = ProjectService.add_member(
        db,
        project,
        data.user_id,
        data.role,
        current_user,
    )

    return SuccessResponse(
        message="Member added to project successfully.",
        data={
            "id": project_member.id,
            "project_id": project_member.project_id,
            "user_id": project_member.user_id,
            "role": project_member.role,
        },
    )


@router.delete(
    "/{project_id}/members/{user_id}",
    response_model=SuccessResponse,
)
def remove_project_member(
    user_id: int,
    project: Project = Depends(get_project_with_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a user from a project.

    The project owner cannot be removed.
    """

    ProjectService.remove_member(
        db,
        project,
        user_id,
        current_user,
    )

    return SuccessResponse(
        message="Member removed from project successfully.",
    )


@router.patch(
    "/{project_id}/members/{user_id}/role",
    response_model=SuccessResponse,
)
def change_project_member_role(
    user_id: int,
    data: ProjectMemberRoleUpdate,
    project: Project = Depends(get_project_with_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change a project member's role.
    """

    project_member = ProjectService.change_member_role(
        db,
        project,
        user_id,
        data.role,
        current_user,
    )

    return SuccessResponse(
        message="Project member role updated successfully.",
        data={
            "id": project_member.id,
            "project_id": project_member.project_id,
            "user_id": project_member.user_id,
            "role": project_member.role,
        },
    )