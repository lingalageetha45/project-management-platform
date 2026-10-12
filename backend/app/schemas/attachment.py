
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentOut(BaseModel):
    id: int
    filename: str
    original_filename: str
    mime_type: str
    file_size: int
    uploaded_by_id: int
    project_id: int | None = None
    task_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
