"""
Data models for the workflow engine.

These models are STIX-compatible and support MineMeld's data structures.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Status of a workflow."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class IndicatorType(str, Enum):
    """Types of threat indicators (STIX compatible)."""

    IPV4 = "ipv4"
    IPV6 = "ipv6"
    DOMAIN = "domain"
    URL = "url"
    HASH_MD5 = "hash_md5"
    HASH_SHA1 = "hash_sha1"
    HASH_SHA256 = "hash_sha256"
    EMAIL = "email"
    FILE_NAME = "file_name"
    MUTEX = "mutex"
    REGISTRY_KEY = "registry_key"


class ShareLevel(str, Enum):
    """Traffic Light Protocol (TLP) share levels."""

    WHITE = "white"  # Unlimited disclosure
    GREEN = "green"  # Community-wide
    AMBER = "amber"  # Limited disclosure
    RED = "red"  # Named recipients only


class IndicatorSource(BaseModel):
    """Source information for an indicator."""

    feed_id: str
    feed_name: str
    confidence: int = Field(ge=0, le=100)
    first_seen: datetime
    last_seen: datetime


class Indicator(BaseModel):
    """
    A threat indicator.

    STIX-compatible data model for threat intelligence.
    """

    id: str = Field(default_factory=lambda: f"indicator--{uuid4()}")
    type: IndicatorType
    value: str
    confidence: int = Field(ge=0, le=100, default=50)
    severity: str = "medium"  # low, medium, high, critical

    # STIX fields
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    # Source tracking
    sources: list[IndicatorSource] = Field(default_factory=list)

    # MineMeld compatibility
    share_level: ShareLevel = ShareLevel.AMBER

    # Custom metadata
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class WorkflowNode(BaseModel):
    """
    A node in a workflow graph.

    Represents a miner, processor, or output in the data flow.
    """

    id: str = Field(default_factory=lambda: f"node-{uuid4().hex[:8]}")
    type: str  # miner, processor, output
    prototype: str  # Reference to prototype ID
    config: dict[str, Any] = Field(default_factory=dict)
    inputs: list[str] = Field(default_factory=list)  # Connected input node IDs
    outputs: list[str] = Field(default_factory=list)  # Connected output node IDs
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})

    # Runtime state
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_error: Optional[str] = None
    indicators_processed: int = 0


class WorkflowEdge(BaseModel):
    """
    An edge connecting two nodes in the workflow.
    """

    id: str = Field(default_factory=lambda: f"edge-{uuid4().hex[:8]}")
    source: str  # Source node ID
    target: str  # Target node ID
    filters: list[dict[str, Any]] = Field(default_factory=list)  # Optional filters


class Workflow(BaseModel):
    """
    A threat intelligence workflow.

    Equivalent to a MineMeld graph configuration.
    """

    id: str = Field(default_factory=lambda: f"workflow-{uuid4()}")
    name: str
    description: str = ""
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    schedule: Optional[str] = None  # Cron expression
    status: WorkflowStatus = WorkflowStatus.DRAFT

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None

    # Runtime state
    last_run: Optional[datetime] = None
    last_error: Optional[str] = None
    run_count: int = 0

    class Config:
        use_enum_values = True

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Get a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_upstream_nodes(self, node_id: str) -> list[WorkflowNode]:
        """Get all nodes that feed into the given node."""
        upstream_ids = set()
        for edge in self.edges:
            if edge.target == node_id:
                upstream_ids.add(edge.source)
        return [n for n in self.nodes if n.id in upstream_ids]

    def get_downstream_nodes(self, node_id: str) -> list[WorkflowNode]:
        """Get all nodes that receive from the given node."""
        downstream_ids = set()
        for edge in self.edges:
            if edge.source == node_id:
                downstream_ids.add(edge.target)
        return [n for n in self.nodes if n.id in downstream_ids]

    def get_execution_order(self) -> list[WorkflowNode]:
        """
        Get nodes in topological order for execution.

        Returns nodes ordered so that dependencies are processed first.
        """
        # Build adjacency list
        in_degree: dict[str, int] = {n.id: 0 for n in self.nodes}
        for edge in self.edges:
            if edge.target in in_degree:
                in_degree[edge.target] += 1

        # Start with nodes that have no inputs (miners)
        queue = [n for n in self.nodes if in_degree[n.id] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for downstream in self.get_downstream_nodes(node.id):
                in_degree[downstream.id] -= 1
                if in_degree[downstream.id] == 0:
                    queue.append(downstream)

        return result
