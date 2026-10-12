from sqlalchemy import (
    Column,
    Integer,
    Text,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    __table_args__ = (
        CheckConstraint(
            """
            (project_id IS NOT NULL AND task_id IS NULL)
            OR
            (project_id IS NULL AND task_id IS NOT NULL)
            """,
            name="ck_comment_exactly_one_target",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    content = Column(
        Text,
        nullable=False,
    )

    author_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    author = relationship(
        "User",
        back_populates="comments",
    )

    project = relationship(
        "Project",
        back_populates="comments",
    )

    task = relationship(
        "Task",
        back_populates="comments",
    )