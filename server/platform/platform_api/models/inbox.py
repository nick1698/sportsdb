import uuid
from django.conf import settings
from django.db import models
from shared.utils.models import GrowingTable


class EntityType(models.TextChoices):
    PERSON = "Person"
    ORG = "Org"
    GEO_PLACE = "Location"
    VENUE = "Venue"


class RequestedAction(models.TextChoices):
    CREATE = "Create"
    UPDATE = "Update"
    MERGE = "Merge"


class RequestStatus(models.TextChoices):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    DUPLICATE = "Duplicate"
    APPLIED = "Applied"


class EditRequestsInbox(GrowingTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    entity_type = models.CharField(max_length=16, choices=EntityType.choices)
    action = models.CharField(max_length=16, choices=RequestedAction.choices)
    status = models.CharField(
        max_length=16, choices=RequestStatus.choices, default=RequestStatus.PENDING
    )

    sport = models.ForeignKey(
        "platform_api.Sport",
        to_field="key",
        db_column="sport_key",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="inbox_requests",
    )
    vertical_entity_id = models.UUIDField(null=True, blank=True)

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
    finalised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="edit_requests_finalized",
        verbose_name="Review closed by",
        help_text="NOTE: not null with APPLIED status",
    )
    ts_taken_in_charge = models.DateTimeField(
        null=True, blank=True, verbose_name="Taken in charge at"
    )
    ts_review_completed = models.DateTimeField(
        null=True, blank=True, verbose_name="Completed review at"
    )
    review_notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "edit_requests_inbox"
        verbose_name_plural = "Edit requests inbox"
        indexes = [
            models.Index(fields=["status", "entity_type"], name="ix_inbox_status_type"),
            models.Index(fields=["sport"], name="ix_inbox_sport"),
            models.Index(fields=["target_entity_id"], name="ix_inbox_target"),
            models.Index(
                fields=["vertical_entity_id"], name="ix_inbox_vertical_entity"
            ),
        ]

    def __str__(self):
        return f"InboxRequest({self.action} {self.entity_type}: {self.status})"


class EventType(models.TextChoices):
    CREATED = "Created"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    COMMENT = "Comment"
    REVIEWED = "Reviewed"  # NOTE: when editing some proposed info
    APPLIED = "Applied"


class EditRequestsInboxEvent(GrowingTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    request = models.ForeignKey(
        EditRequestsInbox,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=16, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="edit_request_events",
    )

    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "edit_requests_inbox_event"
        indexes = [
            models.Index(
                fields=["request", "event_type"], name="ix_inbox_event__req_type"
            ),
        ]

    def __str__(self):
        return f"{self.request} - {self.event_type} by {self.actor}"
