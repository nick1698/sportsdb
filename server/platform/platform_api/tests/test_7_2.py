from http import HTTPStatus
import uuid

from django.test import TestCase

from shared.utils.testing import assert_list_envelope, print_exit, subtest

from platform_api.models.entities import Org, Person, Sex, Sport
from platform_api.models.geo import Country, GeoPlace, Venue
from platform_api.models.presence import OrgPresence, PersonPresence
from platform_api.routers import PlatformRoute


# region --- Factory helpers (same style as Phase 1) ---


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
    sex=Sex.MALE,
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


def _mk_orgpresence(*, org, sport, vertical_entity_id=None):
    return OrgPresence.objects.create(
        org=org,
        sport=sport,
        vertical_entity_id=vertical_entity_id or uuid.uuid4(),
    )


def _mk_personpresence(*, person, sport, vertical_entity_id=None):
    return PersonPresence.objects.create(
        person=person,
        sport=sport,
        vertical_entity_id=vertical_entity_id or uuid.uuid4(),
    )


# endregion

# region --- Tests ---


class PublicCoreReadOnlyAPITests(TestCase):
    """Phase 7.2.1: Core API contracts"""

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

    @print_exit("Public core API contracts")
    def test_public_core_api_contract(self):
        country_ep = PlatformRoute(Country)
        with subtest(self, f"GET {country_ep.base} -> envelope + pagination"):
            r = self.client.get(country_ep.list(limit=1, offset=0))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data, limit=1, offset=0)
            self.assertIn("sort", data)

            self.assertEqual(data["total"], 2)
            self.assertEqual(len(data["items"]), 1)

        with subtest(self, f"GET {country_ep.base_id} -> 200 + payload"):
            r = self.client.get(country_ep.retrieve("IT"))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["iso2"], "IT")
            self.assertIn("name_en", data)

        with subtest(self, f"GET {country_ep.base_id} -> 404 if missing"):
            r = self.client.get(country_ep.retrieve("ZZ"))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.NOT_FOUND)

        sport_ep = PlatformRoute(Sport)
        with subtest(self, f"GET {sport_ep.base} -> sort by key"):
            r = self.client.get(sport_ep.list(sort="key"))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data)
            self.assertIn("sort", data)

            keys = [x["key"] for x in data["items"]]
            self.assertEqual(keys, sorted(keys))

        with subtest(self, f"GET {sport_ep.base_id} -> 200 + payload"):
            r = self.client.get(sport_ep.retrieve("volley"))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["key"], "volley")
            self.assertIn("name_en", data)

        with subtest(self, "GET /api/core/sports/{key} -> 404 if missing"):
            r = self.client.get(sport_ep.retrieve("not-a-sport"))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.NOT_FOUND)


class GeoPlacesReadOnlyAPITests(TestCase):
    """Phase 7.2.2: GeoPlace read-only endpoints (list/detail + filter)"""

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

    @print_exit("GeoPlace API contracts")
    def test_geo_places_api_contract(self):
        geoplace_ep = PlatformRoute(GeoPlace)
        with subtest(self, f"GET {geoplace_ep.base} -> envelope + pagination"):
            r = self.client.get(geoplace_ep.list(limit=2, offset=0))
            self.assertEqual(HTTPStatus(r.status_code), 200)

            data = r.json()
            assert_list_envelope(data, limit=2, offset=0)
            self.assertIn("sort", data)

            self.assertEqual(data["total"], 3)
            self.assertEqual(len(data["items"]), 2)

        with subtest(self, f"GET {geoplace_ep.base} -> filter by country_id"):
            r = self.client.get(geoplace_ep.list(country_id="IT"))
            self.assertEqual(HTTPStatus(r.status_code), 200)
            data = r.json()

            self.assertEqual(data["total"], 2)
            self.assertTrue(all(item["country_id"] == "IT" for item in data["items"]))

        with subtest(self, f"GET {geoplace_ep.base_id} -> 200"):
            gp = GeoPlace.objects.first()
            r = self.client.get(geoplace_ep.retrieve(gp.id))
            self.assertEqual(HTTPStatus(r.status_code), 200)
            data = r.json()
            self.assertEqual(data["id"], str(gp.id))
            self.assertIn("name", data)
            self.assertIn("kind", data)
            self.assertIn("country_id", data)

        with subtest(self, f"GET {geoplace_ep.base_id} -> 404 if missing"):
            r = self.client.get(geoplace_ep.retrieve(uuid.uuid4()))
            self.assertEqual(HTTPStatus(r.status_code), 404)


