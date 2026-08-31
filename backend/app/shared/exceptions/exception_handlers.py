"""
Maps domain/application exceptions to HTTP responses.

Registered once in `main.py`. This is the boundary where framework-agnostic
errors become FastAPI-specific ones — Domain and Application never import
`fastapi`, so this is the only file that bridges the two worlds for errors.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.shared.exceptions.domain_exceptions import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)

_STATUS_CODE_BY_EXCEPTION: dict[type[DomainError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    ValidationError: 400,
    UnauthorizedError: 401,
    ForbiddenError: 403,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status_code = 500
        for exc_type, code in _STATUS_CODE_BY_EXCEPTION.items():
            if isinstance(exc, exc_type):
                status_code = code
                break
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})
