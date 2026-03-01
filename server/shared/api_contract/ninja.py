from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.http import Http404
from ninja.errors import ValidationError, HttpError

from .codes import ErrorCode
from .errors import ApiError, error_payload


def _request_id(request) -> str:
    # Set by RequestIdMiddleware; fallback for safety
    return getattr(request, "request_id", None) or request.META.get(
        "HTTP_X_REQUEST_ID", "unknown"
    )


def handle_validation_error(request, exc: ValidationError):
    rid = _request_id(request)

    # Ninja ValidationError exposes a list of pydantic-like errors
    details = []
    for e in exc.errors:
        loc = e.get("loc", [])
        details.append(
            {
                "field": ".".join(str(x) for x in loc if x is not None),
                "issue": e.get("msg", "invalid"),
                "type": e.get("type"),
            }
        )

    err = ApiError(
        code=ErrorCode.VALIDATION_ERROR,
        message="Validation error",
        status=422,
        details=details,
    )
    return JsonResponse(error_payload(err, rid), status=err.status)


def handle_unexpected_error(request, exc: Exception):
    rid = _request_id(request)

    err = ApiError(
        code=ErrorCode.INTERNAL_ERROR,
        message="Internal error",
        status=500,
        details=[],
    )
    return JsonResponse(error_payload(err, rid), status=err.status)


def handle_http_error(request, exc: HttpError):
    """
    Useful for clean 401/403/404 without stacktraces.
    """
    rid = _request_id(request)

    status = int(getattr(exc, "status_code", 400))
    # Map common statuses to stable codes
    code = {
        400: ErrorCode.BAD_REQUEST,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
    }.get(status, ErrorCode.BAD_REQUEST)

    err = ApiError(code=code, message=str(exc), status=status, details=[])
    return JsonResponse(error_payload(err, rid), status=err.status)


def handle_not_found(request, exc: Http404):
    rid = _request_id(request)
    err = ApiError(
        code=ErrorCode.NOT_FOUND, message="Not found", status=404, details=[]
    )
    return JsonResponse(error_payload(err, rid), status=err.status)


def handle_permission_denied(request, exc: PermissionDenied):
    rid = _request_id(request)
    err = ApiError(
        code=ErrorCode.FORBIDDEN, message="Forbidden", status=403, details=[]
    )
    return JsonResponse(error_payload(err, rid), status=err.status)
