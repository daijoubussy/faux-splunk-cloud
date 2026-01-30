"""
Customer Instance Management API endpoints.

All operations are scoped to the customer's tenant.
Customers can only see and manage instances belonging to their tenant.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from faux_splunk_cloud.api.deps import AnyAuthData, get_actor_context, require_customer
from faux_splunk_cloud.models.impersonation import ActorContext
from faux_splunk_cloud.models.instance import (
    Instance,
    InstanceCreate,
    InstanceStatus,
)
from faux_splunk_cloud.services.instance_manager import instance_manager

router = APIRouter()


class InstanceListResponse(BaseModel):
    """Response model for listing instances."""

    instances: list[Instance]
    total: int


class InstanceStartResponse(BaseModel):
    """Response model for starting an instance."""

    id: str
    status: InstanceStatus
    message: str


class ExtendTTLRequest(BaseModel):
    """Request model for extending instance TTL."""

    hours: int = Field(ge=1, le=168, description="Hours to extend")


class CustomerContext(BaseModel):
    """Customer context for API responses."""

    tenant_id: str
    user_id: str


@router.get("/me")
async def get_customer_context(
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> CustomerContext:
    """Get the current customer's context (tenant, user info)."""
    return CustomerContext(
        tenant_id=actor.effective_tenant_id,
        user_id=actor.effective_user_id,
    )


@router.post("", response_model=Instance)
async def create_instance(
    request: InstanceCreate,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> Instance:
    """
    Create a new ephemeral Splunk instance.

    The instance will be provisioned with Victoria Experience defaults
    and configured according to the specified topology.

    Instance is automatically scoped to the customer's tenant.
    """
    # Add tenant label to instance
    if request.labels is None:
        request.labels = {}
    request.labels["tenant_id"] = actor.effective_tenant_id
    request.labels["created_by"] = actor.effective_user_id

    instance = await instance_manager.create_instance(request)
    return instance


@router.get("", response_model=InstanceListResponse)
async def list_instances(
    actor: Annotated[ActorContext, Depends(get_actor_context)],
    status: InstanceStatus | None = None,
    label: Annotated[list[str] | None, Query()] = None,
) -> InstanceListResponse:
    """
    List instances belonging to the customer's tenant.

    Only instances owned by this tenant are returned.
    Filter by status or additional labels.
    """
    # Build labels filter - always include tenant_id
    labels = {"tenant_id": actor.effective_tenant_id}
    if label:
        for l in label:
            if "=" in l:
                k, v = l.split("=", 1)
                labels[k] = v

    instances = await instance_manager.list_instances(status=status, labels=labels)
    return InstanceListResponse(instances=instances, total=len(instances))


@router.get("/{instance_id}", response_model=Instance)
async def get_instance(
    instance_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> Instance:
    """Get a specific instance by ID (must belong to customer's tenant)."""
    instance = await instance_manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

    # Verify tenant ownership
    instance_tenant = instance.labels.get("tenant_id") if instance.labels else None
    if instance_tenant != actor.effective_tenant_id:
        raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

    return instance


@router.post("/{instance_id}/start", response_model=InstanceStartResponse)
async def start_instance(
    instance_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> InstanceStartResponse:
    """Start an instance (must belong to customer's tenant)."""
    # Verify ownership first
    instance = await _get_tenant_instance(instance_id, actor)

    try:
        instance = await instance_manager.start_instance(instance_id)
        return InstanceStartResponse(
            id=instance.id,
            status=instance.status,
            message="Instance starting",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{instance_id}/stop", response_model=InstanceStartResponse)
async def stop_instance(
    instance_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> InstanceStartResponse:
    """Stop an instance (must belong to customer's tenant)."""
    # Verify ownership first
    instance = await _get_tenant_instance(instance_id, actor)

    try:
        instance = await instance_manager.stop_instance(instance_id)
        return InstanceStartResponse(
            id=instance.id,
            status=instance.status,
            message="Instance stopped",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{instance_id}")
async def destroy_instance(
    instance_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
):
    """Destroy an instance and all its resources (must belong to customer's tenant)."""
    # Verify ownership first
    await _get_tenant_instance(instance_id, actor)

    try:
        await instance_manager.destroy_instance(instance_id)
        return {"message": f"Instance {instance_id} destroyed"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{instance_id}/wait", response_model=Instance)
async def wait_for_instance(
    instance_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
    timeout: int = Query(default=300, ge=30, le=600),
) -> Instance:
    """
    Wait for an instance to become ready.

    Blocks until the instance is running or times out.
    Instance must belong to customer's tenant.
    """
    # Verify ownership first
    await _get_tenant_instance(instance_id, actor)

    try:
        instance = await instance_manager.wait_for_ready(instance_id, timeout)
        return instance
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{instance_id}/health")
async def get_instance_health(
    instance_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
):
    """Get the health status of an instance (must belong to customer's tenant)."""
    # Verify ownership first
    await _get_tenant_instance(instance_id, actor)

    try:
        status = await instance_manager.get_instance_health(instance_id)
        return {"id": instance_id, "status": status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{instance_id}/logs")
async def get_instance_logs(
    instance_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
    container: str | None = None,
    tail: int = Query(default=100, ge=1, le=1000),
):
    """Get logs from an instance's containers (must belong to customer's tenant)."""
    # Verify ownership first
    await _get_tenant_instance(instance_id, actor)

    try:
        logs = await instance_manager.get_instance_logs(instance_id, container, tail)
        return {"id": instance_id, "logs": logs}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{instance_id}/extend", response_model=Instance)
async def extend_instance_ttl(
    instance_id: str,
    request: ExtendTTLRequest,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> Instance:
    """Extend an instance's time-to-live (must belong to customer's tenant)."""
    # Verify ownership first
    await _get_tenant_instance(instance_id, actor)

    try:
        instance = await instance_manager.extend_ttl(instance_id, request.hours)
        return instance
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Helper Functions
# =============================================================================


async def _get_tenant_instance(instance_id: str, actor: ActorContext) -> Instance:
    """Get instance and verify it belongs to the customer's tenant."""
    instance = await instance_manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

    # Verify tenant ownership
    instance_tenant = instance.labels.get("tenant_id") if instance.labels else None
    if instance_tenant != actor.effective_tenant_id:
        raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

    return instance
