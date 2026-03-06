from django.shortcuts import get_object_or_404

from ninja import Router, Query, Schema

from shared.api_contract.ninja import (
    ListEnvelope,
    ListQueryParams,
    apply_sort,
    paginate,
)

from platform_api.models.geo import Country
from platform_api.models.entities import Sport


router = Router(tags=["public-core"])


# --- Schemas ---
class CountryOut(Schema):
    iso2: str
    name_en: str


class SportOut(Schema):
    key: str
    name_en: str


# --- Endpoints ---
@router.get("/countries", response=ListEnvelope[CountryOut])
def list_countries(request, q: ListQueryParams = Query(...)):
    qs = Country.objects.all()
    qs, sort_used = apply_sort(
        qs, q.sort, allowed={"iso2", "name_en"}, default="name_en"
    )
    items, total = paginate(qs, q.limit, q.offset)
    return {
        "items": items,
        "limit": q.limit,
        "offset": q.offset,
        "total": total,
        "sort": sort_used,
    }


@router.get("/countries/{iso2}", response=CountryOut)
def get_country(request, iso2: str):
    return get_object_or_404(Country, iso2=iso2.upper())


@router.get("/sports", response=ListEnvelope[SportOut])
def list_sports(request, q: ListQueryParams = Query(...)):
    qs = Sport.objects.all()
    qs, sort_used = apply_sort(
        qs, q.sort, allowed={"key", "name_en"}, default="name_en"
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


@router.get("/sports/{key}", response=SportOut)
def get_sport(request, key: str):
    return get_object_or_404(Sport, key=key)
