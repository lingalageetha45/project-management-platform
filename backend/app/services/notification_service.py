from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.notification import Notification


class NotificationService:
    @staticmethod
    def create(
        db: Session,
        *,
        user_id: int,
        organization_id: Optional[int] = None,
        type: str,
        title: str,
        message: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        extra_data: Optional[dict] = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            organization_id=organization_id,
            type=type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            extra_data=extra_data,
        )

        try:
            db.add(notification)
            db.commit()
            db.refresh(notification)
        except Exception:
            db.rollback()
            raise

        return notification

    @staticmethod
    def list_for_user(
        db: Session,
        user_id: int,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ):
        query = db.query(Notification).filter(
            Notification.user_id == user_id
        )

        if unread_only:
            query = query.filter(
                Notification.is_read.is_(False)
            )

        total = query.count()

        items = (
            query.order_by(
                Notification.created_at.desc(),
                Notification.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return items, total

    @staticmethod
    def mark_read(
        db: Session,
        notification_id: int,
        user_id: int,
    ) -> Notification:
        notification = (
            db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .first()
        )

        if notification is None:
            raise NotFoundError("Notification")

        if not notification.is_read:
            notification.is_read = True

            try:
                db.commit()
                db.refresh(notification)
            except Exception:
                db.rollback()
                raise

        return notification

    @staticmethod
    def mark_all_read(
        db: Session,
        user_id: int,
    ) -> int:
        try:
            updated_count = (
                db.query(Notification)
                .filter(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
                .update(
                    {"is_read": True},
                    synchronize_session=False,
                )
            )

            db.commit()
            return updated_count
        except Exception:
            db.rollback()
            raise
