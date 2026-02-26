from ninja import NinjaAPI

api = NinjaAPI(title="SPDB Platform API")


@api.get("/health")
def health(request):
    return {"status": "ok", "service": "platform"}
