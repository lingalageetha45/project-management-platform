
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    project_id: Optional[int] = Field(default=None, gt=0)
    task_id: Optional[int] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_target(self):
        if (self.project_id is None) == (self.task_id is None):
            raise ValueError(
                "Provide exactly one of project_id or task_id."
            )

        if not self.content.strip():
            raise ValueError("Comment content cannot be empty.")

        return self


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)

    @model_validator(mode="after")
    def validate_content(self):
        if not self.content.strip():
            raise ValueError("Comment content cannot be empty.")

        return self


class CommentOut(BaseModel):
    id: int
    content: str
    author_id: int
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)