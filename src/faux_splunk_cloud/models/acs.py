"""
ACS (Admin Config Service) API models.

These models are designed to be 1:1 compatible with the official Splunk ACS API
to ensure compatibility with:
- Splunk Terraform Provider
- Splunk SDK for Python
- Direct ACS API calls

Reference: https://help.splunk.com/en/splunk-cloud-platform/administer/admin-config-service-manual/
OpenAPI spec: https://admin.splunk.com/service/info/specs/v2/openapi.json
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Index Management Models
# =============================================================================


class IndexDatatype(str, Enum):
    """Splunk index datatype."""

    EVENT = "event"
    METRIC = "metric"


class ACSIndex(BaseModel):
    """
    ACS Index representation.

    Matches the ACS API response format for index resources.
    """

    name: str = Field(description="Index name")
    datatype: IndexDatatype = Field(
        default=IndexDatatype.EVENT,
        description="Index data type (event or metric)",
    )
    searchableDays: int = Field(
        default=90,
        ge=1,
        description="Number of days data remains searchable",
    )
    maxDataSizeMB: int = Field(
        default=500000,
        ge=0,
        description="Maximum data size in MB (0 for unlimited)",
    )
    totalEventCount: int = Field(
        default=0,
        ge=0,
        description="Total number of events in index",
    )
    totalRawSizeMB: int = Field(
        default=0,
        ge=0,
        description="Total raw data size in MB",
    )
    splunkArchivalRetentionDays: int | None = Field(
        default=None,
        description="Days to retain in archival storage (DDAA)",
    )
    selfStorageLocationPath: str | None = Field(
        default=None,
        description="Self-storage (DDSS) location path",
    )

    # Computed fields for compatibility
    frozenTimePeriodInSecs: int = Field(
        default=7776000,  # 90 days
        description="Time period before data is frozen",
    )


class ACSIndexCreateRequest(BaseModel):
    """Request body for creating an index via ACS API."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=80,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Index name (lowercase, alphanumeric, underscores)",
    )
    datatype: IndexDatatype = Field(
        default=IndexDatatype.EVENT,
        description="Index data type",
    )
    searchableDays: int = Field(
        default=90,
        ge=1,
        le=3650,
        description="Searchable retention in days",
    )
    maxDataSizeMB: int = Field(
        default=0,
        ge=0,
        description="Maximum index size in MB (0 for unlimited)",
    )
    splunkArchivalRetentionDays: int | None = Field(
        default=None,
        ge=0,
        description="Archival retention in days",
    )


class ACSIndexListResponse(BaseModel):
    """Response body for listing indexes via ACS API."""

    indexes: list[ACSIndex] = Field(description="List of indexes")


# =============================================================================
# HEC Token Management Models
# =============================================================================


class ACSHECToken(BaseModel):
    """
    ACS HEC Token representation.

    Matches the ACS API response format for HEC token resources.
    """

    name: str = Field(description="Token name")
    token: str = Field(description="The HEC token value")
    defaultIndex: str = Field(
        default="main",
        description="Default index for events",
    )
    defaultSource: str | None = Field(
        default=None,
        description="Default source value",
    )
    defaultSourcetype: str | None = Field(
        default=None,
        description="Default sourcetype",
    )
    indexes: list[str] = Field(
        default_factory=lambda: ["main"],
        description="Allowed indexes",
    )
    disabled: bool = Field(
        default=False,
        description="Whether token is disabled",
    )
    useACK: bool = Field(
        default=False,
        description="Enable indexer acknowledgment",
    )
    allowQueryStringAuth: bool = Field(
        default=False,
        description="Allow token in query string",
    )


