"""
Admin API endpoints for platform administration.

Provides tenant management, impersonation, and audit log access.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from faux_splunk_cloud.api.deps import (
    AnyTokenData,
    require_admin,
    require_auth,
    get_actor_context,
)
from faux_splunk_cloud.models.impersonation import ActorContext
from faux_splunk_cloud.models.instance import Instance, InstanceStatus
from faux_splunk_cloud.models.tenant import (
    Tenant,
    TenantCreate,
    TenantList,
    TenantStatus,
    TenantUpdate,
)
from faux_splunk_cloud.services.instance_manager import instance_manager
from faux_splunk_cloud.services.tenant_service import tenant_service

router = APIRouter()


# Response models


class TenantWithInstances(BaseModel):
    """Tenant with associated instances."""

    tenant: Tenant
    instances: list[Instance]


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class TenantStatsResponse(BaseModel):
    """Tenant statistics response."""

    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    total_instances: int
    total_memory_mb: int


# Tenant Management Endpoints


@router.get("/stats", response_model=TenantStatsResponse)
async def get_admin_stats(
    _: Annotated[AnyTokenData, Depends(require_admin)],
) -> TenantStatsResponse:
    """
    Get platform-wide statistics.

    Requires admin privileges.
    """
    tenant_list = await tenant_service.list_tenants(include_deleted=False)

    active = sum(1 for t in tenant_list.tenants if t.status == TenantStatus.ACTIVE)
    suspended = sum(1 for t in tenant_list.tenants if t.status == TenantStatus.SUSPENDED)
    total_instances = sum(t.instance_count for t in tenant_list.tenants)
    total_memory = sum(t.total_memory_mb for t in tenant_list.tenants)

    return TenantStatsResponse(
        total_tenants=tenant_list.total,
        active_tenants=active,
        suspended_tenants=suspended,
        total_instances=total_instances,
        total_memory_mb=total_memory,
    )


@router.get("/tenants", response_model=TenantList)
async def list_tenants(
    _: Annotated[AnyTokenData, Depends(require_admin)],
    status: TenantStatus | None = None,
    include_deleted: bool = False,
) -> TenantList:
    """
    List all tenants.

    Requires admin privileges.
    """
    return await tenant_service.list_tenants(
        status=status,
        include_deleted=include_deleted,
    )


@router.post("/tenants", response_model=Tenant)
async def create_tenant(
    request: TenantCreate,
    _: Annotated[AnyTokenData, Depends(require_admin)],
) -> Tenant:
    """
    Create a new tenant.

    Requires admin privileges.
    """
    try:
        return await tenant_service.create_tenant(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tenants/{tenant_id}", response_model=Tenant)
async def get_tenant(
    tenant_id: str,
    _: Annotated[AnyTokenData, Depends(require_admin)],
) -> Tenant:
    """
    Get a specific tenant.

    Requires admin privileges.
    """
    tenant = await tenant_service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    return tenant


@router.patch("/tenants/{tenant_id}", response_model=Tenant)
async def update_tenant(
    tenant_id: str,
    request: TenantUpdate,
    _: Annotated[AnyTokenData, Depends(require_admin)],
) -> Tenant:
    """
    Update a tenant.

    Requires admin privileges.
    """
    tenant = await tenant_service.update_tenant(tenant_id, request)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    return tenant


@router.delete("/tenants/{tenant_id}", response_model=MessageResponse)
async def delete_tenant(
    tenant_id: str,
    _: Annotated[AnyTokenData, Depends(require_admin)],
    hard_delete: bool = False,
) -> MessageResponse:
    """
    Delete a tenant.

    By default performs a soft delete (marks as deleted).
    Use hard_delete=true to permanently remove.

    Requires admin privileges.
    """
    success = await tenant_service.delete_tenant(tenant_id, hard_delete=hard_delete)
    if not success:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

    action = "permanently deleted" if hard_delete else "deleted"
    return MessageResponse(message=f"Tenant {tenant_id} {action}")


@router.post("/tenants/{tenant_id}/suspend", response_model=Tenant)
async def suspend_tenant(
    tenant_id: str,
    _: Annotated[AnyTokenData, Depends(require_admin)],
) -> Tenant:
    """
    Suspend a tenant.

    Suspended tenants cannot create new instances but existing instances remain.

    Requires admin privileges.
    """
    tenant = await tenant_service.suspend_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    return tenant


@router.post("/tenants/{tenant_id}/activate", response_model=Tenant)
async def activate_tenant(
    tenant_id: str,
    _: Annotated[AnyTokenData, Depends(require_admin)],
) -> Tenant:
    """
    Activate a suspended tenant.

    Requires admin privileges.
    """
    tenant = await tenant_service.activate_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    return tenant


@router.get("/tenants/{tenant_id}/instances")
async def list_tenant_instances(
    tenant_id: str,
    _: Annotated[AnyTokenData, Depends(require_admin)],
    status: InstanceStatus | None = None,
) -> TenantWithInstances:
    """
    List all instances for a tenant.

    Requires admin privileges.
    """
    tenant = await tenant_service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

    # Get all instances and filter by tenant
    all_instances = await instance_manager.list_instances(status=status)
    tenant_instances = [i for i in all_instances if i.tenant_id == tenant_id]

    return TenantWithInstances(tenant=tenant, instances=tenant_instances)


# Current User / Context Endpoints


@router.get("/me", response_model=ActorContext)
async def get_current_user(
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> ActorContext:
    """
    Get the current user context.

    Returns information about the authenticated user including:
    - Real identity (the actual user)
    - Effective identity (may differ if impersonating)
    - Current tenant
    - Permissions and roles
    """
    return actor


@router.get("/me/tenant", response_model=Tenant)
async def get_my_tenant(
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> Tenant:
    """
    Get the current user's tenant.

    For non-admin users, returns their effective tenant.
    """
    tenant = await tenant_service.get_tenant(actor.effective_tenant_id)
    if not tenant:
        # Try to get or create default tenant
        tenant = await tenant_service.get_or_create_default_tenant()
    return tenant


@router.get("/me/instances")
async def list_my_instances(
    actor: Annotated[ActorContext, Depends(get_actor_context)],
    status: InstanceStatus | None = None,
) -> dict:
    """
    List instances for the current user's tenant.
    """
    # Get all instances and filter by tenant
    all_instances = await instance_manager.list_instances(status=status)
    my_instances = [i for i in all_instances if i.tenant_id == actor.effective_tenant_id]

    return {"instances": my_instances, "total": len(my_instances)}


# Lookup Endpoints


@router.get("/lookup/tenant-by-slug/{slug}", response_model=Tenant)
async def lookup_tenant_by_slug(
    slug: str,
    _: Annotated[AnyTokenData, Depends(require_admin)],
) -> Tenant:
    """
    Look up a tenant by slug.

    Requires admin privileges.
    """
    tenant = await tenant_service.get_tenant_by_slug(slug)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant with slug '{slug}' not found")
    return tenant


@router.get("/lookup/tenant-by-idp-org/{idp_org_id}", response_model=Tenant)
async def lookup_tenant_by_idp_org(
    idp_org_id: str,
    _: Annotated[AnyTokenData, Depends(require_admin)],
) -> Tenant:
    """
    Look up a tenant by Identity Provider organization ID (Keycloak realm, etc).

    Requires admin privileges.
    """
    tenant = await tenant_service.get_tenant_by_idp_org(idp_org_id)
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail=f"Tenant with IdP org '{idp_org_id}' not found"
        )
    return tenant
