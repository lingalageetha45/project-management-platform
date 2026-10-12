from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    get_current_user,
    get_user_org_membership,
    require_org_role,
)
from app.db.session import get_db
from app.models.organization import OrganizationMember
from app.models.user import SystemRole, User
from app.schemas.common import SuccessResponse
from app.schemas.organization import (
    MemberAdd,
    MemberRoleUpdate,
    OrganizationCreate,
    OrganizationOut,
    OrganizationUpdate,
)
from app.services.organization_service import OrganizationService


router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
)


ORG_ADMIN_ROLES = [
    SystemRole.ORGANIZATION_ADMIN.value,
]


@router.post(
    "",
    response_model=SuccessResponse,
)
def create_organization(
    data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new organization.

    The authenticated user becomes the initial
    organization administrator.
    """

    organization = OrganizationService.create(
        db=db,
        name=data.name,
        description=data.description,
        owner=current_user,
        slug=data.slug,
    )

    return SuccessResponse(
        message="Organization created successfully.",
        data=OrganizationOut.model_validate(organization),
    )


@router.get(
    "",
    response_model=SuccessResponse,
)
def list_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List organizations accessible to the current user.
    """

    organizations = OrganizationService.list_for_user(
        db,
        current_user,
    )

    return SuccessResponse(
        data=[
            OrganizationOut.model_validate(organization)
            for organization in organizations
        ]
    )


@router.get(
    "/{org_id}",
    response_model=SuccessResponse,
)
def get_organization(
    org_id: int,
    membership: OrganizationMember = Depends(
        get_user_org_membership
    ),
    db: Session = Depends(get_db),
):
    """
    Get an organization.

    Access is restricted to active organization members.
    """

    organization = OrganizationService.get(
        db,
        org_id,
    )

    return SuccessResponse(
        data=OrganizationOut.model_validate(organization)
    )


@router.patch(
    "/{org_id}",
    response_model=SuccessResponse,
)
def update_organization(
    org_id: int,
    data: OrganizationUpdate,
    membership: OrganizationMember = Depends(
        require_org_role(ORG_ADMIN_ROLES)
    ),
    db: Session = Depends(get_db),
):
    """
    Update organization details.

    Only Organization Admins and Super Admins can perform
    this operation.
    """

    organization = OrganizationService.get(
        db,
        org_id,
    )

    updates = data.model_dump(
        exclude_unset=True,
    )

    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip()

        setattr(
            organization,
            field,
            value,
        )

    db.commit()
    db.refresh(organization)

    return SuccessResponse(
        message="Organization updated successfully.",
        data=OrganizationOut.model_validate(organization),
    )


@router.post(
    "/{org_id}/members",
    response_model=SuccessResponse,
)
def add_member(
    org_id: int,
    data: MemberAdd,
    membership: OrganizationMember = Depends(
        require_org_role(ORG_ADMIN_ROLES)
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add an existing user to an organization.
    """

    member = OrganizationService.add_member(
        db=db,
        org_id=org_id,
        email=data.email,
        role=data.role,
        actor=current_user,
    )

    return SuccessResponse(
        message="Member added successfully.",
        data={
            "id": member.id,
            "user_id": member.user_id,
            "organization_id": member.organization_id,
            "role": member.role,
            "is_active": member.is_active,
        },
    )


@router.delete(
    "/{org_id}/members/{user_id}",
    response_model=SuccessResponse,
)
def remove_member(
    org_id: int,
    user_id: int,
    membership: OrganizationMember = Depends(
        require_org_role(ORG_ADMIN_ROLES)
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a user from an organization.

    The service prevents removal of the last active
    Organization Admin.
    """

    OrganizationService.remove_member(
        db=db,
        org_id=org_id,
        user_id=user_id,
        actor=current_user,
    )

    return SuccessResponse(
        message="Member removed successfully."
    )


@router.patch(
    "/{org_id}/members/{user_id}/role",
    response_model=SuccessResponse,
)
def change_member_role(
    org_id: int,
    user_id: int,
    data: MemberRoleUpdate,
    membership: OrganizationMember = Depends(
        require_org_role(ORG_ADMIN_ROLES)
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change an organization member's role.
    """

    member = OrganizationService.change_role(
        db=db,
        org_id=org_id,
        user_id=user_id,
        new_role=data.role,
        actor=current_user,
    )

    return SuccessResponse(
        message="Member role updated successfully.",
        data={
            "id": member.id,
            "user_id": member.user_id,
            "organization_id": member.organization_id,
            "role": member.role,
            "is_active": member.is_active,
        },
    )


@router.patch(
    "/{org_id}/members/{user_id}/activate",
    response_model=SuccessResponse,
)
def activate_member(
    org_id: int,
    user_id: int,
    membership: OrganizationMember = Depends(
        require_org_role(ORG_ADMIN_ROLES)
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Activate a user's membership in the organization.

    This changes organization membership status only.
    It does not change the user's global account status.
    """

    member = OrganizationService.set_member_active_status(
        db=db,
        org_id=org_id,
        user_id=user_id,
        is_active=True,
        actor=current_user,
    )

    return SuccessResponse(
        message="Member activated successfully.",
        data={
            "id": member.id,
            "user_id": member.user_id,
            "organization_id": member.organization_id,
            "role": member.role,
            "is_active": member.is_active,
        },
    )


@router.patch(
    "/{org_id}/members/{user_id}/deactivate",
    response_model=SuccessResponse,
)
def deactivate_member(
    org_id: int,
    user_id: int,
    membership: OrganizationMember = Depends(
        require_org_role(ORG_ADMIN_ROLES)
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deactivate a user's membership in the organization.

    The service prevents deactivation of the last active
    Organization Admin.
    """

    member = OrganizationService.set_member_active_status(
        db=db,
        org_id=org_id,
        user_id=user_id,
        is_active=False,
        actor=current_user,
    )

    return SuccessResponse(
        message="Member deactivated successfully.",
        data={
            "id": member.id,
            "user_id": member.user_id,
            "organization_id": member.organization_id,
            "role": member.role,
            "is_active": member.is_active,
        },
    )


@router.get(
    "/{org_id}/members",
    response_model=SuccessResponse,
)
def list_members(
    org_id: int,
    membership: OrganizationMember = Depends(
        get_user_org_membership
    ),
    db: Session = Depends(get_db),
):
    """
    List members of an organization.

    Any active organization member can view the member list.
    """

    members = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_id
        )
        .order_by(OrganizationMember.id.asc())
        .all()
    )

    result = [
        {
            "id": member.id,
            "user": {
                "id": member.user.id,
                "email": member.user.email,
                "full_name": member.user.full_name,
            },
            "role": member.role,
            "is_active": member.is_active,
        }
        for member in members
    ]

    return SuccessResponse(
        data=result
    )