from pydantic import Field
from typing import Generic, List, Optional, Tuple, TypeVar

from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.http import Http404

from ninja import Schema
from ninja.errors import ValidationError, HttpError

from .codes import ErrorCode
from .errors import ApiError, ApiErrorException, error_payload


def _request_id(request) -> str:
    return getattr(request, "request_id", None) or request.META.get("HTTP_X_REQUEST_ID")


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

    msg = str(exc) or "Request error"
    err = ApiError(code=code, message=msg, status=status, details=[])
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


def handle_api_error(request, exc: ApiErrorException):
    rid = _request_id(request)
    err = exc.error
    return JsonResponse(error_payload(err, rid), status=err.status)


# region LIST CONTRACT + STANDARD QUERY PARAMS

T = TypeVar("T")


class ListEnvelope(Schema, Generic[T]):
    items: List[T]
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    sort: Optional[str] = None


class ListQueryParams(Schema):
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
    sort: Optional[str] = None


def apply_sort(qs, sort: Optional[str], allowed: set[str], default: str) -> tuple:
    """
    sort examples:
      - "name_en"
      - "-name_en"
    """
    if not sort:
        return qs.order_by(default), default

    field = sort[1:] if sort.startswith("-") else sort
    if field not in allowed:
        raise ApiErrorException(
            ApiError(
                code=ErrorCode.BAD_REQUEST,
                message="Invalid sort field",
                status=400,
                details=[
                    {
                        "field": "sort",
                        "issue": f"Unsupported sort field '{sort}'",
                        "type": "invalid_choice",
                        "value": sort,
                    }
                ],
            )
        )

    return qs.order_by(sort), sort


def paginate(qs, limit: int, offset: int) -> Tuple[list, int]:
    total = qs.count()
    items = list(qs[offset : offset + limit])  # noqa: E203
    return items, total


# endregion
