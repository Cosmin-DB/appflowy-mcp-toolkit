from __future__ import annotations

from typing import Any


class AppFlowyError(Exception):
    """Base error with a safe, user-facing message."""

    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class AppFlowyAuthError(AppFlowyError):
    pass


class AppFlowyRateLimitError(AppFlowyError):
    def __init__(self, message: str, *, retry_after: str | None = None, **kwargs: Any):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class AppFlowyNotFoundError(AppFlowyError):
    pass


class AppFlowyServerError(AppFlowyError):
    pass


class AppFlowySchemaError(AppFlowyError):
    pass


def classify_http_error(
    status_code: int, message: str, *, retry_after: str | None = None
) -> AppFlowyError:
    if status_code in {401, 403}:
        return AppFlowyAuthError(message, status_code=status_code)
    if status_code == 404:
        return AppFlowyNotFoundError(message, status_code=status_code)
    if status_code == 429:
        return AppFlowyRateLimitError(message, status_code=status_code, retry_after=retry_after)
    if status_code >= 500:
        return AppFlowyServerError(message, status_code=status_code)
    return AppFlowyError(message, status_code=status_code)
