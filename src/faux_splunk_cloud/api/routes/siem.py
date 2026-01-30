"""
SIEM API endpoints for the Faux Splunk Cloud administrative portal.

Provides search, dashboarding, alerting, and reporting capabilities
using the Splunk Enterprise backend for platform-wide tenant reporting.

NOTE: All SIEM endpoints require platform admin access. This module is
specifically for the FSC administrative team to monitor and report on
all tenants across the platform.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from faux_splunk_cloud.api.deps import AnyAuthData, require_admin
from faux_splunk_cloud.services.siem_service import siem_service

router = APIRouter(
    dependencies=[Depends(require_admin)],  # All SIEM endpoints require admin
    tags=["siem-admin"],
)


# ==================== Request/Response Models ====================


class SearchRequest(BaseModel):
    """Request to execute a SPL search."""

    query: str = Field(..., min_length=1, description="SPL query string")
    earliest_time: str = Field(default="-24h", description="Start time")
    latest_time: str = Field(default="now", description="End time")
    max_results: int = Field(default=1000, ge=1, le=10000, description="Maximum results")
    timeout_seconds: int = Field(default=60, ge=1, le=300, description="Search timeout")


class AsyncSearchRequest(BaseModel):
    """Request to start an async search."""

    query: str = Field(..., min_length=1, description="SPL query string")
    earliest_time: str = Field(default="-24h", description="Start time")
    latest_time: str = Field(default="now", description="End time")


class SavedSearchCreate(BaseModel):
    """Request to create a saved search."""

    name: str = Field(..., min_length=1, max_length=100, description="Search name")
    query: str = Field(..., min_length=1, description="SPL query string")
    description: str = Field(default="", max_length=500, description="Description")
    cron_schedule: str | None = Field(default=None, description="Cron schedule for scheduling")
    earliest_time: str = Field(default="-24h", description="Default earliest time")
    latest_time: str = Field(default="now", description="Default latest time")


class DashboardCreate(BaseModel):
    """Request to create a dashboard."""

    name: str = Field(..., min_length=1, max_length=100, description="Dashboard name")
    label: str = Field(..., min_length=1, max_length=200, description="Display label")
    xml_content: str = Field(..., description="Dashboard XML definition")


# ==================== Health/Status ====================


@router.get("/status")
async def get_siem_status() -> dict[str, Any]:
    """Get SIEM service connection status."""
    return {
        "connected": siem_service.is_connected(),
        "service": "splunk",
    }


# ==================== Search ====================


@router.post("/search")
async def execute_search(
    request: SearchRequest,
    _: Annotated[AnyAuthData, Depends(require_admin)],
) -> dict[str, Any]:
    """
    Execute a synchronous SPL search and return results.

    The search will block until completion or timeout.
    """
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    try:
        result = await siem_service.search(
            query=request.query,
            earliest_time=request.earliest_time,
            latest_time=request.latest_time,
            max_results=request.max_results,
            timeout_seconds=request.timeout_seconds,
        )
        return result
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.post("/search/async")
async def start_async_search(
    request: AsyncSearchRequest,
    _: Annotated[AnyAuthData, Depends(require_admin)],
) -> dict[str, str]:
    """
    Start an asynchronous search and return the job ID.

    Use GET /search/{job_id}/status to check progress.
    Use GET /search/{job_id}/results to retrieve results.
    """
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    try:
        job_id = await siem_service.search_async(
            query=request.query,
            earliest_time=request.earliest_time,
            latest_time=request.latest_time,
        )
        return {"job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start search: {e}")


@router.get("/search/{job_id}/status")
async def get_search_status(
    job_id: str,
    _: Annotated[AnyAuthData, Depends(require_admin)],
) -> dict[str, Any]:
    """Get the status of an async search job."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    return await siem_service.get_search_status(job_id)


