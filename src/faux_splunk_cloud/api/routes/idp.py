"""
Identity Provider configuration API endpoints.

Allows tenants to configure their own IdP for Splunk instance authentication.
Supports SAML, OIDC, and platform Keycloak integration.
"""

import logging
import secrets
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from faux_splunk_cloud.api.deps import (
    AnyAuthData,
    get_actor_context,
    require_auth,
    require_admin,
)
from faux_splunk_cloud.models.idp_config import (
    IdPStatus,
    IdPType,
    IdPValidationResult,
    SAMLIdPConfig,
    OIDCIdPConfig,
    SplunkAuthConfig,
    TenantIdPConfig,
    TenantIdPConfigCreate,
    TenantIdPConfigList,
)
from faux_splunk_cloud.models.impersonation import ActorContext

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for IdP configs (would be database in production)
_idp_configs: dict[str, TenantIdPConfig] = {}
_tenant_config_index: dict[str, list[str]] = {}  # tenant_id -> [config_ids]


def _generate_config_id() -> str:
    """Generate a unique IdP config ID."""
    return f"idp-{secrets.token_hex(8)}"


# Response models


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


class GenerateConfigResponse(BaseModel):
    """Response when generating Splunk auth config."""
    config: SplunkAuthConfig
    instructions: list[str] = Field(
        default_factory=list,
        description="Setup instructions for the IdP",
    )


# Tenant IdP Configuration Endpoints


@router.get("/configs", response_model=TenantIdPConfigList)
async def list_my_idp_configs(
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> TenantIdPConfigList:
    """
    List IdP configurations for the current tenant.

    Returns all configured Identity Providers for the tenant.
    """
    tenant_id = actor.effective_tenant_id
    config_ids = _tenant_config_index.get(tenant_id, [])
    configs = [_idp_configs[cid] for cid in config_ids if cid in _idp_configs]

    return TenantIdPConfigList(configs=configs, total=len(configs))


@router.post("/configs", response_model=TenantIdPConfig)
async def create_idp_config(
    request: TenantIdPConfigCreate,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> TenantIdPConfig:
    """
    Create a new IdP configuration for the tenant.

    Supports SAML, OIDC, or platform Keycloak (default).
    """
    tenant_id = actor.effective_tenant_id

    # Validate the request based on IdP type
    if request.idp_type == IdPType.SAML and not request.saml_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SAML configuration is required for SAML IdP type",
        )

    if request.idp_type == IdPType.OIDC and not request.oidc_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC configuration is required for OIDC IdP type",
        )

    # For SAML, ensure either metadata_url or metadata_xml is provided
    if request.idp_type == IdPType.SAML and request.saml_config:
        if not request.saml_config.metadata_url and not request.saml_config.metadata_xml:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either metadata_url or metadata_xml must be provided for SAML",
            )

    # If this is set as default, unset other defaults
    if request.is_default:
        config_ids = _tenant_config_index.get(tenant_id, [])
        for cid in config_ids:
            if cid in _idp_configs:
                _idp_configs[cid].is_default = False

    now = datetime.utcnow()
    config = TenantIdPConfig(
        id=_generate_config_id(),
        tenant_id=tenant_id,
        name=request.name,
        idp_type=request.idp_type,
        is_default=request.is_default,
        status=IdPStatus.PENDING,
        saml_config=request.saml_config,
        oidc_config=request.oidc_config,
        created_at=now,
        updated_at=now,
    )

    # Store the config
    _idp_configs[config.id] = config
    if tenant_id not in _tenant_config_index:
        _tenant_config_index[tenant_id] = []
    _tenant_config_index[tenant_id].append(config.id)

    logger.info(f"Created IdP config {config.id} for tenant {tenant_id}")

    # Trigger async validation (in production, this would be a background task)
    # For now, just mark as active if platform_keycloak
    if request.idp_type == IdPType.PLATFORM_KEYCLOAK:
        config.status = IdPStatus.ACTIVE
        config.validated_at = now

    return config


