"""Custom application exceptions."""

from typing import Any, Optional


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        code: str = "app_error",
        status_code: int = 400,
        details: Optional[Any] = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ProviderNotConfiguredError(AppError):
    """Raised when required API key or provider is missing."""

    def __init__(self, provider: str, message: Optional[str] = None) -> None:
        super().__init__(
            message or f"Провайдер «{provider}» не настроен. Укажите API-ключ в .env.",
            code="provider_not_configured",
            status_code=503,
        )


class ProviderUnavailableError(AppError):
    """Raised when external provider is unreachable or returns an error."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(
            message,
            code="provider_unavailable",
            status_code=502,
            details=details,
        )


class UnsupportedOperationError(AppError):
    """Raised when the selected model does not support the requested operation."""

    def __init__(self, operation: str, provider: str) -> None:
        super().__init__(
            f"Операция «{operation}» не поддерживается провайдером «{provider}».",
            code="unsupported_operation",
            status_code=400,
        )


class ImageValidationError(AppError):
    """Raised when uploaded image fails validation."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="image_validation_error", status_code=400)


class TaskNotFoundError(AppError):
    """Raised when task id does not exist."""

    def __init__(self, task_id: str) -> None:
        super().__init__(
            f"Задача «{task_id}» не найдена.",
            code="task_not_found",
            status_code=404,
        )


class RateLimitError(AppError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Превышен лимит запросов. Попробуйте позже.") -> None:
        super().__init__(message, code="rate_limit", status_code=429)


class StorageError(AppError):
    """Raised on file storage problems."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="storage_error", status_code=500)
