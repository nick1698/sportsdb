from datetime import UTC, datetime
import uuid

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
from platform_api.services.inbox import InboxService


def _mk_sport(key=None, name_en="Volleyball"):
    if key is None:
        key = f"volley_{uuid.uuid4().hex[:8]}"
    return Sport.objects.create(key=key, name_en=name_en)


def _mk_user(username=None, email=None, password="testpass123"):
    User = get_user_model()

    if username is None:
        username = f"user_{uuid.uuid4().hex[:8]}"
    if email is None:
        email = f"{uuid.uuid4().hex[:8]}@example.com"

    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )


def _mk_inbox_request(
    status=RequestStatus.PENDING,
    entity_type=EntityType.ORG,
    action=RequestedAction.CREATE,
    sport=None,
    vertical_entity_id=None,
    payload=None,
    created_by=None,
    taken_in_charge_by=None,
    finalised_by=None,
    ref_request_id=None,
    target_entity_id=None,
    **kwargs,
):
    if vertical_entity_id is None:
        vertical_entity_id = uuid.uuid4()

    if payload is None:
        payload = {"proposed_name": "Test Entity"}

    if sport is None:
        sport = _mk_sport()

    if created_by is None:
        created_by = _mk_user()

    return EditRequestsInbox.objects.create(
        status=status,
        entity_type=entity_type,
        action=action,
        sport=sport,
        vertical_entity_id=vertical_entity_id,
        target_entity_id=target_entity_id,
        ref_request_id=ref_request_id,
        payload=payload,
        created_by=created_by,
        taken_in_charge_by=taken_in_charge_by,
        finalised_by=finalised_by,
        **kwargs,
    )


def _mk_pending_request(**kwargs):
    return _mk_inbox_request(status=RequestStatus.PENDING, **kwargs)


def _mk_approved_request(**kwargs):
    reviewer = kwargs.pop("taken_in_charge_by", None) or kwargs.get("created_by")
    if reviewer is None:
        reviewer = _mk_user(username=f"reviewer_{uuid.uuid4().hex[:8]}")

    return _mk_inbox_request(
        status=RequestStatus.APPROVED,
        taken_in_charge_by=reviewer,
        **kwargs,
    )


def _mk_applied_request(**kwargs):
    reviewer = kwargs.pop("taken_in_charge_by", None) or kwargs.get("created_by")
    if reviewer is None:
        reviewer = _mk_user(username=f"reviewer_{uuid.uuid4().hex[:8]}")

    finaliser = kwargs.pop("finalised_by", None) or reviewer

    return _mk_inbox_request(
        status=RequestStatus.APPLIED,
        taken_in_charge_by=reviewer,
        finalised_by=finaliser,
        **kwargs,
    )


def _mk_merged_request(*, ref_request_id, **kwargs):
    reviewer = kwargs.pop("taken_in_charge_by", None) or kwargs.get("created_by")
    if reviewer is None:
        reviewer = _mk_user(username=f"reviewer_{uuid.uuid4().hex[:8]}")

    finaliser = kwargs.pop("finalised_by", None) or reviewer

    return _mk_inbox_request(
        status=RequestStatus.MERGED,
        taken_in_charge_by=reviewer,
        finalised_by=finaliser,
        ref_request_id=ref_request_id,
        **kwargs,
    )


class InboxModelContractTests(TestCase):
    """Phase 7.3.1: Inbox Django model contract freeze"""

    def setUp(self):
        self.user = _mk_user(username="nick", email="nick@example.com")
        self.reviewer = _mk_user(
            username="reviewer",
            email="reviewer@example.com",
        )
        self.volley = _mk_sport("volley", "Volleyball")

    @print_exit("Inbox model API/contracts")
    def test_edit_requests_inbox_model_contract(self):
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
            self.assertIn("idx_inbox_ref_request", index_names)
            self.assertIn("idx_inbox_created_at", index_names)
            self.assertIn("idx_inbox_entity_created", index_names)

    @print_exit("Inbox event model contracts")
    def test_edit_requests_inbox_event_model_contract(self):
        with subtest(self, "EditRequestsInboxEvent -> indexes contract"):
            index_names = {idx.name for idx in EditRequestsInboxEvent._meta.indexes}
            self.assertIn("ix_inbox_event__req_type", index_names)

        with subtest(self, "EventType choices contract"):
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
                    "merged",
                },
            )

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
            payload = {
                "entity_type": EntityType.ORG,
                "action": RequestedAction.CREATE,
                "sport": self.volley,
                "vertical_entity_id": "11111111-1111-1111-1111-111111111111",
                "payload": {"proposed_name": "Volley Milano"},
            }

            with self.captureOnCommitCallbacks(execute=True):
                req = InboxService.create_request(payload, self.user)

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

            with self.assertRaises(ValidationError):
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
                ts_taken_in_charge=datetime(2026, 3, 10, 10, 0, tzinfo=UTC),
            )

            with self.assertRaises(ValidationError):
                req.full_clean()

        with subtest(
            self,
            "Approved request with finalised fields -> ValidationError",
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
                ts_taken_in_charge=datetime(2026, 3, 10, 10, 0, tzinfo=UTC),
                finalised_by=self.reviewer,
                ts_finalised=datetime(2026, 3, 10, 11, 0, tzinfo=UTC),
            )

            with self.assertRaises(ValidationError):
                req.full_clean()


