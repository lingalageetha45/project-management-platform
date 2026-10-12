from fastapi import HTTPException, status
from typing import Any, Dict, Optional


class AppException(HTTPException):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(
            status_code=status_code,
            detail={"success": False, "error": {"code": code, "message": message, **({"details": details} if details else {})}},
        )


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            code=f"{resource.upper()}_NOT_FOUND",
            message=f"{resource} not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class AccessDeniedError(AppException):
    def __init__(self, message: str = "You do not have access to this resource."):
        super().__init__(
            code="ACCESS_DENIED",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Could not validate credentials."):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ValidationError(AppException):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        super().__init__(code=code, message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class ConflictError(AppException):
    def __init__(self, message: str, code: str = "CONFLICT"):
        super().__init__(code=code, message=message, status_code=status.HTTP_409_CONFLICT)
