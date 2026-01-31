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


@router.post("", response_model=Instance, status_code=201)
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


# ==================== Instance Export ====================

from enum import Enum
from fastapi.responses import StreamingResponse


class ExportFormat(str, Enum):
    """Supported export formats."""
    DOCKER_COMPOSE = "docker-compose"
    KUBERNETES = "kubernetes"
    ANSIBLE = "ansible"
    BARE_METAL = "bare-metal"
    TERRAFORM = "terraform"


class ExportScope(str, Enum):
    """What to include in the export."""
    CONFIG_ONLY = "config-only"
    CONFIG_AND_APPS = "config-and-apps"
    FULL = "full"


class ExportInstanceRequest(BaseModel):
    """Request to export an instance for deployment elsewhere."""

    format: ExportFormat = Field(
        default=ExportFormat.DOCKER_COMPOSE,
        description="Export format",
    )
    scope: ExportScope = Field(
        default=ExportScope.CONFIG_AND_APPS,
        description="What to include",
    )
    include_credentials: bool = Field(
        default=False,
        description="Include passwords (not recommended for sharing)",
    )


class ExportFormatInfo(BaseModel):
    """Information about an export format."""

    id: str
    name: str
    description: str
    use_case: str


class ExportFormatsResponse(BaseModel):
    """List of available export formats."""

    formats: list[ExportFormatInfo]


@router.get("/{instance_id}/export/formats", response_model=ExportFormatsResponse)
async def list_export_formats(instance_id: str) -> ExportFormatsResponse:
    """
    List available export formats for deploying this instance elsewhere.

    Returns all supported formats with descriptions and use cases.
    """
    instance = await instance_manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    formats = [
        ExportFormatInfo(
            id=ExportFormat.DOCKER_COMPOSE.value,
            name="Docker Compose",
            description="Ready-to-run docker-compose.yml with configuration files",
            use_case="Local development, single-server Docker deployment",
        ),
        ExportFormatInfo(
            id=ExportFormat.KUBERNETES.value,
            name="Kubernetes",
            description="Kubernetes manifests and optional Helm chart",
            use_case="Container orchestration, cloud-native deployment",
        ),
        ExportFormatInfo(
            id=ExportFormat.ANSIBLE.value,
            name="Ansible",
            description="Ansible playbook and roles for automated deployment",
            use_case="Multi-server deployment, configuration management",
        ),
        ExportFormatInfo(
            id=ExportFormat.BARE_METAL.value,
            name="Bare Metal",
            description="Installation scripts and systemd service files",
            use_case="Traditional server deployment, on-premises",
        ),
        ExportFormatInfo(
            id=ExportFormat.TERRAFORM.value,
            name="Terraform",
            description="Terraform configuration for AWS deployment",
            use_case="Infrastructure as Code, cloud deployment",
        ),
    ]

    return ExportFormatsResponse(formats=formats)


@router.get("/{instance_id}/export/preview")
async def preview_instance_export(
    instance_id: str,
    format: ExportFormat = Query(default=ExportFormat.DOCKER_COMPOSE),
) -> dict:
    """
    Preview what will be included in an export.

    Returns a summary of configuration files, apps, dashboards,
    and saved searches that will be exported.
    """
    instance = await instance_manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    if instance.status != "running":
        raise HTTPException(
            status_code=400,
            detail="Instance must be running to preview export. Please start the instance first.",
        )

    # Import here to avoid circular imports
    from faux_splunk_cloud.services.instance_export import (
        ExportScope as ServiceExportScope,
        instance_export_service,
    )

    try:
        configs = await instance_export_service._extract_configs(
            instance=instance,
            scope=ServiceExportScope.CONFIG_AND_APPS,
        )

        return {
            "instance_id": instance.id,
            "instance_name": instance.name,
            "format": format.value,
            "preview": {
                "config_files": list(configs["etc"].keys()),
                "apps": [app["name"] for app in configs["apps"]],
                "saved_searches_count": len(configs["saved_searches"]),
                "dashboards_count": len(configs["dashboards"]),
                "indexes_count": len(configs["indexes"]),
            },
            "estimated_size_kb": sum(len(v) for v in configs["etc"].values()) // 1024 + 10,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {e}")


@router.post("/{instance_id}/export")
async def export_instance_deployment(
    instance_id: str,
    request: ExportInstanceRequest,
    _: Annotated[str, Depends(require_auth)],
) -> StreamingResponse:
    """
    Export an instance for deployment on your own infrastructure.

    Downloads a tar.gz archive containing all necessary files to deploy
    the same Splunk configuration on Docker, Kubernetes, bare metal, or cloud.

    ## Export Formats

    - **docker-compose**: Ready-to-run Docker Compose deployment
    - **kubernetes**: Kubernetes manifests and Helm chart
    - **ansible**: Ansible playbook for automated deployment
    - **bare-metal**: Installation scripts for traditional servers
    - **terraform**: Terraform configuration for AWS

    ## Export Scope

    - **config-only**: Only configuration files (smallest)
    - **config-and-apps**: Configuration + installed apps (recommended)
    - **full**: Everything including index data (can be very large!)

    ## Security Note

    By default, credentials are NOT included in the export.
    Set `include_credentials: true` only if you understand the risks
    and need to replicate exact credentials.
    """
    instance = await instance_manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    if instance.status != "running":
        raise HTTPException(
            status_code=400,
            detail="Instance must be running to export. Please start the instance first.",
        )

    # Import here to avoid circular imports
    from faux_splunk_cloud.services.instance_export import (
        ExportFormat as ServiceExportFormat,
        ExportScope as ServiceExportScope,
        instance_export_service,
    )

    try:
        # Map API enums to service enums
        service_format = ServiceExportFormat(request.format.value)
        service_scope = ServiceExportScope(request.scope.value)

        export_data, filename = await instance_export_service.export_instance(
            instance=instance,
            format=service_format,
            scope=service_scope,
            include_credentials=request.include_credentials,
        )

        return StreamingResponse(
            iter([export_data]),
            media_type="application/gzip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(export_data)),
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")
