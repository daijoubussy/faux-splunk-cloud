"""
SAML Authentication API routes.

Handles SAML SSO/SLO flows and Splunk SAML integration wizard.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from faux_splunk_cloud.api.deps import get_current_token, require_auth
from faux_splunk_cloud.services.keycloak import keycloak_service
from faux_splunk_cloud.services.keycloak_admin import keycloak_admin

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================


class SAMLLoginResponse(BaseModel):
    """SAML login initiation response."""

    redirect_url: str
    message: str = "Redirect to IdP for authentication"


class SAMLSessionResponse(BaseModel):
    """SAML session info response."""

    authenticated: bool
    user_id: str | None = None
    email: str | None = None
    name: str | None = None
    tenant_id: str | None = None
    roles: list[str] = []
    expires_at: str | None = None


class EnterpriseRolesResponse(BaseModel):
    """Enterprise roles information for wizard."""

    splunk_roles: dict
    platform_roles: dict


class SplunkSAMLSetupRequest(BaseModel):
    """Request to set up SAML for a Splunk instance."""

    instance_id: str
    instance_name: str
    splunk_base_url: str


class SplunkSAMLSetupResponse(BaseModel):
    """Response with Splunk SAML configuration."""

    keycloak_client: dict
    idp_metadata: str
    splunk_config: dict
    setup_instructions: list[dict]


class TenantSetupRequest(BaseModel):
    """Request to set up a new tenant realm."""

    tenant_id: str
    tenant_name: str
    admin_email: str
    admin_password: str


class TenantSetupResponse(BaseModel):
    """Response from tenant setup."""

    realm: dict
    admin_user: dict
    roles: list[str]
    saml_metadata_url: str


class CustomerRegistrationRequest(BaseModel):
    """Request to register a new customer."""

    company_name: str
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""


class CustomerRegistrationResponse(BaseModel):
    """Response from customer registration."""

    user: dict
    tenant: dict
    login_url: str


# ============================================================================
# Platform SAML Authentication
# ============================================================================


@router.get("/login")
async def saml_login(
    request: Request,
    return_to: str = Query(default="/", description="URL to return to after login"),
    tenant_id: str | None = Query(default=None, description="Tenant ID for tenant-specific IdP"),
) -> RedirectResponse:
    """
    Initiate SAML login flow.

    Redirects to Keycloak (or tenant IdP) for authentication.
    """
    if not keycloak_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="SAML authentication not configured. Set FSC_KEYCLOAK_URL environment variable.",
        )

    try:
        request_data = keycloak_service.prepare_request(request)
        redirect_url = keycloak_service.create_auth_request(
            request_data,
            tenant_id=tenant_id,
            return_to=return_to,
        )
        # Redirect browser to IdP for authentication
        return RedirectResponse(url=redirect_url, status_code=302)
    except Exception as e:
        logger.error(f"SAML login error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"SAML configuration error: {str(e)}. Check Keycloak connectivity and IdP settings.",
        )


@router.post("/acs")
async def saml_acs(
    request: Request,
    response: Response,
) -> RedirectResponse:
    """
    SAML Assertion Consumer Service (ACS).

    Processes SAML response from IdP and creates session.
    """
    if not keycloak_service.is_configured:
        raise HTTPException(status_code=503, detail="SAML not configured")

    # Get form data (SAML response is POSTed)
    form_data = await request.form()
    request_data = keycloak_service.prepare_request(request)
    request_data["post_data"] = dict(form_data)

    # Process SAML response
    user_data = keycloak_service.process_response(request_data)

    if not user_data:
        raise HTTPException(
            status_code=401,
            detail="SAML authentication failed. Check IdP configuration.",
        )

    # Create session
    session = keycloak_service.create_session(user_data)

    # Determine redirect URL based on user type and RelayState
    relay_state = str(form_data.get("RelayState", "/"))

    # If relay_state is just "/" or empty, redirect based on user type
    if relay_state in ("/", ""):
        # Check if user is platform admin
        if "platform_admin" in user_data.roles:
            redirect_url = "/admin"
        elif session.tenant_id:
            # Customer user - redirect to tenant-scoped URL
            redirect_url = f"/{session.tenant_id}"
        else:
            # Fallback for users without tenant
            redirect_url = "/"
    else:
        redirect_url = relay_state

    # Set session cookie and redirect
    redirect = RedirectResponse(url=redirect_url, status_code=303)
    redirect.set_cookie(
        key="fsc_session",
        value=session.session_id,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=28800,  # 8 hours
    )

    return redirect


@router.get("/slo")
async def saml_slo_initiate(
    request: Request,
    fsc_session: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    """
    Initiate SAML Single Logout.

    Redirects to Keycloak to log out from the IdP.
    """
    if not fsc_session:
        redirect = RedirectResponse(url="/", status_code=302)
        redirect.delete_cookie("fsc_session")
        return redirect

    session = keycloak_service.get_session(fsc_session)
    if not session:
        redirect = RedirectResponse(url="/", status_code=302)
        redirect.delete_cookie("fsc_session")
        return redirect

    request_data = keycloak_service.prepare_request(request)
    logout_url = keycloak_service.create_logout_request(
        request_data,
        session,
        return_to="/",
    )

    # Destroy local session
    keycloak_service.destroy_session(fsc_session)

    # Create redirect and clear session cookie
    redirect = RedirectResponse(url=logout_url, status_code=302)
    redirect.delete_cookie("fsc_session")

    return redirect


@router.post("/slo")
async def saml_slo_response(
    fsc_session: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    """
    Handle SAML Single Logout Response from IdP.

    After Keycloak processes the logout, it POSTs back to this endpoint.
    """
    # Destroy local session if it exists
    if fsc_session:
        keycloak_service.destroy_session(fsc_session)

    # Clear the session cookie and redirect to home
    redirect = RedirectResponse(url="/", status_code=303)
    redirect.delete_cookie("fsc_session")

    return redirect


@router.get("/session", response_model=SAMLSessionResponse)
async def get_session(
    fsc_session: Annotated[str | None, Cookie()] = None,
) -> SAMLSessionResponse:
    """
    Get current SAML session info.

    Used by the UI to check authentication status.
    """
    if not fsc_session:
        return SAMLSessionResponse(authenticated=False)

    session = keycloak_service.get_session(fsc_session)
    if not session:
        return SAMLSessionResponse(authenticated=False)

    return SAMLSessionResponse(
        authenticated=True,
        user_id=session.user_data.name_id,
        email=session.user_data.email,
        name=session.user_data.name,
        tenant_id=session.tenant_id,
        roles=session.user_data.roles,
        expires_at=session.expires_at.isoformat(),
    )


@router.post("/logout")
async def logout(
    response: Response,
    fsc_session: Annotated[str | None, Cookie()] = None,
) -> dict:
    """
    Local logout (without SAML SLO).

    Destroys the local session without contacting the IdP.
    """
    if fsc_session:
        keycloak_service.destroy_session(fsc_session)

    response.delete_cookie("fsc_session")
    return {"status": "logged_out"}


@router.post("/register", response_model=CustomerRegistrationResponse)
async def register_customer(
    request: CustomerRegistrationRequest,
) -> CustomerRegistrationResponse:
    """
    Register a new customer with automatic tenant provisioning.

    Creates:
    - A new tenant based on company name
    - A user account with customer/tenant_admin roles
    - Associates the user with the new tenant

    After registration, the user can log in via SAML.
    """
    try:
        result = await keycloak_admin.register_customer(
            company_name=request.company_name,
            email=request.email,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
        )
        return CustomerRegistrationResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Registration failed. Please try again later.",
        )


# ============================================================================
# SAML Setup Wizard API
# ============================================================================


@router.get("/wizard/roles", response_model=EnterpriseRolesResponse)
async def get_enterprise_roles() -> EnterpriseRolesResponse:
    """
    Get enterprise role definitions for the setup wizard.

    Returns role descriptions and mappings for display in the UI.
    """
    roles = keycloak_admin.get_enterprise_roles_info()
    return EnterpriseRolesResponse(**roles)


@router.post("/wizard/tenant", response_model=TenantSetupResponse)
async def setup_tenant_realm(
    request: TenantSetupRequest,
    _: Annotated[str, Depends(require_auth)],
) -> TenantSetupResponse:
    """
    Set up a new tenant realm in Keycloak.

    Creates:
    - Keycloak realm for the tenant
    - Enterprise roles
    - Initial admin user

    This is typically called when a new tenant is created.
    """
    result = await keycloak_admin.setup_tenant_realm(
        tenant_id=request.tenant_id,
        tenant_name=request.tenant_name,
        admin_email=request.admin_email,
        admin_password=request.admin_password,
    )

    return TenantSetupResponse(**result)


@router.post("/wizard/splunk", response_model=SplunkSAMLSetupResponse)
async def setup_splunk_saml(
    request: SplunkSAMLSetupRequest,
    _: Annotated[str, Depends(require_auth)],
    tenant_id: str = Query(description="Tenant ID"),
) -> SplunkSAMLSetupResponse:
    """
    Set up SAML authentication for a Splunk instance.

    Creates:
    - SAML client in Keycloak
    - Role mappings for Splunk roles
    - Returns configuration for Splunk's authentication.conf

    The returned configuration should be applied to the Splunk instance
    to enable SAML authentication.
    """
    result = await keycloak_admin.setup_splunk_saml_client(
        tenant_id=tenant_id,
        instance_id=request.instance_id,
        instance_name=request.instance_name,
        splunk_base_url=request.splunk_base_url,
    )

    return SplunkSAMLSetupResponse(**result)


@router.get("/wizard/metadata/{realm_name}")
async def get_idp_metadata(
    realm_name: str,
) -> Response:
    """
    Get SAML IdP metadata XML for a realm.

    This can be used to configure Splunk's SAML settings.
    """
    try:
        metadata = await keycloak_admin.get_saml_idp_metadata(realm_name)
        return Response(content=metadata, media_type="application/xml")
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Realm not found or metadata unavailable: {e}",
        )


# ============================================================================
# Splunk SAML Auto-Configuration
# ============================================================================


@router.get("/splunk/{instance_id}/metadata")
async def get_splunk_sp_metadata(
    instance_id: str,
) -> Response:
    """
    Generate SAML Service Provider metadata for a Splunk instance.

    This can be imported into Keycloak to set up the SAML client.
    """
    # This would generate SP metadata based on instance configuration
    # For now, return a template
    sp_metadata = f"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     entityID="splunk-{instance_id}">
    <md:SPSSODescriptor
        AuthnRequestsSigned="true"
        WantAssertionsSigned="true"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="https://localhost/splunk-{instance_id}/saml/acs"
            index="0"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""

    return Response(content=sp_metadata, media_type="application/xml")


@router.post("/splunk/{instance_id}/configure")
async def auto_configure_splunk_saml(
    instance_id: str,
    _: Annotated[str, Depends(require_auth)],
    tenant_id: str = Query(description="Tenant ID"),
) -> dict:
    """
    Auto-configure SAML on a running Splunk instance.

    This endpoint:
    1. Creates the Keycloak SAML client
    2. Generates Splunk configuration
    3. Applies configuration to the Splunk instance via REST API

    Note: This requires the instance to be running and accessible.
    """
    # This would use the Splunk SDK to configure SAML
    # For now, return the configuration that would be applied

    from faux_splunk_cloud.services.instance_manager import instance_manager

    instance = instance_manager._instances.get(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    splunk_base_url = instance.endpoints.web_url

    # Get SAML configuration
    saml_config = await keycloak_admin.setup_splunk_saml_client(
        tenant_id=tenant_id,
        instance_id=instance_id,
        instance_name=instance.name,
        splunk_base_url=splunk_base_url,
    )

    # TODO: Apply configuration to Splunk via REST API
    # This would involve:
    # 1. Writing authentication.conf
    # 2. Writing authorize.conf
    # 3. Restarting Splunk

    return {
        "status": "configuration_generated",
        "message": "SAML configuration generated. Apply manually or use auto-apply.",
        "config": saml_config["splunk_config"],
        "instructions": saml_config["setup_instructions"],
        "auto_apply_available": False,  # Would be True when REST API config is implemented
    }
