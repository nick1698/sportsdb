import uuid


IN_REQ_ID = "HTTP_X_REQUEST_ID"  # incoming: X-Request-ID
OUT_REQ_ID = "X-Request-ID"  # outgoing header name

IN_TRACEPARENT = "HTTP_TRACEPARENT"  # optional tracing header
OUT_TRACEPARENT = "traceparent"


class RequestIdMiddleware:
    """
    Ensures every request has a correlation id:
    - uses client-provided X-Request-ID if present
    - otherwise generates a UUID
    Exposes it as request.request_id and returns it in response headers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request.META.get(IN_REQ_ID) or str(uuid.uuid4())
        request.request_id = rid  # your code can log this

        response = self.get_response(request)

        response[OUT_REQ_ID] = rid  # client can report this id
        tp = request.META.get(IN_TRACEPARENT)
        if tp:
            response[OUT_TRACEPARENT] = tp  # passthrough only
        return response
