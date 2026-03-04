import uuid

from django.test import TestCase, TransactionTestCase
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model

from platform_api.models.geo import Country  # :contentReference[oaicite:1]{index=1}
from platform_api.models.entities import (
    Sport,
    Person,
    Org,
    OrgType,
)  # :contentReference[oaicite:2]{index=2}
from platform_api.models.presence import (
    PersonPresence,
    OrgPresence,
)  # :contentReference[oaicite:3]{index=3}
from platform_api.models.inbox import (  # :contentReference[oaicite:4]{index=4}
    EditRequestsInbox,
    EditRequestsInboxEvent,
    EntityType,
    RequestedAction,
    RequestStatus,
    EventType,
)

from .common import ok


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
    def test_ts_contract(self):
        test_sport = _mk_sport()
        t0 = test_sport.ts_creation
        u0 = test_sport.ts_last_update

        test_sport.name_en = "Volleyball (updated)"
        test_sport.save()
        test_sport.refresh_from_db()

        self.assertEqual(test_sport.ts_creation, t0)
        self.assertGreater(test_sport.ts_last_update, u0)

        ok("Timestamps: immutable ts_creation, modified ts_last_update")


class PresenceConstraintTests(TestCase):
    def test_presence_constraints(self):
        test_country = _mk_country()
        test_sport = _mk_sport()

        with self.subTest("PersonPresence: unique(person, sport, vertical_entity_id)"):
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

            ok("PersonPresence unique constraint")

        with self.subTest("OrgPresence: unique(org, sport, vertical_entity_id)"):
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

            ok("OrgPresence unique constraint")


class InboxFlowTests(TransactionTestCase):
    def test_inbox_contracts(self):
        with self.subTest("Inbox CREATE: auto event CREATED on commit"):
            user = _mk_user("inbox_tester1")
            sport = _mk_sport()

            req = EditRequestsInbox.objects.create(
                entity_type=EntityType.PERSON,
                action=RequestedAction.CREATE,
                status=RequestStatus.PENDING,
                sport=sport,
                vertical_entity_id=uuid.uuid4(),
                target_entity_id=None,  # ok for CREATE :contentReference[oaicite:1]{index=1}
                payload={"given_name": "Ada", "family_name": "Lovelace"},
                created_by=user,
            )

            created_events = EditRequestsInboxEvent.objects.filter(
                request=req, event_type=EventType.CREATED
            )
            self.assertEqual(created_events.count(), 1)
            self.assertEqual(created_events.first().actor_id, user.id)

            ok("Inbox: CREATE -> event CREATED")

        with self.subTest("Inbox UPDATE: target required (check constraint)"):
            user = _mk_user("inbox_tester2")

            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    EditRequestsInbox.objects.create(
                        entity_type=EntityType.PERSON,
                        action=RequestedAction.UPDATE,
                        status=RequestStatus.PENDING,
                        target_entity_id=None,  # NOT allowed for UPDATE/MERGE :contentReference[oaicite:2]{index=2}
                        payload={"nickname": "NewNick"},
                        created_by=user,
                    )

            ok("Inbox: UPDATE but no target -> blocked")
