from http import HTTPStatus

from ninja import Schema
from pydantic import Field
from typing import Generic, List, Optional, Tuple, TypeVar

from .errors import ApiError, ApiErrorException

T = TypeVar("T")


class ListEnvelope(Schema, Generic[T]):
    items: List[T]
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    sort: Optional[str] = None


class ListQueryParams(Schema):
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
    sort: Optional[str] = None


def apply_sort(qs, sort: Optional[str], allowed: set[str], default: str) -> tuple:
    """
    sort examples:
      - "name_en"
      - "-name_en"
    """
    if not sort:
        return qs.order_by(default), default

    field = sort[1:] if sort.startswith("-") else sort
    if field not in allowed:
        raise ApiErrorException(
            ApiError(
                status=HTTPStatus.BAD_REQUEST,
                message="Invalid sort field",
                details=[
                    {
                        "field": "sort",
                        "issue": f"Unsupported sort field '{sort}'",
                        "type": "invalid_choice",
                        "value": sort,
                    }
                ],
            )
        )

    return qs.order_by(sort), sort


def paginate(qs, limit: int, offset: int) -> Tuple[list, int]:
    total = qs.count()
    items = list(qs[offset : offset + limit])  # noqa: E203
    return items, total


class ResponseEnvelope(Schema, Generic[T]):
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[dict] = None
    success: bool = True
