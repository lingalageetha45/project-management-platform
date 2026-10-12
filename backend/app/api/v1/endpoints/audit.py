from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    get_current_user,
    require_org_role,
)
from app.db.session import get_db
from app.models.organization import OrganizationMember
from app.models.user import SystemRole, User
from app.schemas.audit import AuditLogOut
from app.schemas.common import PaginatedResponse
from app.services.audit_query_service import AuditQueryService


router = APIRouter(
    prefix="/organizations/{org_id}/audit-logs",
    tags=["Audit Logs"],
)


AUDIT_ROLES = [
    SystemRole.ORGANIZATION_ADMIN.value,
]


@router.get("", response_model=PaginatedResponse[AuditLogOut])
def list_audit_logs(
    org_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None, min_length=1),
    membership: OrganizationMember = Depends(
        require_org_role(AUDIT_ROLES)
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = AuditQueryService.list_for_organization(
        db=db,
        organization_id=org_id,
        page=page,
        page_size=page_size,
        action=action,
    )

    return PaginatedResponse[AuditLogOut](
        data=[
            AuditLogOut.model_validate(entry)
            for entry in result["data"]
        ],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )
