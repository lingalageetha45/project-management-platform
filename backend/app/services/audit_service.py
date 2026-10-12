from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_action(
    db: Session,
    *,
    user_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> AuditLog:
    """
    Add an audit entry to the current database transaction.

    The caller is responsible for committing the transaction.
    This allows the audit entry and the related business change
    to be committed together.
    """
    entry = AuditLog(
        user_id=user_id,
        organization_id=organization_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_=metadata,
    )

    db.add(entry)
    return entry
