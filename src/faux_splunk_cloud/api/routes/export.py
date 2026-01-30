"""
Configuration export API endpoints.

Allows tenants to export Splunk configurations as installable app packages.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from faux_splunk_cloud.api.deps import get_actor_context, require_auth
from faux_splunk_cloud.models.audit import AuditAction, ResourceType
from faux_splunk_cloud.models.impersonation import ActorContext
from faux_splunk_cloud.services.audit_service import audit_service
from faux_splunk_cloud.services.config_export_service import (
    ExportableConfigType,
    ExportRequest,
    ExportResult,
    config_export_service,
)
from faux_splunk_cloud.services.instance_manager import instance_manager

router = APIRouter()


class ExportConfigRequest(BaseModel):
    """API request model for configuration export."""

    instance_id: str = Field(..., description="Instance to export from")
    app_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Name for the exported app (alphanumeric, underscores, hyphens)",
    )
    app_label: str = Field(
        default="",
        max_length=200,
        description="Human-readable label for the app",
    )
    app_version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="App version (e.g., 1.0.0)",
    )
    app_description: str = Field(
        default="",
        max_length=1000,
        description="App description",
    )
    config_types: list[ExportableConfigType] = Field(
        default_factory=lambda: [ExportableConfigType.INDEXES],
        description="Configuration types to export",
    )
    include_default_configs: bool = Field(
        default=False,
        description="Include default/system configurations",
    )


class ExportConfigResponse(BaseModel):
    """Response metadata for configuration export."""

    app_name: str
    filename: str
    size_bytes: int
    exported_configs: dict[str, int]
    download_url: str


@router.get("/config-types")
async def list_exportable_config_types() -> dict:
    """List all configuration types that can be exported."""
    return {
        "config_types": [
            {
                "id": ct.value,
                "name": ct.name.replace("_", " ").title(),
                "description": _get_config_type_description(ct),
            }
            for ct in ExportableConfigType
        ]
    }


def _get_config_type_description(ct: ExportableConfigType) -> str:
    """Get a human-readable description for a config type."""
    descriptions = {
        ExportableConfigType.INDEXES: "Index configurations (data types, retention, etc.)",
        ExportableConfigType.HEC_TOKENS: "HTTP Event Collector token configurations",
        ExportableConfigType.SAVED_SEARCHES: "Saved searches and scheduled searches",
        ExportableConfigType.DASHBOARDS: "Dashboard definitions (SimpleXML)",
        ExportableConfigType.MACROS: "Search macros",
        ExportableConfigType.EVENTTYPES: "Event type definitions",
        ExportableConfigType.TAGS: "Tag configurations",
        ExportableConfigType.FIELD_EXTRACTIONS: "Field extraction rules",
        ExportableConfigType.FIELD_ALIASES: "Field alias mappings",
        ExportableConfigType.LOOKUPS: "Lookup definitions and CSV files",
        ExportableConfigType.PROPS: "Props.conf settings (source types, timestamps)",
        ExportableConfigType.TRANSFORMS: "Transforms.conf settings (field extractions, routing)",
        ExportableConfigType.ALERTS: "Alert configurations",
        ExportableConfigType.REPORTS: "Report configurations",
    }
    return descriptions.get(ct, "")


@router.post("/preview")
async def preview_export(
    request: ExportConfigRequest,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> dict:
    """
    Preview what will be exported without actually creating the package.

    Returns a summary of configurations that would be included.
    """
    # Get the instance
    instance = await instance_manager.get_instance(request.instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    # Check tenant access
    if instance.tenant_id and instance.tenant_id != actor.effective_tenant_id:
        if "admin" not in actor.roles:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get Splunk client
    try:
        client = instance_manager.get_splunk_client(request.instance_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Build preview
    preview = {
        "app_name": request.app_name,
        "config_types": [ct.value for ct in request.config_types],
        "estimated_configs": {},
    }

    # Get counts for each config type
    for ct in request.config_types:
        try:
            count = await _get_config_count(client, ct, request.include_default_configs)
            preview["estimated_configs"][ct.value] = count
        except Exception:
            preview["estimated_configs"][ct.value] = 0

    return preview


async def _get_config_count(
    client,
    config_type: ExportableConfigType,
    include_defaults: bool,
) -> int:
    """Get estimated count for a config type."""
    try:
        if config_type == ExportableConfigType.INDEXES:
            indexes = client.list_indexes()
            if include_defaults:
                return len(indexes)
            return len([i for i in indexes if not i.get("name", "").startswith("_")])

        if config_type == ExportableConfigType.HEC_TOKENS:
            tokens = client.list_hec_tokens()
            return len(tokens)

        if config_type == ExportableConfigType.SAVED_SEARCHES:
            service = client._service
            if service:
                return len(list(service.saved_searches))
            return 0

        if config_type == ExportableConfigType.DASHBOARDS:
            service = client._service
            if service:
                return len(list(service.dashboards))
            return 0

    except Exception:
        pass

    return 0


@router.post("", response_class=Response)
async def export_configurations(
    request: ExportConfigRequest,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> Response:
    """
    Export configurations from a Splunk instance as an app package.

    Returns a .spl (tar.gz) file that can be installed on other Splunk instances.
    """
    # Get the instance
    instance = await instance_manager.get_instance(request.instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    # Check tenant access
    if instance.tenant_id and instance.tenant_id != actor.effective_tenant_id:
        if "admin" not in actor.roles:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get Splunk client
    try:
        client = instance_manager.get_splunk_client(request.instance_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create export request
    export_req = ExportRequest(
        app_name=request.app_name,
        app_label=request.app_label,
        app_version=request.app_version,
        app_description=request.app_description,
        config_types=request.config_types,
        include_default_configs=request.include_default_configs,
    )

    # Perform export
    try:
        tar_bytes, result = await config_export_service.export_configs(
            splunk_client=client,
            request=export_req,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

    # Audit log
    await audit_service.log(
        action=AuditAction.CONFIG_EXPORT,
        resource_type=ResourceType.CONFIG_PACKAGE,
        resource_id=request.app_name,
        actor=actor,
        details={
            "instance_id": request.instance_id,
            "app_name": request.app_name,
            "app_version": request.app_version,
            "config_types": [ct.value for ct in request.config_types],
            "exported_configs": result.exported_configs,
            "size_bytes": result.size_bytes,
        },
    )

    # Return the tarball
    return Response(
        content=tar_bytes,
        media_type="application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "X-Export-App-Name": result.app_name,
            "X-Export-Size-Bytes": str(result.size_bytes),
        },
    )


@router.post("/metadata", response_model=ExportConfigResponse)
async def export_configurations_metadata(
    request: ExportConfigRequest,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> ExportConfigResponse:
    """
    Export configurations and return metadata with a download token.

    Use this for async exports or when you need metadata before downloading.
    """
    # Get the instance
    instance = await instance_manager.get_instance(request.instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    # Check tenant access
    if instance.tenant_id and instance.tenant_id != actor.effective_tenant_id:
        if "admin" not in actor.roles:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get Splunk client
    try:
        client = instance_manager.get_splunk_client(request.instance_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create export request
    export_req = ExportRequest(
        app_name=request.app_name,
        app_label=request.app_label,
        app_version=request.app_version,
        app_description=request.app_description,
        config_types=request.config_types,
        include_default_configs=request.include_default_configs,
    )

    # Perform export
    try:
        tar_bytes, result = await config_export_service.export_configs(
            splunk_client=client,
            request=export_req,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

    # TODO: Store tar_bytes with a download token for later retrieval
    # For now, just return metadata
    return ExportConfigResponse(
        app_name=result.app_name,
        filename=result.filename,
        size_bytes=result.size_bytes,
        exported_configs=result.exported_configs,
        download_url=f"/api/v1/export/download/{result.app_name}",
    )
