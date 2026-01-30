"""
Audit log models for tracking all actions in the system.

Captures both regular actions and impersonation context.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    """Types of auditable actions."""

    # Instance actions
    INSTANCE_CREATE = "instance.create"
    INSTANCE_START = "instance.start"
    INSTANCE_STOP = "instance.stop"
    INSTANCE_DESTROY = "instance.destroy"
    INSTANCE_EXTEND = "instance.extend"

    # Tenant actions
    TENANT_CREATE = "tenant.create"
    TENANT_UPDATE = "tenant.update"
    TENANT_SUSPEND = "tenant.suspend"
    TENANT_REACTIVATE = "tenant.reactivate"
    TENANT_DELETE = "tenant.delete"

    # Impersonation actions
    IMPERSONATION_REQUEST = "impersonation.request"
    IMPERSONATION_APPROVE = "impersonation.approve"
    IMPERSONATION_REJECT = "impersonation.reject"
    IMPERSONATION_START = "impersonation.start"
    IMPERSONATION_END = "impersonation.end"

    # ACS actions
    ACS_INDEX_CREATE = "acs.index.create"
    ACS_INDEX_DELETE = "acs.index.delete"
    ACS_HEC_CREATE = "acs.hec.create"
    ACS_HEC_DELETE = "acs.hec.delete"

    # Attack simulation
    ATTACK_CAMPAIGN_CREATE = "attack.campaign.create"
    ATTACK_CAMPAIGN_START = "attack.campaign.start"
    ATTACK_CAMPAIGN_PAUSE = "attack.campaign.pause"

    # Authentication
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_REFRESH = "auth.token.refresh"

    # Admin actions
    ADMIN_USER_UPDATE = "admin.user.update"
    ADMIN_SETTINGS_UPDATE = "admin.settings.update"

    # Config export actions
    CONFIG_EXPORT = "config.export"
    CONFIG_IMPORT = "config.import"


class ResourceType(str, Enum):
    """Types of resources that can be audited."""

    INSTANCE = "instance"
    TENANT = "tenant"
    USER = "user"
    IMPERSONATION_REQUEST = "impersonation_request"
    IMPERSONATION_SESSION = "impersonation_session"
    ACS_INDEX = "acs_index"
    ACS_HEC = "acs_hec"
    ATTACK_CAMPAIGN = "attack_campaign"
    SETTINGS = "settings"
    CONFIG_PACKAGE = "config_package"


class AuditLog(BaseModel):
    """Audit log entry with full context."""

    id: str = Field(description="Unique audit log ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    # Action details
    action: AuditAction = Field(description="Type of action")
    resource_type: ResourceType = Field(description="Type of resource affected")
    resource_id: str = Field(description="ID of affected resource")

    # Actor information (real identity)
    actor_user_id: str = Field(description="Real user ID performing action")
    actor_email: str = Field(description="Real user email")

    # Impersonation context (if applicable)
    impersonated_user_id: str | None = Field(default=None, description="Impersonated user ID")
    impersonated_email: str | None = Field(default=None, description="Impersonated user email")
    impersonation_session_id: str | None = Field(default=None, description="Impersonation session")

    # Tenant context
    tenant_id: str = Field(description="Tenant ID")
    tenant_name: str | None = Field(default=None, description="Tenant name for display")

    # Action details
    details: dict = Field(default_factory=dict, description="Additional action details")
    changes: dict | None = Field(default=None, description="Before/after changes")

    # Request metadata
    ip_address: str | None = Field(default=None, description="Client IP address")
    user_agent: str | None = Field(default=None, description="Client user agent")
    request_id: str | None = Field(default=None, description="Request correlation ID")

    # Result
    success: bool = Field(default=True, description="Whether action succeeded")
    error_message: str | None = Field(default=None, description="Error message if failed")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AuditLogQuery(BaseModel):
    """Query parameters for filtering audit logs."""

    tenant_id: str | None = Field(default=None, description="Filter by tenant")
    actor_user_id: str | None = Field(default=None, description="Filter by actor")
    resource_type: ResourceType | None = Field(default=None, description="Filter by resource type")
    resource_id: str | None = Field(default=None, description="Filter by resource ID")
    action: AuditAction | None = Field(default=None, description="Filter by action")
    include_impersonation: bool = Field(default=True, description="Include impersonated actions")
    start_time: datetime | None = Field(default=None, description="Start of time range")
    end_time: datetime | None = Field(default=None, description="End of time range")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class AuditLogList(BaseModel):
    """Response model for listing audit logs."""

    logs: list[AuditLog] = Field(default_factory=list)
    total: int = Field(default=0)
    limit: int = Field(default=100)
    offset: int = Field(default=0)
