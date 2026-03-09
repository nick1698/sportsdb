from ninja import NinjaAPI
from ninja.errors import ValidationError, HttpError
from django.core.exceptions import PermissionDenied
from django.http import Http404

from .errors import ApiErrorException

from .ninja import (
    handle_api_error,
    handle_validation_error,
    handle_http_error,
    handle_not_found,
    handle_permission_denied,
    handle_unexpected_error,
)


def build_api(*, title: str, version: str = "1.0") -> NinjaAPI:
    api = NinjaAPI(title=title, version=version)

    # register in one place, once
    api.add_exception_handler(ValidationError, handle_validation_error)
    api.add_exception_handler(ApiErrorException, handle_api_error)
    api.add_exception_handler(HttpError, handle_http_error)
    api.add_exception_handler(Http404, handle_not_found)
    api.add_exception_handler(PermissionDenied, handle_permission_denied)
    api.add_exception_handler(Exception, handle_unexpected_error)

    return api
