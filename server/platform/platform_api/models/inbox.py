import uuid

from django.conf import settings
from django.db import models, transaction
from django.db.models import Q
from django.forms import ValidationError
from django.utils import timezone

from shared.utils.models import GrowingTable


class EntityType(models.TextChoices):
    ORG = "org", "Org"
    PERSON = "person", "Person"
    LOCATION = "location", "Location"
    VENUE = "venue", "Venue"


class RequestedAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    MERGE = "merge", "Merge"


class RequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    DUPLICATE = "duplicate", "Duplicate"
    APPLIED = "applied", "Applied"


class EditRequestsInbox(GrowingTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    entity_type = models.CharField(max_length=32, choices=EntityType.choices)
    action = models.CharField(max_length=32, choices=RequestedAction.choices)
    status = models.CharField(
        max_length=32, choices=RequestStatus.choices, default=RequestStatus.PENDING
    )

    sport = models.ForeignKey(
        "platform_api.Sport",
        on_delete=models.PROTECT,
        related_name="inbox_requests",
    )
    vertical_entity_id = models.UUIDField()
    target_entity_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="Core entity target id",
        help_text="NOTE: Only nullable for CREATE requests",
    )

    payload = models.JSONField(help_text="Content of the request")

    # audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="edit_requests_created",
        verbose_name="Created by",
    )  # NOTE: nullable for MVP?

    taken_in_charge_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="edit_request_taken_in_charge",
        help_text="NOTE: only nullable with PENDING status",
    )
    ts_taken_in_charge = models.DateTimeField(
        null=True, blank=True, verbose_name="Taken in charge at"
    )

    finalised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="edit_request_finalized",
        verbose_name="Request applied by",
        help_text="NOTE: not null with APPLIED status",
    )
    ts_finalised = models.DateTimeField(
        null=True, blank=True, verbose_name="Request applied at"
    )

    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "edit_requests_inbox"
        verbose_name = "edit request"
        verbose_name_plural = "edit requests inbox"
        constraints = [
            # 1) CREATE -> target_entity_id deve essere NULL
            models.CheckConstraint(
                name="ck_inbox_create_target_null",
                condition=(
                    ~Q(action=RequestedAction.CREATE.value)
                    | Q(target_entity_id__isnull=True)
                ),
            ),
            # 2) UPDATE e MERGE -> target_entity_id obbligatorio
            models.CheckConstraint(
                name="ck_inbox_noncreate_target_required",
                condition=(
                    Q(action=RequestedAction.CREATE.value)
                    | Q(target_entity_id__isnull=False)
                ),
            ),
            # 3.1) taken_in_charge_by e ts_taken_in_charge devono essere entrambi NULL oppure entrambi valorizzati
            models.CheckConstraint(
                name="ck_inbox_taken_fields_both_null_or_set",
                condition=(
                    (
                        Q(taken_in_charge_by__isnull=True)
                        & Q(ts_taken_in_charge__isnull=True)
                    )
                    | (
                        Q(taken_in_charge_by__isnull=False)
                        & Q(ts_taken_in_charge__isnull=False)
                    )
                ),
            ),
            # 3.2) taken_in_charge_by e ts_taken_in_charge devono essere entrambi NULL oppure entrambi valorizzati
            models.CheckConstraint(
                name="ck_inbox_nonpending_requires_taken_fields",
                condition=(
                    Q(status="pending")
                    | (
                        Q(taken_in_charge_by__isnull=False)
                        & Q(ts_taken_in_charge__isnull=False)
                    )
                ),
            ),
            # 4) finalised_by e ts_finalised devono essere entrambi NULL oppure entrambi valorizzati
            models.CheckConstraint(
                name="ck_inbox_finalised_fields_both_null_or_set",
                condition=(
                    (Q(finalised_by__isnull=True) & Q(ts_finalised__isnull=True))
                    | (Q(finalised_by__isnull=False) & Q(ts_finalised__isnull=False))
                ),
            ),
            # 5.1) status = applied -> finalised_* obbligatori
            models.CheckConstraint(
                name="ck_inbox_applied_requires_finalised_fields",
                condition=(
                    ~Q(status=RequestStatus.APPLIED.value)
                    | (Q(finalised_by__isnull=False) & Q(ts_finalised__isnull=False))
                ),
            ),
            # 5.2) status != applied -> finalised_* devono essere NULL (coerente con la tua regola: obbligatori solo con applied)
            models.CheckConstraint(
                name="ck_inbox_nonapplied_finalised_fields_null",
                condition=(
                    Q(status=RequestStatus.APPLIED.value)
                    | (Q(finalised_by__isnull=True) & Q(ts_finalised__isnull=True))
                ),
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="idx_inbox_status"),
            models.Index(fields=["entity_type"], name="idx_inbox_entity_type"),
            models.Index(fields=["sport"], name="idx_inbox_sport"),
            models.Index(fields=["target_entity_id"], name="idx_inbox_target_entity"),
            models.Index(fields=["ts_creation"], name="idx_inbox_created_at"),
            models.Index(
                fields=["status", "entity_type", "ts_creation"],
                name="idx_inbox_entity_created",
            ),
        ]

    def __str__(self):
        return f"InboxRequest({self.action} {self.entity_type}: {self.status})"

    def clean(self):
        """Validation checks"""

        errors = {}

        # target_entity_id deve essere [null] per CREATE
        if self.action == RequestedAction.CREATE:
            if self.target_entity_id is not None:
                errors["target_entity_id"] = (
                    "For action='create', target_entity_id must be null."
                )

        # target_entity_id deve essere [valorizzato] per UPDATE e MERGE
        if self.action in {RequestedAction.UPDATE, RequestedAction.MERGE}:
            if self.target_entity_id is None:
                errors["target_entity_id"] = (
                    "For action='update' or 'merge', target_entity_id is required."
                )

        # taken_in_charge_* devono essere [valorizzati] per stati > PENDING
        if self.status != RequestStatus.PENDING:
            if self.taken_in_charge_by is None or self.ts_taken_in_charge is None:
                errors["taken_in_charge_by"] = (
                    "Non-pending requests must have taken_in_charge_by and ts_taken_in_charge."
                )

        # finalised_* devono essere [valorizzati] per APPLIED
        if self.status == RequestStatus.APPLIED:
            if self.finalised_by is None or self.ts_finalised is None:
                errors["finalised_by"] = (
                    "Applied requests must have finalised_by and ts_finalised."
                )
        # finalised_* devono essere [null] per stati < APPLIED
        else:
            if self.finalised_by is not None or self.ts_finalised is not None:
                errors["finalised_by"] = (
                    "finalised_by and ts_finalised must be null unless status='applied'."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # applying constraints about taken_in_charge_* and finalised_* being necessarily valued together
        if self.taken_in_charge_by is not None and self.ts_taken_in_charge is None:
            self.ts_taken_in_charge = timezone.now()
        elif self.ts_taken_in_charge is not None and self.taken_in_charge_by is None:
            self.ts_taken_in_charge = None

        if self.finalised_by is not None and self.ts_finalised is None:
            self.ts_finalised = timezone.now()
        if self.ts_finalised is not None and self.finalised_by is None:
            self.ts_finalised = None

        self.full_clean()
        super().save(*args, **kwargs)


class EventType(models.TextChoices):
    CREATED = "created", "Created"
    COMMENT = "comment", "Comment"
    DATA_EDITING = "data_editing", "Data editing"
    REJECTED = "rejected", "Rejected"
    DUPLICATE = "duplicate", "Duplicate"
    APPROVED = "approved", "Approved"
    APPLIED = "applied", "Applied"


class EditRequestsInboxEvent(GrowingTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    request = models.ForeignKey(
        EditRequestsInbox,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="edit_request_events",
    )
    description = models.TextField(default="", blank=True)

    class Meta:
        db_table = "edit_requests_inbox_event"
        indexes = [
            models.Index(
                fields=["request", "event_type"], name="ix_inbox_event__req_type"
            ),
        ]

    def __str__(self):
        return f"{self.request} - {self.event_type} by {self.actor}"
