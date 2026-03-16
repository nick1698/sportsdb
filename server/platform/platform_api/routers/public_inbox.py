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
    target_entity_id: Optional[UUID] = None  # only optional for CREATE event
    ref_request_id: Optional[UUID]  # only used for Duplicate and Merge events
    payload: dict  # additional info
    notes: Optional[str]

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


# endregion

# region --- Routers ---


class InboxRoute(PlatformRoute):
    __ep__ = PlatformRoute(EditRequestsInbox)

    LIST = __ep__.list_short_url
    CREATE = __ep__.compose_post_url("create", short=True)
    REJECT = __ep__.compose_post_url("reject", pk="req_id", short=True)
    REJ_DUPL = __ep__.compose_post_url("duplicate", pk="req_id", short=True)
    APPROVE = __ep__.compose_post_url("approve", pk="req_id", short=True)
    MERGE = __ep__.compose_post_url("merge", pk="req_id", short=True)


# endregion

# region --- Endpoints ---

# req_ep = PlatformRoute(EditRequestsInbox)


@router.get(InboxRoute.LIST, response=ListEnvelope[InboxRequestsOut])
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


# CREATION
@router.post(
    InboxRoute.CREATE,
    response=ResponseEnvelope[InboxRequestsOut],
)
def create_request(request, payload: InboxRequestIn):
    req = InboxService.create_request(payload.dict(), request.user)
    return {"data": req, "message": "Request created successfully"}


# REJECTION
@router.post(
    InboxRoute.REJECT,
    response=ResponseEnvelope[InboxRequestsOut],
)
def reject_request(request, id: UUID, payload: InboxRequestIn):
    req = InboxService.reject_request(
        request_id=id,
        reviewer=request.user,
        ref_request_id=None,
        notes=payload.notes,
    )
    return {"data": req, "message": "Request rejected successfully"}


# REJECTION BECAUSE DUPLICATE
@router.post(
    InboxRoute.REJ_DUPL,
    response=ResponseEnvelope[InboxRequestsOut],
)
def reject_request_for_duplication(request, id: UUID, payload: InboxRequestIn):
    req = InboxService.reject_request(
        request_id=id,
        reviewer=request.user,
        ref_request_id=payload.ref_request_id,
        notes=payload.notes,
    )
    return {
        "data": req,
        "message": "Request rejected successfully because of duplicate request",
    }


# APPROVAL
@router.post(
    InboxRoute.APPROVE,
    response=ResponseEnvelope[InboxRequestsOut],
)
def approve_request(request, id: UUID, payload: InboxRequestIn):
    req = InboxService.approve_request(
        request_id=id,
        reviewer=request.user,
        notes=payload.notes,
    )
    return {
        "data": req,
        "message": "Request approved successfully",
    }


# MERGE
@router.post(
    InboxRoute.MERGE,
    response=ResponseEnvelope[InboxRequestsOut],
)
def merge_request(request, id: UUID, payload: InboxRequestIn):
    if payload.ref_request_id is None:
        raise ValidationError("ref_request_id is required for merging")

    req = InboxService.merge_request(
        request_id=id,
        reviewer=request.user,
        ref_request_id=payload.ref_request_id,
        notes=payload.notes,
    )
    return {"data": req, "message": "Request merged successfully with another one"}


# endregion
