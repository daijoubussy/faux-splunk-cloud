"""
HashiCorp Vault integration service for secrets management.

Provides access to Vault for storing and retrieving secrets,
with AppRole authentication for the API service.
"""

import logging
import os
from pathlib import Path
from typing import Any

import httpx

from faux_splunk_cloud.config import settings

logger = logging.getLogger(__name__)


class VaultService:
    """
    Service for interacting with HashiCorp Vault.

    Uses AppRole authentication for machine-to-machine access.
    Credentials are provided by Terraform during infrastructure setup.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._token: str | None = None
        self._vault_addr = os.getenv("FSC_VAULT_ADDR", "http://vault:8200")
        self._credentials_file = os.getenv(
            "FSC_VAULT_CREDENTIALS_FILE", "/terraform/output/fsc-api.env"
        )
        self._role_id: str | None = None
        self._secret_id: str | None = None
        self._authenticated = False

    async def start(self) -> None:
        """Initialize the Vault service and authenticate."""
        self._client = httpx.AsyncClient(
            base_url=self._vault_addr,
            timeout=30.0,
        )
        await self._load_credentials()
        if self._role_id and self._secret_id:
            await self._authenticate()
        logger.info(f"Vault service started, server: {self._vault_addr}")

    async def stop(self) -> None:
        """Stop the Vault service."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._token = None
        self._authenticated = False
        logger.info("Vault service stopped")

    async def _load_credentials(self) -> None:
        """Load AppRole credentials from Terraform output."""
        creds_path = Path(self._credentials_file)
        if not creds_path.exists():
            logger.warning(f"Vault credentials file not found: {self._credentials_file}")
            return

        try:
            content = creds_path.read_text()
            for line in content.strip().split("\n"):
                if line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key == "FSC_VAULT_ROLE_ID":
                    self._role_id = value.strip()
                elif key == "FSC_VAULT_SECRET_ID":
                    self._secret_id = value.strip()
            logger.info("Loaded Vault AppRole credentials from Terraform output")
        except Exception as e:
            logger.error(f"Failed to load Vault credentials: {e}")

    async def _authenticate(self) -> None:
        """Authenticate with Vault using AppRole."""
        if not self._client or not self._role_id or not self._secret_id:
            logger.warning("Cannot authenticate: missing client or credentials")
            return

        try:
            resp = await self._client.post(
                "/v1/auth/approle/login",
                json={
                    "role_id": self._role_id,
                    "secret_id": self._secret_id,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["auth"]["client_token"]
            self._authenticated = True
            logger.info("Authenticated with Vault via AppRole")
        except Exception as e:
            logger.error(f"Failed to authenticate with Vault: {e}")
            self._authenticated = False

    def _headers(self) -> dict[str, str]:
        """Get request headers with Vault token."""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["X-Vault-Token"] = self._token
        return headers

    async def is_healthy(self) -> bool:
        """Check if Vault is healthy and accessible."""
        if not self._client:
            return False

        try:
            resp = await self._client.get(
                "/v1/sys/health",
                params={"standbyok": "true"},
            )
            return resp.status_code in [200, 429]  # 200=active, 429=standby
        except Exception as e:
            logger.error(f"Vault health check failed: {e}")
            return False

    async def get_status(self) -> dict[str, Any]:
        """Get Vault status information."""
        if not self._client:
            return {"error": "Vault service not initialized"}

        try:
            # Get health
            health_resp = await self._client.get(
                "/v1/sys/health",
                params={"standbyok": "true", "uninitcode": "200", "sealedcode": "200"},
            )
            health = health_resp.json()

            # Get seal status
            seal_resp = await self._client.get("/v1/sys/seal-status")
            seal = seal_resp.json()

            return {
                "initialized": health.get("initialized", False),
                "sealed": seal.get("sealed", True),
                "standby": health.get("standby", False),
                "version": health.get("version", "unknown"),
                "cluster_name": health.get("cluster_name"),
                "authenticated": self._authenticated,
            }
        except Exception as e:
            logger.error(f"Failed to get Vault status: {e}")
            return {"error": str(e)}

    async def store_secret(self, path: str, data: dict[str, Any]) -> bool:
        """
        Store a secret in Vault KV v2.

        Args:
            path: Secret path (relative to fsc/ mount)
            data: Secret data

        Returns:
            True if successful
        """
        if not self._client or not self._authenticated:
            logger.warning("Cannot store secret: not authenticated")
            return False

        try:
            resp = await self._client.post(
                f"/v1/fsc/data/{path}",
                headers=self._headers(),
                json={"data": data},
            )
            resp.raise_for_status()
            logger.info(f"Stored secret at fsc/{path}")
            return True
        except Exception as e:
            logger.error(f"Failed to store secret at {path}: {e}")
            return False

    async def get_secret(self, path: str) -> dict[str, Any] | None:
        """
        Retrieve a secret from Vault KV v2.

        Args:
            path: Secret path (relative to fsc/ mount)

        Returns:
            Secret data or None if not found
        """
        if not self._client or not self._authenticated:
            logger.warning("Cannot get secret: not authenticated")
            return None

        try:
            resp = await self._client.get(
                f"/v1/fsc/data/{path}",
                headers=self._headers(),
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("data")
        except Exception as e:
            logger.error(f"Failed to get secret at {path}: {e}")
            return None

    async def delete_secret(self, path: str) -> bool:
        """
        Delete a secret from Vault KV v2.

        Args:
            path: Secret path (relative to fsc/ mount)

        Returns:
            True if successful
        """
        if not self._client or not self._authenticated:
            logger.warning("Cannot delete secret: not authenticated")
            return False

        try:
            resp = await self._client.delete(
                f"/v1/fsc/metadata/{path}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            logger.info(f"Deleted secret at fsc/{path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret at {path}: {e}")
            return False

    async def list_secrets(self, path: str = "") -> list[str]:
        """
        List secrets at a path.

        Args:
            path: Path prefix (relative to fsc/)

        Returns:
            List of secret names
        """
        if not self._client or not self._authenticated:
            logger.warning("Cannot list secrets: not authenticated")
            return []

        try:
            resp = await self._client.request(
                "LIST",
                f"/v1/fsc/metadata/{path}",
                headers=self._headers(),
            )
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("keys", [])
        except Exception as e:
            logger.error(f"Failed to list secrets at {path}: {e}")
            return []

    async def encrypt(self, plaintext: str, key_name: str = "fsc") -> str | None:
        """
        Encrypt data using Vault Transit.

        Args:
            plaintext: Data to encrypt (will be base64 encoded)
            key_name: Transit key name

        Returns:
            Ciphertext or None on error
        """
        if not self._client or not self._authenticated:
            logger.warning("Cannot encrypt: not authenticated")
            return None

        import base64
        encoded = base64.b64encode(plaintext.encode()).decode()

        try:
            resp = await self._client.post(
                f"/v1/transit/encrypt/{key_name}",
                headers=self._headers(),
                json={"plaintext": encoded},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("ciphertext")
        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")
            return None

    async def decrypt(self, ciphertext: str, key_name: str = "fsc") -> str | None:
        """
        Decrypt data using Vault Transit.

        Args:
            ciphertext: Encrypted data from encrypt()
            key_name: Transit key name

        Returns:
            Plaintext or None on error
        """
        if not self._client or not self._authenticated:
            logger.warning("Cannot decrypt: not authenticated")
            return None

        try:
            resp = await self._client.post(
                f"/v1/transit/decrypt/{key_name}",
                headers=self._headers(),
                json={"ciphertext": ciphertext},
            )
            resp.raise_for_status()
            data = resp.json()
            import base64
            encoded = data.get("data", {}).get("plaintext")
            if encoded:
                return base64.b64decode(encoded).decode()
            return None
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            return None


# Global service instance
vault_service = VaultService()
