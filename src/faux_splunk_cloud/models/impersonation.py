"""
Impersonation models for admin support access.

Allows platform admins to impersonate tenant users with proper audit trails.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ImpersonationRequestStatus(str, Enum):
    """Status of an impersonation request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    USED = "used"


class ImpersonationRequestCreate(BaseModel):
    """Request to allow admin impersonation."""

    reason: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Reason for requesting admin access",
    )
    duration_hours: int = Field(
        default=4,
        ge=1,
        le=24,
        description="Requested impersonation duration in hours",
    )


class ImpersonationRequest(BaseModel):
    """Impersonation request record."""

    id: str = Field(description="Unique request ID")
    tenant_id: str = Field(description="Tenant ID")
    requested_by_user_id: str = Field(description="User ID who requested (from IdP)")
    requested_by_email: str = Field(description="Email of requester")
    reason: str = Field(description="Reason for request")
    duration_hours: int = Field(description="Requested duration in hours")
    status: ImpersonationRequestStatus = Field(
        default=ImpersonationRequestStatus.PENDING,
        description="Request status",
    )
    approved_by_user_id: str | None = Field(default=None, description="Tenant admin who approved")
    approved_by_email: str | None = Field(default=None, description="Email of approver")
    approved_at: datetime | None = Field(default=None, description="Approval timestamp")
    rejected_reason: str | None = Field(default=None, description="Rejection reason")
    expires_at: datetime | None = Field(default=None, description="When approval expires")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ImpersonationSession(BaseModel):
    """Active impersonation session."""

    id: str = Field(description="Unique session ID")
    request_id: str = Field(description="Associated request ID")
    admin_user_id: str = Field(description="Platform admin user ID")
    admin_email: str = Field(description="Platform admin email")
    target_user_id: str = Field(description="User being impersonated")
    target_user_email: str = Field(description="Email of impersonated user")
    target_tenant_id: str = Field(description="Tenant being accessed")
    target_tenant_name: str = Field(description="Name of tenant")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Session start")
    expires_at: datetime = Field(description="Session expiration")
    ended_at: datetime | None = Field(default=None, description="When session was ended")
    end_reason: str | None = Field(default=None, description="Reason for ending session")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ImpersonationSessionStart(BaseModel):
    """Request to start an impersonation session."""

    request_id: str = Field(description="Approved impersonation request ID")


class ActorContext(BaseModel):
    """Context for the current actor (user or impersonator)."""

    real_user_id: str = Field(description="Actual user ID (admin if impersonating)")
    real_email: str = Field(description="Actual user email")
    effective_user_id: str = Field(description="Effective user ID (impersonated user if applicable)")
    effective_email: str = Field(description="Effective user email")
    effective_tenant_id: str = Field(description="Effective tenant ID")
    is_impersonating: bool = Field(default=False, description="Whether this is an impersonation")
    impersonation_session_id: str | None = Field(default=None, description="Active impersonation session")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    roles: list[str] = Field(default_factory=list, description="User roles")
