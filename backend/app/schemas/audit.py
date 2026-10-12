from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None = None
    organization_id: int | None = None
    action: str
    entity_type: str | None = None
    entity_id: int | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict | None = Field(
        default=None,
        validation_alias="metadata_",
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
