from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.exceptions import AppException
from app.api.v1.router import api_router
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.user import User
from app.core.security import get_password_hash


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (Alembic is preferred in production)
    Base.metadata.create_all(bind=engine)
    # Bootstrap superuser
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.FIRST_SUPERUSER_EMAIL).first()
        if not existing:
            superuser = User(
                email=settings.FIRST_SUPERUSER_EMAIL,
                full_name="Super Admin",
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_active=True,
                is_superuser=True,
            )
            db.add(superuser)
            db.commit()
            print(f"Created superuser: {settings.FIRST_SUPERUSER_EMAIL}")
    finally:
        db.close()
    # Ensure upload dir
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Multi-Tenant Project & Workflow Management Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."},
        },
    )


app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
