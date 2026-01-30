"""
Identity Provider configuration models for multi-tenant federation.

Allows tenants to bring their own IdP for Splunk instance authentication.
Supports both SAML and OIDC providers.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IdPType(str, Enum):
    """Supported Identity Provider types."""

    SAML = "saml"
    OIDC = "oidc"
    PLATFORM_KEYCLOAK = "platform_keycloak"  # Use platform's Keycloak


class IdPStatus(str, Enum):
    """Status of an IdP configuration."""

    PENDING = "pending"  # Awaiting validation
    ACTIVE = "active"  # Validated and active
    ERROR = "error"  # Validation failed
    DISABLED = "disabled"  # Manually disabled


class SAMLIdPConfig(BaseModel):
    """SAML Identity Provider configuration."""

    # Required: Metadata (either URL or XML)
    metadata_url: str | None = Field(
        default=None,
        description="URL to IdP's SAML metadata (recommended)",
    )
    metadata_xml: str | None = Field(
        default=None,
        description="Raw SAML metadata XML (if URL not available)",
    )

    # IdP details (auto-populated from metadata or manual)
    entity_id: str | None = Field(
        default=None,
        description="IdP Entity ID (extracted from metadata)",
    )
    sso_url: str | None = Field(
        default=None,
        description="IdP Single Sign-On URL",
    )
    slo_url: str | None = Field(
        default=None,
        description="IdP Single Logout URL (optional)",
    )
    certificate: str | None = Field(
        default=None,
        description="IdP X.509 signing certificate (PEM format)",
    )

    # Attribute mappings
    name_id_format: str = Field(
        default="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        description="SAML NameID format",
    )
    attribute_mapping: dict[str, str] = Field(
        default_factory=lambda: {
            "email": "email",
            "name": "displayName",
            "first_name": "firstName",
            "last_name": "lastName",
            "groups": "memberOf",
            "roles": "roles",
        },
        description="Mapping of Splunk attributes to IdP SAML attributes",
    )

    # Role mappings for Splunk
    role_mapping: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "admin": ["admin", "sc_admin"],
            "power": ["power", "can_delete"],
            "user": ["user"],
        },
        description="Mapping of IdP roles/groups to Splunk roles",
    )

    # Advanced settings
    sign_authn_requests: bool = Field(
        default=True,
        description="Sign authentication requests",
    )
    want_assertions_signed: bool = Field(
        default=True,
        description="Require signed assertions from IdP",
    )
    want_response_signed: bool = Field(
        default=False,
        description="Require signed responses from IdP",
    )


class OIDCIdPConfig(BaseModel):
    """OpenID Connect Identity Provider configuration."""

    # Discovery
    discovery_url: str | None = Field(
        default=None,
        description="OIDC Discovery URL (.well-known/openid-configuration)",
    )

    # Manual configuration (if discovery not available)
    issuer: str | None = Field(
        default=None,
        description="OIDC Issuer URL",
    )
    authorization_endpoint: str | None = Field(
        default=None,
        description="Authorization endpoint URL",
    )
    token_endpoint: str | None = Field(
        default=None,
        description="Token endpoint URL",
    )
    userinfo_endpoint: str | None = Field(
        default=None,
        description="UserInfo endpoint URL",
    )
    jwks_uri: str | None = Field(
        default=None,
        description="JWKS URI for token validation",
    )

    # Client credentials
    client_id: str = Field(
        ...,
        description="OIDC Client ID",
    )
    client_secret: str | None = Field(
        default=None,
        description="OIDC Client Secret (not needed for PKCE)",
    )

    # Scopes
    scopes: list[str] = Field(
        default_factory=lambda: ["openid", "profile", "email", "groups"],
        description="OIDC scopes to request",
    )

    # Claim mappings
    claim_mapping: dict[str, str] = Field(
        default_factory=lambda: {
            "email": "email",
            "name": "name",
            "groups": "groups",
            "roles": "roles",
        },
        description="Mapping of Splunk attributes to OIDC claims",
    )

    # Role mappings for Splunk
    role_mapping: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "admin": ["admin", "sc_admin"],
            "power": ["power", "can_delete"],
            "user": ["user"],
        },
        description="Mapping of IdP roles/groups to Splunk roles",
    )


class TenantIdPConfigCreate(BaseModel):
    """Request to create or update a tenant's IdP configuration."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Display name for this IdP configuration",
    )
    idp_type: IdPType = Field(
        ...,
        description="Type of Identity Provider",
    )
    is_default: bool = Field(
        default=True,
        description="Use as default IdP for new instances",
    )

    # Type-specific configuration (only one should be set)
    saml_config: SAMLIdPConfig | None = Field(
        default=None,
        description="SAML configuration (required if idp_type is SAML)",
    )
    oidc_config: OIDCIdPConfig | None = Field(
        default=None,
        description="OIDC configuration (required if idp_type is OIDC)",
    )


class TenantIdPConfig(BaseModel):
    """Complete tenant IdP configuration record."""

    id: str = Field(description="Unique configuration ID")
    tenant_id: str = Field(description="Tenant this config belongs to")
    name: str = Field(description="Display name")
    idp_type: IdPType = Field(description="Type of Identity Provider")
    is_default: bool = Field(default=True, description="Use as default for new instances")
    status: IdPStatus = Field(default=IdPStatus.PENDING, description="Configuration status")
    status_message: str | None = Field(default=None, description="Status details/error message")

    # Type-specific configuration
    saml_config: SAMLIdPConfig | None = Field(default=None)
    oidc_config: OIDCIdPConfig | None = Field(default=None)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    validated_at: datetime | None = Field(default=None, description="Last successful validation")

    # Usage tracking
    instances_using: int = Field(default=0, description="Number of instances using this config")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TenantIdPConfigList(BaseModel):
    """Response for listing tenant IdP configurations."""

    configs: list[TenantIdPConfig] = Field(default_factory=list)
    total: int = Field(default=0)


class IdPValidationResult(BaseModel):
    """Result of validating an IdP configuration."""

    valid: bool = Field(description="Whether the configuration is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    extracted_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata extracted during validation",
    )


class SplunkAuthConfig(BaseModel):
    """
    Generated Splunk authentication configuration.

    This is what gets applied to Splunk instances to enable IdP authentication.
    """

    authentication_conf: str = Field(
        description="Contents for authentication.conf",
    )
    authorize_conf: str = Field(
        description="Contents for authorize.conf (role mappings)",
    )
    web_conf: str | None = Field(
        default=None,
        description="Contents for web.conf (if modifications needed)",
    )
    idp_metadata: str | None = Field(
        default=None,
        description="IdP metadata to install (for SAML)",
    )
    sp_metadata: str | None = Field(
        default=None,
        description="SP metadata to register with IdP (for SAML)",
    )
