from django.db import connection
from django.http import JsonResponse

from shared.api_contract.errors import ApiError, error_payload
from shared.api_contract.factory import build_api

from .routers import public_core, public_geo, public_people

api = build_api(title="Platform API")
api.add_router("/core", public_core.router)
api.add_router("/geo", public_geo.router)
api.add_router("/people", public_people.router)


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
