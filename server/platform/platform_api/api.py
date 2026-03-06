from django.db import connection
from django.http import JsonResponse

from shared.api_contract.factory import build_api
from shared.api_contract.errors import ApiError, error_payload

from .routers.public_core import router as public_core_router

api = build_api(title="Platform API")
api.add_router("", public_core_router)


@api.get("/health")
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1;")
        cursor.fetchone()
    return {"status": "ok", "service": "platform", "db": "ok"}


@api.get("/_debug/error")
def debug_error(request):
    # request.request_id is set by the RequestIdMiddleware
    rid = getattr(request, "request_id", "unknown")

    err = ApiError(
        code="PLATFORM_DEBUG_ERROR",
        message="This is a debug error endpoint",
        status=418,
        details=[{"hint": "Remove this endpoint in production"}],
    )
    return JsonResponse(error_payload(err, rid), status=err.status)


@api.get("/_debug/crash")
def debug_crash(request):
    1 / 0
