import uuid

from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from django.test import TestCase

from shared.utils.testing import print_exit, subtest

from platform_api.models.geo import Country
from platform_api.models.entities import (
    Sport,
    Person,
    Org,
    OrgType,
)
from platform_api.models.presence import (
    PersonPresence,
    OrgPresence,
)


def _mk_country():
    # Country PK = iso2
    return Country.objects.create(
        iso2="IT",
        iso3="ITA",
        numeric_code="380",
        name_en="Italy",
        name_local="Italia",
    )


def _mk_sport():
    # Sport PK = key
    return Sport.objects.create(key="volley", name_en="Volleyball")


def _mk_user(username="tester"):
    User = get_user_model()
    return User.objects.create_user(username=username, password="pass1234")


class TimestampContractTests(TestCase):
    @print_exit("Timestamps - immutable ts_creation, modified ts_last_update")
    def test_ts_contract(self):
        test_sport = _mk_sport()
        t0 = test_sport.ts_creation
        u0 = test_sport.ts_last_update

        test_sport.name_en = "Volleyball (updated)"
        test_sport.save()
        test_sport.refresh_from_db()

        self.assertEqual(test_sport.ts_creation, t0)
        self.assertGreater(test_sport.ts_last_update, u0)


class PresenceConstraintTests(TestCase):
    @print_exit("Presence constraints")
    def test_presence_constraints(self):
        test_country = _mk_country()
        test_sport = _mk_sport()

        with subtest(
            self, "PersonPresence - unique(person, sport, vertical_entity_id)"
        ):
            person = Person.objects.create(
                given_name="Ada",
                family_name="Lovelace",
                primary_nationality=test_country,
            )
            vid = uuid.uuid4()

            PersonPresence.objects.create(
                person=person, sport=test_sport, vertical_entity_id=vid
            )

            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    PersonPresence.objects.create(
                        person=person, sport=test_sport, vertical_entity_id=vid
                    )

        with subtest(self, "OrgPresence - unique(org, sport, vertical_entity_id)"):
            org = Org.objects.create(
                type=OrgType.CLUB,
                name="AC Test Club",
                short_name="TestClub",
                country=test_country,
            )
            vid = uuid.uuid4()

            OrgPresence.objects.create(
                org=org, sport=test_sport, vertical_entity_id=vid
            )

            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    OrgPresence.objects.create(
                        org=org, sport=test_sport, vertical_entity_id=vid
                    )
