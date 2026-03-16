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
    EntityType,
    RequestStatus,
)


class InboxService:
    @staticmethod
    def _apply_core_changes(request: EditRequestsInbox):
        """
        Applies changes to the core based on the request payload.

        Args:
            request: EditRequestsInbox object containing the payload and metadata.
        """
        entity_type = request.entity_type
        payload = request.payload

        match entity_type:
            case EntityType.ORG.value:
                from platform_api.models.entities import Org

                Org(**payload).save()

            case EntityType.PERSON.value:
                from platform_api.models.entities import Person

                Person(**payload).save()

            case EntityType.LOCATION.value:
                from platform_api.models.geo import GeoPlace

                GeoPlace(**payload).save()

            case EntityType.VENUE.value:
                from platform_api.models.geo import Venue

                Venue(**payload).save()

    @staticmethod
    def create_request(payload: Dict, user: "User") -> EditRequestsInbox:
        """
        Creates a new request in the Inbox.

        Args:
            payload: Dictionary containing request data (see InboxRequestIn schema)
            user: User creating the request

        Returns:
            EditRequestsInbox: The created request object
        """
        # Create the inbox request
        new_request = EditRequestsInbox(
            status=RequestStatus.PENDING, created_by=user, **payload
        )
        new_request.save()

        return new_request

    @staticmethod
    def reject_request(
        request_id: UUID,
        reviewer: "User",
        ref_request_id: UUID | None = None,
        notes: Optional[str] = "",
    ) -> EditRequestsInbox:
        """
        Rejects a pending request in the Inbox.

        Args:
            request_id: ID of the request to reject.
            reviewer: User rejecting the request.
            notes: Optional notes explaining the rejection.

        Returns:
            EditRequestsInbox: The updated request object.

        Raises:
            ValidationError: If the request is not in 'pending' status.
        """
        request = EditRequestsInbox.objects.get(id=request_id)

        if request.status != RequestStatus.PENDING:
            raise ValidationError("Only 'pending' requests can be rejected")

        request.status = RequestStatus.REJECTED
        request.taken_in_charge_by = reviewer
        request.notes = notes
        request.save()

        return request

    @staticmethod
    def approve_request(request_id: int, reviewer: "User") -> EditRequestsInbox:
        """
        Approves a pending request in the Inbox.

        Args:
            request_id: ID of the request to approve.
            reviewer: User approving the request.

        Returns:
            EditRequestsInbox: The updated request object.

        Raises:
            ValidationError: If the request is not in 'pending' status.
        """
        with transaction.atomic():
            request = EditRequestsInbox.objects.select_for_update().get(id=request_id)

            if request.status != "pending":
                raise ValidationError("Only 'pending' requests can be approved")

            # Apply changes to the core (e.g., create/update core entities)
            InboxService._apply_core_changes(request)

            # Update request status
            request.status = "approved"
            request.taken_in_charge_by = reviewer
            request.ts_taken_in_charge = timezone.now()
            request.save()

        return request
