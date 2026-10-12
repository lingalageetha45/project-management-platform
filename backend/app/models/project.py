from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin
import enum


class ProjectStatus(str, enum.Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    status = Column(
        SAEnum(
            ProjectStatus,
            values_callable=lambda enum_class: [item.value for item in enum_class],
            name="projectstatus",
        ),
        default=ProjectStatus.PLANNING,
        nullable=False,
    )

    start_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)

    organization = relationship(
        "Organization",
        back_populates="projects",
    )

    owner = relationship(
        "User",
    )

    members = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    tasks = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    comments = relationship(
        "Comment",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    attachments = relationship(
        "Attachment",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectMember(Base, TimestampMixin):
    __tablename__ = "project_members"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_user",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = Column(
        String(50),
        nullable=False,
        default="team_member",
    )

    project = relationship(
        "Project",
        back_populates="members",
    )

    user = relationship(
        "User",
        back_populates="project_memberships",
    )