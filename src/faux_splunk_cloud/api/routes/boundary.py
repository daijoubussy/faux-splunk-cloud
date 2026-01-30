"""
HashiCorp Boundary API endpoints for short-lived access.

Provides just-in-time access to ephemeral Splunk instances with
automatic credential brokering and session management.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from faux_splunk_cloud.api.deps import (
    AnyAuthData,
    get_actor_context,
    require_admin,
    require_auth,
)
from faux_splunk_cloud.models.boundary import (
    BoundaryConnectResponse,
    BoundaryInstanceAccess,
    BoundarySession,
    BoundarySessionList,
    BoundarySessionRequest,
    BoundarySessionStatus,
    BoundaryTarget,
    BoundaryTargetCreate,
    BoundaryTargetList,
    BoundaryTargetType,
)
from faux_splunk_cloud.models.impersonation import ActorContext
from faux_splunk_cloud.services.boundary_service import boundary_service

logger = logging.getLogger(__name__)

router = APIRouter()


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


# Target endpoints


@router.get("/targets", response_model=BoundaryTargetList)
async def list_my_targets(
    actor: Annotated[ActorContext, Depends(get_actor_context)],
    instance_id: str | None = None,
) -> BoundaryTargetList:
    """
    List available Boundary targets for the current tenant.

    Targets represent access points to Splunk instances.
    """
    return await boundary_service.list_targets(
        tenant_id=actor.effective_tenant_id,
        instance_id=instance_id,
    )


@router.get("/targets/{target_id}", response_model=BoundaryTarget)
async def get_target(
    target_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> BoundaryTarget:
    """Get details of a specific Boundary target."""
    target = await boundary_service.get_target(target_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target {target_id} not found",
        )

    # Check tenant access
    if target.tenant_id != actor.effective_tenant_id:
        is_admin = "platform_admin" in actor.roles or "admin" in actor.roles
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this target",
            )

    return target


# Session endpoints


@router.post("/sessions", response_model=BoundaryConnectResponse)
async def create_session(
    request: BoundarySessionRequest,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> BoundaryConnectResponse:
    """
    Create a new Boundary session for accessing a target.

    This initiates just-in-time access with short-lived credentials.
    The session provides a time-limited connection to the Splunk instance.
    """
    # Verify target exists and user has access
    target = await boundary_service.get_target(request.target_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target {request.target_id} not found",
        )

    if target.tenant_id != actor.effective_tenant_id:
        is_admin = "platform_admin" in actor.roles or "admin" in actor.roles
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this target",
            )

    try:
        return await boundary_service.create_session(
            request=request,
            user_id=actor.effective_user_id,
            tenant_id=actor.effective_tenant_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/sessions", response_model=BoundarySessionList)
async def list_my_sessions(
    actor: Annotated[ActorContext, Depends(get_actor_context)],
    target_id: str | None = None,
    status_filter: BoundarySessionStatus | None = Query(None, alias="status"),
    include_expired: bool = False,
) -> BoundarySessionList:
    """
    List Boundary sessions for the current user.

    By default, excludes expired sessions.
    """
    return await boundary_service.list_sessions(
        user_id=actor.effective_user_id,
        target_id=target_id,
        status=status_filter,
        include_expired=include_expired,
    )


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def terminate_session(
    session_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> MessageResponse:
    """Terminate an active Boundary session."""
    try:
        success = await boundary_service.terminate_session(
            session_id=session_id,
            user_id=actor.effective_user_id,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        return MessageResponse(message=f"Session {session_id} terminated")
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# Instance access endpoint (convenience)


@router.get("/instances/{instance_id}/access", response_model=BoundaryInstanceAccess)
async def get_instance_access(
    instance_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> BoundaryInstanceAccess:
    """
    Get complete access information for a Splunk instance.

    Returns all available targets, active sessions, and quick-connect URLs.
    """
    access = await boundary_service.get_instance_access(
        instance_id=instance_id,
        user_id=actor.effective_user_id,
        tenant_id=actor.effective_tenant_id,
    )

    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Boundary access available for instance {instance_id}",
        )

    return access


@router.post("/instances/{instance_id}/connect", response_model=BoundaryConnectResponse)
async def quick_connect(
    instance_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
    target_type: BoundaryTargetType = BoundaryTargetType.SPLUNK_WEB,
    ttl_minutes: int | None = None,
) -> BoundaryConnectResponse:
    """
    Quick connect to an instance.

    Creates a session for the specified target type (defaults to web UI).
    This is a convenience endpoint that finds the appropriate target and creates a session.
    """
    # Get targets for this instance
    targets = await boundary_service.list_targets(
        tenant_id=actor.effective_tenant_id,
        instance_id=instance_id,
    )

    # Find matching target type
    matching_target = None
    for target in targets.targets:
        if target.target_type == target_type:
            matching_target = target
            break

    if not matching_target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {target_type.value} target found for instance {instance_id}",
        )

    # Create session
    request = BoundarySessionRequest(
        target_id=matching_target.id,
        ttl_minutes=ttl_minutes,
        reason="Quick connect",
    )

    return await boundary_service.create_session(
        request=request,
        user_id=actor.effective_user_id,
        tenant_id=actor.effective_tenant_id,
    )


# Admin endpoints


@router.get("/admin/targets", response_model=BoundaryTargetList)
async def admin_list_all_targets(
    _: Annotated[AnyAuthData, Depends(require_admin)],
    tenant_id: str | None = None,
    instance_id: str | None = None,
) -> BoundaryTargetList:
    """List all Boundary targets (admin only)."""
    return await boundary_service.list_targets(
        tenant_id=tenant_id,
        instance_id=instance_id,
    )


@router.get("/admin/sessions", response_model=BoundarySessionList)
async def admin_list_all_sessions(
    _: Annotated[AnyAuthData, Depends(require_admin)],
    tenant_id: str | None = None,
    user_id: str | None = None,
    status_filter: BoundarySessionStatus | None = Query(None, alias="status"),
    include_expired: bool = False,
) -> BoundarySessionList:
    """List all Boundary sessions (admin only)."""
    return await boundary_service.list_sessions(
        tenant_id=tenant_id,
        user_id=user_id,
        status=status_filter,
        include_expired=include_expired,
    )


@router.post("/admin/cleanup", response_model=MessageResponse)
async def admin_cleanup_expired(
    _: Annotated[AnyAuthData, Depends(require_admin)],
) -> MessageResponse:
    """Clean up expired sessions and targets (admin only)."""
    count = await boundary_service.cleanup_expired()
    return MessageResponse(message=f"Cleaned up {count} expired sessions")
