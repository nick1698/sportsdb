from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Field, Query, Router, Schema

from platform_api.models.entities import Org, Person
from platform_api.routers import PlatformRoute
from shared.api_contract.ninja import (
    ListEnvelope,
    ListQueryParams,
    apply_sort,
    paginate,
)


router = Router(tags=["public-people"])

# region --- Schemas ---


class OrgOut(Schema):
    id: UUID
    name: str
    type: int
    country_id: str
    home_geo_place_id: UUID | None = None


class OrgListParams(ListQueryParams):
    country_id: str | None = None
    type: int | None = Field(default=None, ge=1, le=2)


class PersonOut(Schema):
    id: UUID
    given_name: str
    family_name: str
    nickname: str | None = None
    sex: int
    primary_nationality_id: str
    sporting_nationality_id: str | None = None
    birth_date: str | None = None
    death_date: str | None = None


class PersonListParams(ListQueryParams):
    primary_nationality_id: str | None = None
    sex: int | None = Field(default=None, ge=1, le=3)


# endregion

# region --- Endpoints ---

org_ep = PlatformRoute(Org)


@router.get(org_ep.short, response=ListEnvelope[OrgOut])
def list_orgs(request, params: OrgListParams = Query(...)):
    qs = Org.objects.all()

    if params.country_id:
        qs = qs.filter(country_id=params.country_id)

    if params.type is not None:
        qs = qs.filter(type=params.type)

    qs, applied_sort = apply_sort(
        qs,
        params.sort,
        allowed={"name", "type", "country_id"},
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


@router.get(org_ep.short_id, response=OrgOut)
def get_org(request, id: UUID):
    return get_object_or_404(Org, pk=id)


person_ep = PlatformRoute(Person)


@router.get(person_ep.short, response=ListEnvelope[PersonOut])
def list_persons(request, params: PersonListParams = Query(...)):
    qs = Person.objects.all()

    if params.primary_nationality_id:
        qs = qs.filter(primary_nationality_id=params.primary_nationality_id)

    if params.sex is not None:
        qs = qs.filter(sex=params.sex)

    qs, applied_sort = apply_sort(
        qs,
        params.sort,
        allowed={"family_name", "given_name", "sex", "primary_nationality_id"},
        default="family_name",
    )
    items, total = paginate(qs, params.limit, params.offset)

    return {
        "items": items,
        "limit": params.limit,
        "offset": params.offset,
        "total": total,
        "sort": applied_sort,
    }


@router.get(person_ep.short_id, response=PersonOut)
def get_person(request, id: UUID):
    return get_object_or_404(Person, pk=id)


# endregion
