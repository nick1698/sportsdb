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

from platform_api.models.geo import GeoPlace, Venue
from platform_api.routers import PlatformRoute

router = Router(tags=["public-geo"])

# region --- Schemas ---


class GeoPlaceOut(Schema):
    id: UUID
    country_id: str
    parent_id: Optional[UUID] = None
    name: str
    kind: str


class VenueOut(Schema):
    id: UUID
    name: str
    country_id: str
    geo_place_id: UUID | None = None
    lat: float | None = None
    lon: float | None = None


class VenueListParams(ListQueryParams):
    country_id: str | None = None
    geo_place_id: UUID | None = None


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
    items, total = paginate(qs, q.limit, q.offset)
    return {
        "items": items,
        "limit": q.limit,
        "offset": q.offset,
        "total": total,
        "sort": sort_used,
    }


@router.get(geoplace_ep.short_id, response=GeoPlaceOut)
def get_location(request, id: UUID):
    return get_object_or_404(GeoPlace, id=id)


venue_ep = PlatformRoute(Venue)


@router.get(venue_ep.short, response=ListEnvelope[VenueOut])
def list_venues(request, params: VenueListParams = Query(...)):
    qs = Venue.objects.all()

    if params.country_id:
        qs = qs.filter(country_id=params.country_id)

    if params.geo_place_id:
        qs = qs.filter(geo_place_id=params.geo_place_id)

    qs, applied_sort = apply_sort(
        qs,
        params.sort,
        allowed={"name", "country_id"},
        default="name",
    )
    items, total = paginate(qs, params.limit, params.offset)

    return {
        "items": items,
        "limit": params.limit,
        "offset": params.offset,
        "total": total,
        "sort": applied_sort,
    }


@router.get(venue_ep.short_id, response=VenueOut)
def get_venue(request, id: UUID):
    return get_object_or_404(Venue, id=id)


# endregion
