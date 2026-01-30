"""
Impersonation API endpoints.

Handles impersonation request/approval workflow and session management.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from faux_splunk_cloud.api.deps import (
    AnyTokenData,
    get_actor_context,
    require_admin,
    require_auth,
)
from faux_splunk_cloud.models.audit import AuditAction, ResourceType
from faux_splunk_cloud.models.impersonation import (
    ActorContext,
    ImpersonationRequest,
    ImpersonationRequestCreate,
    ImpersonationRequestStatus,
    ImpersonationSession,
)
from faux_splunk_cloud.services.audit_service import audit_service
from faux_splunk_cloud.services.impersonation_service import impersonation_service
from faux_splunk_cloud.services.tenant_service import tenant_service

router = APIRouter()


# Response models


class ImpersonationRequestList(BaseModel):
    """List of impersonation requests."""

    requests: list[ImpersonationRequest]
    total: int


class ImpersonationSessionList(BaseModel):
    """List of impersonation sessions."""

    sessions: list[ImpersonationSession]
    total: int


class RejectRequest(BaseModel):
    """Request body for rejecting an impersonation request."""

    reason: str = Field(..., min_length=5, max_length=500)


class StartSessionRequest(BaseModel):
    """Request body for starting an impersonation session."""

    request_id: str = Field(..., description="Approved impersonation request ID")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# Impersonation Request Endpoints (for tenant users)


@router.post("/requests", response_model=ImpersonationRequest)
async def create_impersonation_request(
    request: ImpersonationRequestCreate,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> ImpersonationRequest:
    """
    Create a new impersonation request.

    Called by a tenant user to request admin support access.
    A tenant admin must approve the request before it can be used.
    """
    imp_request = await impersonation_service.create_request(
        tenant_id=actor.effective_tenant_id,
        user_id=actor.effective_user_id,
        user_email=actor.effective_email,
        data=request,
    )

    # Audit log
    await audit_service.log(
        action=AuditAction.IMPERSONATION_REQUEST,
        resource_type=ResourceType.IMPERSONATION_REQUEST,
        resource_id=imp_request.id,
        actor=actor,
        details={"reason": request.reason, "duration_hours": request.duration_hours},
    )

    return imp_request


@router.get("/requests", response_model=ImpersonationRequestList)
async def list_impersonation_requests(
    actor: Annotated[ActorContext, Depends(get_actor_context)],
    status: ImpersonationRequestStatus | None = None,
) -> ImpersonationRequestList:
    """
    List impersonation requests for the current tenant.

    Tenant admins see all requests. Regular users see only their own.
    """
    requests = await impersonation_service.list_requests_for_tenant(
        tenant_id=actor.effective_tenant_id,
        status=status,
    )

    # Filter to own requests if not admin
    if "admin" not in actor.roles and "tenant_admin" not in actor.roles:
        requests = [r for r in requests if r.requested_by_user_id == actor.effective_user_id]

    return ImpersonationRequestList(requests=requests, total=len(requests))


@router.get("/requests/{request_id}", response_model=ImpersonationRequest)
async def get_impersonation_request(
    request_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> ImpersonationRequest:
    """Get a specific impersonation request."""
    imp_request = await impersonation_service.get_request(request_id)

    if not imp_request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Check access
    if imp_request.tenant_id != actor.effective_tenant_id:
        if "admin" not in actor.roles:
            raise HTTPException(status_code=403, detail="Access denied")

    return imp_request


@router.post("/requests/{request_id}/approve", response_model=ImpersonationRequest)
async def approve_impersonation_request(
    request_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> ImpersonationRequest:
    """
    Approve an impersonation request.

    Must be a tenant admin for the request's tenant.
    """
    imp_request = await impersonation_service.get_request(request_id)

    if not imp_request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Check tenant admin access
    if imp_request.tenant_id != actor.effective_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if "admin" not in actor.roles and "tenant_admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="Tenant admin required")

    try:
        result = await impersonation_service.approve_request(
            request_id=request_id,
            approver_user_id=actor.effective_user_id,
            approver_email=actor.effective_email,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Audit log
    await audit_service.log(
        action=AuditAction.IMPERSONATION_APPROVE,
        resource_type=ResourceType.IMPERSONATION_REQUEST,
        resource_id=request_id,
        actor=actor,
        details={"requested_by": imp_request.requested_by_email},
    )

    return result


@router.post("/requests/{request_id}/reject", response_model=ImpersonationRequest)
async def reject_impersonation_request(
    request_id: str,
    body: RejectRequest,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> ImpersonationRequest:
    """
    Reject an impersonation request.

    Must be a tenant admin for the request's tenant.
    """
    imp_request = await impersonation_service.get_request(request_id)

    if not imp_request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Check tenant admin access
    if imp_request.tenant_id != actor.effective_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if "admin" not in actor.roles and "tenant_admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="Tenant admin required")

    try:
        result = await impersonation_service.reject_request(
            request_id=request_id,
            rejector_user_id=actor.effective_user_id,
            rejector_email=actor.effective_email,
            reason=body.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Audit log
    await audit_service.log(
        action=AuditAction.IMPERSONATION_REJECT,
        resource_type=ResourceType.IMPERSONATION_REQUEST,
        resource_id=request_id,
        actor=actor,
        details={"requested_by": imp_request.requested_by_email, "reason": body.reason},
    )

    return result


# Impersonation Session Endpoints (for platform admins)


@router.post("/sessions", response_model=ImpersonationSession)
async def start_impersonation_session(
    body: StartSessionRequest,
    _: Annotated[AnyTokenData, Depends(require_admin)],
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> ImpersonationSession:
    """
    Start an impersonation session.

    Requires platform admin privileges and an approved request.
    """
    imp_request = await impersonation_service.get_request(body.request_id)

    if not imp_request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Get tenant name for session
    tenant = await tenant_service.get_tenant(imp_request.tenant_id)
    tenant_name = tenant.name if tenant else imp_request.tenant_id

    try:
        session = await impersonation_service.start_session(
            request_id=body.request_id,
            admin_user_id=actor.real_user_id,
            admin_email=actor.real_email,
            target_tenant_name=tenant_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Audit log
    await audit_service.log(
        action=AuditAction.IMPERSONATION_START,
        resource_type=ResourceType.IMPERSONATION_SESSION,
        resource_id=session.id,
        actor=actor,
        details={
            "request_id": body.request_id,
            "target_user": session.target_user_email,
            "target_tenant": tenant_name,
        },
    )

    return session


@router.get("/sessions", response_model=ImpersonationSessionList)
async def list_active_sessions(
    _: Annotated[AnyTokenData, Depends(require_admin)],
    actor: Annotated[ActorContext, Depends(get_actor_context)],
    my_sessions_only: bool = False,
) -> ImpersonationSessionList:
    """
    List active impersonation sessions.

    Requires platform admin privileges.
    """
    sessions = await impersonation_service.list_active_sessions(
        admin_user_id=actor.real_user_id if my_sessions_only else None,
    )

    return ImpersonationSessionList(sessions=sessions, total=len(sessions))


@router.get("/sessions/{session_id}", response_model=ImpersonationSession)
async def get_session(
    session_id: str,
    _: Annotated[AnyTokenData, Depends(require_admin)],
) -> ImpersonationSession:
    """Get a specific impersonation session."""
    session = await impersonation_service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.post("/sessions/{session_id}/end", response_model=ImpersonationSession)
async def end_impersonation_session(
    session_id: str,
    _: Annotated[AnyTokenData, Depends(require_admin)],
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> ImpersonationSession:
    """
    End an impersonation session.

    Can be ended by the admin who started it or any platform admin.
    """
    session = await impersonation_service.end_session(
        session_id=session_id,
        reason="admin_ended",
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Audit log
    await audit_service.log(
        action=AuditAction.IMPERSONATION_END,
        resource_type=ResourceType.IMPERSONATION_SESSION,
        resource_id=session_id,
        actor=actor,
        details={
            "target_user": session.target_user_email,
            "duration_minutes": (
                (session.ended_at - session.started_at).total_seconds() / 60
                if session.ended_at
                else None
            ),
        },
    )

    return session


@router.get("/sessions/validate/{session_id}", response_model=ActorContext)
async def validate_session(
    session_id: str,
) -> ActorContext:
    """
    Validate an impersonation session and get actor context.

    Used internally to validate X-Impersonate-Session header.
    """
    context = await impersonation_service.get_actor_context_for_session(session_id)

    if not context:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return context
