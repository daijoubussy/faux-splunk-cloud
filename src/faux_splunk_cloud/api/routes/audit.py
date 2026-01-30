"""
Audit log API endpoints.

Provides access to audit logs for compliance and security monitoring.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from faux_splunk_cloud.api.deps import (
    AnyTokenData,
    get_actor_context,
    require_admin,
)
from faux_splunk_cloud.models.audit import (
    AuditAction,
    AuditLog,
    AuditLogList,
    AuditLogQuery,
    ResourceType,
)
from faux_splunk_cloud.models.impersonation import ActorContext
from faux_splunk_cloud.services.audit_service import audit_service

router = APIRouter()


@router.get("", response_model=AuditLogList)
async def query_audit_logs(
    actor: Annotated[ActorContext, Depends(get_actor_context)],
    tenant_id: str | None = None,
    actor_user_id: str | None = None,
    resource_type: ResourceType | None = None,
    resource_id: str | None = None,
    action: AuditAction | None = None,
    include_impersonation: bool = True,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> AuditLogList:
    """
    Query audit logs.

    Platform admins can query all logs.
    Tenant users can only query their own tenant's logs.
    """
    # Non-admins can only see their own tenant
    if "admin" not in actor.roles:
        tenant_id = actor.effective_tenant_id

    query = AuditLogQuery(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        include_impersonation=include_impersonation,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    return await audit_service.query(query)


@router.get("/{log_id}", response_model=AuditLog)
async def get_audit_log(
    log_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> AuditLog:
    """Get a specific audit log entry."""
    log = await audit_service.get_log(log_id)

    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")

    # Non-admins can only see their own tenant's logs
    if "admin" not in actor.roles and log.tenant_id != actor.effective_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return log


@router.get("/resource/{resource_type}/{resource_id}")
async def get_resource_audit_history(
    resource_type: ResourceType,
    resource_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """Get audit history for a specific resource."""
    logs = await audit_service.get_resource_history(
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )

    # Filter by tenant access for non-admins
    if "admin" not in actor.roles:
        logs = [l for l in logs if l.tenant_id == actor.effective_tenant_id]

    return {"logs": logs, "total": len(logs)}


@router.get("/user/{user_id}/activity")
async def get_user_activity(
    user_id: str,
    _: Annotated[AnyTokenData, Depends(require_admin)],
    include_impersonation: bool = True,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    """
    Get activity history for a specific user.

    Requires platform admin privileges.
    """
    logs = await audit_service.get_user_activity(
        user_id=user_id,
        include_impersonation=include_impersonation,
        limit=limit,
    )

    return {"logs": logs, "total": len(logs)}


@router.get("/actions", response_model=list[str])
async def list_audit_actions() -> list[str]:
    """List all available audit action types."""
    return [action.value for action in AuditAction]


@router.get("/resource-types", response_model=list[str])
async def list_resource_types() -> list[str]:
    """List all available resource types."""
    return [rt.value for rt in ResourceType]
