
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.comment import (
    CommentCreate,
    CommentOut,
    CommentUpdate,
)
from app.schemas.common import SuccessResponse
from app.services.comment_service import CommentService


router = APIRouter(
    prefix="/comments",
    tags=["Comments"],
)


@router.post("", response_model=SuccessResponse)
def create_comment(
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = CommentService.create(
        db=db,
        user=current_user,
        content=data.content,
        project_id=data.project_id,
        task_id=data.task_id,
    )

    return SuccessResponse(
        message="Comment created successfully.",
        data=CommentOut.model_validate(comment),
    )


@router.get("", response_model=SuccessResponse)
def list_comments(
    project_id: int | None = Query(default=None, gt=0),
    task_id: int | None = Query(default=None, gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comments = CommentService.list_for_target(
        db=db,
        user=current_user,
        project_id=project_id,
        task_id=task_id,
    )

    return SuccessResponse(
        message="Comments retrieved successfully.",
        data=[
            CommentOut.model_validate(comment)
            for comment in comments
        ],
    )


@router.patch("/{comment_id}", response_model=SuccessResponse)
def update_comment(
    comment_id: int,
    data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = CommentService.update(
        db=db,
        user=current_user,
        comment_id=comment_id,
        content=data.content,
    )

    return SuccessResponse(
        message="Comment updated successfully.",
        data=CommentOut.model_validate(comment),
    )


@router.delete("/{comment_id}", response_model=SuccessResponse)
def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    CommentService.delete(
        db=db,
        user=current_user,
        comment_id=comment_id,
    )

    return SuccessResponse(
        message="Comment deleted successfully.",
    )