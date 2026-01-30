"""
Instance models for ephemeral Splunk Cloud environments.

These models define the configuration and state of ephemeral Splunk instances
that mimic Splunk Cloud Victoria Experience.
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class InstanceStatus(str, Enum):
    """Status of an ephemeral Splunk instance."""

    PENDING = "pending"
    PROVISIONING = "provisioning"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    TERMINATED = "terminated"


class InstanceTopology(str, Enum):
    """
    Topology patterns based on Splunk Validated Architectures.

    Reference: https://help.splunk.com/en/splunk-cloud-platform/splunk-validated-architectures/
    """

    # Single instance for basic testing (not production-like)
    STANDALONE = "standalone"

    # Distributed: separate search head and indexer (minimum Victoria-like)
    DISTRIBUTED_MINIMAL = "distributed_minimal"

    # Distributed clustered: SHC + Indexer cluster (production-like Victoria)
    DISTRIBUTED_CLUSTERED = "distributed_clustered"

    # Full Victoria Experience simulation with all components
    VICTORIA_FULL = "victoria_full"


class InstanceConfig(BaseModel):
    """Configuration for a Splunk instance matching Victoria Experience defaults."""

    # Topology selection
    topology: InstanceTopology = Field(
        default=InstanceTopology.STANDALONE,
        description="Deployment topology pattern",
    )

    # Splunk version
    splunk_version: str = Field(
        default="9.3.2",
        description="Splunk Enterprise version",
    )

    # Experience mode (Victoria or Classic)
    experience: Literal["victoria", "classic"] = Field(
        default="victoria",
        description="Splunk Cloud Experience mode",
    )

    # Resource configuration
    search_head_count: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of search heads (for clustered topologies)",
    )
    indexer_count: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of indexers",
    )
    replication_factor: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Indexer cluster replication factor",
    )
    search_factor: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Indexer cluster search factor",
    )

    # Memory and CPU per container
    memory_mb: int = Field(
        default=2048,
        ge=512,
        le=8192,
        description="Memory per container in MB",
    )
    cpu_cores: float = Field(
        default=1.0,
        ge=0.5,
        le=4.0,
        description="CPU cores per container",
    )

    # Victoria Experience features
    enable_hec: bool = Field(
        default=True,
        description="Enable HTTP Event Collector",
    )
    enable_realtime_search: bool = Field(
        default=True,
        description="Enable real-time search (Victoria default)",
    )
    enable_acs_api: bool = Field(
        default=True,
        description="Enable ACS API simulation",
    )

    # Default indexes to create
    create_default_indexes: bool = Field(
        default=True,
        description="Create default indexes (main, summary, etc.)",
    )

    # Apps to pre-install
    preinstall_apps: list[str] = Field(
        default_factory=list,
        description="List of Splunkbase app IDs to pre-install",
    )

    # Custom configuration overrides
    custom_configs: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Custom .conf file settings (e.g., {'limits': {'max_mem_usage_mb': '1000'}})",
    )


class InstanceCreate(BaseModel):
    """Request model for creating a new ephemeral instance."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$",
        description="Instance name (DNS-safe)",
    )
    config: InstanceConfig = Field(
        default_factory=InstanceConfig,
        description="Instance configuration",
    )
    ttl_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Time-to-live in hours (max 1 week)",
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Custom labels for the instance",
    )


class InstanceEndpoints(BaseModel):
    """Network endpoints for accessing an instance."""

    # Splunk Web UI
    web_url: str | None = Field(default=None, description="Splunk Web URL")

    # Splunk REST API (Splunkd)
    api_url: str | None = Field(default=None, description="Splunkd REST API URL")

    # HEC endpoint
    hec_url: str | None = Field(default=None, description="HTTP Event Collector URL")

    # ACS API endpoint (simulated)
    acs_url: str | None = Field(default=None, description="ACS API URL")

    # S2S (Splunk-to-Splunk) forwarding
    s2s_port: int | None = Field(default=None, description="S2S receiving port")


class InstanceCredentials(BaseModel):
    """Credentials for accessing an instance."""

    admin_username: str = Field(default="admin", description="Admin username")
    admin_password: str = Field(description="Admin password")

    # JWT token for ACS API
    acs_token: str | None = Field(default=None, description="ACS API JWT token")

    # HEC token (if HEC is enabled)
    hec_token: str | None = Field(default=None, description="Default HEC token")


class Instance(BaseModel):
    """Complete representation of an ephemeral Splunk instance."""

    # Unique identifier
    id: str = Field(description="Unique instance ID")

    # User-provided name
    name: str = Field(description="Instance name")

    # Current status
    status: InstanceStatus = Field(
        default=InstanceStatus.PENDING,
        description="Current instance status",
    )

    # Configuration
    config: InstanceConfig = Field(description="Instance configuration")

    # Endpoints (populated when running)
    endpoints: InstanceEndpoints = Field(
        default_factory=InstanceEndpoints,
        description="Network endpoints",
    )

    # Credentials
    credentials: InstanceCredentials | None = Field(
        default=None,
        description="Access credentials",
    )

    # Lifecycle timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Start timestamp",
    )
    expires_at: datetime = Field(description="Expiration timestamp")

    # Labels
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Custom labels",
    )

    # Docker resource IDs
    container_ids: list[str] = Field(
        default_factory=list,
        description="Docker container IDs",
    )
    network_id: str | None = Field(
        default=None,
        description="Docker network ID",
    )
    volume_ids: list[str] = Field(
        default_factory=list,
        description="Docker volume IDs",
    )

    # Error message if status is ERROR
    error_message: str | None = Field(
        default=None,
        description="Error message if instance failed",
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
