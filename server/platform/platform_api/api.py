from http import HTTPStatus

from django.db import connection

from shared.api_contract.errors import ApiError, ApiErrorException, build_api

from .routers import public_core, public_geo, public_people, public_inbox

api = build_api(title="Platform API")
api.add_router("/core", public_core.router)
api.add_router("/geo", public_geo.router)
api.add_router("/people", public_people.router)
api.add_router("/inbox", public_inbox.router)


@api.get("/health")
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1;")
        cursor.fetchone()
    return {"status": "ok", "service": "platform", "db": "ok"}


@api.get("/_debug/error")
def debug_error(request):
    raise ApiErrorException(
        ApiError(
            status=HTTPStatus.IM_A_TEAPOT,
            message="This is a debug error endpoint",
            details=[{"hint": "Remove this endpoint in production"}],
        )
    )


@api.get("/_debug/crash")
def debug_crash(request):
    1 / 0
