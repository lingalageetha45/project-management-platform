from typing import List, Optional
import re

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.organization import Organization, OrganizationMember
from app.models.user import SystemRole, User
from app.services.audit_service import log_action


def slugify(name: str) -> str:
    value = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-")[:90]


class OrganizationService:

    MANAGEABLE_ROLES = {
        SystemRole.ORGANIZATION_ADMIN.value,
        SystemRole.PROJECT_MANAGER.value,
        SystemRole.TEAM_MEMBER.value,
        SystemRole.VIEWER.value,
    }

    @staticmethod
    def create(
        db: Session,
        name: str,
        description: Optional[str],
        owner: User,
        slug: Optional[str] = None,
    ) -> Organization:

        name = name.strip()

        if not name:
            raise ValidationError(
                "Organization name is required.",
                code="INVALID_ORGANIZATION_NAME",
            )

        final_slug = (
            slugify(slug)
            if slug
            else slugify(name)
        )

        if not final_slug:
            raise ValidationError(
                "A valid organization slug could not be generated.",
                code="INVALID_ORGANIZATION_SLUG",
            )

        existing = (
            db.query(Organization)
            .filter(Organization.slug == final_slug)
            .first()
        )

        if existing:
            final_slug = f"{final_slug}-{owner.id}"

            existing_slug = (
                db.query(Organization)
                .filter(Organization.slug == final_slug)
                .first()
            )

            if existing_slug:
                raise ConflictError(
                    "Organization slug already exists.",
                    code="ORGANIZATION_SLUG_EXISTS",
                )

        organization = Organization(
            name=name,
            slug=final_slug,
            description=description,
            is_active=True,
        )

        db.add(organization)
        db.flush()

        owner_membership = OrganizationMember(
            organization_id=organization.id,
            user_id=owner.id,
            role=SystemRole.ORGANIZATION_ADMIN.value,
            is_active=True,
        )

        db.add(owner_membership)
        db.commit()
        db.refresh(organization)

        log_action(
            db,
            user_id=owner.id,
            organization_id=organization.id,
            action="ORGANIZATION_CREATED",
            entity_type="organization",
            entity_id=organization.id,
        )

        return organization

    @staticmethod
    def get(
        db: Session,
        org_id: int,
    ) -> Organization:

        organization = (
            db.query(Organization)
            .filter(Organization.id == org_id)
            .first()
        )

        if not organization:
            raise NotFoundError("Organization")

        return organization

    @staticmethod
    def list_for_user(
        db: Session,
        user: User,
    ) -> List[Organization]:

        if user.is_superuser:
            return (
                db.query(Organization)
                .filter(Organization.is_active.is_(True))
                .all()
            )

        memberships = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == user.id,
                OrganizationMember.is_active.is_(True),
            )
            .all()
        )

        return [
            membership.organization
            for membership in memberships
            if membership.organization.is_active
        ]

    @staticmethod
    def add_member(
        db: Session,
        org_id: int,
        email: str,
        role: str,
        actor: User,
    ) -> OrganizationMember:

        organization = OrganizationService.get(
            db,
            org_id,
        )

        if not organization.is_active:
            raise ValidationError(
                "Cannot add members to an inactive organization.",
                code="ORGANIZATION_INACTIVE",
            )

        if role not in OrganizationService.MANAGEABLE_ROLES:
            raise ValidationError(
                "Invalid organization role.",
                code="INVALID_ORGANIZATION_ROLE",
            )

        user = (
            db.query(User)
            .filter(
                User.email == email.lower().strip()
            )
            .first()
        )

        if not user:
            raise NotFoundError("User")

        if not user.is_active:
            raise ValidationError(
                "Inactive users cannot be added to an organization.",
                code="USER_INACTIVE",
            )

        existing = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user.id,
            )
            .first()
        )

        if existing:
            raise ConflictError(
                "User is already a member of this organization.",
                code="DUPLICATE_MEMBERSHIP",
            )

        member = OrganizationMember(
            organization_id=org_id,
            user_id=user.id,
            role=role,
            is_active=True,
        )

        db.add(member)
        db.commit()
        db.refresh(member)

        log_action(
            db,
            user_id=actor.id,
            organization_id=org_id,
            action="MEMBER_ADDED",
            entity_type="user",
            entity_id=user.id,
            metadata={"role": role},
        )

        return member

    @staticmethod
    def remove_member(
        db: Session,
        org_id: int,
        user_id: int,
        actor: User,
    ) -> None:

        member = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
            .first()
        )

        if not member:
            raise NotFoundError("Membership")

        if (
            member.role == SystemRole.ORGANIZATION_ADMIN.value
            and member.is_active
        ):
            admin_count = (
                db.query(OrganizationMember)
                .filter(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.role
                    == SystemRole.ORGANIZATION_ADMIN.value,
                    OrganizationMember.is_active.is_(True),
                )
                .count()
            )

            if admin_count <= 1:
                raise ValidationError(
                    "The organization must have at least one active Organization Admin.",
                    code="LAST_ORGANIZATION_ADMIN",
                )

        db.delete(member)
        db.commit()

        log_action(
            db,
            user_id=actor.id,
            organization_id=org_id,
            action="MEMBER_REMOVED",
            entity_type="user",
            entity_id=user_id,
        )

    @staticmethod
    def change_role(
        db: Session,
        org_id: int,
        user_id: int,
        new_role: str,
        actor: User,
    ) -> OrganizationMember:

        if new_role not in OrganizationService.MANAGEABLE_ROLES:
            raise ValidationError(
                "Invalid organization role.",
                code="INVALID_ORGANIZATION_ROLE",
            )

        member = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
            .first()
        )

        if not member:
            raise NotFoundError("Membership")

        if member.role == new_role:
            return member

        if (
            member.role == SystemRole.ORGANIZATION_ADMIN.value
            and new_role != SystemRole.ORGANIZATION_ADMIN.value
            and member.is_active
        ):
            admin_count = (
                db.query(OrganizationMember)
                .filter(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.role
                    == SystemRole.ORGANIZATION_ADMIN.value,
                    OrganizationMember.is_active.is_(True),
                )
                .count()
            )

            if admin_count <= 1:
                raise ValidationError(
                    "The organization must have at least one active Organization Admin.",
                    code="LAST_ORGANIZATION_ADMIN",
                )

        member.role = new_role

        db.commit()
        db.refresh(member)

        log_action(
            db,
            user_id=actor.id,
            organization_id=org_id,
            action="MEMBER_ROLE_CHANGED",
            entity_type="user",
            entity_id=user_id,
            metadata={"new_role": new_role},
        )

        return member

    @staticmethod
    def set_member_active_status(
        db: Session,
        org_id: int,
        user_id: int,
        is_active: bool,
        actor: User,
    ) -> OrganizationMember:
        """
        Activate or deactivate an organization membership.

        Deactivating a user here only removes their access to this
        organization. It does not deactivate the global User account.

        The organization must always retain at least one active
        Organization Admin.
        """

        organization = OrganizationService.get(
            db,
            org_id,
        )

        if not organization.is_active:
            raise ValidationError(
                "Cannot change membership status in an inactive organization.",
                code="ORGANIZATION_INACTIVE",
            )

        member = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
            .first()
        )

        if not member:
            raise NotFoundError("Membership")

        if member.is_active == is_active:
            status_text = "active" if is_active else "inactive"

            raise ConflictError(
                f"Membership is already {status_text}.",
                code="MEMBERSHIP_STATUS_UNCHANGED",
            )

        if (
            not is_active
            and member.role == SystemRole.ORGANIZATION_ADMIN.value
        ):
            active_admin_count = (
                db.query(OrganizationMember)
                .filter(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.role
                    == SystemRole.ORGANIZATION_ADMIN.value,
                    OrganizationMember.is_active.is_(True),
                )
                .count()
            )

            if active_admin_count <= 1:
                raise ValidationError(
                    "The organization must have at least one active Organization Admin.",
                    code="LAST_ORGANIZATION_ADMIN",
                )

        member.is_active = is_active

        db.commit()
        db.refresh(member)

        log_action(
            db,
            user_id=actor.id,
            organization_id=org_id,
            action=(
                "MEMBER_ACTIVATED"
                if is_active
                else "MEMBER_DEACTIVATED"
            ),
            entity_type="user",
            entity_id=user_id,
            metadata={
                "is_active": is_active,
            },
        )

        return member