@router.get("/configs/{config_id}", response_model=TenantIdPConfig)
async def get_idp_config(
    config_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> TenantIdPConfig:
    """Get a specific IdP configuration."""
    config = _idp_configs.get(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IdP config {config_id} not found",
        )

    # Check tenant access
    if config.tenant_id != actor.effective_tenant_id:
        # Check if admin
        is_admin = "platform_admin" in actor.roles or "admin" in actor.roles
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this IdP configuration",
            )

    return config


@router.patch("/configs/{config_id}", response_model=TenantIdPConfig)
async def update_idp_config(
    config_id: str,
    request: TenantIdPConfigCreate,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> TenantIdPConfig:
    """Update an IdP configuration."""
    config = _idp_configs.get(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IdP config {config_id} not found",
        )

    # Check tenant access
    if config.tenant_id != actor.effective_tenant_id:
        is_admin = "platform_admin" in actor.roles or "admin" in actor.roles
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this IdP configuration",
            )

    # If setting as default, unset other defaults
    if request.is_default and not config.is_default:
        config_ids = _tenant_config_index.get(config.tenant_id, [])
        for cid in config_ids:
            if cid in _idp_configs and cid != config_id:
                _idp_configs[cid].is_default = False

    # Update fields
    config.name = request.name
    config.idp_type = request.idp_type
    config.is_default = request.is_default
    config.saml_config = request.saml_config
    config.oidc_config = request.oidc_config
    config.updated_at = datetime.utcnow()
    config.status = IdPStatus.PENDING  # Re-validate after update

    logger.info(f"Updated IdP config {config_id}")

    return config


@router.delete("/configs/{config_id}", response_model=MessageResponse)
async def delete_idp_config(
    config_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> MessageResponse:
    """Delete an IdP configuration."""
    config = _idp_configs.get(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IdP config {config_id} not found",
        )

    # Check tenant access
    if config.tenant_id != actor.effective_tenant_id:
        is_admin = "platform_admin" in actor.roles or "admin" in actor.roles
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this IdP configuration",
            )

    # Check if in use
    if config.instances_using > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete: {config.instances_using} instances are using this configuration",
        )

    # Remove from indexes
    tenant_configs = _tenant_config_index.get(config.tenant_id, [])
    if config_id in tenant_configs:
        tenant_configs.remove(config_id)
    del _idp_configs[config_id]

    logger.info(f"Deleted IdP config {config_id}")

    return MessageResponse(message=f"IdP configuration {config_id} deleted")


@router.post("/configs/{config_id}/validate", response_model=IdPValidationResult)
async def validate_idp_config(
    config_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> IdPValidationResult:
    """
    Validate an IdP configuration.

    Tests connectivity and metadata for the configured Identity Provider.
    """
    config = _idp_configs.get(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IdP config {config_id} not found",
        )

    # Check tenant access
    if config.tenant_id != actor.effective_tenant_id:
        is_admin = "platform_admin" in actor.roles or "admin" in actor.roles
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this IdP configuration",
            )

    errors: list[str] = []
    warnings: list[str] = []
    extracted: dict = {}

    if config.idp_type == IdPType.PLATFORM_KEYCLOAK:
        # Platform Keycloak is always valid
        config.status = IdPStatus.ACTIVE
        config.validated_at = datetime.utcnow()
        return IdPValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            extracted_metadata={"type": "platform_keycloak"},
        )

    elif config.idp_type == IdPType.SAML and config.saml_config:
        saml = config.saml_config

        # Validate metadata source
        if saml.metadata_url:
            # TODO: Fetch and parse metadata from URL
            # For now, just check that URL is valid format
            if not saml.metadata_url.startswith(("http://", "https://")):
                errors.append("metadata_url must be a valid HTTP(S) URL")
            else:
                extracted["metadata_source"] = "url"
                extracted["metadata_url"] = saml.metadata_url

        elif saml.metadata_xml:
            # TODO: Parse and validate XML
            if not saml.metadata_xml.strip().startswith("<?xml"):
                warnings.append("metadata_xml does not appear to be valid XML")
            extracted["metadata_source"] = "xml"

        # Check required fields
        if not saml.entity_id and not (saml.metadata_url or saml.metadata_xml):
            errors.append("entity_id is required if metadata is not provided")

        if not saml.sso_url and not (saml.metadata_url or saml.metadata_xml):
            errors.append("sso_url is required if metadata is not provided")

        # Check certificate
        if not saml.certificate and not (saml.metadata_url or saml.metadata_xml):
            errors.append("certificate is required if metadata is not provided")

    elif config.idp_type == IdPType.OIDC and config.oidc_config:
        oidc = config.oidc_config

        # Validate discovery or manual endpoints
        if oidc.discovery_url:
            if not oidc.discovery_url.startswith(("http://", "https://")):
                errors.append("discovery_url must be a valid HTTP(S) URL")
            else:
                extracted["discovery_url"] = oidc.discovery_url
        else:
            # Need manual endpoints
            if not oidc.issuer:
                errors.append("issuer is required if discovery_url is not provided")
            if not oidc.authorization_endpoint:
                errors.append("authorization_endpoint is required if discovery_url is not provided")
            if not oidc.token_endpoint:
                errors.append("token_endpoint is required if discovery_url is not provided")

        # Client ID is always required
        if not oidc.client_id:
            errors.append("client_id is required")

    # Update status based on validation
    if errors:
        config.status = IdPStatus.ERROR
        config.status_message = "; ".join(errors)
    else:
        config.status = IdPStatus.ACTIVE
        config.validated_at = datetime.utcnow()
        config.status_message = None

    return IdPValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        extracted_metadata=extracted,
    )


