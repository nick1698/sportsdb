from uuid import UUID

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

# from django.contrib.auth import get_user_model
from typing import TYPE_CHECKING, Dict, Optional

# Only for type hinting
if TYPE_CHECKING:
    from django.contrib.auth.models import User

from platform_api.models.inbox import (
    EditRequestsInbox,
    EditRequestsInboxEvent,
    EventType,
    RequestStatus,
)


class InboxService:
    @staticmethod
    def create_request(payload: Dict, user: "User") -> EditRequestsInbox:
        with transaction.atomic():
            now = timezone.now()

            new_request = EditRequestsInbox(
                ts_creation=now,
                status=RequestStatus.PENDING,
                created_by=user,
                **payload
            )
            new_request.save()

            EditRequestsInboxEvent.objects.create(
                ts_creation=now,
                request=new_request,
                event_type=EventType.CREATED,
                actor=user,
            )

        return new_request

    @staticmethod
    def reject_request(
        request_id: UUID,
        reviewer: "User",
        ref_request_id: UUID | None = None,
        notes: Optional[str] = "",
    ) -> EditRequestsInbox:
        with transaction.atomic():
            req = EditRequestsInbox.objects.get(id=request_id)
            now = timezone.now()

            if req.status != RequestStatus.PENDING:
                raise ValidationError("Only 'pending' requests can be rejected")

            req.status = (
                RequestStatus.REJECTED if not ref_request_id else RequestStatus.DUPLICATE
            )
            req.ref_request_id = ref_request_id if RequestStatus.DUPLICATE else None
            req.taken_in_charge_by = reviewer
            req.ts_taken_in_charge = now
            req.notes = notes
            req.save()

            EditRequestsInboxEvent.objects.create(
                ts_creation=now,
                request=req,
                event_type=(
                    EventType.REJECTED if not ref_request_id else EventType.DUPLICATE
                ),
                actor=reviewer,
                description=f"Duplicated request: {ref_request_id}" if ref_request_id else ""
            )

        return req

    @staticmethod
    def approve_request(
        request_id: UUID,
        reviewer: "User",
        notes: Optional[str] = "",
    ) -> EditRequestsInbox:
        with transaction.atomic():
            req = EditRequestsInbox.objects.get(id=request_id)
            now = timezone.now()

            if req.status != RequestStatus.PENDING:
                raise ValidationError("Only 'pending' requests can be approved")

            req.status = RequestStatus.APPROVED
            req.taken_in_charge_by = reviewer
            req.ts_taken_in_charge = now
            req.notes = notes
            req.save()

            EditRequestsInboxEvent.objects.create(
                ts_creation=now,
                request=req,
                event_type=EventType.APPROVED,
                actor=reviewer,
            )

        return req

    @staticmethod
    def merge_request(
        request_id: UUID,
        reviewer: "User",
        ref_request_id: UUID,
        notes: Optional[str] = "",
    ) -> EditRequestsInbox:
        with transaction.atomic():
            req = EditRequestsInbox.objects.get(id=request_id)
            now = timezone.now()

            if req.status != RequestStatus.APPROVED:
                raise ValidationError("Only 'approved' requests can be merged")

            req.status = RequestStatus.MERGED
            req.ref_request_id = ref_request_id
            req.finalised_by = reviewer
            req.ts_finalised = now
            req.notes = notes
            req.save()

            EditRequestsInboxEvent.objects.create(
                ts_creation=now,
                request=req,
                event_type=EventType.MERGED,
                actor=reviewer,
                description=f"Merged to request: {ref_request_id}"
            )

        return req

    @staticmethod
    def set_request_applied(request_id: UUID, reviewer: "User") -> EditRequestsInbox:
        with transaction.atomic():
            req = EditRequestsInbox.objects.get(id=request_id)
            now = timezone.now()

            if req.status != RequestStatus.APPROVED:
                raise ValidationError("Only 'approved' requests can be approved")

            # TODO: how to apply the updates??? do it here or elsewhere?

            req.status = RequestStatus.APPLIED
            req.finalised_by = reviewer
            req.ts_finalised = now
            req.save()

            EditRequestsInboxEvent.objects.create(
                ts_creation=now,
                request=req,
                event_type=EventType.APPLIED,
                actor=reviewer,
            )

        return req
