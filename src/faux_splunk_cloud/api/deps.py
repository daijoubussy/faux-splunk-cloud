"""
API dependencies for authentication and authorization.

Supports:
- SAML sessions via Keycloak (primary method for web UI)
- Local ACS tokens (HS256) for API/CLI access

Account Types (mutually exclusive):
- PLATFORM_ADMIN: Platform administrators (access /api/v1/admin/*)
- CUSTOMER: Tenant users (access /api/v1/customer/*)
"""

from enum import Enum
from typing import Annotated, Union

from fastapi import Cookie, Depends, Header, HTTPException, Path, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from faux_splunk_cloud.models.impersonation import ActorContext
from faux_splunk_cloud.services.auth import TokenData, auth_service
from faux_splunk_cloud.services.keycloak import SAMLSession, SAMLUserData, keycloak_service

# Security scheme for Bearer tokens
bearer_scheme = HTTPBearer(auto_error=False)

# Union type for authentication methods
AnyAuthData = Union[TokenData, SAMLUserData]
# Backwards compatibility alias
AnyTokenData = AnyAuthData


class AccountType(str, Enum):
    """
    Account types for the platform.

    These are mutually exclusive - a user is EITHER a platform admin OR a customer.
    """

    PLATFORM_ADMIN = "platform_admin"
    CUSTOMER = "customer"


def _get_account_type(auth_data: AnyAuthData) -> AccountType:
    """
    Determine account type from authentication data.

    This is mutually exclusive - accounts are either platform admins or customers.
    Platform admins manage the platform, customers use tenant features.
    """
    if isinstance(auth_data, SAMLUserData):
        roles = auth_data.roles + auth_data.groups
    else:
        roles = auth_data.roles

    if "platform_admin" in roles:
        return AccountType.PLATFORM_ADMIN

    return AccountType.CUSTOMER


async def get_saml_session(
    fsc_session: Annotated[str | None, Cookie()] = None,
) -> SAMLSession | None:
    """
    Get SAML session from cookie.

    This is the primary authentication method for web UI users.
    """
    if not fsc_session:
        return None

    return keycloak_service.get_session(fsc_session)


async def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    authorization: Annotated[str | None, Header()] = None,
) -> TokenData | None:
    """
    Extract and validate JWT token from the request.

    This is the authentication method for API/CLI access.
    """
    token = None

    if credentials:
        token = credentials.credentials
    elif authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

    if not token:
        return None

    # Validate local ACS token
    return auth_service.decode_token(token)


async def get_current_auth(
    saml_session: Annotated[SAMLSession | None, Depends(get_saml_session)],
    token_data: Annotated[TokenData | None, Depends(get_current_token)],
) -> AnyAuthData | None:
    """
    Get current authentication from either SAML session or JWT token.

    Priority:
    1. SAML session (for web UI users)
    2. JWT token (for API/CLI users)
    """
    if saml_session:
        return saml_session.user_data

    return token_data


async def require_auth(
    auth_data: Annotated[AnyAuthData | None, Depends(get_current_auth)],
) -> AnyAuthData:
    """Require valid authentication (SAML or JWT)."""
    if not auth_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in or provide a valid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_data


async def require_stack_auth(
    stack: Annotated[str, Path(description="The stack/instance ID")],
    authorization: Annotated[str | None, Header()] = None,
) -> TokenData:
    """
    Require valid authentication for a specific stack.

    This uses local ACS tokens for stack-specific operations.
    SAML users get auto-generated tokens when accessing their instances.
    """
    token = None

    if authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token for stack access",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = auth_service.validate_token_for_stack(token, stack)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token not authorized for this stack",
        )

    return token_data


