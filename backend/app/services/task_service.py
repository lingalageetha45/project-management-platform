from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.organization import OrganizationMember
from app.models.project import Project, ProjectMember
from app.models.task import (
    Task,
    TaskDependency,
    TaskPriority,
    TaskStatus,
    VALID_TASK_TRANSITIONS,
)
from app.models.user import SystemRole, User
from app.services.audit_service import log_action
from app.services.notification_service import NotificationService


TASK_MANAGEMENT_ROLES = {
    SystemRole.ORGANIZATION_ADMIN.value,
    SystemRole.PROJECT_MANAGER.value,
}

PROJECT_MEMBER_ROLES = {
    SystemRole.PROJECT_MANAGER.value,
    SystemRole.TEAM_MEMBER.value,
    SystemRole.VIEWER.value,
}


class TaskService:

    @staticmethod
    def _get_project(
        db: Session,
        project_id: int,
    ) -> Project:
        project = (
            db.query(Project)
            .filter(Project.id == project_id)
            .first()
        )

        if not project:
            raise NotFoundError("Project")

        return project

    @staticmethod
    def _get_org_membership(
        db: Session,
        organization_id: int,
        user_id: int,
    ) -> Optional[OrganizationMember]:
        return (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def _get_project_membership(
        db: Session,
        project_id: int,
        user_id: int,
    ) -> Optional[ProjectMember]:
        return (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
            .first()
        )

    @staticmethod
    def _get_task(
        db: Session,
        task_id: int,
    ) -> Task:
        task = (
            db.query(Task)
            .filter(Task.id == task_id)
            .first()
        )

        if not task:
            raise NotFoundError("Task")

        return task

    @staticmethod
    def _require_project_access(
        db: Session,
        project: Project,
        user: User,
    ) -> Optional[ProjectMember]:
        """Verify organization membership and project access."""

        if user.is_superuser:
            return None

        org_membership = TaskService._get_org_membership(
            db,
            project.organization_id,
            user.id,
        )

        if not org_membership:
            raise AccessDeniedError(
                "You do not have access to this project."
            )

        project_membership = TaskService._get_project_membership(
            db,
            project.id,
            user.id,
        )

        if not project_membership:
            raise AccessDeniedError(
                "You are not a member of this project."
            )

        return project_membership

    @staticmethod
    def _require_task_management_access(
        db: Session,
        project: Project,
        user: User,
    ) -> Optional[ProjectMember]:
        """Check whether the user can create or manage project tasks."""

        if user.is_superuser:
            return None

        org_membership = TaskService._get_org_membership(
            db,
            project.organization_id,
            user.id,
        )

        if not org_membership:
            raise AccessDeniedError(
                "You do not have access to this project."
            )

        project_membership = TaskService._get_project_membership(
            db,
            project.id,
            user.id,
        )

        if not project_membership:
            raise AccessDeniedError(
                "You are not a member of this project."
            )

        if org_membership.role == SystemRole.ORGANIZATION_ADMIN.value:
            return project_membership

        if (
            org_membership.role == SystemRole.PROJECT_MANAGER.value
            and project_membership.role == SystemRole.PROJECT_MANAGER.value
        ):
            return project_membership

        raise AccessDeniedError(
            "You do not have permission to manage tasks."
        )

    @staticmethod
    def _validate_assignee(
        db: Session,
        project: Project,
        user_id: int,
    ) -> User:
        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:
            raise NotFoundError("User")

        if not user.is_active:
            raise ValidationError(
                "Inactive users cannot be assigned tasks.",
                code="INACTIVE_USER",
            )

        org_membership = TaskService._get_org_membership(
            db,
            project.organization_id,
            user_id,
        )

        if not org_membership:
            raise AccessDeniedError(
                "Assignee must belong to the same organization."
            )

        project_membership = TaskService._get_project_membership(
            db,
            project.id,
            user_id,
        )

        if not project_membership:
            raise AccessDeniedError(
                "Assignee must be a member of the project."
            )

        if project_membership.role == SystemRole.VIEWER.value:
            raise ValidationError(
                "Viewers cannot be assigned tasks.",
                code="VIEWER_CANNOT_BE_ASSIGNED",
            )

        return user

    @staticmethod
    def create(
        db: Session,
        data: dict,
        reporter: User,
    ) -> Task:
        project = TaskService._get_project(
            db,
            data["project_id"],
        )

        TaskService._require_task_management_access(
            db,
            project,
            reporter,
        )

        assignee_id = data.get("assignee_id")

        if assignee_id is not None:
            TaskService._validate_assignee(
                db,
                project,
                assignee_id,
            )

        task = Task(
            title=data["title"].strip(),
            description=data.get("description"),
            project_id=project.id,
            assignee_id=assignee_id,
            reporter_id=reporter.id,
            priority=data.get("priority", TaskPriority.MEDIUM),
            status=data.get("status", TaskStatus.BACKLOG),
            due_date=data.get("due_date"),
            estimated_hours=data.get("estimated_hours"),
        )

        try:
            db.add(task)
            db.commit()
            db.refresh(task)
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=reporter.id,
            organization_id=project.organization_id,
            action="TASK_CREATED",
            entity_type="task",
            entity_id=task.id,
        )

        if assignee_id is not None:
            NotificationService.create(
                db,
                user_id=assignee_id,
                organization_id=project.organization_id,
                type="task_assigned",
                title="New task assigned",
                message=f"You have been assigned: {task.title}",
                entity_type="task",
                entity_id=task.id,
            )

        return task

    @staticmethod
    def get_for_user(
        db: Session,
        task_id: int,
        user: User,
    ) -> Task:
        task = TaskService._get_task(db, task_id)

        TaskService._require_project_access(
            db,
            task.project,
            user,
        )

        return task

    @staticmethod
    def update(
        db: Session,
        task: Task,
        data: dict,
        actor: User,
    ) -> Task:
        TaskService._require_task_management_access(
            db,
            task.project,
            actor,
        )

        old_status = task.status
        old_assignee_id = task.assignee_id
        organization_id = task.project.organization_id
        status_changed = False
        assignee_changed = False
        new_assignee_id = task.assignee_id

        try:
            # Validate and apply all requested field changes before committing.
            if "title" in data and data["title"] is not None:
                title = data["title"].strip()

                if not title:
                    raise ValidationError(
                        "Task title cannot be empty.",
                        code="INVALID_TASK_TITLE",
                    )

                task.title = title

            if "description" in data:
                task.description = data["description"]

            if "priority" in data and data["priority"] is not None:
                task.priority = data["priority"]

            if "due_date" in data:
                task.due_date = data["due_date"]

            if "estimated_hours" in data:
                task.estimated_hours = data["estimated_hours"]

            if "status" in data and data["status"] is not None:
                requested_status = data["status"]

                if requested_status != task.status:
                    TaskService._validate_status_transition(
                        db,
                        task,
                        requested_status,
                    )

                    task.status = requested_status
                    status_changed = True

            if "assignee_id" in data:
                new_assignee_id = data["assignee_id"]

                if new_assignee_id is not None:
                    TaskService._validate_assignee(
                        db,
                        task.project,
                        new_assignee_id,
                    )

                if old_assignee_id != new_assignee_id:
                    task.assignee_id = new_assignee_id
                    assignee_changed = True

            db.commit()
            db.refresh(task)

        except Exception:
            db.rollback()
            raise

        # The task changes have succeeded; now record audit events.
        if status_changed:
            log_action(
                db,
                user_id=actor.id,
                organization_id=organization_id,
                action="TASK_STATUS_CHANGED",
                entity_type="task",
                entity_id=task.id,
                metadata={
                    "from": old_status.value,
                    "to": task.status.value,
                },
            )

        if assignee_changed:
            log_action(
                db,
                user_id=actor.id,
                organization_id=organization_id,
                action="TASK_ASSIGNED",
                entity_type="task",
                entity_id=task.id,
                metadata={
                    "from": old_assignee_id,
                    "to": new_assignee_id,
                },
            )

            if new_assignee_id is not None:
                NotificationService.create(
                    db,
                    user_id=new_assignee_id,
                    organization_id=organization_id,
                    type="task_assigned",
                    title="Task assigned to you",
                    message=f"You have been assigned: {task.title}",
                    entity_type="task",
                    entity_id=task.id,
                )

        log_action(
            db,
            user_id=actor.id,
            organization_id=organization_id,
            action="TASK_UPDATED",
            entity_type="task",
            entity_id=task.id,
        )

        return task

    @staticmethod
    def _validate_status_transition(
        db: Session,
        task: Task,
        new_status: TaskStatus,
    ) -> None:
        allowed = VALID_TASK_TRANSITIONS.get(
            task.status,
            set(),
        )

        if new_status not in allowed:
            raise ValidationError(
                (
                    f"Invalid transition from "
                    f"{task.status.value} to "
                    f"{new_status.value}"
                ),
                code="INVALID_STATUS_TRANSITION",
            )

        if new_status in {
            TaskStatus.IN_PROGRESS,
            TaskStatus.REVIEW,
            TaskStatus.DONE,
        }:
            dependencies = (
                db.query(TaskDependency)
                .filter(TaskDependency.task_id == task.id)
                .all()
            )

            for dependency in dependencies:
                dependency_task = (
                    db.query(Task)
                    .filter(Task.id == dependency.depends_on_id)
                    .first()
                )

                if (
                    dependency_task
                    and dependency_task.status != TaskStatus.DONE
                ):
                    raise ValidationError(
                        (
                            "Cannot move task because dependency "
                            f"'{dependency_task.title}' is not Done."
                        ),
                        code="DEPENDENCY_NOT_COMPLETED",
                    )

    @staticmethod
    def change_status(
        db: Session,
        task: Task,
        new_status: TaskStatus,
        actor: User,
    ) -> Task:
        TaskService._require_task_management_access(
            db,
            task.project,
            actor,
        )

        if new_status == task.status:
            return task

        TaskService._validate_status_transition(
            db,
            task,
            new_status,
        )

        old_status = task.status
        organization_id = task.project.organization_id

        try:
            task.status = new_status
            db.commit()
            db.refresh(task)
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=actor.id,
            organization_id=organization_id,
            action="TASK_STATUS_CHANGED",
            entity_type="task",
            entity_id=task.id,
            metadata={
                "from": old_status.value,
                "to": new_status.value,
            },
        )

        if task.assignee_id is not None and task.assignee_id != actor.id:
            NotificationService.create(
                db,
                user_id=task.assignee_id,
                organization_id=organization_id,
                type="task_status_changed",
                title="Task status updated",
                message=f"'{task.title}' moved to {new_status.value}",
                entity_type="task",
                entity_id=task.id,
            )

        return task

    @staticmethod
    def assign(
        db: Session,
        task: Task,
        assignee_id: Optional[int],
        actor: User,
    ) -> Task:
        TaskService._require_task_management_access(
            db,
            task.project,
            actor,
        )

        if assignee_id is not None:
            TaskService._validate_assignee(
                db,
                task.project,
                assignee_id,
            )

        old_assignee_id = task.assignee_id

        if old_assignee_id == assignee_id:
            raise ConflictError(
                "Task is already assigned to this user.",
                code="ASSIGNEE_UNCHANGED",
            )

        organization_id = task.project.organization_id

        try:
            task.assignee_id = assignee_id
            db.commit()
            db.refresh(task)
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=actor.id,
            organization_id=organization_id,
            action="TASK_ASSIGNED",
            entity_type="task",
            entity_id=task.id,
            metadata={
                "from": old_assignee_id,
                "to": assignee_id,
            },
        )

        if assignee_id is not None:
            NotificationService.create(
                db,
                user_id=assignee_id,
                organization_id=organization_id,
                type="task_assigned",
                title="Task assigned to you",
                message=f"You have been assigned: {task.title}",
                entity_type="task",
                entity_id=task.id,
            )

        return task

    @staticmethod
    def add_dependency(
        db: Session,
        task: Task,
        depends_on_id: int,
        actor: User,
    ) -> TaskDependency:
        TaskService._require_task_management_access(
            db,
            task.project,
            actor,
        )

        if depends_on_id == task.id:
            raise ValidationError(
                "Task cannot depend on itself.",
                code="SELF_DEPENDENCY",
            )

        dependency_task = (
            db.query(Task)
            .filter(Task.id == depends_on_id)
            .first()
        )

        if not dependency_task:
            raise NotFoundError("Dependency task")

        if dependency_task.project_id != task.project_id:
            raise AccessDeniedError(
                "Dependency must belong to the same project."
            )

        if TaskService._would_create_cycle(
            db,
            task.id,
            depends_on_id,
        ):
            raise ValidationError(
                "Adding this dependency would create a cycle.",
                code="CIRCULAR_DEPENDENCY",
            )

        existing = (
            db.query(TaskDependency)
            .filter(
                TaskDependency.task_id == task.id,
                TaskDependency.depends_on_id == depends_on_id,
            )
            .first()
        )

        if existing:
            raise ConflictError(
                "Dependency already exists.",
                code="DUPLICATE_DEPENDENCY",
            )

        dependency = TaskDependency(
            task_id=task.id,
            depends_on_id=depends_on_id,
        )

        try:
            db.add(dependency)
            db.commit()
            db.refresh(dependency)
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=actor.id,
            organization_id=task.project.organization_id,
            action="TASK_DEPENDENCY_ADDED",
            entity_type="task",
            entity_id=task.id,
            metadata={
                "depends_on_task_id": depends_on_id,
            },
        )

        return dependency

    @staticmethod
    def remove_dependency(
        db: Session,
        task: Task,
        depends_on_id: int,
        actor: User,
    ) -> None:
        TaskService._require_task_management_access(
            db,
            task.project,
            actor,
        )

        dependency = (
            db.query(TaskDependency)
            .filter(
                TaskDependency.task_id == task.id,
                TaskDependency.depends_on_id == depends_on_id,
            )
            .first()
        )

        if not dependency:
            raise NotFoundError("Task dependency")

        try:
            db.delete(dependency)
            db.commit()
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=actor.id,
            organization_id=task.project.organization_id,
            action="TASK_DEPENDENCY_REMOVED",
            entity_type="task",
            entity_id=task.id,
            metadata={
                "depends_on_task_id": depends_on_id,
            },
        )

    @staticmethod
    def _would_create_cycle(
        db: Session,
        task_id: int,
        new_dep_id: int,
    ) -> bool:
        visited = set()
        stack = [new_dep_id]

        while stack:
            current_id = stack.pop()

            if current_id == task_id:
                return True

            if current_id in visited:
                continue

            visited.add(current_id)

            dependencies = (
                db.query(TaskDependency)
                .filter(TaskDependency.task_id == current_id)
                .all()
            )

            for dependency in dependencies:
                stack.append(dependency.depends_on_id)

        return False

    @staticmethod
    def delete(
        db: Session,
        task: Task,
        actor: User,
    ) -> None:
        TaskService._require_task_management_access(
            db,
            task.project,
            actor,
        )

        project_id = task.project_id
        organization_id = task.project.organization_id
        task_id = task.id

        try:
            db.delete(task)
            db.commit()
        except Exception:
            db.rollback()
            raise

        log_action(
            db,
            user_id=actor.id,
            organization_id=organization_id,
            action="TASK_DELETED",
            entity_type="task",
            entity_id=task_id,
            metadata={
                "project_id": project_id,
            },
        )

    @staticmethod
    def list_filtered(
        db: Session,
        user: User,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[int] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ):
        if page < 1:
            raise ValidationError(
                "Page must be greater than or equal to 1.",
                code="INVALID_PAGE",
            )

        if page_size < 1 or page_size > 100:
            raise ValidationError(
                "Page size must be between 1 and 100.",
                code="INVALID_PAGE_SIZE",
            )

        query = db.query(Task)

        if user.is_superuser:
            if project_id is not None:
                query = query.filter(Task.project_id == project_id)
        else:
            # Only include projects where the user has an active
            # organization membership and a project membership.
            accessible_project_ids = (
                db.query(ProjectMember.project_id)
                .join(
                    Project,
                    Project.id == ProjectMember.project_id,
                )
                .join(
                    OrganizationMember,
                    OrganizationMember.organization_id
                    == Project.organization_id,
                )
                .filter(
                    ProjectMember.user_id == user.id,
                    OrganizationMember.user_id == user.id,
                    OrganizationMember.is_active.is_(True),
                )
                .subquery()
            )

            query = query.filter(
                Task.project_id.in_(accessible_project_ids)
            )

            if project_id is not None:
                query = query.filter(Task.project_id == project_id)

        if status is not None:
            try:
                status_value = TaskStatus(status)
            except ValueError:
                raise ValidationError(
                    "Invalid task status.",
                    code="INVALID_TASK_STATUS",
                )

            query = query.filter(Task.status == status_value)

        if priority is not None:
            try:
                priority_value = TaskPriority(priority)
            except ValueError:
                raise ValidationError(
                    "Invalid task priority.",
                    code="INVALID_TASK_PRIORITY",
                )

            query = query.filter(Task.priority == priority_value)

        if assignee_id is not None:
            query = query.filter(Task.assignee_id == assignee_id)

        if search:
            search_value = search.strip()

            if search_value:
                query = query.filter(
                    Task.title.ilike(f"%{search_value}%")
                )

        total = query.count()

        items = (
            query
            .order_by(Task.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return items, total