class CoreEntitiesReadOnlyAPITests(TestCase):
    """Phase 7.2.3: Venue / Org / Person read-only endpoints"""

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
            sex=Sex.FEMALE,
            primary_nationality=self.it,
        )
        self.person_nl = _mk_person(
            given_name="Anouk",
            family_name="De Vries",
            sex=Sex.FEMALE,
            primary_nationality=self.nl,
        )
        self.person_m = _mk_person(
            given_name="Marco",
            family_name="Bianchi",
            sex=Sex.MALE,
            primary_nationality=self.it,
        )

    @print_exit("Venue API contracts")
    def test_venue_api_contract(self):
        venue_ep = PlatformRoute(Venue)

        with subtest(self, f"GET {venue_ep.base} -> envelope + pagination"):
            r = self.client.get(venue_ep.list(limit=1, offset=0))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data, limit=1, offset=0)
            self.assertIn("sort", data)
            self.assertEqual(data["total"], 2)
            self.assertEqual(len(data["items"]), 1)

        with subtest(self, f"GET {venue_ep.base} -> filter by country_id"):
            r = self.client.get(venue_ep.list(country_id="IT"))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["id"], str(self.venue_it.id))
            self.assertEqual(data["items"][0]["country_id"], "IT")

        with subtest(self, f"GET {venue_ep.base} -> filter by geo_place_id"):
            r = self.client.get(venue_ep.list(geo_place_id=self.milano.id))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["id"], str(self.venue_it.id))

        with subtest(self, f"GET {venue_ep.base_id} -> 200 + payload"):
            r = self.client.get(venue_ep.retrieve(self.venue_it.id))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["id"], str(self.venue_it.id))
            self.assertEqual(data["name"], "Arena Milano")
            self.assertEqual(data["country_id"], "IT")

        with subtest(self, f"GET {venue_ep.base_id} -> 404 if missing"):
            r = self.client.get(venue_ep.retrieve(uuid.uuid4()))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.NOT_FOUND)

    @print_exit("Org API contracts")
    def test_org_api_contract(self):
        org_ep = PlatformRoute(Org)

        with subtest(self, f"GET {org_ep.base} -> envelope + pagination"):
            r = self.client.get(org_ep.list(limit=1, offset=0))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data, limit=1, offset=0)
            self.assertIn("sort", data)
            self.assertEqual(data["total"], 2)
            self.assertEqual(len(data["items"]), 1)

        with subtest(self, f"GET {org_ep.base} -> filter by country_id"):
            r = self.client.get(org_ep.list(country_id="IT"))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["id"], str(self.org_it.id))
            self.assertEqual(data["items"][0]["country_id"], "IT")

        with subtest(self, f"GET {org_ep.base} -> filter by type"):
            r = self.client.get(org_ep.list(type=2))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["id"], str(self.org_nl.id))
            self.assertEqual(data["items"][0]["type"], 2)

        with subtest(self, f"GET {org_ep.base_id} -> 200 + payload"):
            r = self.client.get(org_ep.retrieve(self.org_it.id))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["id"], str(self.org_it.id))
            self.assertEqual(data["name"], "Volley Milano")
            self.assertEqual(data["country_id"], "IT")

        with subtest(self, f"GET {org_ep.base_id} -> 404 if missing"):
            r = self.client.get(org_ep.retrieve(uuid.uuid4()))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.NOT_FOUND)

    @print_exit("Person API contracts")
    def test_person_api_contract(self):
        person_ep = PlatformRoute(Person)

        with subtest(self, f"GET {person_ep.base} -> envelope + pagination"):
            r = self.client.get(person_ep.list(limit=2, offset=0))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data, limit=2, offset=0)
            self.assertIn("sort", data)
            self.assertEqual(data["total"], 3)
            self.assertEqual(len(data["items"]), 2)

        with subtest(self, f"GET {person_ep.base} -> filter by primary_nationality_id"):
            r = self.client.get(person_ep.list(primary_nationality_id="IT"))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["total"], 2)
            self.assertTrue(
                all(item["primary_nationality_id"] == "IT" for item in data["items"])
            )

        with subtest(self, f"GET {person_ep.base} -> filter by sex"):
            r = self.client.get(person_ep.list(sex=Sex.MALE))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["id"], str(self.person_m.id))
            self.assertEqual(data["items"][0]["sex"], Sex.MALE)

        with subtest(self, f"GET {person_ep.base_id} -> 200 + payload"):
            r = self.client.get(person_ep.retrieve(self.person_it.id))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["id"], str(self.person_it.id))
            self.assertEqual(data["given_name"], "Giulia")
            self.assertEqual(data["family_name"], "Rossi")
            self.assertEqual(data["primary_nationality_id"], "IT")

        with subtest(self, f"GET {person_ep.base_id} -> 404 if missing"):
            r = self.client.get(person_ep.retrieve(uuid.uuid4()))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.NOT_FOUND)

    @print_exit("Venue list invalid sort -> 400")
    def test_venue_list_invalid_sort_returns_400(self):
        venue_ep = PlatformRoute(Venue)

        r = self.client.get(venue_ep.list(sort="not_a_real_field"))
        self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.BAD_REQUEST)

        data = r.json()
        self.assertIn("error", data)
        self.assertIn("code", data["error"])

    @print_exit("Person list invalid sex -> 422")
    def test_person_list_invalid_sex_returns_422(self):
        person_ep = PlatformRoute(Person)

        r = self.client.get(person_ep.list(sex=99))
        self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.UNPROCESSABLE_ENTITY)

        data = r.json()
        self.assertIn("error", data)
        self.assertIn("code", data["error"])


