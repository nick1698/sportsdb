from ninja import NinjaAPI

api = NinjaAPI(title="SPDB volley API")


@api.get("/health")
def health(request):
    return {"status": "ok", "service": "volley"}
