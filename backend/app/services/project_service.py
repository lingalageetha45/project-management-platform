from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.organization import Organization, OrganizationMember
from app.models.project import Project, ProjectMember, ProjectStatus
from app.models.user import SystemRole, User
from app.services.audit_service import log_action


VALID_PROJECT_TRANSITIONS = {
    ProjectStatus.PLANNING: {
        ProjectStatus.ACTIVE,
        ProjectStatus.ARCHIVED,
    },
    ProjectStatus.ACTIVE: {
        ProjectStatus.ON_HOLD,
        ProjectStatus.COMPLETED,
        ProjectStatus.ARCHIVED,
    },
    ProjectStatus.ON_HOLD: {
        ProjectStatus.ACTIVE,
        ProjectStatus.ARCHIVED,
    },
    ProjectStatus.COMPLETED: {
        ProjectStatus.ARCHIVED,
        ProjectStatus.ACTIVE,
    },
    ProjectStatus.ARCHIVED: set(),
}


PROJECT_MANAGEMENT_ROLES = {
    SystemRole.ORGANIZATION_ADMIN.value,
    SystemRole.PROJECT_MANAGER.value,
}

PROJECT_MEMBER_ROLES = {
    SystemRole.PROJECT_MANAGER.value,
    SystemRole.TEAM_MEMBER.value,
    SystemRole.VIEWER.value,
}


