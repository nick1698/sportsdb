from http import HTTPStatus
from typing import Any, Callable, Optional, List, Dict, Type, TypeVar, Union

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError as DjangoValidationError
from django.http import HttpRequest, JsonResponse, Http404

from ninja import Schema, NinjaAPI
from ninja.errors import ValidationError as NinjaValidationError, HttpError

# region DEFS


T = TypeVar("T", bound=Callable[..., Any])


class ErrorEnvelope(Schema):
    status: int
    message: str
    details: Optional[List[Dict[str, Any]]] = None
    request_id: str
    success: bool = False


class ApiError:
    def __init__(
        self,
        status: HTTPStatus,
        message: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        success: bool = False,
    ):
        self.status = status
        self.code = status.value
        self.message = message or status.description
        self.details = details or []

        # TODO: ricavare dal error code?
        self.success = success

    def to_dict(self, request_id: str) -> dict:
        return {
            "status": self.code,
            "message": self.message,
            "details": self.details,
            "request_id": request_id,
            "success": self.success,
        }


class ApiErrorException(Exception):
    """
    Only used for custom errors which are not covered by native exceptions yet

    e.g.: raise ApiErrorException(ApiError(status=400, message="Bad request"))
    """

    def __init__(self, error: ApiError):
        self.error = error
        super().__init__(error.message)


# endregion

# region ERROR HANDLERS


def _get_request_id_(request: HttpRequest) -> str:
    request_id = getattr(request, "request_id", None)
    if request_id is not None:
        return str(request_id)
    return str(request.META.get("HTTP_X_REQUEST_ID", ""))


def __handler_resp__(request: HttpRequest, err: ApiError) -> JsonResponse:
    rid = _get_request_id_(request)
    return JsonResponse(err.to_dict(rid), status=err.status)


def handle_validation_error(
    request: HttpRequest, exc: Union[ValidationError, Type[ValidationError]]
) -> JsonResponse:
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
        status=HTTPStatus.UNPROCESSABLE_ENTITY,
        message="Validation error",
        details=details,
    )
    return __handler_resp__(request, err)


def handle_http_error(
    request: HttpRequest, exc: Union[HttpError, Type[HttpError]]
) -> JsonResponse:
    req_code = int(getattr(exc, "status_code", 400))

    req_status = {
        400: HTTPStatus.BAD_REQUEST,
        401: HTTPStatus.UNAUTHORIZED,
        403: HTTPStatus.FORBIDDEN,
        404: HTTPStatus.NOT_FOUND,
    }.get(req_code, HTTPStatus.BAD_REQUEST)

    err = ApiError(message=str(exc) or "Request error", status=req_status, details=[])
    return __handler_resp__(request, err)


def handle_not_found(
    request: HttpRequest,
    exc: Union[Http404 | ObjectDoesNotExist, Type[Http404 | ObjectDoesNotExist]],
) -> JsonResponse:
    err = ApiError(status=HTTPStatus.NOT_FOUND)
    return __handler_resp__(request, err)


def handle_permission_denied(
    request: HttpRequest, exc: Union[PermissionDenied, Type[PermissionDenied]]
) -> JsonResponse:
    err = ApiError(status=HTTPStatus.FORBIDDEN)
    return __handler_resp__(request, err)


def handle_api_error(
    request: HttpRequest, exc: Union[ApiErrorException, Type[ApiErrorException]]
) -> JsonResponse:
    err = exc.error
    return __handler_resp__(request, err)


def handle_unexpected_error(
    request: HttpRequest, exc: Union[Exception, Type[Exception]]
) -> JsonResponse:
    """Generic error handler"""
    err = ApiError(status=HTTPStatus.INTERNAL_SERVER_ERROR)
    return __handler_resp__(request, err)


HANDLERS = {
    HttpError: handle_http_error,
    ObjectDoesNotExist: handle_not_found,
    PermissionDenied: handle_permission_denied,
    DjangoValidationError: handle_validation_error,
    NinjaValidationError: handle_validation_error,
    Http404: handle_not_found,
    ApiErrorException: handle_api_error,
    Exception: handle_unexpected_error,
}


def build_api(*, title: str, version: str = "1.0") -> NinjaAPI:
    api = NinjaAPI(title=title, version=version)

    for exc, handler in HANDLERS.items():
        api.add_exception_handler(exc, handler)

    return api


# endregion
