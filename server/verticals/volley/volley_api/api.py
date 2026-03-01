from shared.api_contract.factory import build_api

api = build_api(title="Volley API")


@api.get("/health")
def health(request):
    return {"status": "ok", "service": "volley"}