class ACSHECTokenCreateRequest(BaseModel):
    """Request body for creating a HEC token via ACS API."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="Token name",
    )
    defaultIndex: str = Field(
        default="main",
        description="Default index for events",
    )
    defaultSource: str | None = Field(
        default=None,
        description="Default source",
    )
    defaultSourcetype: str | None = Field(
        default=None,
        description="Default sourcetype",
    )
    indexes: list[str] = Field(
        default_factory=lambda: ["main"],
        description="Allowed indexes",
    )
    useACK: bool = Field(
        default=False,
        description="Enable acknowledgment",
    )
    disabled: bool = Field(
        default=False,
        description="Create in disabled state",
    )


class ACSHECTokenListResponse(BaseModel):
    """Response body for listing HEC tokens via ACS API."""

    http_event_collectors: list[ACSHECToken] = Field(
        description="List of HEC tokens",
        alias="http-event-collectors",
    )

    class Config:
        populate_by_name = True


# =============================================================================
# App Management Models (Victoria Experience)
# =============================================================================


class AppStatus(str, Enum):
    """App installation status."""

    INSTALLED = "installed"
    INSTALLING = "installing"
    FAILED = "failed"
    NOT_INSTALLED = "not_installed"


class ACSApp(BaseModel):
    """
    ACS App representation for Victoria Experience.

    In Victoria Experience, apps are automatically installed on all search heads.
    """

    appId: str = Field(description="Splunkbase app ID or package name")
    label: str = Field(description="Human-readable app name")
    version: str = Field(description="Installed version")
    status: AppStatus = Field(description="Installation status")
    splunkbaseId: str | None = Field(
        default=None,
        description="Splunkbase numeric ID",
    )
    visible: bool = Field(
        default=True,
        description="App visibility in UI",
    )
    configured: bool = Field(
        default=False,
        description="Whether app is configured",
    )


class ACSAppInstallRequest(BaseModel):
    """Request body for installing an app via ACS API (Victoria Experience)."""

    splunkbaseID: str | None = Field(
        default=None,
        description="Splunkbase app ID",
    )
    packageURL: str | None = Field(
        default=None,
        description="URL to app package for private apps",
    )
    version: str | None = Field(
        default=None,
        description="Specific version to install",
    )
    licenseUrl: str | None = Field(
        default=None,
        description="License acceptance URL",
    )


class ACSAppListResponse(BaseModel):
    """Response body for listing apps via ACS API."""

    apps: list[ACSApp] = Field(description="List of apps")


# =============================================================================
# IP Allow List Models
# =============================================================================


class IPAllowListFeature(str, Enum):
    """Features that can have IP allow lists."""

    SEARCH_API = "search-api"
    HEC = "hec"
    S2S = "s2s"
    SEARCH_UI = "search-ui"
    ALL = "all"


class ACSIPAllowListEntry(BaseModel):
    """A single IP allow list entry."""

    subnet: str = Field(
        description="CIDR notation subnet (e.g., '10.0.0.0/8')",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description",
    )
    createdAt: datetime | None = Field(
        default=None,
        description="Creation timestamp",
    )


class ACSIPAllowList(BaseModel):
    """IP allow list for a specific feature."""

    feature: IPAllowListFeature = Field(description="Feature this list applies to")
    subnets: list[ACSIPAllowListEntry] = Field(
        default_factory=list,
        description="Allowed subnets",
    )


# =============================================================================
# User and Role Models
# =============================================================================


class ACSRole(BaseModel):
    """ACS Role representation."""

    name: str = Field(description="Role name")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Granted capabilities",
    )
    importRoles: list[str] = Field(
        default_factory=list,
        description="Inherited roles",
    )
    searchIndexesAllowed: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed search indexes",
    )
    searchIndexesDefault: list[str] = Field(
        default_factory=lambda: ["main"],
        description="Default search indexes",
    )


class ACSUser(BaseModel):
    """ACS User representation."""

    name: str = Field(description="Username")
    realname: str | None = Field(default=None, description="Display name")
    email: str | None = Field(default=None, description="Email address")
    roles: list[str] = Field(
        default_factory=lambda: ["user"],
        description="Assigned roles",
    )
    defaultApp: str = Field(
        default="search",
        description="Default app on login",
    )


# =============================================================================
# Common Response Models
# =============================================================================


class ACSError(BaseModel):
    """ACS API error response format."""

    code: str = Field(description="Error code")
    message: str = Field(description="Error message")


class ACSResponse(BaseModel):
    """Generic ACS API response wrapper."""

    code: str | None = Field(default=None, description="Status code")
    message: str | None = Field(default=None, description="Status message")


# =============================================================================
# Limits Configuration Models
# =============================================================================


class ACSLimitsConfig(BaseModel):
    """
    ACS limits.conf configuration.

    Victoria Experience allows modification of certain limits via ACS API.
    """

    # Search limits
    max_mem_usage_mb: int | None = Field(
        default=None,
        description="Maximum memory usage for searches",
    )
    max_searches_per_cpu: int | None = Field(
        default=None,
        description="Maximum concurrent searches per CPU",
    )

    # Real-time search limits
    indexed_realtime_disk_sync_delay: int | None = Field(
        default=None,
        description="Disk sync delay for indexed real-time",
    )


# =============================================================================
# Outbound Port Configuration
# =============================================================================


class ACSOutboundPort(BaseModel):
    """Outbound port configuration."""

    port: int = Field(ge=1, le=65535, description="Port number")
    subnets: list[str] = Field(description="Destination subnets")
    description: str | None = Field(default=None, description="Description")
