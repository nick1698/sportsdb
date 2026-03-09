from http import HTTPStatus
import uuid
from django.test import TestCase

from shared.utils.testing import assert_list_envelope

from platform_api.models.geo import Country, GeoPlace, Venue
from platform_api.models.entities import Org, Person, Sport
from platform_api.routers import PlatformRoute

from .common import ok


# region --- Factory helpers (same style as Phase 1) ---------------------------------


def _mk_country(
    iso2="IT", iso3="ITA", numeric_code="380", name_en="Italy", name_local="Italia"
):
    # Country PK = iso2
    return Country.objects.create(
        iso2=iso2,
        iso3=iso3,
        numeric_code=numeric_code,
        name_en=name_en,
        name_local=name_local,
    )


def _mk_geo_place(
    country: Country,
    name: str,
    normalized_name: str,
    *,
    kind: str = "locality",
    parent: GeoPlace | None = None,
):
    return GeoPlace.objects.create(
        country=country,
        parent=parent,
        name=name,
        normalized_name=normalized_name,
        kind=kind,
    )


def _mk_sport(key="volley", name_en="Volleyball"):
    # Sport PK = key
    return Sport.objects.create(key=key, name_en=name_en)


def _mk_venue(
    *,
    name="Arena Civica",
    country: Country,
    geo_place: GeoPlace | None = None,
    lat=None,
    lon=None,
):
    return Venue.objects.create(
        name=name,
        country=country,
        geo_place=geo_place,
        lat=lat,
        lon=lon,
    )


def _mk_org(
    *,
    name="ACME Club",
    org_type=1,
    country: Country,
    home_geo_place: GeoPlace | None = None,
):
    return Org.objects.create(
        name=name,
        type=org_type,
        country=country,
        home_geo_place=home_geo_place,
    )


def _mk_person(
    *,
    given_name="Mario",
    family_name="Rossi",
    nickname=None,
    sex=1,
    primary_nationality: Country,
    sporting_nationality: Country | None = None,
    birth_date=None,
    death_date=None,
):
    return Person.objects.create(
        given_name=given_name,
        family_name=family_name,
        nickname=nickname,
        sex=sex,
        primary_nationality=primary_nationality,
        sporting_nationality=sporting_nationality,
        birth_date=birth_date,
        death_date=death_date,
    )


# endregion

# region --- Tests -------------------------------------------------------------------


class PublicCoreReadOnlyAPITests(TestCase):
    """
    Phase 7.2.0:
      - Read-only list/detail for countries & sports
      - Pagination envelope keys exist
      - Sorting works (MVP)
    """

    def setUp(self):
        _ = _mk_country(iso2="IT")
        _ = _mk_country(
            iso2="NL",
            iso3="NLD",
            numeric_code="528",
            name_en="Netherlands",
            name_local="Nederland",
        )

        _mk_sport("volley", "Volleyball")
        _mk_sport("football", "Football")

    def test_public_core_api_contract(self):
        country_ep = PlatformRoute(Country)
        with self.subTest(f"GET {country_ep.base} -> envelope + pagination"):
            r = self.client.get(country_ep.list(limit=1, offset=0))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data, limit=1, offset=0)
            self.assertIn("sort", data)

            self.assertEqual(data["total"], 2)
            self.assertEqual(len(data["items"]), 1)

            ok("API Countries list: envelope + pagination")

        with self.subTest(f"GET {country_ep.base_id} -> 200 + payload"):
            r = self.client.get(country_ep.retrieve("IT"))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["iso2"], "IT")
            self.assertIn("name_en", data)

            ok("API Country detail: returns entity")

        with self.subTest(f"GET {country_ep.base_id} -> 404 if missing"):
            r = self.client.get(country_ep.retrieve("ZZ"))
            self.assertEqual(r.status_code, HTTPStatus.NOT_FOUND)

            ok("API Country detail: 404 on missing")

        sport_ep = PlatformRoute(Sport)
        with self.subTest(f"GET {sport_ep.base} -> sort by key"):
            r = self.client.get(sport_ep.list(sort="key"))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data)
            self.assertIn("sort", data)

            keys = [x["key"] for x in data["items"]]
            self.assertEqual(keys, sorted(keys))

            ok("API Sports list: sorting by key")

        with self.subTest(f"GET {sport_ep.base_id} -> 200 + payload"):
            r = self.client.get(sport_ep.retrieve("volley"))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["key"], "volley")
            self.assertIn("name_en", data)

            ok("API Sport detail: returns entity")

        with self.subTest("GET /api/core/sports/{key} -> 404 if missing"):
            r = self.client.get(sport_ep.retrieve("not-a-sport"))
            self.assertEqual(r.status_code, HTTPStatus.NOT_FOUND)

            ok("API Sport detail: 404 on missing")