@router.post("/configs/{config_id}/generate", response_model=GenerateConfigResponse)
async def generate_splunk_config(
    config_id: str,
    instance_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> GenerateConfigResponse:
    """
    Generate Splunk authentication configuration for an IdP.

    Returns the authentication.conf and authorize.conf content
    to apply to a Splunk instance.
    """
    config = _idp_configs.get(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IdP config {config_id} not found",
        )

    # Check tenant access
    if config.tenant_id != actor.effective_tenant_id:
        is_admin = "platform_admin" in actor.roles or "admin" in actor.roles
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this IdP configuration",
            )

    if config.status != IdPStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="IdP configuration must be validated and active before generating Splunk config",
        )

    instructions: list[str] = []

    if config.idp_type == IdPType.SAML and config.saml_config:
        saml = config.saml_config

        # Generate authentication.conf for SAML
        auth_conf = f"""# Faux Splunk Cloud - SAML Authentication Configuration
# Generated for instance: {instance_id}
# IdP Config: {config.name} ({config_id})

[authentication]
authType = SAML
authSettings = idp_{config_id}

[idp_{config_id}]
entityId = {saml.entity_id or 'TO_BE_EXTRACTED_FROM_METADATA'}
idpSSOUrl = {saml.sso_url or 'TO_BE_EXTRACTED_FROM_METADATA'}
idpSLOUrl = {saml.slo_url or ''}
idpCertPath = /opt/splunk/etc/auth/idp_cert.pem
signAuthnRequest = {str(saml.sign_authn_requests).lower()}
signedAssertion = {str(saml.want_assertions_signed).lower()}
nameIdFormat = {saml.name_id_format}
attributeQueryUrl =
issuerId = faux-splunk-{instance_id}
"""

        # Generate role mapping for authorize.conf
        role_mappings = []
        for idp_role, splunk_roles in saml.role_mapping.items():
            for splunk_role in splunk_roles:
                role_mappings.append(f"{idp_role} = {splunk_role}")

        authorize_conf = f"""# Faux Splunk Cloud - SAML Role Mappings
# Generated for instance: {instance_id}

[roleMap_idp_{config_id}]
{chr(10).join(role_mappings)}
"""

        instructions = [
            "1. Copy authentication.conf to $SPLUNK_HOME/etc/system/local/",
            "2. Copy authorize.conf to $SPLUNK_HOME/etc/system/local/",
            "3. Download the IdP certificate and save to /opt/splunk/etc/auth/idp_cert.pem",
            f"4. Register the Splunk SP metadata with your IdP. Entity ID: faux-splunk-{instance_id}",
            "5. Restart Splunk for changes to take effect",
        ]

        return GenerateConfigResponse(
            config=SplunkAuthConfig(
                authentication_conf=auth_conf,
                authorize_conf=authorize_conf,
                idp_metadata=saml.metadata_xml,
            ),
            instructions=instructions,
        )

    elif config.idp_type == IdPType.OIDC and config.oidc_config:
        oidc = config.oidc_config

        # Generate authentication.conf for OIDC (Splunk 9.0+)
        auth_conf = f"""# Faux Splunk Cloud - OIDC Authentication Configuration
# Generated for instance: {instance_id}
# IdP Config: {config.name} ({config_id})

[authentication]
authType = OIDC
authSettings = oidc_{config_id}

[oidc_{config_id}]
issuer = {oidc.issuer or oidc.discovery_url}
clientId = {oidc.client_id}
clientSecret = {oidc.client_secret or ''}
scope = {' '.join(oidc.scopes)}
userAttributeQueryUrl = {oidc.userinfo_endpoint or ''}
authorizationUrl = {oidc.authorization_endpoint or ''}
tokenUrl = {oidc.token_endpoint or ''}
jwksUrl = {oidc.jwks_uri or ''}
"""

        # Generate role mapping
        role_mappings = []
        for idp_role, splunk_roles in oidc.role_mapping.items():
            for splunk_role in splunk_roles:
                role_mappings.append(f"{idp_role} = {splunk_role}")

        authorize_conf = f"""# Faux Splunk Cloud - OIDC Role Mappings
# Generated for instance: {instance_id}

[roleMap_oidc_{config_id}]
{chr(10).join(role_mappings)}
"""

        instructions = [
            "1. Copy authentication.conf to $SPLUNK_HOME/etc/system/local/",
            "2. Copy authorize.conf to $SPLUNK_HOME/etc/system/local/",
            f"3. Register the callback URL in your OIDC provider: https://<splunk-url>/saml/acs",
            "4. Restart Splunk for changes to take effect",
        ]

        return GenerateConfigResponse(
            config=SplunkAuthConfig(
                authentication_conf=auth_conf,
                authorize_conf=authorize_conf,
            ),
            instructions=instructions,
        )

    elif config.idp_type == IdPType.PLATFORM_KEYCLOAK:
        # Use platform Keycloak - this would integrate with keycloak_admin service
        instructions = [
            "1. Platform Keycloak will be automatically configured",
            "2. Users can log in using their platform credentials",
            "3. No additional configuration is required",
        ]

        return GenerateConfigResponse(
            config=SplunkAuthConfig(
                authentication_conf="# Platform Keycloak - auto-configured",
                authorize_conf="# Platform Keycloak - auto-configured",
            ),
            instructions=instructions,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported IdP type or missing configuration",
    )


