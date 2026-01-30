"""
Keycloak Admin API service for multi-tenant management.

Manages Keycloak realms, clients, roles, and SAML configurations
for both the platform and tenant Splunk instances.
"""

import logging
from typing import Any

import httpx
from pydantic import BaseModel

from faux_splunk_cloud.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Enterprise Role Templates
# ============================================================================

ENTERPRISE_ROLES = {
    "splunk_admin": {
        "description": "Full administrative access to Splunk instance",
        "splunk_roles": ["admin", "sc_admin"],
        "capabilities": [
            "admin_all_objects",
            "edit_tokens_settings",
            "edit_httpauths",
            "edit_indexer_cluster",
            "list_inputs",
            "edit_monitor",
            "edit_tcp",
            "edit_udp",
        ],
    },
    "splunk_power_user": {
        "description": "Advanced search and report creation capabilities",
        "splunk_roles": ["power", "can_delete"],
        "capabilities": [
            "schedule_search",
            "accelerate_datamodel",
            "accelerate_search",
            "list_storage_passwords",
            "edit_search_schedule_window",
        ],
    },
    "splunk_analyst": {
        "description": "Standard search and dashboard access",
        "splunk_roles": ["user"],
        "capabilities": [
            "search",
            "list_inputs",
            "get_metadata",
            "run_collect",
        ],
    },
    "splunk_readonly": {
        "description": "View-only access to dashboards and saved searches",
        "splunk_roles": ["user"],
        "capabilities": [
            "get_metadata",
            "list_inputs",
        ],
    },
    # Platform-level roles
    "platform_admin": {
        "description": "Full platform administration including tenant management",
        "platform_permissions": ["admin:tenants", "admin:all", "write:instances", "read:instances"],
    },
    "tenant_admin": {
        "description": "Tenant-level administration",
        "platform_permissions": ["write:instances", "read:instances", "admin:tenant_users"],
    },
    "tenant_user": {
        "description": "Standard tenant user",
        "platform_permissions": ["read:instances", "write:own_instances"],
    },
}


class SAMLClientConfig(BaseModel):
    """SAML client configuration for Keycloak."""

    client_id: str  # Entity ID
    name: str
    description: str
    root_url: str
    base_url: str
    redirect_uris: list[str]
    master_saml_processing_url: str
    idp_initiated_sso_url_name: str | None = None
    name_id_format: str = "email"
    sign_documents: bool = True
    sign_assertions: bool = True
    encrypt_assertions: bool = False
    client_signature_required: bool = False
    force_post_binding: bool = True
    front_channel_logout: bool = True
    # Role mappings
    default_roles: list[str] = []
    role_mappings: dict[str, list[str]] = {}


