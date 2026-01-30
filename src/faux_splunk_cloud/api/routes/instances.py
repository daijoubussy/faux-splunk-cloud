"""
Instance Management API endpoints.

These endpoints are designed for:
- Backstage integration
- CI/CD pipelines (Concourse, GitHub Actions, etc.)
- Direct API usage
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from faux_splunk_cloud.api.deps import get_current_token, require_auth
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


@router.post("", response_model=Instance)
async def create_instance(
    request: InstanceCreate,
    _: Annotated[str, Depends(require_auth)],
) -> Instance:
    """
    Create a new ephemeral Splunk instance.

    The instance will be provisioned with Victoria Experience defaults
    and configured according to the specified topology.
    """
    instance = await instance_manager.create_instance(request)
    return instance


@router.get("", response_model=InstanceListResponse)
async def list_instances(
    status: InstanceStatus | None = None,
    label: Annotated[list[str] | None, Query()] = None,
) -> InstanceListResponse:
    """
    List all instances with optional filtering.

    Filter by status or labels. Labels are specified as key=value pairs.
    """
    # Parse labels
    labels = {}
    if label:
        for l in label:
            if "=" in l:
                k, v = l.split("=", 1)
                labels[k] = v

    instances = await instance_manager.list_instances(status=status, labels=labels or None)
    return InstanceListResponse(instances=instances, total=len(instances))


@router.get("/{instance_id}", response_model=Instance)
async def get_instance(instance_id: str) -> Instance:
    """Get a specific instance by ID."""
    instance = await instance_manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")
    return instance


@router.post("/{instance_id}/start", response_model=InstanceStartResponse)
async def start_instance(
    instance_id: str,
    _: Annotated[str, Depends(require_auth)],
) -> InstanceStartResponse:
    """Start an instance."""
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
    _: Annotated[str, Depends(require_auth)],
) -> InstanceStartResponse:
    """Stop an instance."""
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
    _: Annotated[str, Depends(require_auth)],
):
    """Destroy an instance and all its resources."""
    try:
        await instance_manager.destroy_instance(instance_id)
        return {"message": f"Instance {instance_id} destroyed"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{instance_id}/wait", response_model=Instance)
async def wait_for_instance(
    instance_id: str,
    timeout: int = Query(default=300, ge=30, le=600),
) -> Instance:
    """
    Wait for an instance to become ready.

    Blocks until the instance is running or times out.
    """
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
async def get_instance_health(instance_id: str):
    """Get the health status of an instance."""
    try:
        status = await instance_manager.get_instance_health(instance_id)
        return {"id": instance_id, "status": status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{instance_id}/logs")
async def get_instance_logs(
    instance_id: str,
    container: str | None = None,
    tail: int = Query(default=100, ge=1, le=1000),
):
    """Get logs from an instance's containers."""
    try:
        logs = await instance_manager.get_instance_logs(instance_id, container, tail)
        return {"id": instance_id, "logs": logs}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{instance_id}/extend", response_model=Instance)
async def extend_instance_ttl(
    instance_id: str,
    request: ExtendTTLRequest,
    _: Annotated[str, Depends(require_auth)],
) -> Instance:
    """Extend an instance's time-to-live."""
    try:
        instance = await instance_manager.extend_ttl(instance_id, request.hours)
        return instance
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
