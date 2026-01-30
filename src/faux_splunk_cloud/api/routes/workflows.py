"""
API routes for workflow management.

Provides endpoints for managing threat intelligence workflows
(MineMeld-compatible miner/processor/output pipelines).
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from faux_splunk_cloud.workflows import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowStatus,
    get_workflow_engine,
    list_prototypes,
    get_prototype,
    PrototypeType,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])

# In-memory storage for workflows (would use database in production)
_workflows: dict[str, Workflow] = {}


# =============================================================================
# Request/Response Models
# =============================================================================


class WorkflowCreate(BaseModel):
    """Request model for creating a workflow."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class WorkflowUpdate(BaseModel):
    """Request model for updating a workflow."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    nodes: Optional[list[WorkflowNode]] = None
    edges: Optional[list[WorkflowEdge]] = None
    schedule: Optional[str] = None


class WorkflowResponse(BaseModel):
    """Response model for a workflow."""

    id: str
    name: str
    description: str
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    schedule: Optional[str]
    status: str
    created_at: str
    updated_at: str
    last_run: Optional[str]
    run_count: int


class WorkflowListResponse(BaseModel):
    """Response model for listing workflows."""

    workflows: list[WorkflowResponse]
    total: int


class PrototypeResponse(BaseModel):
    """Response model for a workflow prototype."""

    id: str
    name: str
    type: str
    description: str
    category: str
    config_schema: dict[str, Any]
    default_config: dict[str, Any]


class PrototypeListResponse(BaseModel):
    """Response model for listing prototypes."""

    prototypes: list[PrototypeResponse]
    total: int


class ExecutionResponse(BaseModel):
    """Response model for workflow execution."""

    workflow_id: str
    status: str
    indicators_processed: int
    nodes_executed: int
    timestamp: str


# =============================================================================
# Workflow CRUD Endpoints
# =============================================================================


@router.get("", response_model=WorkflowListResponse)
async def list_workflows_endpoint(
    status: Optional[str] = Query(None, description="Filter by status"),
) -> WorkflowListResponse:
    """List all workflows."""
    workflows = list(_workflows.values())

    if status:
        workflows = [w for w in workflows if w.status == status]

    return WorkflowListResponse(
        workflows=[
            WorkflowResponse(
                id=w.id,
                name=w.name,
                description=w.description,
                nodes=w.nodes,
                edges=w.edges,
                schedule=w.schedule,
                status=w.status,
                created_at=w.created_at.isoformat(),
                updated_at=w.updated_at.isoformat(),
                last_run=w.last_run.isoformat() if w.last_run else None,
                run_count=w.run_count,
            )
            for w in workflows
        ],
        total=len(workflows),
    )


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow_endpoint(request: WorkflowCreate) -> WorkflowResponse:
    """Create a new workflow."""
    workflow = Workflow(
        name=request.name,
        description=request.description,
    )

    _workflows[workflow.id] = workflow

    # Register with engine
    engine = get_workflow_engine()
    engine.register_workflow(workflow)

    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        nodes=workflow.nodes,
        edges=workflow.edges,
        schedule=workflow.schedule,
        status=workflow.status,
        created_at=workflow.created_at.isoformat(),
        updated_at=workflow.updated_at.isoformat(),
        last_run=workflow.last_run.isoformat() if workflow.last_run else None,
        run_count=workflow.run_count,
    )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow_endpoint(workflow_id: str) -> WorkflowResponse:
    """Get a workflow by ID."""
    workflow = _workflows.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        nodes=workflow.nodes,
        edges=workflow.edges,
        schedule=workflow.schedule,
        status=workflow.status,
        created_at=workflow.created_at.isoformat(),
        updated_at=workflow.updated_at.isoformat(),
        last_run=workflow.last_run.isoformat() if workflow.last_run else None,
        run_count=workflow.run_count,
    )


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow_endpoint(
    workflow_id: str,
    request: WorkflowUpdate,
) -> WorkflowResponse:
    """Update a workflow."""
    workflow = _workflows.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if request.name is not None:
        workflow.name = request.name
    if request.description is not None:
        workflow.description = request.description
    if request.nodes is not None:
        workflow.nodes = request.nodes
    if request.edges is not None:
        workflow.edges = request.edges
    if request.schedule is not None:
        workflow.schedule = request.schedule

    from datetime import datetime
    workflow.updated_at = datetime.utcnow()

    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        nodes=workflow.nodes,
        edges=workflow.edges,
        schedule=workflow.schedule,
        status=workflow.status,
        created_at=workflow.created_at.isoformat(),
        updated_at=workflow.updated_at.isoformat(),
        last_run=workflow.last_run.isoformat() if workflow.last_run else None,
        run_count=workflow.run_count,
    )


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow_endpoint(workflow_id: str) -> None:
    """Delete a workflow."""
    if workflow_id not in _workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Unregister from engine
    engine = get_workflow_engine()
    engine.unregister_workflow(workflow_id)

    del _workflows[workflow_id]


# =============================================================================
# Workflow Execution Endpoints
# =============================================================================


@router.post("/{workflow_id}/execute", response_model=ExecutionResponse)
async def execute_workflow_endpoint(workflow_id: str) -> ExecutionResponse:
    """Execute a workflow."""
    workflow = _workflows.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    engine = get_workflow_engine()

    try:
        result = await engine.execute_workflow(workflow_id)
        return ExecutionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}")


@router.post("/{workflow_id}/pause", response_model=WorkflowResponse)
async def pause_workflow_endpoint(workflow_id: str) -> WorkflowResponse:
    """Pause a running workflow."""
    workflow = _workflows.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    engine = get_workflow_engine()

    try:
        await engine.pause_workflow(workflow_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        nodes=workflow.nodes,
        edges=workflow.edges,
        schedule=workflow.schedule,
        status=workflow.status,
        created_at=workflow.created_at.isoformat(),
        updated_at=workflow.updated_at.isoformat(),
        last_run=workflow.last_run.isoformat() if workflow.last_run else None,
        run_count=workflow.run_count,
    )


# =============================================================================
# Prototype Endpoints
# =============================================================================


@router.get("/prototypes", response_model=PrototypeListResponse)
async def list_prototypes_endpoint(
    type: Optional[str] = Query(None, description="Filter by type (miner, processor, output)"),
    category: Optional[str] = Query(None, description="Filter by category"),
) -> PrototypeListResponse:
    """List available workflow prototypes."""
    prototype_type = None
    if type:
        try:
            prototype_type = PrototypeType(type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid type: {type}")

    prototypes = list_prototypes(prototype_type=prototype_type, category=category)

    return PrototypeListResponse(
        prototypes=[
            PrototypeResponse(
                id=p.id,
                name=p.name,
                type=p.type,
                description=p.description,
                category=p.category,
                config_schema={
                    k: v.dict() for k, v in p.config_schema.items()
                },
                default_config=p.default_config,
            )
            for p in prototypes
        ],
        total=len(prototypes),
    )


@router.get("/prototypes/{prototype_id}", response_model=PrototypeResponse)
async def get_prototype_endpoint(prototype_id: str) -> PrototypeResponse:
    """Get a prototype by ID."""
    prototype = get_prototype(prototype_id)
    if not prototype:
        raise HTTPException(status_code=404, detail="Prototype not found")

    return PrototypeResponse(
        id=prototype.id,
        name=prototype.name,
        type=prototype.type,
        description=prototype.description,
        category=prototype.category,
        config_schema={
            k: v.dict() for k, v in prototype.config_schema.items()
        },
        default_config=prototype.default_config,
    )
