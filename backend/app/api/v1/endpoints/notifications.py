from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.services.notification_service import NotificationService


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get("", response_model=SuccessResponse)
def list_notifications(
    unread_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = NotificationService.list_for_user(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )

    unread_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .count()
    )

    return SuccessResponse(
        message="Notifications retrieved successfully.",
        data={
            "items": [
                {
                    "id": item.id,
                    "type": item.type,
                    "title": item.title,
                    "message": item.message,
                    "is_read": item.is_read,
                    "entity_type": item.entity_type,
                    "entity_id": item.entity_id,
                    "created_at": item.created_at.isoformat(),
                }
                for item in items
            ],
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "page_size": page_size,
        },
    )


@router.patch("/{notification_id}/read", response_model=SuccessResponse)
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    NotificationService.mark_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
    )

    return SuccessResponse(
        message="Notification marked as read."
    )


@router.patch("/read-all", response_model=SuccessResponse)
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated_count = NotificationService.mark_all_read(
        db=db,
        user_id=current_user.id,
    )

    return SuccessResponse(
        message="Notifications marked as read.",
        data={"updated_count": updated_count},
    )
