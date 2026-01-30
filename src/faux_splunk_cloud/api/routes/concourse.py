"""
Concourse CI API endpoints for pipeline management.

Provides admin access to Concourse for managing CI/CD pipelines.
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from faux_splunk_cloud.api.deps import (
    AnyAuthData,
    require_platform_admin,
)
from faux_splunk_cloud.services.concourse_service import concourse_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ConcourseInfo(BaseModel):
    """Concourse server information."""
    version: str | None = None
    worker_version: str | None = None
    external_url: str | None = None
    cluster_name: str | None = None
    error: str | None = None


class PipelineInfo(BaseModel):
    """Pipeline information."""
    id: int | None = None
    name: str
    team_name: str
    paused: bool = False
    public: bool = False
    archived: bool = False
    last_updated: int | None = None


class PipelineList(BaseModel):
    """List of pipelines."""
    pipelines: list[PipelineInfo]
    total: int


class JobInfo(BaseModel):
    """Job information."""
    id: int | None = None
    name: str
    pipeline_name: str
    team_name: str
    paused: bool = False
    has_new_inputs: bool = False
    next_build: dict[str, Any] | None = None
    finished_build: dict[str, Any] | None = None


class JobList(BaseModel):
    """List of jobs."""
    jobs: list[JobInfo]
    total: int


class BuildInfo(BaseModel):
    """Build information."""
    id: int
    name: str
    status: str
    team_name: str
    pipeline_name: str | None = None
    job_name: str | None = None
    start_time: int | None = None
    end_time: int | None = None


class BuildList(BaseModel):
    """List of builds."""
    builds: list[BuildInfo]
    total: int


class WorkerInfo(BaseModel):
    """Worker information."""
    name: str
    state: str
    addr: str | None = None
    platform: str | None = None
    version: str | None = None
    start_time: int | None = None


class WorkerList(BaseModel):
    """List of workers."""
    workers: list[WorkerInfo]
    total: int


class TeamInfo(BaseModel):
    """Team information."""
    id: int
    name: str


class TeamList(BaseModel):
    """List of teams."""
    teams: list[TeamInfo]
    total: int


class TriggerResponse(BaseModel):
    """Response from triggering a job."""
    build_id: int
    build_name: str
    status: str


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


# Status endpoints


@router.get("/info", response_model=ConcourseInfo)
async def get_concourse_info() -> ConcourseInfo:
    """
    Get Concourse server information (public endpoint).
    """
    info = await concourse_service.get_info()
    if "error" in info:
        return ConcourseInfo(error=info["error"])
    return ConcourseInfo(
        version=info.get("version"),
        worker_version=info.get("worker_version"),
        external_url=info.get("external_url"),
        cluster_name=info.get("cluster_name"),
    )


@router.get("/health")
async def get_concourse_health() -> dict[str, bool]:
    """
    Check Concourse health (public endpoint).
    """
    healthy = await concourse_service.is_healthy()
    return {"healthy": healthy}


# Team endpoints


@router.get("/teams", response_model=TeamList)
async def list_teams(
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
) -> TeamList:
    """
    List all Concourse teams.

    Requires platform admin role.
    """
    teams_data = await concourse_service.list_teams()
    teams = [TeamInfo(id=t.get("id", 0), name=t.get("name", "")) for t in teams_data]
    return TeamList(teams=teams, total=len(teams))


# Pipeline endpoints


@router.get("/pipelines", response_model=PipelineList)
async def list_pipelines(
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
    team: str = "main",
) -> PipelineList:
    """
    List pipelines for a team.

    Requires platform admin role.
    """
    pipelines_data = await concourse_service.list_pipelines(team)
    pipelines = [
        PipelineInfo(
            id=p.get("id"),
            name=p.get("name", ""),
            team_name=p.get("team_name", team),
            paused=p.get("paused", False),
            public=p.get("public", False),
            archived=p.get("archived", False),
            last_updated=p.get("last_updated"),
        )
        for p in pipelines_data
    ]
    return PipelineList(pipelines=pipelines, total=len(pipelines))


@router.get("/pipelines/{pipeline}", response_model=PipelineInfo)
async def get_pipeline(
    pipeline: str,
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
    team: str = "main",
) -> PipelineInfo:
    """
    Get pipeline details.

    Requires platform admin role.
    """
    data = await concourse_service.get_pipeline(team, pipeline)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline not found: {pipeline}",
        )
    return PipelineInfo(
        id=data.get("id"),
        name=data.get("name", pipeline),
        team_name=data.get("team_name", team),
        paused=data.get("paused", False),
        public=data.get("public", False),
        archived=data.get("archived", False),
        last_updated=data.get("last_updated"),
    )


@router.put("/pipelines/{pipeline}/pause", response_model=MessageResponse)
async def pause_pipeline(
    pipeline: str,
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
    team: str = "main",
) -> MessageResponse:
    """
    Pause a pipeline.

    Requires platform admin role.
    """
    success = await concourse_service.pause_pipeline(team, pipeline)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause pipeline",
        )
    return MessageResponse(message=f"Pipeline {pipeline} paused")


@router.put("/pipelines/{pipeline}/unpause", response_model=MessageResponse)
async def unpause_pipeline(
    pipeline: str,
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
    team: str = "main",
) -> MessageResponse:
    """
    Unpause a pipeline.

    Requires platform admin role.
    """
    success = await concourse_service.unpause_pipeline(team, pipeline)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unpause pipeline",
        )
    return MessageResponse(message=f"Pipeline {pipeline} unpaused")


# Job endpoints


@router.get("/pipelines/{pipeline}/jobs", response_model=JobList)
async def list_jobs(
    pipeline: str,
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
    team: str = "main",
) -> JobList:
    """
    List jobs in a pipeline.

    Requires platform admin role.
    """
    jobs_data = await concourse_service.list_jobs(team, pipeline)
    jobs = [
        JobInfo(
            id=j.get("id"),
            name=j.get("name", ""),
            pipeline_name=j.get("pipeline_name", pipeline),
            team_name=j.get("team_name", team),
            paused=j.get("paused", False),
            has_new_inputs=j.get("has_new_inputs", False),
            next_build=j.get("next_build"),
            finished_build=j.get("finished_build"),
        )
        for j in jobs_data
    ]
    return JobList(jobs=jobs, total=len(jobs))


@router.post("/pipelines/{pipeline}/jobs/{job}/trigger", response_model=TriggerResponse)
async def trigger_job(
    pipeline: str,
    job: str,
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
    team: str = "main",
) -> TriggerResponse:
    """
    Trigger a job to create a new build.

    Requires platform admin role.
    """
    build = await concourse_service.trigger_job(team, pipeline, job)
    if build is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger job",
        )
    return TriggerResponse(
        build_id=build.get("id", 0),
        build_name=build.get("name", ""),
        status=build.get("status", "pending"),
    )


# Build endpoints


@router.get("/builds", response_model=BuildList)
async def list_builds(
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
    team: str | None = None,
    pipeline: str | None = None,
    job: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
) -> BuildList:
    """
    List builds with optional filtering.

    Requires platform admin role.
    """
    builds_data = await concourse_service.list_builds(team, pipeline, job, limit)
    builds = [
        BuildInfo(
            id=b.get("id", 0),
            name=b.get("name", ""),
            status=b.get("status", "unknown"),
            team_name=b.get("team_name", ""),
            pipeline_name=b.get("pipeline_name"),
            job_name=b.get("job_name"),
            start_time=b.get("start_time"),
            end_time=b.get("end_time"),
        )
        for b in builds_data
    ]
    return BuildList(builds=builds, total=len(builds))


@router.get("/builds/{build_id}", response_model=BuildInfo)
async def get_build(
    build_id: int,
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
) -> BuildInfo:
    """
    Get build details.

    Requires platform admin role.
    """
    build = await concourse_service.get_build(build_id)
    if build is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build not found: {build_id}",
        )
    return BuildInfo(
        id=build.get("id", build_id),
        name=build.get("name", ""),
        status=build.get("status", "unknown"),
        team_name=build.get("team_name", ""),
        pipeline_name=build.get("pipeline_name"),
        job_name=build.get("job_name"),
        start_time=build.get("start_time"),
        end_time=build.get("end_time"),
    )


# Worker endpoints


@router.get("/workers", response_model=WorkerList)
async def list_workers(
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
) -> WorkerList:
    """
    List Concourse workers.

    Requires platform admin role.
    """
    workers_data = await concourse_service.list_workers()
    workers = [
        WorkerInfo(
            name=w.get("name", ""),
            state=w.get("state", "unknown"),
            addr=w.get("addr"),
            platform=w.get("platform"),
            version=w.get("version"),
            start_time=w.get("start_time"),
        )
        for w in workers_data
    ]
    return WorkerList(workers=workers, total=len(workers))
