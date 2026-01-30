"""
API dependencies for authentication and authorization.

Implements JWT-based authentication compatible with ACS API.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from faux_splunk_cloud.services.auth import TokenData, auth_service

# Security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    authorization: Annotated[str | None, Header()] = None,
) -> TokenData | None:
    """
    Extract and validate the JWT token from the request.

    Supports both Bearer token and raw Authorization header for ACS compatibility.
    """
    token = None

    if credentials:
        token = credentials.credentials
    elif authorization:
        # Handle "Bearer <token>" format
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

    if not token:
        return None

    return auth_service.decode_token(token)


async def require_auth(
    token_data: Annotated[TokenData | None, Depends(get_current_token)],
) -> TokenData:
    """Require valid authentication."""
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_data


async def require_stack_auth(
    stack: Annotated[str, Path(description="The stack/instance ID")],
    authorization: Annotated[str | None, Header()] = None,
) -> TokenData:
    """
    Require valid authentication for a specific stack.

    This is used by ACS API endpoints to validate that the token
    is authorized for the requested stack.
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
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = auth_service.validate_token_for_stack(token, stack)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token not authorized for this stack",
        )

    return token_data


def require_capability(capability: str):
    """
    Create a dependency that requires a specific capability.

    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(
            token: Annotated[TokenData, Depends(require_capability("admin_all_objects"))]
        ):
            ...
    """
    async def dependency(
        token_data: Annotated[TokenData, Depends(require_auth)],
    ) -> TokenData:
        if not auth_service.has_capability(token_data, capability):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required capability: {capability}",
            )
        return token_data

    return dependency


def require_role(role: str):
    """
    Create a dependency that requires a specific role.

    Usage:
        @router.post("/sc-admin-only")
        async def sc_admin_endpoint(
            token: Annotated[TokenData, Depends(require_role("sc_admin"))]
        ):
            ...
    """
    async def dependency(
        token_data: Annotated[TokenData, Depends(require_auth)],
    ) -> TokenData:
        if not auth_service.has_role(token_data, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role: {role}",
            )
        return token_data

    return dependency