class GeoPlacesReadOnlyAPITests(TestCase):
    """Phase 7.2.1: GeoPlace read-only endpoints (list/detail + filter)"""

    def setUp(self):
        it = _mk_country()
        nl = _mk_country(
            iso2="NL",
            iso3="NLD",
            numeric_code="528",
            name_en="Netherlands",
            name_local="Nederland",
        )

        _mk_geo_place(it, "Milano", "milano", kind="locality")
        _mk_geo_place(it, "Lombardia", "lombardia", kind="region")
        _mk_geo_place(nl, "Utrecht", "utrecht", kind="locality")

    def test_geo_places_api_contract(self):
        geoplace_ep = PlatformRoute(GeoPlace)
        with self.subTest(f"GET {geoplace_ep.base} -> envelope + pagination"):
            r = self.client.get(geoplace_ep.list(limit=2, offset=0))
            self.assertEqual(r.status_code, 200)

            data = r.json()
            assert_list_envelope(data, limit=2, offset=0)
            self.assertIn("sort", data)

            self.assertEqual(data["total"], 3)
            self.assertEqual(len(data["items"]), 2)

            ok("GeoPlace list: envelope + pagination")

        with self.subTest(f"GET {geoplace_ep.base} -> filter by country_id"):
            r = self.client.get(geoplace_ep.list(country_id="IT"))
            self.assertEqual(r.status_code, 200)
            data = r.json()

            self.assertEqual(data["total"], 2)
            self.assertTrue(all(item["country_id"] == "IT" for item in data["items"]))

            ok("GeoPlace list: country_id filter")

        with self.subTest(f"GET {geoplace_ep.base_id} -> 200"):
            gp = GeoPlace.objects.first()
            r = self.client.get(geoplace_ep.retrieve(gp.id))
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["id"], str(gp.id))
            self.assertIn("name", data)
            self.assertIn("kind", data)
            self.assertIn("country_id", data)

            ok("GeoPlace detail: returns entity")

        with self.subTest(f"GET {geoplace_ep.base_id} -> 404 if missing"):
            r = self.client.get(geoplace_ep.retrieve(uuid.uuid4()))
            self.assertEqual(r.status_code, 404)

            ok("GeoPlace detail: 404 on missing")