class KeycloakAdminService:
    """
    Service for managing Keycloak via Admin REST API.

    Handles:
    - Realm creation/management for multi-tenancy
    - SAML client setup for Splunk instances
    - Role and group management
    - User provisioning
    """

    def __init__(self):
        # Use internal URL via Traefik (HTTPS) or fall back to settings
        if settings.keycloak_internal_url:
            # Extract base URL without realm path
            base = settings.keycloak_internal_url.rsplit("/realms/", 1)[0]
            self._base_url = base
        else:
            self._base_url = "https://traefik"  # HTTPS via Traefik
        self._admin_realm = "master"
        self._token: str | None = None
        self._token_expires: float = 0

    async def _get_admin_token(self) -> str:
        """Get admin access token for Keycloak API."""
        import time

        if self._token and time.time() < self._token_expires - 30:
            return self._token

        async with httpx.AsyncClient(verify=False) as client:  # verify=False for self-signed certs
            response = await client.post(
                f"{self._base_url}/realms/{self._admin_realm}/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": "admin",  # From FSC_KEYCLOAK_ADMIN env
                    "password": "admin",  # From FSC_KEYCLOAK_ADMIN_PASSWORD env
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            self._token = data["access_token"]
            self._token_expires = time.time() + data.get("expires_in", 300)

            return self._token

    async def _api_request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """Make authenticated request to Keycloak Admin API."""
        token = await self._get_admin_token()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"

        async with httpx.AsyncClient(verify=False) as client:  # verify=False for self-signed certs
            response = await client.request(
                method,
                f"{self._base_url}/admin/realms{path}",
                headers=headers,
                timeout=30.0,
                **kwargs,
            )
            return response

    # =========================================================================
    # Realm Management
    # =========================================================================

    async def create_realm(
        self,
        realm_name: str,
        display_name: str,
        enabled: bool = True,
    ) -> dict[str, Any]:
        """
        Create a new Keycloak realm for a tenant.

        Each tenant gets their own realm for isolation.
        """
        realm_config = {
            "realm": realm_name,
            "displayName": display_name,
            "enabled": enabled,
            "registrationAllowed": False,
            "resetPasswordAllowed": True,
            "rememberMe": True,
            "loginWithEmailAllowed": True,
            "duplicateEmailsAllowed": False,
            "sslRequired": "external",
            "defaultSignatureAlgorithm": "RS256",
            # SAML settings
            "attributes": {
                "frontendUrl": f"https://localhost/realms/{realm_name}",
            },
        }

        response = await self._api_request("POST", "", json=realm_config)

        if response.status_code == 201:
            logger.info(f"Created realm: {realm_name}")
            # Set up default roles
            await self._setup_realm_roles(realm_name)
            return {"realm": realm_name, "status": "created"}
        elif response.status_code == 409:
            logger.info(f"Realm already exists: {realm_name}")
            return {"realm": realm_name, "status": "exists"}
        else:
            logger.error(f"Failed to create realm: {response.text}")
            response.raise_for_status()

    async def _setup_realm_roles(self, realm_name: str) -> None:
        """Set up enterprise roles in a realm."""
        for role_name, role_config in ENTERPRISE_ROLES.items():
            await self._api_request(
                "POST",
                f"/{realm_name}/roles",
                json={
                    "name": role_name,
                    "description": role_config.get("description", ""),
                    "composite": False,
                },
            )
        logger.info(f"Created enterprise roles in realm: {realm_name}")

    async def get_realm(self, realm_name: str) -> dict[str, Any] | None:
        """Get realm configuration."""
        response = await self._api_request("GET", f"/{realm_name}")
        if response.status_code == 200:
            return response.json()
        return None

    async def delete_realm(self, realm_name: str) -> bool:
        """Delete a realm."""
        response = await self._api_request("DELETE", f"/{realm_name}")
        return response.status_code == 204

    # =========================================================================
    # SAML Client Management
    # =========================================================================

    async def create_saml_client(
        self,
        realm_name: str,
        config: SAMLClientConfig,
    ) -> dict[str, Any]:
        """
        Create a SAML client for a Splunk instance.

        This sets up Keycloak as the IdP for the Splunk instance.
        """
        client_config = {
            "clientId": config.client_id,
            "name": config.name,
            "description": config.description,
            "enabled": True,
            "protocol": "saml",
            "publicClient": True,
            "rootUrl": config.root_url,
            "baseUrl": config.base_url,
            "redirectUris": config.redirect_uris,
            "adminUrl": config.master_saml_processing_url,
            "attributes": {
                "saml.server.signature": str(config.sign_documents).lower(),
                "saml.assertion.signature": str(config.sign_assertions).lower(),
                "saml.encrypt": str(config.encrypt_assertions).lower(),
                "saml.client.signature": str(config.client_signature_required).lower(),
                "saml.force.post.binding": str(config.force_post_binding).lower(),
                "saml_name_id_format": config.name_id_format,
                "saml_force_name_id_format": "true",
                # Attribute statements for Splunk
                "saml.onetimeuse.condition": "false",
            },
            "fullScopeAllowed": True,
            "frontchannelLogout": config.front_channel_logout,
        }

        if config.idp_initiated_sso_url_name:
            client_config["attributes"]["saml_idp_initiated_sso_url_name"] = config.idp_initiated_sso_url_name

        response = await self._api_request(
            "POST",
            f"/{realm_name}/clients",
            json=client_config,
        )

        if response.status_code == 201:
            # Get the created client ID
            location = response.headers.get("Location", "")
            client_uuid = location.split("/")[-1] if location else None

            if client_uuid:
                # Add protocol mappers for Splunk attributes
                await self._setup_saml_mappers(realm_name, client_uuid)

            logger.info(f"Created SAML client: {config.client_id} in realm {realm_name}")
            return {"client_id": config.client_id, "uuid": client_uuid, "status": "created"}
        elif response.status_code == 409:
            logger.info(f"SAML client already exists: {config.client_id}")
            return {"client_id": config.client_id, "status": "exists"}
        else:
            logger.error(f"Failed to create SAML client: {response.text}")
            response.raise_for_status()

    async def _setup_saml_mappers(self, realm_name: str, client_uuid: str) -> None:
        """Set up SAML protocol mappers for Splunk attributes."""
        mappers = [
            {
                "name": "email",
                "protocol": "saml",
                "protocolMapper": "saml-user-property-mapper",
                "config": {
                    "user.attribute": "email",
                    "friendly.name": "email",
                    "attribute.name": "email",
                    "attribute.nameformat": "Basic",
                },
            },
            {
                "name": "firstName",
                "protocol": "saml",
                "protocolMapper": "saml-user-property-mapper",
                "config": {
                    "user.attribute": "firstName",
                    "friendly.name": "givenName",
                    "attribute.name": "givenName",
                    "attribute.nameformat": "Basic",
                },
            },
            {
                "name": "lastName",
                "protocol": "saml",
                "protocolMapper": "saml-user-property-mapper",
                "config": {
                    "user.attribute": "lastName",
                    "friendly.name": "surname",
                    "attribute.name": "surname",
                    "attribute.nameformat": "Basic",
                },
            },
            {
                "name": "roles",
                "protocol": "saml",
                "protocolMapper": "saml-role-list-mapper",
                "config": {
                    "single": "false",
                    "attribute.nameformat": "Basic",
                    "attribute.name": "roles",
                    "friendly.name": "roles",
                },
            },
            {
                "name": "groups",
                "protocol": "saml",
                "protocolMapper": "saml-group-membership-mapper",
                "config": {
                    "single": "false",
                    "attribute.nameformat": "Basic",
                    "attribute.name": "groups",
                    "friendly.name": "groups",
                    "full.path": "false",
                },
            },
        ]

        for mapper in mappers:
            await self._api_request(
                "POST",
                f"/{realm_name}/clients/{client_uuid}/protocol-mappers/models",
                json=mapper,
            )

    async def get_saml_client(
        self,
        realm_name: str,
        client_id: str,
    ) -> dict[str, Any] | None:
        """Get SAML client by client ID."""
        response = await self._api_request(
            "GET",
            f"/{realm_name}/clients",
            params={"clientId": client_id},
        )
        if response.status_code == 200:
            clients = response.json()
            return clients[0] if clients else None
        return None

    async def delete_saml_client(
        self,
        realm_name: str,
        client_uuid: str,
    ) -> bool:
        """Delete a SAML client."""
        response = await self._api_request(
            "DELETE",
            f"/{realm_name}/clients/{client_uuid}",
        )
        return response.status_code == 204

    async def get_saml_idp_metadata(self, realm_name: str) -> str:
        """Get SAML IdP metadata XML for a realm."""
        async with httpx.AsyncClient(verify=False) as client:  # verify=False for self-signed certs
            response = await client.get(
                f"{self._base_url}/realms/{realm_name}/protocol/saml/descriptor",
                timeout=10.0,
            )
            response.raise_for_status()
            return response.text

    # =========================================================================
    # User Management
    # =========================================================================

    async def create_user(
        self,
        realm_name: str,
        username: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        roles: list[str] | None = None,
        enabled: bool = True,
        attributes: dict[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        """Create a user in a realm."""
        user_config = {
            "username": username,
            "email": email,
            "emailVerified": True,
            "enabled": enabled,
            "firstName": first_name,
            "lastName": last_name,
            "credentials": [
                {
                    "type": "password",
                    "value": password,
                    "temporary": False,
                }
            ],
        }

        # Add custom attributes (e.g., tenant_id)
        if attributes:
            user_config["attributes"] = attributes

        response = await self._api_request(
            "POST",
            f"/{realm_name}/users",
            json=user_config,
        )

        if response.status_code == 201:
            # Get user ID and assign roles
            location = response.headers.get("Location", "")
            user_id = location.split("/")[-1] if location else None

            if user_id and roles:
                await self._assign_user_roles(realm_name, user_id, roles)

            return {"username": username, "user_id": user_id, "status": "created"}
        elif response.status_code == 409:
            return {"username": username, "status": "exists"}
        else:
            response.raise_for_status()

    async def _assign_user_roles(
        self,
        realm_name: str,
        user_id: str,
        role_names: list[str],
    ) -> None:
        """Assign realm roles to a user."""
        # Get role representations
        roles_response = await self._api_request("GET", f"/{realm_name}/roles")
        all_roles = roles_response.json() if roles_response.status_code == 200 else []

        roles_to_assign = [
            {"id": r["id"], "name": r["name"]}
            for r in all_roles
            if r["name"] in role_names
        ]

        if roles_to_assign:
            await self._api_request(
                "POST",
                f"/{realm_name}/users/{user_id}/role-mappings/realm",
                json=roles_to_assign,
            )

    # =========================================================================
    # Wizard/Setup Helpers
    # =========================================================================

    async def setup_tenant_realm(
        self,
        tenant_id: str,
        tenant_name: str,
        admin_email: str,
        admin_password: str,
    ) -> dict[str, Any]:
        """
        Complete tenant realm setup wizard.

        Creates realm, roles, and initial admin user.
        """
        realm_name = f"tenant-{tenant_id}"

        # Create realm
        realm_result = await self.create_realm(
            realm_name=realm_name,
            display_name=tenant_name,
        )

        # Create admin user
        admin_result = await self.create_user(
            realm_name=realm_name,
            username="admin",
            email=admin_email,
            password=admin_password,
            first_name="Tenant",
            last_name="Admin",
            roles=["tenant_admin", "splunk_admin"],
        )

        return {
            "realm": realm_result,
            "admin_user": admin_result,
            "roles": list(ENTERPRISE_ROLES.keys()),
            "saml_metadata_url": f"https://localhost/realms/{realm_name}/protocol/saml/descriptor",
        }

    async def setup_splunk_saml_client(
        self,
        tenant_id: str,
        instance_id: str,
        instance_name: str,
        splunk_base_url: str,
    ) -> dict[str, Any]:
        """
        Set up SAML client for a Splunk instance.

        Returns configuration needed for Splunk's authentication.conf.
        """
        realm_name = f"tenant-{tenant_id}"
        client_id = f"splunk-{instance_id}"

        # Create SAML client in Keycloak
        config = SAMLClientConfig(
            client_id=client_id,
            name=instance_name,
            description=f"Splunk instance {instance_name}",
            root_url=splunk_base_url,
            base_url="/",
            redirect_uris=[f"{splunk_base_url}/*"],
            master_saml_processing_url=f"{splunk_base_url}/saml/acs",
            idp_initiated_sso_url_name=instance_id,
            default_roles=["splunk_analyst"],
        )

        client_result = await self.create_saml_client(realm_name, config)

        # Get IdP metadata
        idp_metadata = await self.get_saml_idp_metadata(realm_name)

        # Generate Splunk configuration
        splunk_config = self._generate_splunk_auth_config(
            realm_name=realm_name,
            client_id=client_id,
            splunk_base_url=splunk_base_url,
        )

        return {
            "keycloak_client": client_result,
            "idp_metadata": idp_metadata,
            "splunk_config": splunk_config,
            "setup_instructions": self._get_setup_instructions(
                realm_name, splunk_base_url
            ),
        }

    def _generate_splunk_auth_config(
        self,
        realm_name: str,
        client_id: str,
        splunk_base_url: str,
    ) -> dict[str, Any]:
        """Generate Splunk authentication.conf content."""
        keycloak_url = f"https://localhost/realms/{realm_name}"

        return {
            "authentication": {
                "authType": "SAML",
                "authSettings": "keycloak_saml",
            },
            "keycloak_saml": {
                "fqdn": splunk_base_url.replace("https://", "").replace("http://", "").split(":")[0],
                "entityId": client_id,
                "idpSSOUrl": f"{keycloak_url}/protocol/saml",
                "idpSLOUrl": f"{keycloak_url}/protocol/saml",
                "idpCertPath": "/opt/splunk/etc/auth/keycloak.pem",
                "signAuthnRequest": "true",
                "signedAssertion": "true",
                "nameIdFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "ssoBinding": "HTTPPost",
                "sloBinding": "HTTPPost",
                "redirectPort": "0",
                "redirectAfterLogoutToUrl": splunk_base_url,
                "defaultRoleIfMissing": "user",
            },
            "roleMap_keycloak_saml": {
                "splunk_admin": "admin",
                "splunk_power_user": "power;can_delete",
                "splunk_analyst": "user",
                "splunk_readonly": "user",
            },
        }

    def _get_setup_instructions(
        self,
        realm_name: str,
        splunk_base_url: str,
    ) -> list[dict[str, str]]:
        """Get human-readable setup instructions."""
        return [
            {
                "step": "1",
                "title": "Download IdP Certificate",
                "description": f"Download the Keycloak signing certificate from the realm settings and save it to /opt/splunk/etc/auth/keycloak.pem on your Splunk instance.",
            },
            {
                "step": "2",
                "title": "Configure authentication.conf",
                "description": "Copy the generated authentication.conf settings to $SPLUNK_HOME/etc/system/local/authentication.conf",
            },
            {
                "step": "3",
                "title": "Configure authorize.conf",
                "description": "Map SAML roles to Splunk roles in authorize.conf for proper access control.",
            },
            {
                "step": "4",
                "title": "Restart Splunk",
                "description": "Restart Splunk for the SAML configuration to take effect.",
            },
            {
                "step": "5",
                "title": "Test Login",
                "description": f"Navigate to {splunk_base_url} and click 'Login with SAML' to test the integration.",
            },
        ]

    def get_enterprise_roles_info(self) -> dict[str, Any]:
        """Get enterprise role descriptions for UI display."""
        return {
            "splunk_roles": {
                name: {
                    "description": config["description"],
                    "splunk_roles": config.get("splunk_roles", []),
                    "capabilities": config.get("capabilities", [])[:5],  # First 5 for display
                }
                for name, config in ENTERPRISE_ROLES.items()
                if "splunk_roles" in config
            },
            "platform_roles": {
                name: {
                    "description": config["description"],
                    "permissions": config.get("platform_permissions", []),
                }
                for name, config in ENTERPRISE_ROLES.items()
                if "platform_permissions" in config
            },
        }

    async def register_customer(
        self,
        company_name: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
    ) -> dict[str, Any]:
        """
        Register a new customer with automatic tenant provisioning.

        Creates:
        - A new Keycloak realm for the tenant
        - Enterprise roles in the tenant realm
        - A tenant admin user who can manage users in their realm
        - A reference user in the main faux-splunk realm for platform access
        """
        import re
        import secrets

        # Generate tenant slug from company name
        tenant_slug = re.sub(r'[^a-z0-9-]', '', company_name.lower().replace(' ', '-'))
        tenant_slug = re.sub(r'-+', '-', tenant_slug).strip('-')
        if not tenant_slug:
            tenant_slug = "tenant"

        # Make slug unique by appending random suffix
        tenant_id = f"{tenant_slug}-{secrets.token_hex(4)}"
        tenant_realm = f"tenant-{tenant_id}"
        username = email.split('@')[0]

        # 1. Create the tenant's own Keycloak realm
        await self.create_realm(
            realm_name=tenant_realm,
            display_name=company_name,
        )

        # 2. Create the admin user in the tenant realm
        tenant_user_result = await self.create_user(
            realm_name=tenant_realm,
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            roles=["tenant_admin", "splunk_admin"],
            attributes={
                "tenant_id": [tenant_id],
                "company_name": [company_name],
            },
        )

        if tenant_user_result.get("status") == "exists":
            raise ValueError(f"User with email {email} already exists")

        # 3. Also create a reference user in the main platform realm
        # This allows the user to access the platform with customer role
        platform_realm = settings.keycloak_realm  # faux-splunk
        await self.create_user(
            realm_name=platform_realm,
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            roles=["customer", "tenant_admin"],
            attributes={
                "tenant_id": [tenant_id],
                "tenant_realm": [tenant_realm],
                "company_name": [company_name],
            },
        )

        return {
            "user": {
                "username": username,
                "user_id": tenant_user_result.get("user_id"),
                "status": tenant_user_result.get("status"),
            },
            "tenant": {
                "tenant_id": tenant_id,
                "name": company_name,
                "slug": tenant_slug,
                "realm": tenant_realm,
            },
            "login_url": f"/api/v1/auth/saml/login?return_to=/{tenant_id}",
        }

    async def invite_tenant_user(
        self,
        tenant_id: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Invite a new user to a tenant.

        This allows tenant admins to add users to their organization.
        Users are created in the tenant's dedicated realm.
        """
        tenant_realm = f"tenant-{tenant_id}"
        username = email.split('@')[0]

        # Default roles for new tenant users
        if roles is None:
            roles = ["tenant_user", "splunk_analyst"]

        user_result = await self.create_user(
            realm_name=tenant_realm,
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            roles=roles,
            attributes={
                "tenant_id": [tenant_id],
            },
        )

        if user_result.get("status") == "exists":
            raise ValueError(f"User with email {email} already exists in this tenant")

        return {
            "user": user_result,
            "tenant_id": tenant_id,
        }

    async def list_tenant_users(self, tenant_id: str) -> list[dict[str, Any]]:
        """
        List all users in a tenant's realm.
        """
        tenant_realm = f"tenant-{tenant_id}"

        response = await self._api_request("GET", f"/{tenant_realm}/users")
        if response.status_code == 200:
            return response.json()
        return []

    async def delete_tenant_user(self, tenant_id: str, user_id: str) -> bool:
        """
        Delete a user from a tenant's realm.
        """
        tenant_realm = f"tenant-{tenant_id}"

        response = await self._api_request("DELETE", f"/{tenant_realm}/users/{user_id}")
        return response.status_code == 204


# Global instance
keycloak_admin = KeycloakAdminService()