class CoreSearchReadOnlyAPITests(TestCase):
    """Phase 7.2.4: Search MVP for Org / Person"""

    org_ep = PlatformRoute(Org)
    person_ep = PlatformRoute(Person)

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

        # Org fixtures for deterministic ranking: exact > startswith > contains
        self.org_exact = _mk_org(
            name="Milan",
            org_type=1,
            country=self.it,
            home_geo_place=self.milano,
        )
        self.org_starts = _mk_org(
            name="Milan Volley",
            org_type=1,
            country=self.it,
            home_geo_place=self.milano,
        )
        self.org_contains = _mk_org(
            name="New Milan Club",
            org_type=1,
            country=self.it,
            home_geo_place=self.milano,
        )
        self.org_other = _mk_org(
            name="Utrecht United",
            org_type=2,
            country=self.nl,
            home_geo_place=self.utrecht,
        )

        # Person fixtures for deterministic ranking: exact > startswith > contains
        self.person_exact = _mk_person(
            given_name="Anna",
            family_name="Rossi",
            nickname="Mila",
            sex=Sex.FEMALE,
            primary_nationality=self.it,
        )
        self.person_starts = _mk_person(
            given_name="Milan",
            family_name="Bianchi",
            sex=Sex.MALE,
            primary_nationality=self.it,
        )
        self.person_contains = _mk_person(
            given_name="Luca",
            family_name="Di Milano",
            sex=Sex.MALE,
            primary_nationality=self.it,
        )
        self.person_other = _mk_person(
            given_name="Anouk",
            family_name="De Vries",
            sex=Sex.FEMALE,
            primary_nationality=self.nl,
        )

    @print_exit("Org search API contracts")
    def test_org_search_api_contract(self):
        with subtest(
            self, f"GET {self.org_ep.search}?q=... -> envelope + deterministic ranking"
        ):
            r = self.client.get(self.org_ep.search, {"q": "milan"})
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data)
            self.assertEqual(data["total"], 3)
            self.assertEqual(len(data["items"]), 3)

            returned_ids = [item["id"] for item in data["items"]]
            self.assertEqual(
                returned_ids,
                [
                    str(self.org_exact.id),
                    str(self.org_starts.id),
                    str(self.org_contains.id),
                ],
            )

        with subtest(self, f"GET {self.org_ep.search}?q=... -> payload shape"):
            r = self.client.get(self.org_ep.search, {"q": "milan"})
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            first = data["items"][0]

            self.assertIn("id", first)
            self.assertIn("name", first)
            self.assertIn("type", first)
            self.assertIn("country_id", first)

        with subtest(
            self, f"GET {self.org_ep.search}?q=... -> empty result if no match"
        ):
            r = self.client.get(self.org_ep.search, {"q": "zzzzzz"})
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data)
            self.assertEqual(data["total"], 0)
            self.assertEqual(data["items"], [])

    @print_exit("Person search API contracts")
    def test_person_search_api_contract(self):
        with subtest(
            self,
            f"GET {self.person_ep.search}?q=... -> envelope + deterministic ranking",
        ):
            r = self.client.get(self.person_ep.search, {"q": "mila"})
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data)
            self.assertEqual(data["total"], 3)
            self.assertEqual(len(data["items"]), 3)

            returned_ids = [item["id"] for item in data["items"]]
            self.assertEqual(
                returned_ids,
                [
                    str(self.person_exact.id),
                    str(self.person_starts.id),
                    str(self.person_contains.id),
                ],
            )

        with subtest(self, f"GET {self.person_ep.search}?q=... -> payload shape"):
            r = self.client.get(self.person_ep.search, {"q": "mila"})
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            first = data["items"][0]

            self.assertIn("id", first)
            self.assertIn("given_name", first)
            self.assertIn("family_name", first)
            self.assertIn("full_name", first)
            self.assertIn("nickname", first)
            self.assertIn("sex", first)
            self.assertIn("primary_nationality_id", first)

        with subtest(
            self, f"GET {self.person_ep.search}?q=... -> empty result if no match"
        ):
            r = self.client.get(self.person_ep.search, {"q": "zzzzzz"})
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data)
            self.assertEqual(data["total"], 0)
            self.assertEqual(data["items"], [])

    @print_exit("Search invalid query -> 422")
    def test_search_empty_query_returns_422(self):
        with subtest(self, f"GET {self.org_ep.search}?q='' -> 422"):
            r = self.client.get(self.org_ep.search, {"q": ""})
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.UNPROCESSABLE_ENTITY)

            data = r.json()
            self.assertIn("error", data)
            self.assertIn("code", data["error"])

        with subtest(self, f"GET {self.person_ep.search}?q='' -> 422"):
            r = self.client.get(self.person_ep.search, {"q": ""})
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.UNPROCESSABLE_ENTITY)

            data = r.json()
            self.assertIn("error", data)
            self.assertIn("code", data["error"])


