"""
Splunk client service using the official Splunk SDK.

This service provides a wrapper around the official splunk-sdk-python
to interact with Splunk instances for:
- Index management
- HEC token management
- App management
- Search execution
- Health checks

Reference: https://github.com/splunk/splunk-sdk-python
"""

import logging
import ssl
from typing import Any

import splunklib.client as splunk_client
import splunklib.results as splunk_results
from splunklib.binding import HTTPError

from faux_splunk_cloud.models.acs import (
    ACSApp,
    ACSHECToken,
    ACSIndex,
    AppStatus,
    IndexDatatype,
)

logger = logging.getLogger(__name__)


class SplunkClientService:
    """
    Service for interacting with Splunk instances via the official SDK.

    Uses the splunk-sdk-python for all operations to ensure compatibility
    with Splunk Cloud Victoria Experience.

    Optimized for ARM64 emulation with extended timeouts and retry logic.
    """

    def __init__(
        self,
        host: str,
        port: int = 8089,
        username: str = "admin",
        password: str | None = None,
        token: str | None = None,
        verify_ssl: bool = False,
        timeout: int = 60,
    ) -> None:
        """
        Initialize the Splunk client service.

        Args:
            host: Splunk host address
            port: Splunkd management port (default 8089)
            username: Admin username
            password: Admin password
            token: Authentication token (alternative to password)
            verify_ssl: Whether to verify SSL certificates
            timeout: Connection timeout in seconds (default 60 for emulation)
        """
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._token = token
        self._verify_ssl = verify_ssl
        self._timeout = timeout
        self._service: splunk_client.Service | None = None

    def is_connected(self) -> bool:
        """Check if client is connected and session is valid."""
        if self._service is None:
            return False
        try:
            # Try a lightweight operation to verify connection
            _ = self._service.info
            return True
        except Exception:
            return False

    def connect(self) -> None:
        """Establish connection to Splunk (or reconnect if disconnected)."""
        self._service = None  # Reset to force reconnection
        self._get_service()

    def _get_service(self) -> splunk_client.Service:
        """Get or create the Splunk service connection."""
        if self._service is None:
            connect_args: dict[str, Any] = {
                "host": self._host,
                "port": self._port,
                "username": self._username,
                "timeout": self._timeout,
            }

            if self._token:
                connect_args["splunkToken"] = self._token
            elif self._password:
                connect_args["password"] = self._password

            # Handle SSL verification
            if not self._verify_ssl:
                # Disable SSL verification for self-signed certs in dev
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            try:
                self._service = splunk_client.connect(**connect_args)
                logger.debug(f"Connected to Splunk at {self._host}:{self._port}")
            except Exception as e:
                logger.error(f"Failed to connect to Splunk at {self._host}:{self._port}: {e}")
                raise

        return self._service

    async def check_health(self) -> bool:
        """Check if the Splunk instance is healthy."""
        try:
            service = self._get_service()
            # Check server info endpoint
            info = service.info
            return info is not None and info.get("version") is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def get_server_info(self) -> dict[str, Any]:
        """Get Splunk server information."""
        try:
            service = self._get_service()
            info = service.info
            return {
                "version": info.get("version"),
                "build": info.get("build"),
                "serverName": info.get("serverName"),
                "os_name": info.get("os_name"),
                "cpu_arch": info.get("cpu_arch"),
                "license_state": info.get("licenseState"),
            }
        except Exception as e:
            logger.error(f"Failed to get server info: {e}")
            raise

    # =========================================================================
    # Index Management (ACS API compatible)
    # =========================================================================

    async def list_indexes(self) -> list[ACSIndex]:
        """List all indexes in ACS API format."""
        try:
            service = self._get_service()
            indexes = []

            for index in service.indexes:
                # Skip internal indexes for ACS compatibility
                if index.name.startswith("_") and index.name != "_internal":
                    continue

                indexes.append(
                    ACSIndex(
                        name=index.name,
                        datatype=IndexDatatype.METRIC
                        if index.get("datatype") == "metric"
                        else IndexDatatype.EVENT,
                        searchableDays=int(
                            index.get("frozenTimePeriodInSecs", 7776000) / 86400
                        ),
                        maxDataSizeMB=int(index.get("maxTotalDataSizeMB", 500000)),
                        totalEventCount=int(index.get("totalEventCount", 0)),
                        totalRawSizeMB=int(
                            float(index.get("currentDBSizeMB", 0))
                        ),
                        frozenTimePeriodInSecs=int(
                            index.get("frozenTimePeriodInSecs", 7776000)
                        ),
                    )
                )

            return indexes
        except Exception as e:
            logger.error(f"Failed to list indexes: {e}")
            raise

    async def create_index(
        self,
        name: str,
        datatype: IndexDatatype = IndexDatatype.EVENT,
        searchable_days: int = 90,
        max_data_size_mb: int = 500000,
    ) -> ACSIndex:
        """Create a new index."""
        try:
            service = self._get_service()

            # Calculate frozenTimePeriodInSecs from searchable_days
            frozen_time = searchable_days * 86400

            index = service.indexes.create(
                name,
                datatype=datatype.value,
                frozenTimePeriodInSecs=frozen_time,
                maxTotalDataSizeMB=max_data_size_mb,
            )

            return ACSIndex(
                name=index.name,
                datatype=datatype,
                searchableDays=searchable_days,
                maxDataSizeMB=max_data_size_mb,
                frozenTimePeriodInSecs=frozen_time,
            )
        except HTTPError as e:
            logger.error(f"Failed to create index {name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create index {name}: {e}")
            raise

    async def delete_index(self, name: str) -> None:
        """Delete an index."""
        try:
            service = self._get_service()
            index = service.indexes[name]
            index.delete()
        except KeyError:
            raise ValueError(f"Index {name} not found")
        except Exception as e:
            logger.error(f"Failed to delete index {name}: {e}")
            raise

    async def get_index(self, name: str) -> ACSIndex:
        """Get a specific index."""
        try:
            service = self._get_service()
            index = service.indexes[name]

            return ACSIndex(
                name=index.name,
                datatype=IndexDatatype.METRIC
                if index.get("datatype") == "metric"
                else IndexDatatype.EVENT,
                searchableDays=int(
                    index.get("frozenTimePeriodInSecs", 7776000) / 86400
                ),
                maxDataSizeMB=int(index.get("maxTotalDataSizeMB", 500000)),
                totalEventCount=int(index.get("totalEventCount", 0)),
                totalRawSizeMB=int(float(index.get("currentDBSizeMB", 0))),
                frozenTimePeriodInSecs=int(
                    index.get("frozenTimePeriodInSecs", 7776000)
                ),
            )
        except KeyError:
            raise ValueError(f"Index {name} not found")
        except Exception as e:
            logger.error(f"Failed to get index {name}: {e}")
            raise

    # =========================================================================
    # HEC Token Management (ACS API compatible)
    # =========================================================================

    async def list_hec_tokens(self) -> list[ACSHECToken]:
        """List all HEC tokens in ACS API format."""
        try:
            service = self._get_service()
            tokens = []

            # Access HEC inputs via REST endpoint
            response = service.get("data/inputs/http")
            feed = splunk_results.JSONResultsReader(response.body)

            for result in feed:
                if isinstance(result, dict):
                    token_name = result.get("name", "").replace("http://", "")
                    tokens.append(
                        ACSHECToken(
                            name=token_name,
                            token=result.get("token", ""),
                            defaultIndex=result.get("index", "main"),
                            defaultSource=result.get("source"),
                            defaultSourcetype=result.get("sourcetype"),
                            indexes=result.get("indexes", "main").split(","),
                            disabled=result.get("disabled", "0") == "1",
                            useACK=result.get("useACK", "0") == "1",
                        )
                    )

            return tokens
        except Exception as e:
            logger.error(f"Failed to list HEC tokens: {e}")
            # Return empty list if HEC is not configured
            return []

    async def create_hec_token(
        self,
        name: str,
        default_index: str = "main",
        indexes: list[str] | None = None,
        default_sourcetype: str | None = None,
        use_ack: bool = False,
    ) -> ACSHECToken:
        """Create a new HEC token."""
        try:
            service = self._get_service()

            # Create HEC input
            params: dict[str, Any] = {
                "name": name,
                "index": default_index,
            }

            if indexes:
                params["indexes"] = ",".join(indexes)
            if default_sourcetype:
                params["sourcetype"] = default_sourcetype
            if use_ack:
                params["useACK"] = "1"

            response = service.post("data/inputs/http", **params)

            # Parse response to get the generated token
            # The token is returned in the response
            import xml.etree.ElementTree as ET

            root = ET.fromstring(response.body.read())
            token_value = ""
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                content = entry.find("{http://www.w3.org/2005/Atom}content")
                if content is not None:
                    dict_elem = content.find(
                        "{http://dev.splunk.com/ns/rest}dict"
                    )
                    if dict_elem is not None:
                        for key in dict_elem.findall(
                            "{http://dev.splunk.com/ns/rest}key"
                        ):
                            if key.get("name") == "token":
                                token_value = key.text or ""
                                break

            return ACSHECToken(
                name=name,
                token=token_value,
                defaultIndex=default_index,
                defaultSourcetype=default_sourcetype,
                indexes=indexes or [default_index],
                useACK=use_ack,
            )
        except Exception as e:
            logger.error(f"Failed to create HEC token {name}: {e}")
            raise

    async def delete_hec_token(self, name: str) -> None:
        """Delete a HEC token."""
        try:
            service = self._get_service()
            service.delete(f"data/inputs/http/{name}")
        except Exception as e:
            logger.error(f"Failed to delete HEC token {name}: {e}")
            raise

    # =========================================================================
    # App Management (ACS API compatible for Victoria Experience)
    # =========================================================================

    async def list_apps(self) -> list[ACSApp]:
        """List all installed apps in ACS API format."""
        try:
            service = self._get_service()
            apps = []

            for app in service.apps:
                apps.append(
                    ACSApp(
                        appId=app.name,
                        label=app.get("label", app.name),
                        version=app.get("version", "unknown"),
                        status=AppStatus.INSTALLED,
                        visible=app.get("visible", "true") == "true",
                        configured=app.get("configured", "false") == "true",
                    )
                )

            return apps
        except Exception as e:
            logger.error(f"Failed to list apps: {e}")
            raise

    async def install_app(self, app_path: str) -> ACSApp:
        """
        Install an app from a local path or URL.

        In Victoria Experience, apps are automatically installed
        on all search heads.
        """
        try:
            service = self._get_service()

            # Install the app
            service.post(
                "apps/local",
                name=app_path,
                update="true",
            )

            # Get app info after installation
            # Extract app name from path
            import os

            app_name = os.path.basename(app_path).replace(".tgz", "").replace(".tar.gz", "")

            return ACSApp(
                appId=app_name,
                label=app_name,
                version="installed",
                status=AppStatus.INSTALLED,
            )
        except Exception as e:
            logger.error(f"Failed to install app {app_path}: {e}")
            raise

    # =========================================================================
    # Search Operations
    # =========================================================================

    async def run_search(
        self,
        query: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        max_results: int = 1000,
    ) -> list[dict[str, Any]]:
        """Run a search and return results."""
        try:
            service = self._get_service()

            # Create a search job
            job = service.jobs.create(
                query,
                earliest_time=earliest_time,
                latest_time=latest_time,
            )

            # Wait for the job to complete
            while not job.is_done():
                import time

                time.sleep(0.5)

            # Get results
            results = []
            result_stream = job.results(count=max_results, output_mode="json")

            import json

            result_data = json.loads(result_stream.read())
            if "results" in result_data:
                results = result_data["results"]

            job.cancel()
            return results
        except Exception as e:
            logger.error(f"Failed to run search: {e}")
            raise

    # =========================================================================
    # User and Role Management
    # =========================================================================

    async def list_users(self) -> list[dict[str, Any]]:
        """List all users."""
        try:
            service = self._get_service()
            users = []

            for user in service.users:
                users.append(
                    {
                        "name": user.name,
                        "realname": user.get("realname", ""),
                        "email": user.get("email", ""),
                        "roles": user.get("roles", []),
                        "defaultApp": user.get("defaultApp", "search"),
                    }
                )

            return users
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            raise

    async def create_user(
        self,
        username: str,
        password: str,
        roles: list[str] | None = None,
        email: str | None = None,
        realname: str | None = None,
    ) -> dict[str, Any]:
        """Create a new user."""
        try:
            service = self._get_service()

            params: dict[str, Any] = {
                "name": username,
                "password": password,
                "roles": roles or ["user"],
            }

            if email:
                params["email"] = email
            if realname:
                params["realname"] = realname

            user = service.users.create(**params)

            return {
                "name": user.name,
                "realname": user.get("realname", ""),
                "email": user.get("email", ""),
                "roles": user.get("roles", []),
            }
        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from Splunk."""
        if self._service:
            self._service.logout()
            self._service = None
