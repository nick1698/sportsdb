from dataclasses import dataclass
from typing import Any, Optional, List, Dict


@dataclass(frozen=True)
class ApiError:
    # code is stable for the UI (machine-readable); message is for humans
    code: str
    message: str
    status: int = 400
    details: Optional[List[Dict[str, Any]]] = None


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
