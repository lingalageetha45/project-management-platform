from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.audit import AuditLog
from app.models.organization import Organization


class AuditQueryService:
    @staticmethod
    def list_for_organization(
        db: Session,
        organization_id: int,
        page: int = 1,
        page_size: int = 20,
        action: str | None = None,
    ) -> dict:
        organization = (
            db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )

        if organization is None:
            raise NotFoundError("Organization")

        query = db.query(AuditLog).filter(
            AuditLog.organization_id == organization_id
        )

        if action:
            query = query.filter(AuditLog.action == action.strip())

        total = query.count()

        entries = (
            query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "data": entries,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
