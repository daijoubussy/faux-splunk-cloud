"""
Data models for Faux Splunk Cloud.

These models are designed to be compatible with:
- Splunk ACS API request/response formats
- Splunk Enterprise REST API
- Splunk SDK for Python
- Splunk Terraform Provider
"""

from faux_splunk_cloud.models.acs import (
    ACSApp,
    ACSAppInstallRequest,
    ACSAppListResponse,
    ACSHECToken,
    ACSHECTokenCreateRequest,
    ACSHECTokenListResponse,
    ACSIndex,
    ACSIndexCreateRequest,
    ACSIndexListResponse,
    ACSIPAllowList,
    ACSIPAllowListEntry,
)
from faux_splunk_cloud.models.instance import (
    Instance,
    InstanceConfig,
    InstanceCreate,
    InstanceStatus,
    InstanceTopology,
)
from faux_splunk_cloud.models.tenant import (
    Tenant,
    TenantCreate,
    TenantList,
    TenantSettings,
    TenantStatus,
    TenantUpdate,
)
from faux_splunk_cloud.models.impersonation import (
    ActorContext,
    ImpersonationRequest,
    ImpersonationRequestCreate,
    ImpersonationRequestStatus,
    ImpersonationSession,
    ImpersonationSessionStart,
)
from faux_splunk_cloud.models.audit import (
    AuditAction,
    AuditLog,
    AuditLogList,
    AuditLogQuery,
    ResourceType,
)
from faux_splunk_cloud.models.idp_config import (
    IdPStatus,
    IdPType,
    IdPValidationResult,
    OIDCIdPConfig,
    SAMLIdPConfig,
    SplunkAuthConfig,
    TenantIdPConfig,
    TenantIdPConfigCreate,
    TenantIdPConfigList,
)

__all__ = [
    # Instance models
    "Instance",
    "InstanceConfig",
    "InstanceCreate",
    "InstanceStatus",
    "InstanceTopology",
    # ACS models
    "ACSIndex",
    "ACSIndexCreateRequest",
    "ACSIndexListResponse",
    "ACSHECToken",
    "ACSHECTokenCreateRequest",
    "ACSHECTokenListResponse",
    "ACSApp",
    "ACSAppInstallRequest",
    "ACSAppListResponse",
    "ACSIPAllowList",
    "ACSIPAllowListEntry",
    # Tenant models
    "Tenant",
    "TenantCreate",
    "TenantList",
    "TenantSettings",
    "TenantStatus",
    "TenantUpdate",
    # Impersonation models
    "ActorContext",
    "ImpersonationRequest",
    "ImpersonationRequestCreate",
    "ImpersonationRequestStatus",
    "ImpersonationSession",
    "ImpersonationSessionStart",
    # Audit models
    "AuditAction",
    "AuditLog",
    "AuditLogList",
    "AuditLogQuery",
    "ResourceType",
    # IdP Config models
    "IdPStatus",
    "IdPType",
    "IdPValidationResult",
    "OIDCIdPConfig",
    "SAMLIdPConfig",
    "SplunkAuthConfig",
    "TenantIdPConfig",
    "TenantIdPConfigCreate",
    "TenantIdPConfigList",
]
