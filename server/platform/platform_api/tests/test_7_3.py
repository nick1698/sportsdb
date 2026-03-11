from datetime import UTC, datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from shared.utils.testing import print_exit, subtest

from platform_api.models.entities import Sport
from platform_api.models.inbox import (
    EditRequestsInbox,
    EditRequestsInboxEvent,
    EntityType,
    EventType,
    RequestedAction,
    RequestStatus,
)


def _mk_sport(key="volley", name_en="Volleyball"):
    return Sport.objects.create(key=key, name_en=name_en)


def _mk_user(username="nick", email="nick@example.com", password="testpass123"):
    User = get_user_model()
    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )


class InboxModelContractTests(TestCase):
    """Phase 7.3.1: Inbox Django model contract freeze"""

    def setUp(self):
        self.user = _mk_user()
        self.reviewer = _mk_user(
            username="reviewer",
            email="reviewer@example.com",
        )
        self.volley = _mk_sport("volley", "Volleyball")

    @print_exit("Inbox model API/contracts")
    def test_edit_requests_inbox_model_contract(self):
        with subtest(self, "EditRequestsInbox -> db table + enum contract"):
            self.assertEqual(EditRequestsInbox._meta.db_table, "edit_requests_inbox")

            self.assertEqual(
                {choice for choice, _ in EntityType.choices},
                {"Person", "Org", "Location", "Venue"},
            )
            self.assertEqual(
                {choice for choice, _ in RequestedAction.choices},
                {"Create", "Update", "Merge"},
            )
            self.assertEqual(
                {choice for choice, _ in RequestStatus.choices},
                {"Pending", "Approved", "Rejected", "Duplicate", "Applied"},
            )

        with subtest(self, "EditRequestsInbox -> field nullability/defaults"):
            status_field = EditRequestsInbox._meta.get_field("status")
            vertical_entity_id_field = EditRequestsInbox._meta.get_field(
                "vertical_entity_id"
            )
            target_entity_id_field = EditRequestsInbox._meta.get_field(
                "target_entity_id"
            )
            payload_field = EditRequestsInbox._meta.get_field("payload")
            created_by_field = EditRequestsInbox._meta.get_field("created_by")
            finalised_by_field = EditRequestsInbox._meta.get_field("finalised_by")
            sport_field = EditRequestsInbox._meta.get_field("sport")

            self.assertEqual(status_field.default, RequestStatus.PENDING)

            self.assertFalse(vertical_entity_id_field.null)
            self.assertTrue(target_entity_id_field.null)
            self.assertFalse(payload_field.null)
            self.assertFalse(created_by_field.null)
            self.assertTrue(finalised_by_field.null)
            self.assertTrue(sport_field.null)

        with subtest(self, "EditRequestsInbox -> indexes contract"):
            index_names = {idx.name for idx in EditRequestsInbox._meta.indexes}
            self.assertIn("ix_inbox_status_type", index_names)
            self.assertIn("ix_inbox_sport", index_names)
            self.assertIn("ix_inbox_target", index_names)
            self.assertIn("ix_inbox_vertical_entity", index_names)

        with subtest(self, "EditRequestsInbox -> constraints contract"):
            constraint_names = {
                constraint.name for constraint in EditRequestsInbox._meta.constraints
            }
            self.assertIn(
                "ck_inbox_review_completed_after_taken_in_charge",
                constraint_names,
            )
            self.assertIn(
                "ck_inbox_target_required_for_update_merge",
                constraint_names,
            )

    @print_exit("Inbox event model contracts")
    def test_edit_requests_inbox_event_model_contract(self):
        with subtest(self, "EditRequestsInboxEvent -> db table + enum contract"):
            self.assertEqual(
                EditRequestsInboxEvent._meta.db_table,
                "edit_requests_inbox_event",
            )
            self.assertEqual(
                {choice for choice, _ in EventType.choices},
                {"Created", "Approved", "Rejected", "Comment", "Reviewed", "Applied"},
            )

        with subtest(self, "EditRequestsInboxEvent -> indexes contract"):
            index_names = {idx.name for idx in EditRequestsInboxEvent._meta.indexes}
            self.assertIn("ix_inbox_event__req_type", index_names)

    @print_exit("Inbox event persistence contracts")
    def test_inbox_event_can_be_created_for_request(self):
        with subtest(self, "creating inbox event -> persists and links to request"):
            req = EditRequestsInbox.objects.create(
                entity_type=EntityType.ORG,
                action=RequestedAction.CREATE,
                status=RequestStatus.PENDING,
                sport=self.volley,
                vertical_entity_id="11111111-1111-1111-1111-111111111111",
                payload={"proposed_name": "Volley Milano"},
                created_by=self.user,
            )

            event = EditRequestsInboxEvent.objects.create(
                request=req,
                event_type=EventType.CREATED,
                actor=self.user,
                notes="Request created",
            )

            events = EditRequestsInboxEvent.objects.filter(request=req)
            self.assertEqual(events.count(), 1)

            saved_event = events.get()
            self.assertEqual(saved_event.id, event.id)
            self.assertEqual(saved_event.event_type, EventType.CREATED)
            self.assertEqual(saved_event.actor, self.user)
            self.assertEqual(saved_event.notes, "Request created")

    @print_exit("Inbox check constraints")
    def test_inbox_request_constraints(self):
        with subtest(self, "Update request without target_entity_id -> IntegrityError"):
            with transaction.atomic():
                with self.assertRaises(IntegrityError):
                    EditRequestsInbox.objects.create(
                        entity_type=EntityType.ORG,
                        action=RequestedAction.UPDATE,
                        status=RequestStatus.PENDING,
                        sport=self.volley,
                        vertical_entity_id="33333333-3333-3333-3333-333333333333",
                        payload={"name": "Updated Org"},
                        created_by=self.user,
                    )

        with subtest(
            self,
            "Create request without target_entity_id -> allowed",
        ):
            req = EditRequestsInbox.objects.create(
                entity_type=EntityType.VENUE,
                action=RequestedAction.CREATE,
                status=RequestStatus.PENDING,
                sport=self.volley,
                vertical_entity_id="44444444-4444-4444-4444-444444444444",
                payload={"name": "Arena Nuova"},
                created_by=self.user,
            )
            self.assertIsNone(req.target_entity_id)

        with subtest(
            self,
            "review completed earlier than taken in charge -> IntegrityError",
        ):
            req = EditRequestsInbox(
                entity_type=EntityType.ORG,
                action=RequestedAction.MERGE,
                status=RequestStatus.APPROVED,
                sport=self.volley,
                vertical_entity_id="55555555-5555-5555-5555-555555555555",
                target_entity_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                payload={"source_entity_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"},
                created_by=self.user,
                finalised_by=self.reviewer,
            )
            req.ts_taken_in_charge = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
            req.ts_review_completed = datetime(2026, 3, 10, 11, 0, tzinfo=UTC)

            with transaction.atomic():
                with self.assertRaises(IntegrityError):
                    req.save()