class InboxServiceTest(TestCase):
    def setUp(self):
        self.user = _mk_user(username="nick", email="nick@example.com")
        self.volley = _mk_sport("volley", "Volleyball")
        self.payload = {
            "entity_type": EntityType.ORG,
            "action": RequestedAction.CREATE,
            "sport": self.volley,
            "vertical_entity_id": uuid.uuid4(),
            "payload": {"proposed_name": "Test Entity"},
        }

    def test_create_request_success(self):
        with self.captureOnCommitCallbacks(execute=True):
            request = InboxService.create_request(self.payload, self.user)

        self.assertEqual(request.status, RequestStatus.PENDING)
        self.assertEqual(request.entity_type, self.payload["entity_type"])
        self.assertEqual(request.created_by, self.user)

    def test_approve_request_success(self):
        pending_request = _mk_pending_request(created_by=self.user, sport=self.volley)

        approved_request = InboxService.approve_request(pending_request.id, self.user)

        self.assertEqual(approved_request.status, RequestStatus.APPROVED)
        self.assertEqual(approved_request.taken_in_charge_by, self.user)
        self.assertIsNotNone(approved_request.ts_taken_in_charge)
        self.assertIsNone(approved_request.finalised_by)
        self.assertIsNone(approved_request.ts_finalised)

    def test_approve_request_validation_error(self):
        rejected_request = _mk_inbox_request(
            created_by=self.user,
            sport=self.volley,
            status=RequestStatus.REJECTED,
            taken_in_charge_by=self.user,
        )

        with self.assertRaises(ValidationError):
            InboxService.approve_request(rejected_request.id, self.user)

    def test_reject_request_success(self):
        pending_request = _mk_pending_request(created_by=self.user, sport=self.volley)

        rejected_request = InboxService.reject_request(pending_request.id, self.user)

        self.assertEqual(rejected_request.status, RequestStatus.REJECTED)
        self.assertEqual(rejected_request.taken_in_charge_by, self.user)
        self.assertIsNotNone(rejected_request.ts_taken_in_charge)
        self.assertIsNone(rejected_request.finalised_by)
        self.assertIsNone(rejected_request.ts_finalised)

    def test_merge_request_success(self):
        approved_request = _mk_approved_request(created_by=self.user, sport=self.volley)
        ref_request = _mk_approved_request(created_by=self.user, sport=self.volley)

        merged_request = InboxService.merge_request(
            approved_request.id, self.user, ref_request.id
        )

        self.assertEqual(merged_request.status, RequestStatus.MERGED)
        self.assertEqual(merged_request.ref_request_id, ref_request.id)
        self.assertEqual(merged_request.taken_in_charge_by, self.user)
        self.assertIsNotNone(merged_request.ts_taken_in_charge)
        self.assertEqual(merged_request.finalised_by, self.user)
        self.assertIsNotNone(merged_request.ts_finalised)

    def test_merge_request_validation_error(self):
        pending_request = _mk_pending_request(created_by=self.user, sport=self.volley)

        with self.assertRaises(ValidationError):
            InboxService.merge_request(pending_request.id, self.user, uuid.uuid4())

    def test_apply_request_success(self):
        approved_request = _mk_approved_request(created_by=self.user, sport=self.volley)

        applied_request = InboxService.set_request_applied(approved_request.id, self.user)

        self.assertEqual(applied_request.status, RequestStatus.APPLIED)
        self.assertEqual(applied_request.taken_in_charge_by, self.user)
        self.assertIsNotNone(applied_request.ts_taken_in_charge)
        self.assertEqual(applied_request.finalised_by, self.user)
        self.assertIsNotNone(applied_request.ts_finalised)
