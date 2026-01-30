"""
HashiCorp Vault API endpoints for secrets management.

Provides admin-only access to Vault status and secret management.
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from faux_splunk_cloud.api.deps import (
    AnyAuthData,
    require_platform_admin,
)
from faux_splunk_cloud.services.vault_service import vault_service

logger = logging.getLogger(__name__)

router = APIRouter()


class VaultStatus(BaseModel):
    """Vault status information."""
    initialized: bool = False
    sealed: bool = True
    standby: bool = False
    version: str = "unknown"
    cluster_name: str | None = None
    authenticated: bool = False
    error: str | None = None


class SecretRequest(BaseModel):
    """Request to store a secret."""
    path: str = Field(..., description="Secret path (relative to fsc/)")
    data: dict[str, Any] = Field(..., description="Secret data to store")


class SecretResponse(BaseModel):
    """Response containing secret data."""
    path: str
    data: dict[str, Any] | None


class SecretListResponse(BaseModel):
    """Response containing list of secrets."""
    path: str
    keys: list[str]


class EncryptRequest(BaseModel):
    """Request to encrypt data."""
    plaintext: str = Field(..., description="Data to encrypt")
    key_name: str = Field(default="fsc", description="Transit key name")


class EncryptResponse(BaseModel):
    """Response with encrypted data."""
    ciphertext: str


class DecryptRequest(BaseModel):
    """Request to decrypt data."""
    ciphertext: str = Field(..., description="Encrypted data")
    key_name: str = Field(default="fsc", description="Transit key name")


class DecryptResponse(BaseModel):
    """Response with decrypted data."""
    plaintext: str


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


# Status endpoints


@router.get("/status", response_model=VaultStatus)
async def get_vault_status(
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
) -> VaultStatus:
    """
    Get Vault status information.

    Returns initialization state, seal status, and version info.
    Requires platform admin role.
    """
    status_data = await vault_service.get_status()
    return VaultStatus(**status_data)


@router.get("/health")
async def get_vault_health() -> dict[str, bool]:
    """
    Check Vault health (public endpoint).

    Returns simple healthy/unhealthy status.
    """
    healthy = await vault_service.is_healthy()
    return {"healthy": healthy}


# Secrets endpoints


@router.get("/secrets", response_model=SecretListResponse)
async def list_secrets(
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
    path: str = "",
) -> SecretListResponse:
    """
    List secrets at a path.

    Requires platform admin role.
    """
    keys = await vault_service.list_secrets(path)
    return SecretListResponse(path=path, keys=keys)


@router.get("/secrets/{path:path}", response_model=SecretResponse)
async def get_secret(
    path: str,
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
) -> SecretResponse:
    """
    Get a secret by path.

    Requires platform admin role.
    """
    data = await vault_service.get_secret(path)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret not found at path: {path}",
        )
    return SecretResponse(path=path, data=data)


@router.post("/secrets", response_model=MessageResponse)
async def store_secret(
    request: SecretRequest,
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
) -> MessageResponse:
    """
    Store a secret.

    Requires platform admin role.
    """
    success = await vault_service.store_secret(request.path, request.data)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store secret",
        )
    return MessageResponse(message=f"Secret stored at fsc/{request.path}")


@router.delete("/secrets/{path:path}", response_model=MessageResponse)
async def delete_secret(
    path: str,
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
) -> MessageResponse:
    """
    Delete a secret.

    Requires platform admin role.
    """
    success = await vault_service.delete_secret(path)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete secret",
        )
    return MessageResponse(message=f"Secret deleted at fsc/{path}")


# Transit encryption endpoints


@router.post("/encrypt", response_model=EncryptResponse)
async def encrypt_data(
    request: EncryptRequest,
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
) -> EncryptResponse:
    """
    Encrypt data using Vault Transit.

    Requires platform admin role.
    """
    ciphertext = await vault_service.encrypt(request.plaintext, request.key_name)
    if ciphertext is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to encrypt data",
        )
    return EncryptResponse(ciphertext=ciphertext)


@router.post("/decrypt", response_model=DecryptResponse)
async def decrypt_data(
    request: DecryptRequest,
    _: Annotated[AnyAuthData, Depends(require_platform_admin)],
) -> DecryptResponse:
    """
    Decrypt data using Vault Transit.

    Requires platform admin role.
    """
    plaintext = await vault_service.decrypt(request.ciphertext, request.key_name)
    if plaintext is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt data",
        )
    return DecryptResponse(plaintext=plaintext)