class ProjectService:

    @staticmethod
    def _get_org_membership(
        db: Session,
        organization_id: int,
        user_id: int,
    ) -> Optional[OrganizationMember]:
        return (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def _get_project_membership(
        db: Session,
        project_id: int,
        user_id: int,
    ) -> Optional[ProjectMember]:
        return (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
            .first()
        )

    @staticmethod
    def _require_project_management_role(
        membership: OrganizationMember,
        user: User,
    ) -> None:
        if user.is_superuser:
            return

        if membership.role not in PROJECT_MANAGEMENT_ROLES:
            raise AccessDeniedError(
                "You do not have permission to manage this project."
            )

    @staticmethod
    def _require_project_member_management_role(
        db: Session,
        project: Project,
        membership: OrganizationMember,
        user: User,
    ) -> None:
        if user.is_superuser:
            return

        if membership.role == SystemRole.ORGANIZATION_ADMIN.value:
            return

        if membership.role != SystemRole.PROJECT_MANAGER.value:
            raise AccessDeniedError(
                "You do not have permission to manage project members."
            )

        project_membership = ProjectService._get_project_membership(
            db,
            project.id,
            user.id,
        )

        if not project_membership:
            raise AccessDeniedError(
                "You are not a member of this project."
            )

        if project_membership.role != SystemRole.PROJECT_MANAGER.value:
            raise AccessDeniedError(
                "You do not have project-manager permission for this project."
            )

    @staticmethod
    def create(
        db: Session,
        data: dict,
        owner: User,
    ) -> Project:
        organization_id = data["organization_id"]

        # Confirm that the organization exists and is active.
        organization = (
            db.query(Organization)
            .filter(
                Organization.id == organization_id,
                Organization.is_active.is_(True),
            )
            .first()
        )

        if not organization:
            raise NotFoundError("Active organization")

        if not owner.is_superuser:
            membership = ProjectService._get_org_membership(
                db,
                organization_id,
                owner.id,
            )

            if not membership:
                raise AccessDeniedError(
                    "You do not belong to this organization."
                )

            ProjectService._require_project_management_role(
                membership,
                owner,
            )

        project = Project(
            name=data["name"].strip(),
            description=data.get("description"),
            organization_id=organization_id,
            owner_id=owner.id,
            status=data.get("status", ProjectStatus.PLANNING),
            start_date=data.get("start_date"),
            due_date=data.get("due_date"),
        )

        db.add(project)
        db.flush()

        # The creator becomes the project manager.
        project_manager = ProjectMember(
            project_id=project.id,
            user_id=owner.id,
            role=SystemRole.PROJECT_MANAGER.value,
        )

        db.add(project_manager)

        try:
            db.commit()
            db.refresh(project)
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=owner.id,
            organization_id=project.organization_id,
            action="PROJECT_CREATED",
            entity_type="project",
            entity_id=project.id,
        )

        return project

    @staticmethod
    def get(
        db: Session,
        project_id: int,
    ) -> Project:
        project = (
            db.query(Project)
            .filter(Project.id == project_id)
            .first()
        )

        if not project:
            raise NotFoundError("Project")

        return project

    @staticmethod
    def list_for_user(
        db: Session,
        user: User,
        organization_id: Optional[int] = None,
    ) -> List[Project]:
        """List projects authorized for the current user."""

        if user.is_superuser:
            query = db.query(Project)

            if organization_id is not None:
                query = query.filter(
                    Project.organization_id == organization_id
                )

            return query.order_by(Project.created_at.desc()).all()

        membership_query = (
            db.query(OrganizationMember)
            .join(
                Organization,
                Organization.id == OrganizationMember.organization_id,
            )
            .filter(
                OrganizationMember.user_id == user.id,
                OrganizationMember.is_active.is_(True),
                Organization.is_active.is_(True),
            )
        )

        if organization_id is not None:
            membership_query = membership_query.filter(
                OrganizationMember.organization_id == organization_id
            )

        memberships = membership_query.all()

        if not memberships:
            return []

        active_org_ids = {
            membership.organization_id
            for membership in memberships
        }

        admin_org_ids = {
            membership.organization_id
            for membership in memberships
            if membership.role == SystemRole.ORGANIZATION_ADMIN.value
        }

        project_member_ids = (
            db.query(ProjectMember.project_id)
            .filter(ProjectMember.user_id == user.id)
            .subquery()
        )

        query = db.query(Project).filter(
            Project.organization_id.in_(active_org_ids)
        )

        # Organization admins see all projects in their active
        # organizations. Other users see only projects they belong to.
        query = query.filter(
            or_(
                Project.organization_id.in_(admin_org_ids),
                Project.id.in_(project_member_ids),
            )
        )

        return query.order_by(Project.created_at.desc()).all()

    @staticmethod
    def update(
        db: Session,
        project: Project,
        data: dict,
        actor: User,
    ) -> Project:
        if actor.is_superuser:
            membership = None
        else:
            membership = ProjectService._get_org_membership(
                db,
                project.organization_id,
                actor.id,
            )

            if not membership:
                raise AccessDeniedError(
                    "You do not belong to this organization."
                )

            ProjectService._require_project_management_role(
                membership,
                actor,
            )

            if membership.role == SystemRole.PROJECT_MANAGER.value:
                project_membership = ProjectService._get_project_membership(
                    db,
                    project.id,
                    actor.id,
                )

                if not project_membership:
                    raise AccessDeniedError(
                        "You are not a member of this project."
                    )

                if project_membership.role != SystemRole.PROJECT_MANAGER.value:
                    raise AccessDeniedError(
                        "You do not have project-manager permission for this project."
                    )

        if "status" in data and data["status"] is not None:
            new_status = data["status"]

            if new_status != project.status:
                allowed_transitions = VALID_PROJECT_TRANSITIONS.get(
                    project.status,
                    set(),
                )

                if new_status not in allowed_transitions:
                    raise ValidationError(
                        (
                            f"Invalid status transition from "
                            f"{project.status.value} to "
                            f"{new_status.value}"
                        ),
                        code="INVALID_STATUS_TRANSITION",
                    )

        if "name" in data and data["name"] is not None:
            name = data["name"].strip()

            if not name:
                raise ValidationError(
                    "Project name cannot be empty.",
                    code="INVALID_PROJECT_NAME",
                )

            project.name = name

        if "description" in data:
            project.description = data["description"]

        if "status" in data and data["status"] is not None:
            project.status = data["status"]

        if "start_date" in data:
            project.start_date = data["start_date"]

        if "due_date" in data:
            project.due_date = data["due_date"]

        if (
            project.start_date is not None
            and project.due_date is not None
            and project.due_date < project.start_date
        ):
            raise ValidationError(
                "Due date cannot be earlier than start date.",
                code="INVALID_PROJECT_DATES",
            )

        try:
            db.commit()
            db.refresh(project)
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=actor.id,
            organization_id=project.organization_id,
            action="PROJECT_UPDATED",
            entity_type="project",
            entity_id=project.id,
        )

        return project

    @staticmethod
    def add_member(
        db: Session,
        project: Project,
        user_id: int,
        role: str,
        actor: User,
    ) -> ProjectMember:
        if not actor.is_superuser:
            actor_membership = ProjectService._get_org_membership(
                db,
                project.organization_id,
                actor.id,
            )

            if not actor_membership:
                raise AccessDeniedError(
                    "You do not belong to this organization."
                )

            ProjectService._require_project_member_management_role(
                db,
                project,
                actor_membership,
                actor,
            )

        if role not in PROJECT_MEMBER_ROLES:
            raise ValidationError(
                "Invalid project member role.",
                code="INVALID_PROJECT_MEMBER_ROLE",
            )

        target_org_membership = (
            db.query(OrganizationMember)
            .join(
                Organization,
                Organization.id == OrganizationMember.organization_id,
            )
            .filter(
                OrganizationMember.organization_id == project.organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.is_active.is_(True),
                Organization.is_active.is_(True),
            )
            .first()
        )

        if not target_org_membership:
            raise AccessDeniedError(
                "User does not belong to the active project organization."
            )

        target_user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not target_user:
            raise NotFoundError("User")

        if not target_user.is_active:
            raise ValidationError(
                "Inactive users cannot be added to a project.",
                code="INACTIVE_USER",
            )

        existing = ProjectService._get_project_membership(
            db,
            project.id,
            user_id,
        )

        if existing:
            raise ConflictError(
                "User is already a project member.",
                code="DUPLICATE_PROJECT_MEMBERSHIP",
            )

        project_member = ProjectMember(
            project_id=project.id,
            user_id=user_id,
            role=role,
        )

        db.add(project_member)

        try:
            db.commit()
            db.refresh(project_member)
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=actor.id,
            organization_id=project.organization_id,
            action="PROJECT_MEMBER_ADDED",
            entity_type="user",
            entity_id=user_id,
            metadata={
                "project_id": project.id,
                "role": role,
            },
        )

        return project_member

    @staticmethod
    def remove_member(
        db: Session,
        project: Project,
        user_id: int,
        actor: User,
    ) -> None:
        if not actor.is_superuser:
            actor_membership = ProjectService._get_org_membership(
                db,
                project.organization_id,
                actor.id,
            )

            if not actor_membership:
                raise AccessDeniedError(
                    "You do not belong to this organization."
                )

            ProjectService._require_project_member_management_role(
                db,
                project,
                actor_membership,
                actor,
            )

        project_member = ProjectService._get_project_membership(
            db,
            project.id,
            user_id,
        )

        if not project_member:
            raise NotFoundError("Project member")

        if user_id == project.owner_id:
            raise ConflictError(
                "The project owner cannot be removed from the project.",
                code="PROJECT_OWNER_CANNOT_BE_REMOVED",
            )

        db.delete(project_member)

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=actor.id,
            organization_id=project.organization_id,
            action="PROJECT_MEMBER_REMOVED",
            entity_type="user",
            entity_id=user_id,
            metadata={"project_id": project.id},
        )

    @staticmethod
    def change_member_role(
        db: Session,
        project: Project,
        user_id: int,
        role: str,
        actor: User,
    ) -> ProjectMember:
        if not actor.is_superuser:
            actor_membership = ProjectService._get_org_membership(
                db,
                project.organization_id,
                actor.id,
            )

            if not actor_membership:
                raise AccessDeniedError(
                    "You do not belong to this organization."
                )

            ProjectService._require_project_member_management_role(
                db,
                project,
                actor_membership,
                actor,
            )

        if role not in PROJECT_MEMBER_ROLES:
            raise ValidationError(
                "Invalid project member role.",
                code="INVALID_PROJECT_MEMBER_ROLE",
            )

        project_member = ProjectService._get_project_membership(
            db,
            project.id,
            user_id,
        )

        if not project_member:
            raise NotFoundError("Project member")

        if (
            user_id == project.owner_id
            and role != SystemRole.PROJECT_MANAGER.value
        ):
            raise ConflictError(
                "The project owner must remain a project manager.",
                code="PROJECT_OWNER_ROLE_REQUIRED",
            )

        if project_member.role == role:
            raise ConflictError(
                "Project member already has this role.",
                code="PROJECT_MEMBER_ROLE_UNCHANGED",
            )

        old_role = project_member.role
        project_member.role = role

        try:
            db.commit()
            db.refresh(project_member)
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=actor.id,
            organization_id=project.organization_id,
            action="PROJECT_MEMBER_ROLE_CHANGED",
            entity_type="user",
            entity_id=user_id,
            metadata={
                "project_id": project.id,
                "old_role": old_role,
                "new_role": role,
            },
        )

        return project_member