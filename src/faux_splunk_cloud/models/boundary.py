"""
HashiCorp Boundary integration models for short-lived access.

Provides just-in-time access to ephemeral Splunk instances with:
- Identity-aware access based on SAML/Keycloak authentication
- Auto-expiring credentials matching instance TTL
- Full audit trail of access grants
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BoundaryTargetType(str, Enum):
    """Types of Boundary targets for Splunk instances."""

    SPLUNK_WEB = "splunk_web"  # Web UI access (8000)
    SPLUNK_API = "splunk_api"  # REST API access (8089)
    SPLUNK_HEC = "splunk_hec"  # HEC endpoint (8088)
    SSH = "ssh"  # Container SSH access


class BoundarySessionStatus(str, Enum):
    """Status of a Boundary session."""

    PENDING = "pending"  # Session requested, awaiting approval/creation
    ACTIVE = "active"  # Session is active
    TERMINATED = "terminated"  # Session ended normally
    EXPIRED = "expired"  # Session TTL expired
    REVOKED = "revoked"  # Session manually revoked


class BoundaryCredentialType(str, Enum):
    """Types of credentials Boundary can provide."""

    SPLUNK_TOKEN = "splunk_token"  # Splunk auth token
    USERNAME_PASSWORD = "username_password"  # Static credentials
    SSH_CERTIFICATE = "ssh_certificate"  # SSH certificate
    BROKERED = "brokered"  # Brokered through credential store


class BoundaryConfig(BaseModel):
    """Boundary server configuration."""

    # Boundary cluster settings
    cluster_url: str = Field(
        default="http://boundary:9200",
        description="Boundary Controller URL",
    )
    worker_url: str = Field(
        default="boundary-worker:9202",
        description="Boundary Worker address for proxied connections",
    )

    # Authentication
    auth_method_id: str = Field(
        default="",
        description="Boundary auth method ID (OIDC with Keycloak)",
    )

    # Organization structure
    org_id: str = Field(
        default="",
        description="Boundary organization ID",
    )
    project_id: str = Field(
        default="",
        description="Boundary project ID for Faux Splunk",
    )

    # Credential store
    credential_store_id: str = Field(
        default="",
        description="Credential store ID for dynamic credentials",
    )

    # Default session settings
    default_session_ttl_minutes: int = Field(
        default=60,
        description="Default session TTL in minutes",
    )
    max_session_ttl_minutes: int = Field(
        default=480,
        description="Maximum session TTL (8 hours)",
    )


class BoundaryTarget(BaseModel):
    """
    A Boundary target representing access to a Splunk instance.

    Created automatically when a Splunk instance is provisioned.
    """

    id: str = Field(description="Boundary target ID")
    instance_id: str = Field(description="Associated Splunk instance ID")
    tenant_id: str = Field(description="Tenant that owns this target")
    name: str = Field(description="Target name (derived from instance)")
    description: str = Field(default="", description="Target description")

    target_type: BoundaryTargetType = Field(description="Type of access")
    address: str = Field(description="Target address (host:port)")
    port: int = Field(description="Target port")

    # Access control
    host_catalog_id: str = Field(default="", description="Boundary host catalog ID")
    host_set_id: str = Field(default="", description="Boundary host set ID")
    credential_library_id: str | None = Field(
        default=None,
        description="Credential library for dynamic creds",
    )

    # TTL matching instance
    expires_at: datetime | None = Field(default=None, description="When this target expires (matches instance)")
    session_max_seconds: int = Field(
        default=3600,
        description="Max session duration in seconds",
    )
    session_connection_limit: int = Field(
        default=-1,
        description="Max connections per session (-1 = unlimited)",
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class BoundaryTargetCreate(BaseModel):
    """Request to create a Boundary target for an instance."""

    instance_id: str = Field(description="Splunk instance to create access for")
    target_types: list[BoundaryTargetType] = Field(
        default_factory=lambda: [BoundaryTargetType.SPLUNK_WEB, BoundaryTargetType.SPLUNK_API],
        description="Types of access to create",
    )
    session_max_seconds: int | None = Field(
        default=None,
        description="Override session max duration",
    )


class BoundarySession(BaseModel):
    """
    A Boundary session for accessing a Splunk instance.

    Sessions provide time-limited, audited access to targets.
    """

    id: str = Field(description="Boundary session ID")
    target_id: str = Field(description="Target being accessed")
    user_id: str = Field(description="User who initiated the session")
    tenant_id: str = Field(description="User's tenant")

    status: BoundarySessionStatus = Field(default=BoundarySessionStatus.PENDING)
    target_type: BoundaryTargetType = Field(default=BoundaryTargetType.SPLUNK_WEB, description="Type of access")

    # Connection details
    endpoint: str | None = Field(
        default=None,
        description="Connection endpoint (worker:port)",
    )
    credentials: dict[str, Any] | None = Field(
        default=None,
        description="Brokered credentials (if any)",
    )

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = Field(default=None, description="Session expiration")
    terminated_at: datetime | None = Field(default=None)

    # Audit
    bytes_up: int = Field(default=0, description="Bytes sent to target")
    bytes_down: int = Field(default=0, description="Bytes received from target")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class BoundarySessionRequest(BaseModel):
    """Request to create a new Boundary session."""

    target_id: str = Field(description="Target to connect to")
    ttl_minutes: int | None = Field(
        default=None,
        description="Requested session TTL (capped by target settings)",
    )
    reason: str | None = Field(
        default=None,
        description="Reason for access (for audit)",
    )


class BoundarySessionList(BaseModel):
    """List of Boundary sessions."""

    sessions: list[BoundarySession] = Field(default_factory=list)
    total: int = Field(default=0)


class BoundaryTargetList(BaseModel):
    """List of Boundary targets."""

    targets: list[BoundaryTarget] = Field(default_factory=list)
    total: int = Field(default=0)


class BoundaryConnectResponse(BaseModel):
    """
    Response when connecting to a Boundary target.

    Contains the information needed to establish the proxied connection.
    """

    session_id: str = Field(description="Boundary session ID")
    authorization_token: str = Field(default="", description="Token for the Boundary proxy")
    endpoint: str = Field(default="", description="Boundary worker endpoint")
    port: int = Field(default=0, description="Port to connect to on the worker")
    expires_at: datetime | None = Field(default=None, description="Session expiration")

    # For web access, provide a direct URL
    connect_url: str | None = Field(
        default=None,
        description="Direct URL to access (for web targets)",
    )

    # Credentials if brokered
    credentials: dict[str, str] | None = Field(
        default=None,
        description="Injected credentials (if using credential brokering)",
    )

    # CLI command example
    cli_command: str = Field(
        default="",
        description="Example CLI command to connect",
    )


class BoundaryCredentialLibrary(BaseModel):
    """
    A credential library for generating dynamic Splunk credentials.

    Integrates with Vault or generates ephemeral Splunk tokens.
    """

    id: str = Field(description="Credential library ID")
    name: str = Field(description="Library name")
    credential_type: BoundaryCredentialType = Field(description="Type of credentials")

    # Vault integration (optional)
    vault_path: str | None = Field(
        default=None,
        description="Vault secret path for credential generation",
    )

    # Splunk token generation settings
    splunk_capabilities: list[str] = Field(
        default_factory=lambda: ["search", "list_inputs"],
        description="Splunk capabilities for generated tokens",
    )
    token_ttl_seconds: int = Field(
        default=3600,
        description="TTL for generated Splunk tokens",
    )


class BoundaryInstanceAccess(BaseModel):
    """
    Complete access information for a Splunk instance via Boundary.

    Combines targets, sessions, and connection info.
    """

    instance_id: str = Field(description="Splunk instance ID")
    instance_name: str = Field(default="", description="Instance display name")
    instance_status: str = Field(default="running", description="Instance status")
    instance_expires_at: datetime | None = Field(default=None, description="When instance expires")

    # Available access targets
    targets: list[BoundaryTarget] = Field(
        default_factory=list,
        description="Available Boundary targets",
    )

    # Active sessions for current user
    active_sessions: list[BoundarySession] = Field(
        default_factory=list,
        description="User's active sessions",
    )

    # Quick connect info (if session exists)
    web_url: str | None = Field(
        default=None,
        description="Direct web access URL (if web session active)",
    )
    api_endpoint: str | None = Field(
        default=None,
        description="API endpoint URL (if API session active)",
    )
