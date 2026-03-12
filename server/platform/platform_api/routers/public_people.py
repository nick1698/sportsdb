from typing import Optional
from uuid import UUID

from django.db.models import Q, Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404

from ninja import Field, Query, Router, Schema

from shared.api_contract.schemas import (
    ListEnvelope,
    ListQueryParams,
    apply_sort,
    paginate,
)
from shared.utils.routing import search_query_helper as search

from platform_api.models.entities import Org, Person
from platform_api.models.presence import OrgPresence, PersonPresence
from platform_api.routers import PlatformRoute

router = Router(tags=["public-people"])

# region --- Schemas ---


class OrgOut(Schema):
    id: UUID
    name: str
    type: int
    country_id: str
    home_geo_place_id: UUID | None = None


class OrgSearchOut(Schema):
    id: UUID
    name: str
    short_name: Optional[str] = None
    type: int
    country_id: str


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


class PersonSearchOut(Schema):
    id: UUID
    given_name: str
    family_name: str
    nickname: Optional[str] = None
    full_name: str
    primary_nationality_id: str
    sporting_nationality_id: Optional[str] = None
    sex: int


class PersonListParams(ListQueryParams):
    primary_nationality_id: str | None = None
    sex: int | None = Field(default=None, ge=1, le=3)


class PresenceOut(Schema):
    sport_key: str
    vertical_entity_id: UUID


# endregion

# region --- ORG Endpoints ---

org_ep = PlatformRoute(Org)


@router.get(org_ep.list_short_url, response=ListEnvelope[OrgOut])
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


@router.get(org_ep.retrieve_short_url, response=OrgOut)
def get_org(request, id: UUID):
    return get_object_or_404(Org, pk=id)


@router.get(org_ep.search_short_url, response=ListEnvelope[OrgSearchOut])
def search_orgs(request, q: str = Query(..., min_length=1)):
    def query(param):
        return (
            Org.objects.filter(
                Q(name__icontains=param) | Q(short_name__icontains=param)
            )
            .annotate(
                search_rank=Case(
                    When(name__iexact=param, then=Value(0)),
                    When(short_name__iexact=param, then=Value(0)),
                    When(name__istartswith=param, then=Value(1)),
                    When(short_name__istartswith=param, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .order_by("search_rank", "name", "id")
        )

    return search(q, query)


@router.get(org_ep.presence_retrieve_url, response=ListEnvelope[PresenceOut])
def list_org_presences(request, id: UUID, sport_key: str | None = None):
    get_object_or_404(Org, id=id)

    qs = OrgPresence.objects.filter(org_id=id)

    if sport_key:
        qs = qs.filter(sport_id=sport_key)

    qs = qs.order_by("sport_id", "vertical_entity_id")
    items = [
        PresenceOut(
            sport_key=row.sport_id,
            vertical_entity_id=row.vertical_entity_id,
        )
        for row in qs.order_by("sport_id", "vertical_entity_id")
    ]

    return {
        "items": items,
        "total": len(items),
        "limit": len(items),
        "offset": 0,
        "sort": None,
    }


# endregion

# region --- PERSON Endpoints ---

person_ep = PlatformRoute(Person)


@router.get(person_ep.list_short_url, response=ListEnvelope[PersonOut])
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


@router.get(person_ep.retrieve_short_url, response=PersonOut)
def get_person(request, id: UUID):
    return get_object_or_404(Person, pk=id)


@router.get(person_ep.search_short_url, response=ListEnvelope[PersonSearchOut])
def search_persons(request, q: str = Query(..., min_length=1)):
    def query(param):
        return (
            Person.objects.filter(
                Q(given_name__icontains=param)
                | Q(family_name__icontains=param)
                | Q(nickname__icontains=param)
            )
            .annotate(
                search_rank=Case(
                    When(nickname__iexact=param, then=Value(0)),
                    When(given_name__iexact=param, then=Value(0)),
                    When(family_name__iexact=param, then=Value(0)),
                    When(nickname__istartswith=param, then=Value(1)),
                    When(given_name__istartswith=param, then=Value(1)),
                    When(family_name__istartswith=param, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                ),
            )
            .order_by("search_rank", "family_name", "given_name", "id")
        )

    return search(q, query)


@router.get(person_ep.presence_retrieve_url, response=ListEnvelope[PresenceOut])
def list_person_presences(request, id: UUID, sport_key: str | None = None):
    get_object_or_404(Person, id=id)

    qs = PersonPresence.objects.filter(person_id=id)

    if sport_key:
        qs = qs.filter(sport_id=sport_key)

    qs = qs.order_by("sport_id", "vertical_entity_id")
    items = [
        PresenceOut(
            sport_key=row.sport_id,
            vertical_entity_id=row.vertical_entity_id,
        )
        for row in qs.order_by("sport_id", "vertical_entity_id")
    ]

    return {
        "items": items,
        "total": len(items),
        "limit": len(items),
        "offset": 0,
        "sort": None,
    }


# endregion
