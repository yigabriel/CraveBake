"""
Maps every error to one HTTP response shape.

Registered once in `main.py`. This is the boundary where framework-agnostic
errors become FastAPI-specific ones — Domain and Application never import
`fastapi`, so this is the only file that bridges the two worlds for errors.

Every error body, whatever its origin, looks like:

    {"detail": "<human readable>", "code": "<stable machine code>", "errors": [{"field": ..., "message": ...}]}

`errors` lists per-field problems (filled for request validation, empty
otherwise), so a client parses one format for 400, 401, 403, 404, 409, 422,
429 and 500 alike.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.exceptions.domain_exceptions import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
    ServiceUnavailableError,
    ValidationError,
)

logger = logging.getLogger(__name__)

_STATUS_AND_CODE_BY_EXCEPTION: dict[type[DomainError], tuple[int, str]] = {
    NotFoundError: (404, "not_found"),
    ConflictError: (409, "conflict"),
    ValidationError: (400, "validation_error"),
    UnauthorizedError: (401, "unauthorized"),
    ForbiddenError: (403, "forbidden"),
    TooManyRequestsError: (429, "too_many_requests"),
    ServiceUnavailableError: (503, "service_unavailable"),
}

_CODE_BY_HTTP_STATUS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "request_validation_error",
    429: "too_many_requests",
}


def error_body(detail: str, code: str, errors: list[dict] | None = None) -> dict:
    return {"detail": detail, "code": code, "errors": errors or []}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status_code, code = 500, "internal_error"
        for exc_type, (exc_status, exc_code) in _STATUS_AND_CODE_BY_EXCEPTION.items():
            if isinstance(exc, exc_type):
                status_code, code = exc_status, exc_code
                break
        headers = None
        if isinstance(exc, TooManyRequestsError):
            headers = {"Retry-After": str(exc.retry_after_seconds)}
        return JSONResponse(status_code=status_code, content=error_body(str(exc), code), headers=headers)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_body("The request is invalid", "request_validation_error", errors),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Raised by the framework itself (unknown route, missing bearer token, ...).
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(str(exc.detail), _CODE_BY_HTTP_STATUS.get(exc.status_code, "http_error")),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=error_body("Internal server error", "internal_error"))
