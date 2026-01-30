"""
ACS (Admin Config Service) API simulation endpoints.

These endpoints are designed to be compatible with:
- Splunk Terraform Provider (terraform-provider-splunk)
- Splunk SDK for Python
- Direct ACS API calls

Reference: https://help.splunk.com/en/splunk-cloud-platform/administer/admin-config-service-manual/

OpenAPI spec: https://admin.splunk.com/service/info/specs/v2/openapi.json
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from faux_splunk_cloud.api.deps import require_stack_auth
from faux_splunk_cloud.models.acs import (
    ACSApp,
    ACSAppInstallRequest,
    ACSAppListResponse,
    ACSError,
    ACSHECToken,
    ACSHECTokenCreateRequest,
    ACSHECTokenListResponse,
    ACSIndex,
    ACSIndexCreateRequest,
    ACSIndexListResponse,
    ACSResponse,
    IndexDatatype,
)
from faux_splunk_cloud.services.auth import TokenData
from faux_splunk_cloud.services.instance_manager import instance_manager

router = APIRouter()


# =============================================================================
# Index Management Endpoints
# Reference: https://help.splunk.com/en/splunk-cloud-platform/administer/admin-config-service-manual/
# =============================================================================


@router.get(
    "/indexes",
    response_model=ACSIndexListResponse,
    responses={
        401: {"model": ACSError, "description": "Unauthorized"},
        403: {"model": ACSError, "description": "Forbidden"},
    },
)
async def list_indexes(
    stack: Annotated[str, Path(description="Stack/instance ID")],
    token: Annotated[TokenData, Depends(require_stack_auth)],
) -> ACSIndexListResponse:
    """
    List all indexes.

    Returns a list of all indexes configured on the Splunk Cloud Platform deployment.
    This endpoint is compatible with the ACS API format.
    """
    try:
        client = instance_manager.get_splunk_client(stack)
        indexes = await client.list_indexes()
        return ACSIndexListResponse(indexes=indexes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list indexes: {e}")


@router.post(
    "/indexes",
    response_model=ACSIndex,
    status_code=201,
    responses={
        400: {"model": ACSError, "description": "Bad request"},
        401: {"model": ACSError, "description": "Unauthorized"},
        409: {"model": ACSError, "description": "Index already exists"},
    },
)
async def create_index(
    stack: Annotated[str, Path(description="Stack/instance ID")],
    request: ACSIndexCreateRequest,
    token: Annotated[TokenData, Depends(require_stack_auth)],
) -> ACSIndex:
    """
    Create a new index.

    Creates a new index with the specified configuration.
    The index will be created with Victoria Experience defaults.
    """
    try:
        client = instance_manager.get_splunk_client(stack)
        index = await client.create_index(
            name=request.name,
            datatype=request.datatype,
            searchable_days=request.searchableDays,
            max_data_size_mb=request.maxDataSizeMB,
        )
        return index
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Index {request.name} already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create index: {e}")


@router.get(
    "/indexes/{index_name}",
    response_model=ACSIndex,
    responses={
        401: {"model": ACSError, "description": "Unauthorized"},
        404: {"model": ACSError, "description": "Index not found"},
    },
)
async def get_index(
    stack: Annotated[str, Path(description="Stack/instance ID")],
    index_name: Annotated[str, Path(description="Index name")],
    token: Annotated[TokenData, Depends(require_stack_auth)],
) -> ACSIndex:
    """Get a specific index by name."""
    try:
        client = instance_manager.get_splunk_client(stack)
        index = await client.get_index(index_name)
        return index
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get index: {e}")


@router.delete(
    "/indexes/{index_name}",
    response_model=ACSResponse,
    responses={
        401: {"model": ACSError, "description": "Unauthorized"},
        404: {"model": ACSError, "description": "Index not found"},
    },
)
async def delete_index(
    stack: Annotated[str, Path(description="Stack/instance ID")],
    index_name: Annotated[str, Path(description="Index name")],
    token: Annotated[TokenData, Depends(require_stack_auth)],
) -> ACSResponse:
    """Delete an index."""
    try:
        client = instance_manager.get_splunk_client(stack)
        await client.delete_index(index_name)
        return ACSResponse(code="OK", message=f"Index {index_name} deleted")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete index: {e}")


# =============================================================================
# HEC Token Management Endpoints
# =============================================================================


@router.get(
    "/inputs/http-event-collectors",
    response_model=ACSHECTokenListResponse,
    responses={
        401: {"model": ACSError, "description": "Unauthorized"},
    },
)
async def list_hec_tokens(
    stack: Annotated[str, Path(description="Stack/instance ID")],
    token: Annotated[TokenData, Depends(require_stack_auth)],
) -> ACSHECTokenListResponse:
    """
    List all HTTP Event Collector tokens.

    Returns all HEC tokens configured on the deployment.
    """
    try:
        client = instance_manager.get_splunk_client(stack)
        tokens = await client.list_hec_tokens()
        return ACSHECTokenListResponse(**{"http-event-collectors": tokens})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list HEC tokens: {e}")


@router.post(
    "/inputs/http-event-collectors",
    response_model=ACSHECToken,
    status_code=201,
    responses={
        400: {"model": ACSError, "description": "Bad request"},
        401: {"model": ACSError, "description": "Unauthorized"},
        409: {"model": ACSError, "description": "Token already exists"},
    },
)
async def create_hec_token(
    stack: Annotated[str, Path(description="Stack/instance ID")],
    request: ACSHECTokenCreateRequest,
    token: Annotated[TokenData, Depends(require_stack_auth)],
) -> ACSHECToken:
    """
    Create a new HEC token.

    Creates a new HTTP Event Collector token with the specified configuration.
    """
    try:
        client = instance_manager.get_splunk_client(stack)
        hec_token = await client.create_hec_token(
            name=request.name,
            default_index=request.defaultIndex,
            indexes=request.indexes,
            default_sourcetype=request.defaultSourcetype,
            use_ack=request.useACK,
        )
        return hec_token
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"HEC token {request.name} already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create HEC token: {e}")


@router.delete(
    "/inputs/http-event-collectors/{token_name}",
    response_model=ACSResponse,
    responses={
        401: {"model": ACSError, "description": "Unauthorized"},
        404: {"model": ACSError, "description": "Token not found"},
    },
)
async def delete_hec_token(
    stack: Annotated[str, Path(description="Stack/instance ID")],
    token_name: Annotated[str, Path(description="HEC token name")],
    token: Annotated[TokenData, Depends(require_stack_auth)],
) -> ACSResponse:
    """Delete a HEC token."""
    try:
        client = instance_manager.get_splunk_client(stack)
        await client.delete_hec_token(token_name)
        return ACSResponse(code="OK", message=f"HEC token {token_name} deleted")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete HEC token: {e}")


# =============================================================================
# App Management Endpoints (Victoria Experience)
# =============================================================================


@router.get(
    "/apps/victoria",
    response_model=ACSAppListResponse,
    responses={
        401: {"model": ACSError, "description": "Unauthorized"},
    },
)
async def list_apps(
    stack: Annotated[str, Path(description="Stack/instance ID")],
    token: Annotated[TokenData, Depends(require_stack_auth)],
) -> ACSAppListResponse:
    """
    List all installed apps (Victoria Experience).

    In Victoria Experience, apps are automatically installed on all search heads.
    """
    try:
        client = instance_manager.get_splunk_client(stack)
        apps = await client.list_apps()
        return ACSAppListResponse(apps=apps)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list apps: {e}")


@router.post(
    "/apps/victoria",
    response_model=ACSApp,
    status_code=202,  # Accepted - installation is async
    responses={
        400: {"model": ACSError, "description": "Bad request"},
        401: {"model": ACSError, "description": "Unauthorized"},
    },
)
async def install_app(
    stack: Annotated[str, Path(description="Stack/instance ID")],
    request: ACSAppInstallRequest,
    token: Annotated[TokenData, Depends(require_stack_auth)],
) -> ACSApp:
    """
    Install an app (Victoria Experience).

    In Victoria Experience, apps are automatically installed on all search heads
    across the deployment.
    """
    if not request.splunkbaseID and not request.packageURL:
        raise HTTPException(
            status_code=400,
            detail="Either splunkbaseID or packageURL must be provided",
        )

    try:
        client = instance_manager.get_splunk_client(stack)
        # Use package URL if provided, otherwise construct from Splunkbase ID
        app_path = request.packageURL or f"splunkbase:{request.splunkbaseID}"
        app = await client.install_app(app_path)
        return app
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to install app: {e}")


# =============================================================================
# OpenAPI Specification Endpoint
# Mimics the ACS API spec endpoint
# =============================================================================


@router.get(
    "/info/specs/openapi.json",
    include_in_schema=False,
)
async def get_openapi_spec():
    """
    Get the OpenAPI specification for the ACS API.

    This endpoint mimics the official ACS API spec endpoint at:
    https://admin.splunk.com/service/info/specs/v2/openapi.json
    """
    from faux_splunk_cloud.api.app import app

    return app.openapi()
