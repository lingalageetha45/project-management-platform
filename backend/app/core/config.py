from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
import json


class Settings(BaseSettings):
    APP_NAME: str = "ProjectFlow"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    DATABASE_URL: str
    REDIS_URL: Optional[str] = None

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_MIME_TYPES: str = "image/jpeg,image/png,image/gif,application/pdf,text/plain"

    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    FIRST_SUPERUSER_EMAIL: str = "superadmin@projectflow.local"
    FIRST_SUPERUSER_PASSWORD: str = "SuperAdmin@123"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [i.strip() for i in v.split(",")]
        return v

    @property
    def allowed_mime_list(self) -> List[str]:
        return [m.strip() for m in self.ALLOWED_MIME_TYPES.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
