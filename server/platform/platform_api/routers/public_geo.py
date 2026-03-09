from typing import Optional
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Query, Router, Schema

from shared.api_contract.ninja import (
    ListEnvelope,
    ListQueryParams,
    apply_sort,
    paginate,
)

from platform_api.models.geo import GeoPlace
from platform_api.routers import PlatformRoute

router = Router(tags=["public-geo"])

# region --- Schemas ---


class GeoPlaceOut(Schema):
    id: UUID
    country_id: str
    parent_id: Optional[UUID] = None
    name: str
    kind: str


# endregion


# region --- Endpoints ---

geoplace_ep = PlatformRoute(GeoPlace)


@router.get(geoplace_ep.short, response=ListEnvelope[GeoPlaceOut])
def list_locations(
    request, q: ListQueryParams = Query(...), country_id: Optional[str] = None
):
    qs = GeoPlace.objects.all()
    if country_id:
        qs = qs.filter(country_id=country_id.upper())

    qs, sort_used = apply_sort(
        qs,
        q.sort,
        allowed={"name", "normalized_name", "kind", "country_id"},
        default="normalized_name",
    )
    total = qs.count()
    items, total = paginate(qs, q.limit, q.offset)
    return {
        "items": items,
        "limit": q.limit,
        "offset": q.offset,
        "total": total,
        "sort": sort_used,
    }


@router.get(geoplace_ep.short_id, response=GeoPlaceOut)
def get_location(request, id: str):
    return get_object_or_404(GeoPlace, id=id)


# endregion
