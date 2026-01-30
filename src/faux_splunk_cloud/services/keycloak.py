"""
Keycloak SAML authentication service.

Handles SAML authentication flow with Keycloak as the Identity Provider.
Supports tenant-specific IdP federation for multi-tenancy.
"""

import logging
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import httpx
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils
from pydantic import BaseModel

from faux_splunk_cloud.config import settings

logger = logging.getLogger(__name__)

# XML namespaces for SAML metadata parsing
SAML_NAMESPACES = {
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


class SAMLUserData(BaseModel):
    """Parsed SAML assertion user data."""

    name_id: str  # SAML NameID (user identifier)
    session_index: str | None = None
    email: str | None = None
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    groups: list[str] = []
    roles: list[str] = []
    tenant_id: str | None = None  # From SAML attribute
    attributes: dict[str, list[str]] = {}


class SAMLSession(BaseModel):
    """SAML authentication session."""

    session_id: str
    user_data: SAMLUserData
    created_at: datetime
    expires_at: datetime
    tenant_id: str | None = None


class TenantIdPConfig(BaseModel):
    """Tenant-specific Identity Provider configuration."""

    tenant_id: str
    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: str | None = None
    idp_x509_cert: str
    # For Splunk SAML integration
    splunk_saml_enabled: bool = False
    splunk_idp_entity_id: str | None = None
    splunk_idp_sso_url: str | None = None
    splunk_idp_cert: str | None = None


class KeycloakSAMLService:
    """
    Service for SAML authentication with Keycloak.

    Supports:
    - Standard SAML SSO/SLO flows
    - Tenant-specific IdP federation
    - Session management
    - Splunk SAML configuration generation
    - Auto-fetching IdP certificate from Keycloak metadata
    """

    def __init__(self):
        self._sessions: dict[str, SAMLSession] = {}
        self._tenant_idps: dict[str, TenantIdPConfig] = {}
        self._idp_metadata_cache: dict[str, tuple[dict, datetime]] = {}
        self._metadata_cache_ttl = timedelta(hours=1)
        self._idp_cert_cache: dict[str, str] = {}  # Cache for IdP certificates

    @property
    def is_configured(self) -> bool:
        """Check if Keycloak SAML is configured."""
        return bool(settings.keycloak_url)

    def get_idp_metadata_url(self, tenant_id: str | None = None, internal: bool = False) -> str:
        """
        Get the IdP metadata URL (Keycloak or tenant-specific).

        Args:
            tenant_id: Optional tenant ID for tenant-specific IdP
            internal: If True, use internal URL for server-to-server calls
        """
        if tenant_id and tenant_id in self._tenant_idps:
            # Tenant has federated IdP - would return their metadata URL
            pass

        # Default to Keycloak
        if settings.saml_metadata_url and not internal:
            return settings.saml_metadata_url

        # For internal server-to-server calls, use internal URL if available
        if internal and settings.keycloak_internal_url:
            return f"{settings.keycloak_internal_url}/protocol/saml/descriptor"

        # Auto-construct from external Keycloak URL
        base_url = settings.keycloak_url or f"https://localhost/realms/{settings.keycloak_realm}"
        return f"{base_url}/protocol/saml/descriptor"

    def fetch_idp_certificate_sync(self, tenant_id: str | None = None) -> str | None:
        """
        Synchronously fetch IdP certificate from Keycloak's SAML descriptor.

        This is called during SAML request creation to ensure we have the cert.
        Uses caching to avoid repeated network calls.
        """
        cache_key = tenant_id or "_default"

        # Check cache first
        if cache_key in self._idp_cert_cache:
            return self._idp_cert_cache[cache_key]

        # Use internal URL for server-to-server metadata fetch
        metadata_url = self.get_idp_metadata_url(tenant_id, internal=True)

        try:
            # Use synchronous request for simplicity in SAML flow
            with httpx.Client(verify=False, timeout=10.0) as client:
                response = client.get(metadata_url)
                response.raise_for_status()

                # Parse the metadata XML to extract certificate
                cert = self._extract_certificate_from_metadata(response.text)

                if cert:
                    self._idp_cert_cache[cache_key] = cert
                    logger.info(f"Successfully fetched IdP certificate from {metadata_url}")
                    return cert
                else:
                    logger.warning(f"No certificate found in IdP metadata from {metadata_url}")
                    return None

        except httpx.ConnectError as e:
            logger.warning(f"Cannot connect to IdP metadata URL {metadata_url}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch IdP metadata from {metadata_url}: {e}")
            return None

    def _extract_certificate_from_metadata(self, metadata_xml: str) -> str | None:
        """
        Extract X509 certificate from SAML IdP metadata XML.

        The certificate is typically in:
        <md:EntityDescriptor>
          <md:IDPSSODescriptor>
            <md:KeyDescriptor use="signing">
              <ds:KeyInfo>
                <ds:X509Data>
                  <ds:X509Certificate>BASE64_CERT_HERE</ds:X509Certificate>
                </ds:X509Data>
              </ds:KeyInfo>
            </md:KeyDescriptor>
          </md:IDPSSODescriptor>
        </md:EntityDescriptor>
        """
        try:
            root = ET.fromstring(metadata_xml)

            # Try to find the signing certificate in IDPSSODescriptor
            for key_desc in root.findall(".//md:KeyDescriptor", SAML_NAMESPACES):
                use = key_desc.get("use", "signing")
                if use in ("signing", None):  # None means both signing and encryption
                    cert_elem = key_desc.find(".//ds:X509Certificate", SAML_NAMESPACES)
                    if cert_elem is not None and cert_elem.text:
                        # Return the certificate, cleaned up
                        cert = cert_elem.text.strip()
                        # Remove any whitespace/newlines that might be in the XML
                        cert = re.sub(r'\s+', '', cert)
                        return cert

            # Fallback: try without namespace prefix (some IdPs don't use prefixes)
            for cert_elem in root.iter():
                if cert_elem.tag.endswith("X509Certificate") and cert_elem.text:
                    cert = cert_elem.text.strip()
                    cert = re.sub(r'\s+', '', cert)
                    return cert

            return None

        except ET.ParseError as e:
            logger.error(f"Failed to parse IdP metadata XML: {e}")
            return None

    async def fetch_idp_metadata(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Fetch and parse IdP metadata with caching (async version)."""
        cache_key = tenant_id or "_default"

        # Check cache
        if cache_key in self._idp_metadata_cache:
            metadata, cached_at = self._idp_metadata_cache[cache_key]
            if datetime.utcnow() - cached_at < self._metadata_cache_ttl:
                return metadata

        # Use internal URL for server-to-server metadata fetch
        metadata_url = self.get_idp_metadata_url(tenant_id, internal=True)

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(metadata_url, timeout=10.0)
                response.raise_for_status()

                # Parse XML metadata
                metadata = self._parse_idp_metadata_xml(response.text)
                self._idp_metadata_cache[cache_key] = (metadata, datetime.utcnow())

                logger.debug(f"Fetched IdP metadata from {metadata_url}")
                return metadata

        except Exception as e:
            logger.error(f"Failed to fetch IdP metadata: {e}")
            raise

    def _parse_idp_metadata_xml(self, metadata_xml: str) -> dict[str, Any]:
        """Parse SAML IdP metadata XML into a dict with all relevant fields."""
        result = {
            "entity_id": "",
            "sso_url": "",
            "slo_url": "",
            "x509_cert": "",
        }

        try:
            root = ET.fromstring(metadata_xml)

            # Get entity ID
            result["entity_id"] = root.get("entityID", "")

            # Find IDPSSODescriptor
            idp_desc = root.find(".//md:IDPSSODescriptor", SAML_NAMESPACES)
            if idp_desc is not None:
                # Get SSO URL (HTTP-Redirect binding preferred)
                for sso in idp_desc.findall("md:SingleSignOnService", SAML_NAMESPACES):
                    binding = sso.get("Binding", "")
                    if "HTTP-Redirect" in binding:
                        result["sso_url"] = sso.get("Location", "")
                        break
                    elif not result["sso_url"]:
                        result["sso_url"] = sso.get("Location", "")

                # Get SLO URL
                for slo in idp_desc.findall("md:SingleLogoutService", SAML_NAMESPACES):
                    binding = slo.get("Binding", "")
                    if "HTTP-Redirect" in binding:
                        result["slo_url"] = slo.get("Location", "")
                        break
                    elif not result["slo_url"]:
                        result["slo_url"] = slo.get("Location", "")

            # Get certificate
            result["x509_cert"] = self._extract_certificate_from_metadata(metadata_xml) or ""

        except ET.ParseError as e:
            logger.error(f"Failed to parse IdP metadata: {e}")

        return result

    def get_saml_settings(
        self,
        request_data: dict[str, Any],
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Build SAML settings for python3-saml.

        Args:
            request_data: HTTP request data (https, host, script_name, etc.)
            tenant_id: Optional tenant for tenant-specific IdP

        Returns:
            Settings dict for OneLogin_Saml2_Auth
        """
        base_url = f"{request_data.get('https', 'https')}://{request_data.get('http_host', 'localhost')}"

        # Get IdP settings
        idp_settings = self._get_idp_settings(tenant_id)

        # Check if IdP certificate is available
        has_idp_cert = bool(idp_settings.get("x509cert"))

        # If no IdP cert, disable signature verification (development mode)
        # In production, you should configure the IdP certificate
        if not has_idp_cert:
            logger.warning(
                "No IdP certificate configured. Signature verification disabled. "
                "This is insecure - configure IdP certificate for production use."
            )

        return {
            "strict": has_idp_cert,  # Only strict when cert is available
            "debug": settings.debug,
            "sp": {
                "entityId": settings.saml_entity_id,
                "assertionConsumerService": {
                    "url": settings.saml_acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": settings.saml_slo_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "x509cert": self._get_sp_cert(),
                "privateKey": self._get_sp_key(),
            },
            "idp": idp_settings,
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": bool(settings.saml_cert_file),
                "logoutRequestSigned": bool(settings.saml_cert_file),
                "logoutResponseSigned": bool(settings.saml_cert_file),
                "signMetadata": bool(settings.saml_cert_file),
                # Only require signed messages/assertions if we have IdP cert to verify
                "wantMessagesSigned": has_idp_cert,
                "wantAssertionsSigned": has_idp_cert,
                "wantAssertionsEncrypted": False,
                "wantNameIdEncrypted": False,
                "requestedAuthnContext": False,
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
                # Allow duplicate attribute names (Keycloak sends roles in multiple ways)
                "allowRepeatAttributeName": True,
            },
        }

    def _get_idp_settings(self, tenant_id: str | None = None) -> dict[str, Any]:
        """
        Get IdP settings (default Keycloak or tenant-specific).

        Automatically fetches the IdP certificate from Keycloak's SAML metadata
        endpoint if not already cached.
        """
        if tenant_id and tenant_id in self._tenant_idps:
            config = self._tenant_idps[tenant_id]
            return {
                "entityId": config.idp_entity_id,
                "singleSignOnService": {
                    "url": config.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "singleLogoutService": {
                    "url": config.idp_slo_url or config.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": config.idp_x509_cert,
            }

        # Default Keycloak settings
        keycloak_base = settings.keycloak_url or f"https://localhost/realms/{settings.keycloak_realm}"

        # Try to fetch IdP certificate from Keycloak metadata
        idp_cert = self.fetch_idp_certificate_sync(tenant_id)

        return {
            "entityId": keycloak_base,
            "singleSignOnService": {
                "url": f"{keycloak_base}/protocol/saml",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "singleLogoutService": {
                "url": f"{keycloak_base}/protocol/saml",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": idp_cert or "",
        }

    def _get_sp_cert(self) -> str:
        """Get SP certificate content."""
        if settings.saml_cert_file and settings.saml_cert_file.exists():
            return settings.saml_cert_file.read_text()
        return ""

    def _get_sp_key(self) -> str:
        """Get SP private key content."""
        if settings.saml_key_file and settings.saml_key_file.exists():
            return settings.saml_key_file.read_text()
        return ""

    def prepare_request(self, request: Any) -> dict[str, Any]:
        """
        Prepare request data for SAML processing.

        Args:
            request: FastAPI/Starlette request object

        Returns:
            Dict compatible with python3-saml
        """
        # Check X-Forwarded-Proto header for reverse proxy (Traefik) scenarios
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        if forwarded_proto == "https":
            is_https = True
        elif forwarded_proto == "http":
            is_https = False
        else:
            # Fall back to request URL scheme
            is_https = request.url.scheme == "https"

        # Get the host from X-Forwarded-Host or request
        forwarded_host = request.headers.get("x-forwarded-host")
        http_host = forwarded_host or request.url.netloc

        # Determine port
        if is_https:
            server_port = 443
        else:
            server_port = request.url.port or 80

        url_data = {
            "https": "on" if is_https else "off",
            "http_host": http_host,
            "server_port": server_port,
            "script_name": request.url.path,
            "get_data": dict(request.query_params),
            "post_data": {},  # Will be populated for POST requests
        }
        return url_data

    def create_auth_request(
        self,
        request_data: dict[str, Any],
        tenant_id: str | None = None,
        return_to: str | None = None,
    ) -> str:
        """
        Create SAML authentication request and return redirect URL.

        Args:
            request_data: Prepared request data
            tenant_id: Optional tenant for tenant-specific IdP
            return_to: URL to return to after authentication

        Returns:
            SAML SSO redirect URL
        """
        saml_settings = self.get_saml_settings(request_data, tenant_id)
        auth = OneLogin_Saml2_Auth(request_data, saml_settings)

        return auth.login(return_to=return_to)

    def process_response(
        self,
        request_data: dict[str, Any],
        tenant_id: str | None = None,
    ) -> SAMLUserData | None:
        """
        Process SAML response from IdP.

        Args:
            request_data: Request data including POST body
            tenant_id: Optional tenant for tenant-specific IdP

        Returns:
            SAMLUserData if valid, None otherwise
        """
        saml_settings = self.get_saml_settings(request_data, tenant_id)
        auth = OneLogin_Saml2_Auth(request_data, saml_settings)

        auth.process_response()
        errors = auth.get_errors()

        if errors:
            logger.warning(f"SAML response errors: {errors}")
            logger.warning(f"SAML last error reason: {auth.get_last_error_reason()}")
            return None

        if not auth.is_authenticated():
            logger.warning("SAML: User not authenticated")
            return None

        # Extract user data from assertion
        attributes = auth.get_attributes()
        name_id = auth.get_nameid()
        session_index = auth.get_session_index()

        # Map common SAML attributes
        user_data = SAMLUserData(
            name_id=name_id,
            session_index=session_index,
            email=self._get_attribute(attributes, ["email", "mail", "emailAddress"]),
            name=self._get_attribute(attributes, ["displayName", "cn", "name"]),
            given_name=self._get_attribute(attributes, ["givenName", "firstName"]),
            family_name=self._get_attribute(attributes, ["sn", "surname", "lastName"]),
            groups=self._get_attribute_list(attributes, ["groups", "memberOf", "group"]),
            roles=self._get_attribute_list(attributes, ["roles", "role"]),
            tenant_id=self._get_attribute(attributes, ["tenantId", "tenant", "organization"]),
            attributes={k: v if isinstance(v, list) else [v] for k, v in attributes.items()},
        )

        return user_data

    def _get_attribute(
        self,
        attributes: dict[str, Any],
        names: list[str],
    ) -> str | None:
        """Get first matching attribute value."""
        for name in names:
            if name in attributes:
                val = attributes[name]
                if isinstance(val, list) and val:
                    return val[0]
                elif isinstance(val, str):
                    return val
        return None

    def _get_attribute_list(
        self,
        attributes: dict[str, Any],
        names: list[str],
    ) -> list[str]:
        """Get attribute values as list."""
        for name in names:
            if name in attributes:
                val = attributes[name]
                if isinstance(val, list):
                    return val
                elif isinstance(val, str):
                    return [val]
        return []

    def create_session(
        self,
        user_data: SAMLUserData,
        tenant_id: str | None = None,
    ) -> SAMLSession:
        """Create a new SAML session."""
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()

        session = SAMLSession(
            session_id=session_id,
            user_data=user_data,
            created_at=now,
            expires_at=now + timedelta(hours=settings.saml_session_duration_hours),
            tenant_id=tenant_id or user_data.tenant_id,
        )

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> SAMLSession | None:
        """Get a session by ID."""
        session = self._sessions.get(session_id)
        if session and session.expires_at > datetime.utcnow():
            return session

        # Clean up expired session
        if session:
            del self._sessions[session_id]

        return None

    def destroy_session(self, session_id: str) -> None:
        """Destroy a session."""
        self._sessions.pop(session_id, None)

    def create_logout_request(
        self,
        request_data: dict[str, Any],
        session: SAMLSession,
        return_to: str | None = None,
    ) -> str:
        """Create SAML logout request."""
        saml_settings = self.get_saml_settings(request_data, session.tenant_id)
        auth = OneLogin_Saml2_Auth(request_data, saml_settings)

        return auth.logout(
            name_id=session.user_data.name_id,
            session_index=session.user_data.session_index,
            return_to=return_to,
        )

    # =========================================================================
    # Tenant IdP Federation
    # =========================================================================

    def register_tenant_idp(self, config: TenantIdPConfig) -> None:
        """Register a tenant-specific IdP configuration."""
        self._tenant_idps[config.tenant_id] = config
        logger.info(f"Registered IdP for tenant {config.tenant_id}")

    def get_tenant_idp(self, tenant_id: str) -> TenantIdPConfig | None:
        """Get tenant IdP configuration."""
        return self._tenant_idps.get(tenant_id)

    def remove_tenant_idp(self, tenant_id: str) -> None:
        """Remove tenant IdP configuration."""
        self._tenant_idps.pop(tenant_id, None)
        self._idp_metadata_cache.pop(tenant_id, None)

    # =========================================================================
    # Splunk SAML Integration
    # =========================================================================

    def generate_splunk_saml_config(
        self,
        tenant_id: str,
        splunk_base_url: str,
    ) -> dict[str, Any]:
        """
        Generate Splunk SAML configuration for a tenant's instance.

        This allows tenant users to authenticate to their Splunk instances
        using their organization's IdP (federated through Keycloak).

        Args:
            tenant_id: The tenant ID
            splunk_base_url: Base URL of the Splunk instance

        Returns:
            Splunk authentication.conf settings for SAML
        """
        # Get tenant IdP config or use Keycloak
        tenant_config = self._tenant_idps.get(tenant_id)

        if tenant_config and tenant_config.splunk_saml_enabled:
            # Use tenant's IdP directly for Splunk
            idp_entity_id = tenant_config.splunk_idp_entity_id or tenant_config.idp_entity_id
            idp_sso_url = tenant_config.splunk_idp_sso_url or tenant_config.idp_sso_url
            idp_cert = tenant_config.splunk_idp_cert or tenant_config.idp_x509_cert
        else:
            # Use Keycloak as IdP for Splunk
            keycloak_base = settings.keycloak_url or f"https://localhost/realms/{settings.keycloak_realm}"
            idp_entity_id = keycloak_base
            idp_sso_url = f"{keycloak_base}/protocol/saml"
            idp_cert = ""  # Would need to fetch from Keycloak metadata

        # Splunk authentication.conf SAML stanza
        return {
            "authentication": {
                "authType": "SAML",
                "authSettings": "saml_idp",
            },
            "saml_idp": {
                "fqdn": splunk_base_url.replace("https://", "").replace("http://", "").split(":")[0],
                "idpSSOUrl": idp_sso_url,
                "idpSLOUrl": idp_sso_url,  # Often same endpoint
                "idpCertPath": "/opt/splunk/etc/auth/idp_cert.pem",
                "idpCertChainPath": "",
                "entityId": f"{splunk_base_url}/saml/metadata",
                "signAuthnRequest": "true",
                "signedAssertion": "true",
                "attributeQueryUrl": "",
                "attributeQueryTTL": "3600",
                "redirectPort": "0",
                "redirectAfterLogoutToUrl": splunk_base_url,
                "defaultRoleIfMissing": "user",
                "skipAttributeQueryRequestForUsers": "",
                "maxAttributeQueryThreads": "2",
                "maxAttributeQueryQueueSize": "50",
                "attributeQueryRequestTimeout": "10",
                "attributeQuerySoapPassword": "",
                "attributeQuerySoapUsername": "",
                "nameIdFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "ssoBinding": "HTTPPost",
                "sloBinding": "HTTPPost",
                "isIdpLicenseSigned": "false",
                "idpAttributeQueryUrl": "",
                "ecdhCurves": "",
                "sslVersions": "tls1.2",
                "cipherSuite": "",
            },
            # Role mappings
            "roleMap_saml_idp": {
                "admin": "admin;sc_admin",
                "power": "power",
                "user": "user",
            },
            # IdP certificate content (to write to file)
            "_idp_cert": idp_cert,
        }


# Global instance
keycloak_service = KeycloakSAMLService()