@router.post("/configs/{config_id}/set-default", response_model=TenantIdPConfig)
async def set_default_idp_config(
    config_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> TenantIdPConfig:
    """Set an IdP configuration as the default for new instances."""
    config = _idp_configs.get(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IdP config {config_id} not found",
        )

    # Check tenant access
    if config.tenant_id != actor.effective_tenant_id:
        is_admin = "platform_admin" in actor.roles or "admin" in actor.roles
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this IdP configuration",
            )

    # Unset other defaults
    config_ids = _tenant_config_index.get(config.tenant_id, [])
    for cid in config_ids:
        if cid in _idp_configs:
            _idp_configs[cid].is_default = False

    # Set this as default
    config.is_default = True
    config.updated_at = datetime.utcnow()

    logger.info(f"Set IdP config {config_id} as default for tenant {config.tenant_id}")

    return config


# Admin endpoints


@router.get("/admin/configs", response_model=TenantIdPConfigList)
async def admin_list_all_idp_configs(
    _: Annotated[AnyAuthData, Depends(require_admin)],
    tenant_id: str | None = None,
    status: IdPStatus | None = None,
) -> TenantIdPConfigList:
    """
    List all IdP configurations (admin only).

    Can filter by tenant_id and status.
    """
    configs = list(_idp_configs.values())

    if tenant_id:
        configs = [c for c in configs if c.tenant_id == tenant_id]

    if status:
        configs = [c for c in configs if c.status == status]

    return TenantIdPConfigList(configs=configs, total=len(configs))