@router.get("/search/{job_id}/results")
async def get_search_results(
    job_id: str,
    _: Annotated[AnyAuthData, Depends(require_admin)],
    offset: int = Query(default=0, ge=0),
    count: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    """Get results from a completed search job."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    return await siem_service.get_search_results(job_id, offset=offset, count=count)


@router.delete("/search/{job_id}")
async def cancel_search(
    job_id: str,
    _: Annotated[AnyAuthData, Depends(require_admin)],
) -> dict[str, Any]:
    """Cancel a running search job."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    success = await siem_service.cancel_search(job_id)
    return {"cancelled": success}


# ==================== Saved Searches ====================


@router.get("/savedsearches")
async def list_saved_searches(
    _: Annotated[AnyAuthData, Depends(require_admin)],
    app: str | None = Query(default=None, description="Filter by Splunk app"),
) -> dict[str, Any]:
    """List all saved searches."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    searches = await siem_service.list_saved_searches(app=app)
    return {"saved_searches": searches, "count": len(searches)}


@router.get("/savedsearches/{name}")
async def get_saved_search(
    name: str,
    _: Annotated[AnyAuthData, Depends(require_admin)],
) -> dict[str, Any]:
    """Get a specific saved search."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    search = await siem_service.get_saved_search(name)
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return search


@router.post("/savedsearches")
async def create_saved_search(
    request: SavedSearchCreate,
    _: Annotated[AnyAuthData, Depends(require_admin)],
) -> dict[str, Any]:
    """Create a new saved search."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    try:
        result = await siem_service.create_saved_search(
            name=request.name,
            query=request.query,
            description=request.description,
            cron_schedule=request.cron_schedule,
            earliest_time=request.earliest_time,
            latest_time=request.latest_time,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create saved search: {e}")


@router.post("/savedsearches/{name}/run")
async def run_saved_search(
    name: str,
    _: Annotated[AnyAuthData, Depends(require_admin)],
) -> dict[str, str]:
    """Run a saved search and return the job ID."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    try:
        job_id = await siem_service.run_saved_search(name)
        return {"job_id": job_id}
    except KeyError:
        raise HTTPException(status_code=404, detail="Saved search not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run saved search: {e}")


# ==================== Dashboards ====================


@router.get("/dashboards")
async def list_dashboards(
    _: Annotated[AnyAuthData, Depends(require_admin)],
    app: str | None = Query(default=None, description="Filter by Splunk app"),
) -> dict[str, Any]:
    """List all dashboards."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    dashboards = await siem_service.list_dashboards(app=app)
    return {"dashboards": dashboards, "count": len(dashboards)}


@router.get("/dashboards/{name}")
async def get_dashboard(
    name: str,
    _: Annotated[AnyAuthData, Depends(require_admin)],
) -> dict[str, Any]:
    """Get a specific dashboard with its XML definition."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    dashboard = await siem_service.get_dashboard(name)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return dashboard


@router.post("/dashboards")
async def create_dashboard(
    request: DashboardCreate,
    _: Annotated[AnyAuthData, Depends(require_admin)],
) -> dict[str, Any]:
    """Create a new dashboard."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    try:
        result = await siem_service.create_dashboard(
            name=request.name,
            label=request.label,
            xml_content=request.xml_content,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create dashboard: {e}")


# ==================== Alerts ====================


@router.get("/alerts")
async def list_alerts(
    _: Annotated[AnyAuthData, Depends(require_admin)],
) -> dict[str, Any]:
    """List all triggered alerts."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    alerts = await siem_service.list_alerts()
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/alerts/{saved_search_name}/history")
async def get_alert_history(
    saved_search_name: str,
    _: Annotated[AnyAuthData, Depends(require_admin)],
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    """Get alert trigger history for a saved search."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    history = await siem_service.get_alert_history(saved_search_name, limit=limit)
    return {"history": history, "count": len(history)}


# ==================== Reports ====================


@router.get("/reports")
async def list_reports(
    _: Annotated[AnyAuthData, Depends(require_admin)],
) -> dict[str, Any]:
    """List all scheduled reports (scheduled saved searches)."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    reports = await siem_service.list_reports()
    return {"reports": reports, "count": len(reports)}


# ==================== Quick Queries ====================


@router.get("/stats/event-count")
async def get_event_count(
    _: Annotated[AnyAuthData, Depends(require_admin)],
    index: str = Query(default="*", description="Index to count"),
    earliest_time: str = Query(default="-24h", description="Time range start"),
) -> dict[str, Any]:
    """Get total event count for an index."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    count = await siem_service.get_event_count(index=index, earliest_time=earliest_time)
    return {"index": index, "count": count, "earliest_time": earliest_time}


@router.get("/stats/top-sources")
async def get_top_sources(
    _: Annotated[AnyAuthData, Depends(require_admin)],
    index: str = Query(default="*", description="Index to analyze"),
    limit: int = Query(default=10, ge=1, le=100),
    earliest_time: str = Query(default="-24h", description="Time range start"),
) -> dict[str, Any]:
    """Get top sources by event count."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    sources = await siem_service.get_top_sources(
        index=index, limit=limit, earliest_time=earliest_time
    )
    return {"index": index, "sources": sources, "earliest_time": earliest_time}


@router.get("/stats/top-sourcetypes")
async def get_top_sourcetypes(
    _: Annotated[AnyAuthData, Depends(require_admin)],
    index: str = Query(default="*", description="Index to analyze"),
    limit: int = Query(default=10, ge=1, le=100),
    earliest_time: str = Query(default="-24h", description="Time range start"),
) -> dict[str, Any]:
    """Get top sourcetypes by event count."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    sourcetypes = await siem_service.get_top_sourcetypes(
        index=index, limit=limit, earliest_time=earliest_time
    )
    return {"index": index, "sourcetypes": sourcetypes, "earliest_time": earliest_time}


@router.get("/stats/timeline")
async def get_timeline(
    _: Annotated[AnyAuthData, Depends(require_admin)],
    index: str = Query(default="*", description="Index to analyze"),
    span: str = Query(default="1h", description="Time bucket span"),
    earliest_time: str = Query(default="-24h", description="Time range start"),
) -> dict[str, Any]:
    """Get event timeline for visualization."""
    if not siem_service.is_connected():
        raise HTTPException(status_code=503, detail="SIEM service not connected")

    timeline = await siem_service.get_timeline(
        index=index, span=span, earliest_time=earliest_time
    )
    return {"index": index, "timeline": timeline, "span": span, "earliest_time": earliest_time}
