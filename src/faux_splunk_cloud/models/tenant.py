"""
Multi-tenancy models for Faux Splunk Cloud.

Supports external Identity Provider organizations for tenant isolation.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TenantStatus(str, Enum):
    """Status of a tenant."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class TenantSettings(BaseModel):
    """Tenant-specific settings."""

    max_instances: int = Field(default=5, description="Maximum instances allowed")
    max_memory_mb: int = Field(default=8192, description="Maximum memory across all instances")
    max_cpu_cores: float = Field(default=8.0, description="Maximum CPU cores across all instances")
    allowed_topologies: list[str] = Field(
        default_factory=lambda: ["standalone", "distributed_minimal"],
        description="Allowed instance topologies",
    )
    enable_attack_simulation: bool = Field(default=True, description="Enable attack simulation features")
    enable_siem_access: bool = Field(default=False, description="Enable SIEM portal access")


class TenantCreate(BaseModel):
    """Request model for creating a new tenant."""

    name: str = Field(..., min_length=1, max_length=100, description="Tenant display name")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$",
        description="URL-safe tenant identifier",
    )
    idp_org_id: str | None = Field(default=None, description="Identity Provider organization ID (Keycloak realm, Auth0 org, etc.)")
    settings: TenantSettings = Field(default_factory=TenantSettings, description="Tenant settings")


class TenantUpdate(BaseModel):
    """Request model for updating a tenant."""

    name: str | None = Field(default=None, description="Tenant display name")
    settings: TenantSettings | None = Field(default=None, description="Tenant settings")
    status: TenantStatus | None = Field(default=None, description="Tenant status")


class Tenant(BaseModel):
    """Complete representation of a tenant."""

    id: str = Field(description="Unique tenant ID")
    name: str = Field(description="Tenant display name")
    slug: str = Field(description="URL-safe tenant identifier")
    idp_org_id: str | None = Field(default=None, description="Identity Provider organization ID (Keycloak realm, Auth0 org, etc.)")
    settings: TenantSettings = Field(default_factory=TenantSettings, description="Tenant settings")
    status: TenantStatus = Field(default=TenantStatus.ACTIVE, description="Tenant status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    # Usage tracking
    instance_count: int = Field(default=0, description="Current number of instances")
    total_memory_mb: int = Field(default=0, description="Total memory usage in MB")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TenantList(BaseModel):
    """Response model for listing tenants."""

    tenants: list[Tenant] = Field(default_factory=list)
    total: int = Field(default=0)
