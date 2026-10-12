
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.organization import OrganizationMember
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.models.user import User
from app.core.exceptions import (
    AccessDeniedError,
    NotFoundError,
    ValidationError,
)
from app.services.audit_service import log_action


class CommentService:
    @staticmethod
    def _get_project(db: Session, project_id: int) -> Project:
        project = (
            db.query(Project)
            .filter(Project.id == project_id)
            .first()
        )

        if not project:
            raise NotFoundError("Project")

        return project

    @staticmethod
    def _get_task(db: Session, task_id: int) -> Task:
        task = (
            db.query(Task)
            .filter(Task.id == task_id)
            .first()
        )

        if not task:
            raise NotFoundError("Task")

        return task

    @staticmethod
    def _require_project_access(
        db: Session,
        user: User,
        project: Project,
    ) -> None:
        if getattr(user, "is_superuser", False):
            return

        organization_membership = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id
                == project.organization_id,
                OrganizationMember.user_id == user.id,
                OrganizationMember.is_active.is_(True),
            )
            .first()
        )

        if not organization_membership:
            raise AccessDeniedError(
                "You do not have access to this project."
            )

        role = getattr(
            organization_membership.role,
            "value",
            organization_membership.role,
        )

        # Organization administrators can access projects
        # within their organization.
        if role == "organization_admin":
            return

        project_membership = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user.id,
            )
            .first()
        )

        if not project_membership:
            raise AccessDeniedError(
                "You do not have access to this project."
            )

    @classmethod
    def _get_authorized_target(
        cls,
        db: Session,
        user: User,
        *,
        project_id: int | None = None,
        task_id: int | None = None,
    ) -> tuple[Project, int | None, int | None]:
        if (project_id is None) == (task_id is None):
            raise ValidationError(
                "Provide exactly one of project_id or task_id."
            )

        if project_id is not None:
            project = cls._get_project(db, project_id)
            cls._require_project_access(db, user, project)

            return project, project.id, None

        task = cls._get_task(db, task_id)
        project = cls._get_project(db, task.project_id)
        cls._require_project_access(db, user, project)

        return project, None, task.id

    @classmethod
    def list_for_target(
        cls,
        db: Session,
        user: User,
        *,
        project_id: int | None = None,
        task_id: int | None = None,
    ) -> list[Comment]:
        cls._get_authorized_target(
            db,
            user,
            project_id=project_id,
            task_id=task_id,
        )

        query = db.query(Comment)

        if project_id is not None:
            query = query.filter(
                Comment.project_id == project_id
            )
        else:
            query = query.filter(
                Comment.task_id == task_id
            )

        return (
            query.order_by(
                Comment.created_at.asc(),
                Comment.id.asc(),
            )
            .all()
        )

    @classmethod
    def create(
        cls,
        db: Session,
        user: User,
        *,
        content: str,
        project_id: int | None = None,
        task_id: int | None = None,
    ) -> Comment:
        project, target_project_id, target_task_id = (
            cls._get_authorized_target(
                db,
                user,
                project_id=project_id,
                task_id=task_id,
            )
        )

        cleaned_content = content.strip()

        if not cleaned_content:
            raise ValidationError(
                "Comment content cannot be empty."
            )

        comment = Comment(
            content=cleaned_content,
            author_id=user.id,
            project_id=target_project_id,
            task_id=target_task_id,
        )

        try:
            db.add(comment)
            db.commit()
            db.refresh(comment)
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=user.id,
            organization_id=project.organization_id,
            action="COMMENT_CREATED",
            entity_type="comment",
            entity_id=comment.id,
            metadata={
                "project_id": target_project_id,
                "task_id": target_task_id,
            },
        )

        return comment

    @classmethod
    def update(
        cls,
        db: Session,
        user: User,
        comment_id: int,
        *,
        content: str,
    ) -> Comment:
        comment = (
            db.query(Comment)
            .filter(Comment.id == comment_id)
            .first()
        )

        if not comment:
            raise NotFoundError("Comment")

        project, _, _ = cls._get_authorized_target(
            db,
            user,
            project_id=comment.project_id,
            task_id=comment.task_id,
        )

        if (
            not getattr(user, "is_superuser", False)
            and comment.author_id != user.id
        ):
            raise AccessDeniedError(
                "You can only edit your own comments."
            )

        cleaned_content = content.strip()

        if not cleaned_content:
            raise ValidationError(
                "Comment content cannot be empty."
            )

        comment.content = cleaned_content

        try:
            db.commit()
            db.refresh(comment)
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=user.id,
            organization_id=project.organization_id,
            action="COMMENT_UPDATED",
            entity_type="comment",
            entity_id=comment.id,
        )

        return comment

    @classmethod
    def delete(
        cls,
        db: Session,
        user: User,
        comment_id: int,
    ) -> None:
        comment = (
            db.query(Comment)
            .filter(Comment.id == comment_id)
            .first()
        )

        if not comment:
            raise NotFoundError("Comment")

        project, _, _ = cls._get_authorized_target(
            db,
            user,
            project_id=comment.project_id,
            task_id=comment.task_id,
        )

        if (
            not getattr(user, "is_superuser", False)
            and comment.author_id != user.id
        ):
            raise AccessDeniedError(
                "You can only delete your own comments."
            )

        comment_id_for_audit = comment.id

        try:
            db.delete(comment)
            db.commit()
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=user.id,
            organization_id=project.organization_id,
            action="COMMENT_DELETED",
            entity_type="comment",
            entity_id=comment_id_for_audit,
        )