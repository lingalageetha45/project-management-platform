from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    ForeignKey,
    Float,
    Enum as SAEnum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin
import enum


class TaskStatus(str, enum.Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


VALID_TASK_TRANSITIONS = {
    TaskStatus.BACKLOG: {
        TaskStatus.TODO,
        TaskStatus.CANCELLED,
    },
    TaskStatus.TODO: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.BACKLOG,
        TaskStatus.CANCELLED,
    },
    TaskStatus.IN_PROGRESS: {
        TaskStatus.REVIEW,
        TaskStatus.BLOCKED,
        TaskStatus.TODO,
        TaskStatus.CANCELLED,
    },
    TaskStatus.BLOCKED: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.TODO,
        TaskStatus.CANCELLED,
    },
    TaskStatus.REVIEW: {
        TaskStatus.DONE,
        TaskStatus.IN_PROGRESS,
        TaskStatus.CANCELLED,
    },
    TaskStatus.DONE: {
        TaskStatus.TODO,
    },
    TaskStatus.CANCELLED: {
        TaskStatus.BACKLOG,
        TaskStatus.TODO,
    },
}


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    title = Column(
        String(255),
        nullable=False,
        index=True,
    )

    description = Column(
        Text,
        nullable=True,
    )

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assignee_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    reporter_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    priority = Column(
        SAEnum(
            TaskPriority,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
            name="taskpriority",
        ),
        default=TaskPriority.MEDIUM,
        nullable=False,
    )

    status = Column(
        SAEnum(
            TaskStatus,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
            name="taskstatus",
        ),
        default=TaskStatus.BACKLOG,
        nullable=False,
        index=True,
    )

    due_date = Column(
        Date,
        nullable=True,
    )

    estimated_hours = Column(
        Float,
        nullable=True,
    )

    actual_hours = Column(
        Float,
        nullable=True,
    )

    project = relationship(
        "Project",
        back_populates="tasks",
    )

    assignee = relationship(
        "User",
        foreign_keys=[assignee_id],
        back_populates="assigned_tasks",
    )

    reporter = relationship(
        "User",
        foreign_keys=[reporter_id],
        back_populates="reported_tasks",
    )

    comments = relationship(
        "Comment",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    attachments = relationship(
        "Attachment",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    dependents = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_id",
        back_populates="depends_on",
        cascade="all, delete-orphan",
    )


class TaskDependency(Base, TimestampMixin):
    __tablename__ = "task_dependencies"

    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "depends_on_id",
            name="uq_task_dependency",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    depends_on_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    task = relationship(
        "Task",
        foreign_keys=[task_id],
        back_populates="dependencies",
    )

    depends_on = relationship(
        "Task",
        foreign_keys=[depends_on_id],
        back_populates="dependents",
    )