async def get_actor_context(
    request: Request,
    auth_data: Annotated[AnyAuthData, Depends(require_auth)],
    saml_session: Annotated[SAMLSession | None, Depends(get_saml_session)],
    x_impersonate_session: Annotated[str | None, Header()] = None,
) -> ActorContext:
    """
    Get the current actor context, handling impersonation.

    Returns an ActorContext with both real identity and effective identity.
    """
    # Determine user identity based on auth type
    if isinstance(auth_data, SAMLUserData):
        real_user_id = auth_data.name_id
        real_email = auth_data.email or auth_data.name_id
        effective_tenant_id = auth_data.tenant_id or (saml_session.tenant_id if saml_session else "default")
        permissions = []  # SAML uses roles, not permissions
        roles = auth_data.roles + auth_data.groups
    else:
        # TokenData (JWT)
        real_user_id = auth_data.sub
        real_email = f"{auth_data.sub}@local"
        effective_tenant_id = auth_data.stack or "default"
        permissions = auth_data.capabilities
        roles = auth_data.roles

    # TODO: Handle impersonation session validation
    # For now, return non-impersonated context
    if x_impersonate_session:
        # Impersonation will be implemented in Phase 7
        pass

    return ActorContext(
        real_user_id=real_user_id,
        real_email=real_email,
        effective_user_id=real_user_id,
        effective_email=real_email,
        effective_tenant_id=effective_tenant_id,
        is_impersonating=False,
        impersonation_session_id=None,
        permissions=permissions,
        roles=roles,
    )


def require_permission(permission: str):
    """
    Create a dependency that requires a specific permission.

    Works with local capabilities. For SAML users, use require_role instead.
    """
    async def dependency(
        auth_data: Annotated[AnyAuthData, Depends(require_auth)],
    ) -> AnyAuthData:
        has_perm = False

        if isinstance(auth_data, SAMLUserData):
            # SAML users don't have fine-grained permissions
            # Map common permissions to roles
            permission_to_role = {
                "admin_all_objects": ["splunk_admin", "platform_admin"],
                "write:instances": ["tenant_admin", "platform_admin"],
                "read:instances": ["tenant_user", "tenant_admin", "platform_admin"],
                "admin:tenants": ["platform_admin"],
            }
            required_roles = permission_to_role.get(permission, [])
            has_perm = any(r in auth_data.roles for r in required_roles)
        else:
            has_perm = auth_service.has_capability(auth_data, permission)

        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return auth_data

    return dependency


def require_role(role: str):
    """
    Create a dependency that requires a specific role.

    Works with both SAML roles and local roles.
    """
    async def dependency(
        auth_data: Annotated[AnyAuthData, Depends(require_auth)],
    ) -> AnyAuthData:
        has_role = False

        if isinstance(auth_data, SAMLUserData):
            has_role = role in auth_data.roles or role in auth_data.groups
        else:
            has_role = auth_service.has_role(auth_data, role)

        if not has_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role: {role}",
            )
        return auth_data

    return dependency


async def require_admin(
    auth_data: Annotated[AnyAuthData, Depends(require_auth)],
) -> AnyAuthData:
    """Require admin privileges."""
    is_admin = False

    if isinstance(auth_data, SAMLUserData):
        admin_roles = ["platform_admin", "admin", "splunk_admin"]
        is_admin = any(r in auth_data.roles for r in admin_roles)
    else:
        # Local tokens: check for admin role or admin_all_objects capability
        is_admin = (
            auth_service.has_role(auth_data, "admin")
            or auth_service.has_capability(auth_data, "admin_all_objects")
        )

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return auth_data


async def require_platform_admin(
    auth_data: Annotated[AnyAuthData, Depends(require_auth)],
) -> AnyAuthData:
    """
    Require PLATFORM_ADMIN account type.

    Platform admins have access to /api/v1/admin/* endpoints including:
    - Tenant management
    - SIEM portal
    - Platform-wide audit logs
    - All instances (cross-tenant)
    """
    if _get_account_type(auth_data) != AccountType.PLATFORM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )
    return auth_data


async def require_customer(
    auth_data: Annotated[AnyAuthData, Depends(require_auth)],
) -> AnyAuthData:
    """
    Require CUSTOMER account type.

    Customers have access to /api/v1/customer/* endpoints including:
    - Their tenant's instances
    - Attack simulations
    - Their tenant's audit logs
    """
    if _get_account_type(auth_data) != AccountType.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account required",
        )
    return auth_data


# Optional auth - returns None if not authenticated
async def optional_auth(
    auth_data: Annotated[AnyAuthData | None, Depends(get_current_auth)],
) -> AnyAuthData | None:
    """Optional authentication - returns None if not authenticated."""
    return auth_data


# Backwards compatibility aliases
require_capability = require_permission