class CorePresencesReadOnlyAPITests(TestCase):
    """Phase 7.2.5: Presence read-only nested endpoints"""

    org_ep = PlatformRoute(Org)
    person_ep = PlatformRoute(Person)

    def setUp(self):
        self.it = _mk_country()
        self.nl = _mk_country(
            iso2="NL",
            iso3="NLD",
            numeric_code="528",
            name_en="Netherlands",
            name_local="Nederland",
        )

        self.volley = _mk_sport("volley", "Volleyball")
        self.football = _mk_sport("football", "Football")

        self.org = _mk_org(
            name="Volley Milano",
            org_type=1,
            country=self.it,
        )
        self.person = _mk_person(
            given_name="Giulia",
            family_name="Rossi",
            sex=Sex.FEMALE,
            primary_nationality=self.it,
        )

        self.org_volley_presence_id = uuid.uuid4()
        self.org_football_presence_id = uuid.uuid4()
        self.person_volley_presence_id = uuid.uuid4()
        self.person_football_presence_id = uuid.uuid4()

        _mk_orgpresence(
            org=self.org,
            sport=self.volley,
            vertical_entity_id=self.org_volley_presence_id,
        )
        _mk_orgpresence(
            org=self.org,
            sport=self.football,
            vertical_entity_id=self.org_football_presence_id,
        )

        _mk_personpresence(
            person=self.person,
            sport=self.volley,
            vertical_entity_id=self.person_volley_presence_id,
        )
        _mk_personpresence(
            person=self.person,
            sport=self.football,
            vertical_entity_id=self.person_football_presence_id,
        )

    @print_exit("Org presences API contracts")
    def test_org_presences_api_contract(self):
        with subtest(self, f"GET {self.org_ep.presence_base} -> envelope + payload"):
            r = self.client.get(self.org_ep.presence(self.org.id))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data)
            self.assertIn("sort", data)

            self.assertEqual(data["total"], 2)
            self.assertEqual(len(data["items"]), 2)

            returned_sport_keys = [item["sport_key"] for item in data["items"]]
            self.assertEqual(returned_sport_keys, ["football", "volley"])

            returned_vertical_ids = [
                item["vertical_entity_id"] for item in data["items"]
            ]
            self.assertEqual(
                returned_vertical_ids,
                [
                    str(self.org_football_presence_id),
                    str(self.org_volley_presence_id),
                ],
            )

        with subtest(self, f"GET {self.org_ep.presence_base}?sport_key=... -> filter"):
            r = self.client.get(self.org_ep.presence(self.org.id, sport_key="volley"))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data)

            self.assertEqual(data["total"], 1)
            self.assertEqual(len(data["items"]), 1)
            self.assertEqual(data["items"][0]["sport_key"], "volley")
            self.assertEqual(
                data["items"][0]["vertical_entity_id"],
                str(self.org_volley_presence_id),
            )

        with subtest(self, f"GET {self.org_ep.presence_base} -> 404 if org missing"):
            r = self.client.get(self.org_ep.presence(uuid.uuid4()))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.NOT_FOUND)

    @print_exit("Person presences API contracts")
    def test_person_presences_api_contract(self):
        with subtest(self, f"GET {self.person_ep.presence_base} -> envelope + payload"):
            r = self.client.get(self.person_ep.presence(self.person.id))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data)
            self.assertIn("sort", data)

            self.assertEqual(data["total"], 2)
            self.assertEqual(len(data["items"]), 2)

            returned_sport_keys = [item["sport_key"] for item in data["items"]]
            self.assertEqual(returned_sport_keys, ["football", "volley"])

            returned_vertical_ids = [
                item["vertical_entity_id"] for item in data["items"]
            ]
            self.assertEqual(
                returned_vertical_ids,
                [
                    str(self.person_football_presence_id),
                    str(self.person_volley_presence_id),
                ],
            )

        with subtest(
            self, f"GET {self.person_ep.presence_base}?sport_key=... -> filter"
        ):
            r = self.client.get(
                self.person_ep.presence(self.person.id, sport_key="football")
            )
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.OK)

            data = r.json()
            assert_list_envelope(data)

            self.assertEqual(data["total"], 1)
            self.assertEqual(len(data["items"]), 1)
            self.assertEqual(data["items"][0]["sport_key"], "football")
            self.assertEqual(
                data["items"][0]["vertical_entity_id"],
                str(self.person_football_presence_id),
            )

        with subtest(
            self, f"GET {self.person_ep.presence_base} -> 404 if person missing"
        ):
            r = self.client.get(self.person_ep.presence(uuid.uuid4()))
            self.assertEqual(HTTPStatus(r.status_code), HTTPStatus.NOT_FOUND)


# endregion
