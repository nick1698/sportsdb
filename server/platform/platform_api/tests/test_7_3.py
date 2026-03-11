from datetime import UTC, datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.forms import ValidationError
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
                {"org", "person", "location", "venue"},
            )
            self.assertEqual(
                {choice for choice, _ in RequestedAction.choices},
                {"create", "update", "merge"},
            )
            self.assertEqual(
                {choice for choice, _ in RequestStatus.choices},
                {"pending", "approved", "rejected", "duplicate", "applied"},
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
            self.assertFalse(sport_field.null)

        with subtest(self, "EditRequestsInbox -> indexes contract"):
            index_names = {idx.name for idx in EditRequestsInbox._meta.indexes}
            self.assertIn("idx_inbox_status", index_names)
            self.assertIn("idx_inbox_entity_type", index_names)
            self.assertIn("idx_inbox_sport", index_names)
            self.assertIn("idx_inbox_target_entity", index_names)
            self.assertIn("idx_inbox_created_at", index_names)
            self.assertIn("idx_inbox_entity_created", index_names)

        with subtest(self, "EditRequestsInbox -> constraints contract"):
            constraint_names = {
                constraint.name for constraint in EditRequestsInbox._meta.constraints
            }
            self.assertIn("ck_inbox_create_target_null", constraint_names)
            self.assertIn("ck_inbox_noncreate_target_required", constraint_names)
            self.assertIn("ck_inbox_taken_fields_both_null_or_set", constraint_names)
            self.assertIn("ck_inbox_nonpending_requires_taken_fields", constraint_names)
            self.assertIn(
                "ck_inbox_finalised_fields_both_null_or_set", constraint_names
            )
            self.assertIn(
                "ck_inbox_applied_requires_finalised_fields", constraint_names
            )
            self.assertIn("ck_inbox_nonapplied_finalised_fields_null", constraint_names)

    @print_exit("Inbox event model contracts")
    def test_edit_requests_inbox_event_model_contract(self):
        with subtest(self, "EditRequestsInboxEvent -> db table + enum contract"):
            self.assertEqual(
                EditRequestsInboxEvent._meta.db_table,
                "edit_requests_inbox_event",
            )
            self.assertEqual(
                {choice for choice, _ in EventType.choices},
                {
                    "created",
                    "comment",
                    "data_editing",
                    "rejected",
                    "duplicate",
                    "approved",
                    "applied",
                },
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
                event_type=EventType.COMMENT,
                actor=self.user,
                description="First review comment",
            )

            events = EditRequestsInboxEvent.objects.filter(request=req).order_by(
                "ts_creation"
            )
            self.assertEqual(events.count(), 1)

            saved_event = events.get()
            self.assertEqual(saved_event.id, event.id)
            self.assertEqual(saved_event.event_type, EventType.COMMENT)
            self.assertEqual(saved_event.actor, self.user)
            self.assertEqual(saved_event.description, "First review comment")

    @print_exit("Inbox save hook contracts")
    def test_inbox_request_create_generates_created_event(self):
        with subtest(self, "creating inbox request -> auto create Created event"):
            with self.captureOnCommitCallbacks(execute=True):
                req = EditRequestsInbox.objects.create(
                    entity_type=EntityType.ORG,
                    action=RequestedAction.CREATE,
                    status=RequestStatus.PENDING,
                    sport=self.volley,
                    vertical_entity_id="11111111-1111-1111-1111-111111111111",
                    payload={"proposed_name": "Volley Milano"},
                    created_by=self.user,
                )

            events = EditRequestsInboxEvent.objects.filter(request=req)
            self.assertEqual(events.count(), 1)

            event = events.get()
            self.assertEqual(event.event_type, EventType.CREATED)
            self.assertEqual(event.actor, self.user)

    @print_exit("Inbox check constraints")
    def test_inbox_request_constraints(self):
        with subtest(
            self, "Update request without target_entity_id -> ValidationError"
        ):
            with transaction.atomic():
                with self.assertRaises(ValidationError):
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
            "Non-pending request without taken_in_charge fields -> ValidationError",
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
            )

            with self.assertRaises(Exception):
                req.full_clean()

        with subtest(
            self,
            "Applied request without finalised fields -> ValidationError",
        ):
            req = EditRequestsInbox(
                entity_type=EntityType.ORG,
                action=RequestedAction.UPDATE,
                status=RequestStatus.APPLIED,
                sport=self.volley,
                vertical_entity_id="66666666-6666-6666-6666-666666666666",
                target_entity_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                payload={"name": "Updated Org"},
                created_by=self.user,
                taken_in_charge_by=self.reviewer,
            )

            with self.assertRaises(ValidationError):
                req.full_clean()

        with subtest(
            self,
            "Non-applied request with finalised fields set -> ValidationError",
        ):
            req = EditRequestsInbox(
                entity_type=EntityType.ORG,
                action=RequestedAction.UPDATE,
                status=RequestStatus.APPROVED,
                sport=self.volley,
                vertical_entity_id="77777777-7777-7777-7777-777777777777",
                target_entity_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                payload={"name": "Updated Org"},
                created_by=self.user,
                taken_in_charge_by=self.reviewer,
                finalised_by=self.reviewer,
                ts_finalised=datetime(2026, 3, 10, 11, 0, tzinfo=UTC),
            )

            with self.assertRaises(ValidationError):
                req.full_clean()
