from dataclasses import dataclass
from typing import Any, Optional, List, Dict

from ninja import Schema


class ErrorDetail(Schema):
    field: str | None = None
    issue: str
    type: str | None = None
    value: Any | None = None


class ErrorBody(Schema):
    code: str
    message: str
    details: list[ErrorDetail]
    request_id: str | None = None


class ErrorEnvelope(Schema):
    error: ErrorBody


@dataclass(frozen=True)
class ApiError:
    # code is stable for the UI (machine-readable); message is for humans
    code: str
    message: str
    status: int = 400
    details: Optional[List[Dict[str, Any]]] = None


class ApiErrorException(Exception):
    def __init__(self, error: ApiError):
        self.error = error
        super().__init__(error.message)


def error_payload(err: ApiError, request_id: str) -> Dict[str, Any]:
    # single standard shape for ALL services (platform + verticals)
    return {
        "error": {
            "code": err.code,
            "message": err.message,
            "details": err.details or [],
            "request_id": request_id,
        }
    }
