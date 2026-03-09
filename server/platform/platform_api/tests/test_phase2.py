from http import HTTPStatus
import uuid
from django.test import TestCase

from server.shared.utils.testing import assert_list_envelope

from platform_api.models.geo import Country, GeoPlace
from platform_api.models.entities import Sport
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


# endregion

# region --- Tests -------------------------------------------------------------------


class PublicCoreReadOnlyAPITests(TestCase):
    """
    Phase 2.1 baseline:
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
    """Phase 2.2: GeoPlace read-only endpoints (list/detail + filter)."""

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


# endregion
