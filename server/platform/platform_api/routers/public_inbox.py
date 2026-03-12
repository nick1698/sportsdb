from typing import Optional
from uuid import UUID

from ninja import Router, Schema
from django.core.exceptions import ValidationError

from shared.api_contract.schemas import (
    ListEnvelope,
    ListQueryParams,
    ResponseEnvelope,
    paginate,
)

from platform_api.models.inbox import (
    EditRequestsInbox,
    EntityType,
    RequestStatus,
    RequestedAction,
)
from platform_api.routers import PlatformRoute
from platform_api.services.inbox import InboxService

router = Router(tags=["public-inbox"])

# region --- Schemas ---


class InboxRequestIn(Schema):
    entity_type: str
    action: Optional[str]
    sport: str  # vertical slug
    vertical_entity_id: UUID
    target_entity_id: UUID
    payload: dict  # additional info

    def validate_entity_type(self, value):
        if value not in EntityType.values:
            raise ValidationError(f"Invalid entity_type: {value}")
        return value

    def validate_action(self, value):
        if value not in RequestedAction.values:
            raise ValidationError(f"Invalid action: {value}")
        return value


class InboxRequestsOut(Schema):
    id: UUID
    entity_type: str
    action: str
    status: str
    # add fields if needed


# endregion

# region --- Endpoints ---

req_ep = PlatformRoute(EditRequestsInbox)


@router.get(req_ep.list_short_url, response=ListEnvelope[InboxRequestsOut])
def list_requests(request, params: ListQueryParams):
    qs = EditRequestsInbox.objects.filter(status=RequestStatus.PENDING)
    items, total = paginate(qs, params.limit, params.offset)
    return {
        "items": items,
        "limit": params.limit,
        "offset": params.offset,
        "total": total,
        "sort": params.sort,
    }


@router.post(
    req_ep.compose_post_url("create", short=True),
    response=ResponseEnvelope[InboxRequestsOut],
)
def create_request(request, payload: InboxRequestIn):
    created_request = InboxService.create_request(payload.dict(), request.user)
    return {"data": created_request, "message": "Request created successfully"}


@router.post(
    req_ep.compose_post_url("reject", pk="req_id", short=True),
    response=ResponseEnvelope[InboxRequestsOut],
)
def reject_request(request, request_id: UUID, payload: InboxRequestIn):
    rejected_request = InboxService.reject_request(
        request_id=request_id, reviewer=request.user, notes=payload.notes
    )
    return {"data": rejected_request, "message": "Request rejected successfully"}


# endregion
