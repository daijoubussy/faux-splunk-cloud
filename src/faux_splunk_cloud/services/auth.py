"""
Authentication service for ACS API.

The Splunk ACS API uses JWT tokens for authentication. This service
provides JWT generation and validation compatible with the ACS API format.

Reference: https://help.splunk.com/en/splunk-cloud-platform/administer/admin-config-service-manual/
"""

from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from faux_splunk_cloud.config import settings


class TokenData(BaseModel):
    """JWT token payload data."""

    sub: str  # Subject (username or instance ID)
    stack: str  # Splunk Cloud stack name (instance ID)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    roles: list[str]  # User roles
    capabilities: list[str]  # Granted capabilities


class AuthService:
    """
    Authentication service for ACS API compatibility.

    Generates and validates JWT tokens matching the ACS API authentication scheme.
    """

    def __init__(self) -> None:
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._secret_key = settings.jwt_secret_key.get_secret_value()
        self._algorithm = settings.jwt_algorithm
        self._expiration_hours = settings.jwt_expiration_hours

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return self._pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self._pwd_context.verify(plain_password, hashed_password)

    def create_acs_token(
        self,
        instance_id: str,
        username: str = "admin",
        roles: list[str] | None = None,
        capabilities: list[str] | None = None,
        expiration_hours: int | None = None,
    ) -> str:
        """
        Create a JWT token compatible with ACS API format.

        Args:
            instance_id: The Splunk Cloud stack/instance identifier
            username: The username (subject)
            roles: List of roles (defaults to sc_admin)
            capabilities: List of capabilities
            expiration_hours: Token expiration in hours

        Returns:
            JWT token string
        """
        if roles is None:
            roles = ["sc_admin", "admin"]

        if capabilities is None:
            # Default sc_admin capabilities for ACS API
            capabilities = [
                "admin_all_objects",
                "edit_tokens_settings",
                "edit_httpauths",
                "edit_indexer_cluster",
                "list_inputs",
                "edit_monitor",
                "edit_tcp",
                "edit_udp",
                "edit_splunktcp",
                "edit_splunktcp_ssl",
                "list_deployment_client",
                "edit_deployment_client",
            ]

        exp_hours = expiration_hours or self._expiration_hours
        now = datetime.utcnow()
        expiration = now + timedelta(hours=exp_hours)

        payload: dict[str, Any] = {
            "sub": username,
            "stack": instance_id,
            "exp": expiration,
            "iat": now,
            "roles": roles,
            "capabilities": capabilities,
            # ACS-specific claims
            "iss": "faux-splunk-cloud",
            "aud": f"acs:{instance_id}",
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> TokenData | None:
        """
        Decode and validate a JWT token.

        Args:
            token: The JWT token string

        Returns:
            TokenData if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token, self._secret_key, algorithms=[self._algorithm]
            )
            return TokenData(
                sub=payload.get("sub", ""),
                stack=payload.get("stack", ""),
                exp=datetime.fromtimestamp(payload.get("exp", 0)),
                iat=datetime.fromtimestamp(payload.get("iat", 0)),
                roles=payload.get("roles", []),
                capabilities=payload.get("capabilities", []),
            )
        except JWTError:
            return None

    def validate_token_for_stack(self, token: str, stack_id: str) -> TokenData | None:
        """
        Validate a token and ensure it's authorized for the given stack.

        Args:
            token: The JWT token string
            stack_id: The stack/instance ID to validate against

        Returns:
            TokenData if valid and authorized, None otherwise
        """
        token_data = self.decode_token(token)
        if token_data is None:
            return None

        # Check if token is for this stack or has wildcard access
        if token_data.stack != stack_id and token_data.stack != "*":
            return None

        # Check expiration
        if token_data.exp < datetime.utcnow():
            return None

        return token_data

    def has_capability(self, token_data: TokenData, capability: str) -> bool:
        """Check if token has a specific capability."""
        return capability in token_data.capabilities

    def has_role(self, token_data: TokenData, role: str) -> bool:
        """Check if token has a specific role."""
        return role in token_data.roles


# Global auth service instance
auth_service = AuthService()
