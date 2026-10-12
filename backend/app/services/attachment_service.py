
import os
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AccessDeniedError,
    NotFoundError,
    ValidationError,
)
from app.models.attachment import Attachment
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.services.audit_service import log_action


class AttachmentService:
    @staticmethod
    def _get_target(
        db: Session,
        user: User,
        project_id: int | None = None,
        task_id: int | None = None,
    ):
        if (project_id is None) == (task_id is None):
            raise ValidationError(
                "Provide exactly one of project_id or task_id."
            )

        if project_id is not None:
            project = (
                db.query(Project)
                .filter(Project.id == project_id)
                .first()
            )

            if not project:
                raise NotFoundError("Project")

        else:
            task = (
                db.query(Task)
                .filter(Task.id == task_id)
                .first()
            )

            if not task:
                raise NotFoundError("Task")

            project = (
                db.query(Project)
                .filter(Project.id == task.project_id)
                .first()
            )

            if not project:
                raise NotFoundError("Project")

        if not user.is_superuser:
            from app.models.organization import OrganizationMember
            from app.models.project import ProjectMember

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

            project_membership = (
                db.query(ProjectMember)
                .filter(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id == user.id,
                )
                .first()
            )

            is_org_admin = (
                organization_membership is not None
                and organization_membership.role
                == "organization_admin"
            )

            if (
                organization_membership is None
                or (
                    project_membership is None
                    and not is_org_admin
                )
            ):
                raise AccessDeniedError(
                    "You do not have access to this project."
                )

        return project

    @staticmethod
    async def create(
        db: Session,
        user: User,
        upload: UploadFile,
        project_id: int | None = None,
        task_id: int | None = None,
    ) -> Attachment:
        project = AttachmentService._get_target(
            db,
            user,
            project_id=project_id,
            task_id=task_id,
        )

        original_filename = Path(
            upload.filename or "upload"
        ).name

        if not original_filename.strip():
            raise ValidationError("Filename is required.")

        mime_type = upload.content_type or (
            "application/octet-stream"
        )

        if mime_type not in settings.allowed_mime_list:
            raise ValidationError(
                "This file type is not allowed."
            )

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        content = await upload.read(max_bytes + 1)

        if not content:
            raise ValidationError("The uploaded file is empty.")

        if len(content) > max_bytes:
            raise ValidationError(
                f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit."
            )

        safe_name = f"{uuid.uuid4().hex}_{original_filename}"
        upload_dir = Path(settings.UPLOAD_DIR).resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)

        storage_path = (upload_dir / safe_name).resolve()

        if storage_path.parent != upload_dir:
            raise ValidationError("Invalid filename.")

        try:
            with storage_path.open("xb") as file:
                file.write(content)

            attachment = Attachment(
                filename=safe_name,
                original_filename=original_filename,
                mime_type=mime_type,
                file_size=len(content),
                storage_path=str(storage_path),
                uploaded_by_id=user.id,
                project_id=project_id,
                task_id=task_id,
            )

            db.add(attachment)
            db.commit()
            db.refresh(attachment)

        except Exception:
            db.rollback()

            if storage_path.exists():
                storage_path.unlink()

            raise

        log_action(
            db,
            user_id=user.id,
            organization_id=project.organization_id,
            action="ATTACHMENT_CREATED",
            entity_type="attachment",
            entity_id=attachment.id,
            metadata={
                "project_id": project_id,
                "task_id": task_id,
                "filename": original_filename,
                "file_size": len(content),
            },
        )

        return attachment

    @staticmethod
    def get_for_user(
        db: Session,
        user: User,
        attachment_id: int,
    ) -> Attachment:
        attachment = (
            db.query(Attachment)
            .filter(Attachment.id == attachment_id)
            .first()
        )

        if not attachment:
            raise NotFoundError("Attachment")

        AttachmentService._get_target(
            db,
            user,
            project_id=attachment.project_id,
            task_id=attachment.task_id,
        )

        return attachment

    @staticmethod
    def delete(
        db: Session,
        user: User,
        attachment_id: int,
    ) -> None:
        attachment = AttachmentService.get_for_user(
            db,
            user,
            attachment_id,
        )

        if (
            not user.is_superuser
            and attachment.uploaded_by_id != user.id
        ):
            raise AccessDeniedError(
                "You can only delete your own attachments."
            )

        project = None

        if attachment.project_id is not None:
            project = (
                db.query(Project)
                .filter(Project.id == attachment.project_id)
                .first()
            )
        else:
            task = (
                db.query(Task)
                .filter(Task.id == attachment.task_id)
                .first()
            )

            if task:
                project = (
                    db.query(Project)
                    .filter(Project.id == task.project_id)
                    .first()
                )

        attachment_id_for_audit = attachment.id
        storage_path = Path(attachment.storage_path)

        try:
            db.delete(attachment)
            db.commit()
        except Exception:
            db.rollback()
            raise

        if storage_path.is_file():
            storage_path.unlink()

        log_action(
            db,
            user_id=user.id,
            organization_id=(
                project.organization_id if project else None
            ),
            action="ATTACHMENT_DELETED",
            entity_type="attachment",
            entity_id=attachment_id_for_audit,
        )

