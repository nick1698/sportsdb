# server/platform/platform_api/tests/test_phase2.py

import uuid

from django.test import TestCase
from http import HTTPStatus

from platform_api.models.geo import Country
from platform_api.models.entities import Sport

from .common import ok


# --- Factory helpers (same style as Phase 1) ---------------------------------


def _mk_country(iso2="IT", name_en="Italy"):
    # Country PK = iso2
    return Country.objects.create(
        iso2=iso2,
        iso3=(iso2 + "A")[
            :3
        ],  # minimal placeholder, adjust if your model requires strict iso3
        numeric_code=str(uuid.uuid4().int)[:3].zfill(
            3
        ),  # minimal placeholder, adjust if needed
        name_en=name_en,
        name_local=name_en,
    )


def _mk_sport(key="volley", name_en="Volleyball"):
    # Sport PK = key
    return Sport.objects.create(key=key, name_en=name_en)


# --- Tests -------------------------------------------------------------------


class PublicCoreReadOnlyAPITests(TestCase):
    """
    Phase 2 baseline:
      - Read-only list/detail for countries & sports
      - Pagination envelope keys exist
      - Sorting works (MVP)
    """

    def setUp(self):
        # Countries
        _mk_country("IT", "Italy")
        _mk_country("NL", "Netherlands")

        # Sports
        _mk_sport("volley", "Volleyball")
        _mk_sport("football", "Football")

    def test_public_core_api_contract(self):
        with self.subTest("GET /api/countries -> envelope + pagination"):
            r = self.client.get("/api/countries?limit=1&offset=0")
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertIn("items", data)
            self.assertIn("limit", data)
            self.assertIn("offset", data)
            self.assertIn("total", data)
            self.assertIn("sort", data)

            self.assertEqual(data["limit"], 1)
            self.assertEqual(data["offset"], 0)
            self.assertEqual(data["total"], 2)
            self.assertEqual(len(data["items"]), 1)

            ok("API Countries list: envelope + pagination")

        with self.subTest("GET /api/countries/{iso2} -> 200 + payload"):
            r = self.client.get("/api/countries/IT")
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["iso2"], "IT")
            self.assertIn("name_en", data)

            ok("API Country detail: returns entity")

        with self.subTest("GET /api/countries/{iso2} -> 404 if missing"):
            r = self.client.get("/api/countries/ZZ")
            self.assertEqual(r.status_code, HTTPStatus.NOT_FOUND)

            ok("API Country detail: 404 on missing")

        with self.subTest("GET /api/sports -> sort by key"):
            r = self.client.get("/api/sports?sort=key")
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            keys = [x["key"] for x in data["items"]]
            self.assertEqual(keys, sorted(keys))

            ok("API Sports list: sorting by key")

        with self.subTest("GET /api/sports/{key} -> 200 + payload"):
            r = self.client.get("/api/sports/volley")
            self.assertEqual(r.status_code, HTTPStatus.OK)

            data = r.json()
            self.assertEqual(data["key"], "volley")
            self.assertIn("name_en", data)

            ok("API Sport detail: returns entity")

        with self.subTest("GET /api/sports/{key} -> 404 if missing"):
            r = self.client.get("/api/sports/not-a-sport")
            self.assertEqual(r.status_code, HTTPStatus.NOT_FOUND)

            ok("API Sport detail: 404 on missing")
