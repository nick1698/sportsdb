from django.db import connection
from ninja import NinjaAPI

api = NinjaAPI(title="SPDB Platform API")


@api.get("/health")
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1;")
        cursor.fetchone()
    return {"status": "ok", "service": "platform", "db": "ok"}
