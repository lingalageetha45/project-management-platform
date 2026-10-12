from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from app.models.task import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None


class TaskCreate(TaskBase):
    project_id: int
    assignee_id: Optional[int] = None
    status: TaskStatus = TaskStatus.BACKLOG


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    assignee_id: Optional[int] = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskAssign(BaseModel):
    assignee_id: Optional[int] = None


class TaskOut(TaskBase):
    id: int
    project_id: int
    assignee_id: Optional[int] = None
    reporter_id: int
    status: TaskStatus
    actual_hours: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskDependencyCreate(BaseModel):
    depends_on_id: int
