from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
}


def error_payload(
    *,
    status_code: int,
    message: str,
    code: str | None = None,
    details: Any | None = None,
) -> dict:
    error = {
        "code": code or ERROR_CODES.get(status_code, "error"),
        "message": message,
        "status": status_code,
    }
    if details is not None:
        error["details"] = jsonable_encoder(details)
    return {"error": error}


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        message = str(detail.get("message") or detail.get("detail") or "Request failed")
        code = detail.get("code")
        details = detail.get("details")
    else:
        message = str(detail)
        code = None
        details = None
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            status_code=exc.status_code,
            code=code,
            message=message,
            details=details,
        ),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_payload(
            status_code=422,
            message="Request validation failed",
            details=exc.errors(),
        ),
    )
