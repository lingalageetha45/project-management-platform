from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.attachment import AttachmentOut
from app.schemas.common import SuccessResponse
from app.services.attachment_service import AttachmentService


router = APIRouter(
    prefix="/attachments",
    tags=["Attachments"],
)


@router.post("", response_model=SuccessResponse)
async def upload_attachment(
    project_id: int | None = Query(default=None, gt=0),
    task_id: int | None = Query(default=None, gt=0),
    upload: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = await AttachmentService.create(
        db=db,
        user=current_user,
        upload=upload,
        project_id=project_id,
        task_id=task_id,
    )

    return SuccessResponse(
        message="Attachment uploaded successfully.",
        data=AttachmentOut.model_validate(attachment),
    )


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = AttachmentService.get_for_user(
        db=db,
        user=current_user,
        attachment_id=attachment_id,
    )

    file_path = Path(attachment.storage_path).resolve()

    if not file_path.is_file():
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Attachment file")

    return FileResponse(
        path=file_path,
        media_type=attachment.mime_type,
        filename=attachment.original_filename,
    )


@router.get("/{attachment_id}", response_model=SuccessResponse)
def get_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = AttachmentService.get_for_user(
        db=db,
        user=current_user,
        attachment_id=attachment_id,
    )

    return SuccessResponse(
        message="Attachment retrieved successfully.",
        data=AttachmentOut.model_validate(attachment),
    )


@router.delete("/{attachment_id}", response_model=SuccessResponse)
def delete_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    AttachmentService.delete(
        db=db,
        user=current_user,
        attachment_id=attachment_id,
    )

    return SuccessResponse(
        message="Attachment deleted successfully.",
    )