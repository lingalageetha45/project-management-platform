from sqlalchemy import (
    Column,
    Integer,
    String,
    BigInteger,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"

    __table_args__ = (
        CheckConstraint(
            """
            (project_id IS NOT NULL AND task_id IS NULL)
            OR
            (project_id IS NULL AND task_id IS NOT NULL)
            """,
            name="ck_attachment_exactly_one_target",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    filename = Column(
        String(255),
        nullable=False,
    )

    original_filename = Column(
        String(255),
        nullable=False,
    )

    mime_type = Column(
        String(100),
        nullable=False,
    )

    file_size = Column(
        BigInteger,
        nullable=False,
    )

    storage_path = Column(
        String(512),
        nullable=False,
    )

    uploaded_by_id = Column(
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

    uploaded_by = relationship(
        "User",
    )

    project = relationship(
        "Project",
        back_populates="attachments",
    )

    task = relationship(
        "Task",
        back_populates="attachments",
    )