class CoreEntitiesReadOnlyAPITests(TestCase):
    """Phase 2.3: Venue / Org / Person read-only endpoints."""

    def setUp(self):
        self.it = _mk_country()
        self.nl = _mk_country(
            iso2="NL",
            iso3="NLD",
            numeric_code="528",
            name_en="Netherlands",
            name_local="Nederland",
        )

        self.milano = _mk_geo_place(self.it, "Milano", "milano", kind="locality")
        self.utrecht = _mk_geo_place(self.nl, "Utrecht", "utrecht", kind="locality")

        self.venue_it = _mk_venue(
            name="Arena Milano",
            country=self.it,
            geo_place=self.milano,
        )
        self.venue_nl = _mk_venue(
            name="Utrecht Hall",
            country=self.nl,
            geo_place=self.utrecht,
        )

        self.org_it = _mk_org(
            name="Volley Milano",
            org_type=1,
            country=self.it,
            home_geo_place=self.milano,
        )
        self.org_nl = _mk_org(
            name="Utrecht United",
            org_type=2,
            country=self.nl,
            home_geo_place=self.utrecht,
        )

        self.person_it = _mk_person(
            given_name="Giulia",
            family_name="Rossi",
            sex=2,
            primary_nationality=self.it,
        )
        self.person_nl = _mk_person(
            given_name="Anouk",
            family_name="De Vries",
            sex=2,
            primary_nationality=self.nl,
        )
        self.person_m = _mk_person(
            given_name="Marco",
            family_name="Bianchi",
            sex=1,
            primary_nationality=self.it,
        )

    def test_venue_api_contract(self):
        venue_ep = PlatformRoute(Venue)

        with self.subTest(f"GET {venue_ep.base} -> envelope + pagination"):
            r = self.client.get(venue_ep.list(limit=1, offset=0))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data, limit=1, offset=0)
            self.assertIn("sort", data)
            self.assertEqual(data["total"], 2)
            self.assertEqual(len(data["items"]), 1)

            ok("API Venues list: envelope + pagination")

        with self.subTest(f"GET {venue_ep.base} -> filter by country_id"):
            r = self.client.get(venue_ep.list(country_id="IT"))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["id"], str(self.venue_it.id))
            self.assertEqual(data["items"][0]["country_id"], "IT")

            ok("API Venues list: country_id filter")

        with self.subTest(f"GET {venue_ep.base} -> filter by geo_place_id"):
            r = self.client.get(venue_ep.list(geo_place_id=self.milano.id))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["id"], str(self.venue_it.id))

            ok("API Venues list: geo_place_id filter")

        with self.subTest(f"GET {venue_ep.base_id} -> 200 + payload"):
            r = self.client.get(venue_ep.retrieve(self.venue_it.id))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["id"], str(self.venue_it.id))
            self.assertEqual(data["name"], "Arena Milano")
            self.assertEqual(data["country_id"], "IT")

            ok("API Venue detail: returns entity")

        with self.subTest(f"GET {venue_ep.base_id} -> 404 if missing"):
            r = self.client.get(venue_ep.retrieve(uuid.uuid4()))
            self.assertEqual(r.status_code, HTTPStatus.NOT_FOUND)

            ok("API Venue detail: 404 on missing")

    def test_org_api_contract(self):
        org_ep = PlatformRoute(Org)

        with self.subTest(f"GET {org_ep.base} -> envelope + pagination"):
            r = self.client.get(org_ep.list(limit=1, offset=0))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data, limit=1, offset=0)
            self.assertIn("sort", data)
            self.assertEqual(data["total"], 2)
            self.assertEqual(len(data["items"]), 1)

            ok("API Orgs list: envelope + pagination")

        with self.subTest(f"GET {org_ep.base} -> filter by country_id"):
            r = self.client.get(org_ep.list(country_id="IT"))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["id"], str(self.org_it.id))
            self.assertEqual(data["items"][0]["country_id"], "IT")

            ok("API Orgs list: country_id filter")

        with self.subTest(f"GET {org_ep.base} -> filter by type"):
            r = self.client.get(org_ep.list(type=2))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["id"], str(self.org_nl.id))
            self.assertEqual(data["items"][0]["type"], 2)

            ok("API Orgs list: type filter")

        with self.subTest(f"GET {org_ep.base_id} -> 200 + payload"):
            r = self.client.get(org_ep.retrieve(self.org_it.id))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["id"], str(self.org_it.id))
            self.assertEqual(data["name"], "Volley Milano")
            self.assertEqual(data["country_id"], "IT")

            ok("API Org detail: returns entity")

        with self.subTest(f"GET {org_ep.base_id} -> 404 if missing"):
            r = self.client.get(org_ep.retrieve(uuid.uuid4()))
            self.assertEqual(r.status_code, HTTPStatus.NOT_FOUND)

            ok("API Org detail: 404 on missing")

    def test_person_api_contract(self):
        person_ep = PlatformRoute(Person)

        with self.subTest(f"GET {person_ep.base} -> envelope + pagination"):
            r = self.client.get(person_ep.list(limit=2, offset=0))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data, limit=2, offset=0)
            self.assertIn("sort", data)
            self.assertEqual(data["total"], 3)
            self.assertEqual(len(data["items"]), 2)

            ok("API Persons list: envelope + pagination")

        with self.subTest(f"GET {person_ep.base} -> filter by primary_nationality_id"):
            r = self.client.get(person_ep.list(primary_nationality_id="IT"))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["total"], 2)
            self.assertTrue(
                all(item["primary_nationality_id"] == "IT" for item in data["items"])
            )

            ok("API Persons list: primary_nationality_id filter")

        with self.subTest(f"GET {person_ep.base} -> filter by sex"):
            r = self.client.get(person_ep.list(sex=1))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["id"], str(self.person_m.id))
            self.assertEqual(data["items"][0]["sex"], 1)

            ok("API Persons list: sex filter")

        with self.subTest(f"GET {person_ep.base_id} -> 200 + payload"):
            r = self.client.get(person_ep.retrieve(self.person_it.id))
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["id"], str(self.person_it.id))
            self.assertEqual(data["given_name"], "Giulia")
            self.assertEqual(data["family_name"], "Rossi")
            self.assertEqual(data["primary_nationality_id"], "IT")

            ok("API Person detail: returns entity")

        with self.subTest(f"GET {person_ep.base_id} -> 404 if missing"):
            r = self.client.get(person_ep.retrieve(uuid.uuid4()))
            self.assertEqual(r.status_code, HTTPStatus.NOT_FOUND)

            ok("API Person detail: 404 on missing")

    def test_venue_list_invalid_sort_returns_400(self):
        venue_ep = PlatformRoute(Venue)

        r = self.client.get(venue_ep.list(sort="not_a_real_field"))
        self.assertEqual(r.status_code, HTTPStatus.BAD_REQUEST)

        data = r.json()
        self.assertIn("error", data)
        self.assertIn("code", data["error"])

        ok("API Venues list: invalid sort returns 400")

    def test_person_list_invalid_sex_returns_422(self):
        person_ep = PlatformRoute(Person)

        r = self.client.get(person_ep.list(sex=99))
        self.assertEqual(r.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)

        data = r.json()
        self.assertIn("error", data)
        self.assertIn("code", data["error"])

        ok("API Persons list: invalid sex returns 422")


# endregion
