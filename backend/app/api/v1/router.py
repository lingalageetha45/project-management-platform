from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    organizations,
    projects,
    tasks,
    notifications,
    comments,
    attachments,
    audit,
)


api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(notifications.router)
api_router.include_router(comments.router)
api_router.include_router(attachments.router)
api_router.include_router(audit.router)
