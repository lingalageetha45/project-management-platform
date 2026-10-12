from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    get_current_user,
    get_project_with_access,
    get_task_with_access,
)
from app.db.session import get_db
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.task import (
    TaskAssign,
    TaskCreate,
    TaskDependencyCreate,
    TaskOut,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.task_service import TaskService


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)


@router.post("", response_model=SuccessResponse)
def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = TaskService.create(
        db=db,
        data=data.model_dump(),
        reporter=current_user,
    )

    return SuccessResponse(
        message="Task created successfully.",
        data=TaskOut.model_validate(task),
    )


@router.get("", response_model=SuccessResponse)
def list_tasks(
    project_id: Optional[int] = Query(default=None, gt=0),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee_id: Optional[int] = Query(default=None, gt=0),
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = TaskService.list_filtered(
        db=db,
        user=current_user,
        project_id=project_id,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        search=search,
        page=page,
        page_size=page_size,
    )

    return SuccessResponse(
        data={
            "items": [
                TaskOut.model_validate(task)
                for task in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (
                (total + page_size - 1) // page_size
            ),
        }
    )


@router.get("/{task_id}", response_model=SuccessResponse)
def get_task(
    task: Task = Depends(get_task_with_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorized_task = TaskService.get_for_user(
        db=db,
        task_id=task.id,
        user=current_user,
    )

    return SuccessResponse(
        data=TaskOut.model_validate(authorized_task),
    )


@router.patch("/{task_id}", response_model=SuccessResponse)
def update_task(
    data: TaskUpdate,
    task: Task = Depends(get_task_with_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated_task = TaskService.update(
        db=db,
        task=task,
        data=data.model_dump(exclude_unset=True),
        actor=current_user,
    )

    return SuccessResponse(
        message="Task updated successfully.",
        data=TaskOut.model_validate(updated_task),
    )


@router.patch(
    "/{task_id}/status",
    response_model=SuccessResponse,
)
def change_status(
    data: TaskStatusUpdate,
    task: Task = Depends(get_task_with_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated_task = TaskService.change_status(
        db=db,
        task=task,
        new_status=data.status,
        actor=current_user,
    )

    return SuccessResponse(
        message="Task status updated successfully.",
        data=TaskOut.model_validate(updated_task),
    )


@router.patch(
    "/{task_id}/assign",
    response_model=SuccessResponse,
)
def assign_task(
    data: TaskAssign,
    task: Task = Depends(get_task_with_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated_task = TaskService.assign(
        db=db,
        task=task,
        assignee_id=data.assignee_id,
        actor=current_user,
    )

    return SuccessResponse(
        message="Task assignment updated successfully.",
        data=TaskOut.model_validate(updated_task),
    )


@router.post(
    "/{task_id}/dependencies",
    response_model=SuccessResponse,
)
def add_dependency(
    data: TaskDependencyCreate,
    task: Task = Depends(get_task_with_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dependency = TaskService.add_dependency(
        db=db,
        task=task,
        depends_on_id=data.depends_on_id,
        actor=current_user,
    )

    return SuccessResponse(
        message="Task dependency added successfully.",
        data={
            "id": dependency.id,
            "task_id": dependency.task_id,
            "depends_on_id": dependency.depends_on_id,
        },
    )


@router.delete(
    "/{task_id}/dependencies/{depends_on_id}",
    response_model=SuccessResponse,
)
def remove_dependency(
    depends_on_id: int,
    task: Task = Depends(get_task_with_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    TaskService.remove_dependency(
        db=db,
        task=task,
        depends_on_id=depends_on_id,
        actor=current_user,
    )

    return SuccessResponse(
        message="Task dependency removed successfully.",
    )


@router.delete(
    "/{task_id}",
    response_model=SuccessResponse,
)
def delete_task(
    task: Task = Depends(get_task_with_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    TaskService.delete(
        db=db,
        task=task,
        actor=current_user,
    )

    return SuccessResponse(
        message="Task deleted successfully.",
    )