"""
Tenant user management API routes.

These routes allow tenant admins to manage users within their tenant's Keycloak realm.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from faux_splunk_cloud.api.deps import ActorContext, get_actor_context
from faux_splunk_cloud.services.keycloak_admin import keycloak_admin

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class InviteUserRequest(BaseModel):
    """Request to invite a new user to the tenant."""

    email: str
    password: str
    first_name: str = ""
    last_name: str = ""
    roles: list[str] | None = None


class InviteUserResponse(BaseModel):
    """Response from user invitation."""

    user: dict
    tenant_id: str


class TenantUser(BaseModel):
    """Tenant user info."""

    id: str
    username: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    enabled: bool = True


class ListUsersResponse(BaseModel):
    """Response with list of tenant users."""

    users: list[TenantUser]
    tenant_id: str
    count: int


# ============================================================================
# Tenant User Management Routes
# ============================================================================


@router.get("", response_model=ListUsersResponse)
async def list_users(
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> ListUsersResponse:
    """
    List all users in the current tenant.

    Only tenant admins can list users.
    """
    if not actor.effective_tenant_id:
        raise HTTPException(status_code=400, detail="No tenant context")

    # Check if user has tenant_admin role
    if "tenant_admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    try:
        users = await keycloak_admin.list_tenant_users(actor.effective_tenant_id)
        tenant_users = [
            TenantUser(
                id=u.get("id", ""),
                username=u.get("username", ""),
                email=u.get("email"),
                first_name=u.get("firstName"),
                last_name=u.get("lastName"),
                enabled=u.get("enabled", True),
            )
            for u in users
        ]
        return ListUsersResponse(
            users=tenant_users,
            tenant_id=actor.effective_tenant_id,
            count=len(tenant_users),
        )
    except Exception as e:
        logger.error(f"Failed to list tenant users: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.post("", response_model=InviteUserResponse)
async def invite_user(
    request: InviteUserRequest,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> InviteUserResponse:
    """
    Invite a new user to the current tenant.

    Creates a user in the tenant's Keycloak realm.
    Only tenant admins can invite users.
    """
    if not actor.effective_tenant_id:
        raise HTTPException(status_code=400, detail="No tenant context")

    # Check if user has tenant_admin role
    if "tenant_admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    try:
        result = await keycloak_admin.invite_tenant_user(
            tenant_id=actor.effective_tenant_id,
            email=request.email,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
            roles=request.roles,
        )
        return InviteUserResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to invite user: {e}")
        raise HTTPException(status_code=500, detail="Failed to invite user")


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    actor: Annotated[ActorContext, Depends(get_actor_context)],
) -> dict:
    """
    Delete a user from the current tenant.

    Only tenant admins can delete users.
    Users cannot delete themselves.
    """
    if not actor.effective_tenant_id:
        raise HTTPException(status_code=400, detail="No tenant context")

    # Check if user has tenant_admin role
    if "tenant_admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    # Prevent self-deletion
    if user_id == actor.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    try:
        success = await keycloak_admin.delete_tenant_user(
            tenant_id=actor.effective_tenant_id,
            user_id=user_id,
        )
        if success:
            return {"status": "deleted", "user_id": user_id}
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")
