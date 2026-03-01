from django.db import connection
from django.http import JsonResponse

from shared.api_contract.factory import build_api
from shared.api_contract.errors import ApiError, error_payload

api = build_api(title="Volley API")


@api.get("/health")
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1;")
        cursor.fetchone()
    return {"status": "ok", "service": "platform", "db": "ok"}
