"""
HashiCorp Boundary integration service for short-lived access.

Automatically creates Boundary targets for ephemeral Splunk instances
and manages just-in-time session access with credential brokering.

Reference: https://www.boundaryproject.io/docs
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

import httpx

from faux_splunk_cloud.config import settings
from faux_splunk_cloud.models.boundary import (
    BoundaryConfig,
    BoundaryConnectResponse,
    BoundaryCredentialLibrary,
    BoundaryCredentialType,
    BoundaryInstanceAccess,
    BoundarySession,
    BoundarySessionList,
    BoundarySessionRequest,
    BoundarySessionStatus,
    BoundaryTarget,
    BoundaryTargetCreate,
    BoundaryTargetList,
    BoundaryTargetType,
)

logger = logging.getLogger(__name__)


class BoundaryService:
    """
    Service for managing short-lived access to Splunk instances via Boundary.

    Provides:
    - Automatic target creation when instances are provisioned
    - Just-in-time session access with configurable TTL
    - Credential brokering for seamless authentication
    - Session tracking and audit integration
    """

    def __init__(self) -> None:
        self._config = BoundaryConfig()
        self._client: httpx.AsyncClient | None = None
        self._token: str | None = None

        # In-memory storage (production would use Boundary's API)
        self._targets: dict[str, BoundaryTarget] = {}
        self._sessions: dict[str, BoundarySession] = {}
        self._instance_targets: dict[str, list[str]] = {}  # instance_id -> [target_ids]
        self._credential_libraries: dict[str, BoundaryCredentialLibrary] = {}

    async def start(self) -> None:
        """Initialize the Boundary service."""
        self._client = httpx.AsyncClient(
            base_url=self._config.cluster_url,
            timeout=30.0,
        )
        logger.info(f"Boundary service started, controller: {self._config.cluster_url}")

    async def stop(self) -> None:
        """Stop the Boundary service."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("Boundary service stopped")

    def _generate_target_id(self) -> str:
        """Generate a unique target ID."""
        return f"ttcp_{secrets.token_hex(16)}"

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"s_{secrets.token_hex(16)}"

    def _get_port_for_target_type(self, target_type: BoundaryTargetType) -> int:
        """Get the default port for a target type."""
        ports = {
            BoundaryTargetType.SPLUNK_WEB: 8000,
            BoundaryTargetType.SPLUNK_API: 8089,
            BoundaryTargetType.SPLUNK_HEC: 8088,
            BoundaryTargetType.SSH: 22,
        }
        return ports.get(target_type, 8000)

    async def create_targets_for_instance(
        self,
        instance_id: str,
        instance_name: str,
        tenant_id: str,
        container_address: str,
        expires_at: datetime,
        target_types: list[BoundaryTargetType] | None = None,
    ) -> list[BoundaryTarget]:
        """
        Create Boundary targets for a new Splunk instance.

        Called automatically when an instance is provisioned.

        Args:
            instance_id: The Splunk instance ID
            instance_name: Instance display name
            tenant_id: Owning tenant
            container_address: Instance container hostname/IP
            expires_at: When the instance expires
            target_types: Types of access to create (defaults to web + API)

        Returns:
            List of created Boundary targets
        """
        if target_types is None:
            target_types = [
                BoundaryTargetType.SPLUNK_WEB,
                BoundaryTargetType.SPLUNK_API,
            ]

        created_targets: list[BoundaryTarget] = []
        now = datetime.utcnow()

        # Calculate session max based on instance TTL
        instance_ttl_seconds = int((expires_at - now).total_seconds())
        # Cap session at 8 hours or instance TTL, whichever is shorter
        session_max_seconds = min(
            instance_ttl_seconds,
            self._config.max_session_ttl_minutes * 60,
        )

        for target_type in target_types:
            port = self._get_port_for_target_type(target_type)

            target = BoundaryTarget(
                id=self._generate_target_id(),
                instance_id=instance_id,
                tenant_id=tenant_id,
                name=f"{instance_name}-{target_type.value}",
                description=f"{target_type.value} access to {instance_name}",
                target_type=target_type,
                address=container_address,
                port=port,
                host_catalog_id=f"hcst_{secrets.token_hex(8)}",
                host_set_id=f"hsst_{secrets.token_hex(8)}",
                credential_library_id=None,  # Will be set if using credential brokering
                expires_at=expires_at,
                session_max_seconds=session_max_seconds,
                created_at=now,
                updated_at=now,
            )

            self._targets[target.id] = target
            created_targets.append(target)

            logger.info(
                f"Created Boundary target {target.id} ({target_type.value}) "
                f"for instance {instance_id}"
            )

        # Index targets by instance
        self._instance_targets[instance_id] = [t.id for t in created_targets]

        return created_targets

    async def delete_targets_for_instance(self, instance_id: str) -> int:
        """
        Delete all Boundary targets for an instance.

        Called when an instance is destroyed.

        Returns:
            Number of targets deleted
        """
        target_ids = self._instance_targets.pop(instance_id, [])
        count = 0

        for target_id in target_ids:
            if target_id in self._targets:
                del self._targets[target_id]
                count += 1

                # Terminate any active sessions
                for session in list(self._sessions.values()):
                    if session.target_id == target_id and session.status == BoundarySessionStatus.ACTIVE:
                        session.status = BoundarySessionStatus.TERMINATED
                        session.terminated_at = datetime.utcnow()

        logger.info(f"Deleted {count} Boundary targets for instance {instance_id}")
        return count

    async def list_targets(
        self,
        tenant_id: str | None = None,
        instance_id: str | None = None,
    ) -> BoundaryTargetList:
        """
        List available Boundary targets.

        Args:
            tenant_id: Filter by tenant
            instance_id: Filter by instance

        Returns:
            List of targets
        """
        targets = list(self._targets.values())

        if tenant_id:
            targets = [t for t in targets if t.tenant_id == tenant_id]

        if instance_id:
            targets = [t for t in targets if t.instance_id == instance_id]

        # Filter out expired targets
        now = datetime.utcnow()
        targets = [t for t in targets if t.expires_at > now]

        return BoundaryTargetList(targets=targets, total=len(targets))

    async def get_target(self, target_id: str) -> BoundaryTarget | None:
        """Get a specific Boundary target."""
        return self._targets.get(target_id)

    async def create_session(
        self,
        request: BoundarySessionRequest,
        user_id: str,
        tenant_id: str,
    ) -> BoundaryConnectResponse:
        """
        Create a new Boundary session for accessing a target.

        This initiates just-in-time access with short-lived credentials.

        Args:
            request: Session request details
            user_id: User requesting access
            tenant_id: User's tenant

        Returns:
            Connection details including endpoint and credentials
        """
        target = self._targets.get(request.target_id)
        if not target:
            raise ValueError(f"Target {request.target_id} not found")

        # Verify target hasn't expired
        now = datetime.utcnow()
        if target.expires_at <= now:
            raise ValueError("Target has expired (instance no longer available)")

        # Calculate session TTL
        if request.ttl_minutes:
            session_seconds = min(
                request.ttl_minutes * 60,
                target.session_max_seconds,
            )
        else:
            session_seconds = min(
                self._config.default_session_ttl_minutes * 60,
                target.session_max_seconds,
            )

        # Ensure session doesn't outlive the target
        max_session_end = target.expires_at
        requested_end = now + timedelta(seconds=session_seconds)
        if requested_end > max_session_end:
            session_seconds = int((max_session_end - now).total_seconds())

        expires_at = now + timedelta(seconds=session_seconds)

        # Generate session
        session = BoundarySession(
            id=self._generate_session_id(),
            target_id=request.target_id,
            user_id=user_id,
            tenant_id=tenant_id,
            status=BoundarySessionStatus.ACTIVE,
            target_type=target.target_type,
            endpoint=f"{self._config.worker_url}:{target.port}",
            created_at=now,
            expires_at=expires_at,
        )

        # Generate authorization token
        auth_token = f"at_{secrets.token_hex(32)}"

        # For credential brokering, generate Splunk credentials
        credentials: dict[str, str] | None = None
        if target.target_type in [BoundaryTargetType.SPLUNK_WEB, BoundaryTargetType.SPLUNK_API]:
            # Generate short-lived Splunk token
            credentials = {
                "type": "splunk_token",
                "token": f"splunk_{secrets.token_hex(32)}",
                "expires_at": expires_at.isoformat(),
            }
            session.credentials = credentials

        self._sessions[session.id] = session

        # Build connect URL for web targets
        connect_url = None
        if target.target_type == BoundaryTargetType.SPLUNK_WEB:
            connect_url = f"https://boundary.localhost/connect/{session.id}"

        # Build CLI command
        cli_command = (
            f"boundary connect -target-id {target.id} "
            f"-token {auth_token}"
        )
        if target.target_type == BoundaryTargetType.SPLUNK_WEB:
            cli_command = f"boundary connect http -target-id {target.id}"
        elif target.target_type == BoundaryTargetType.SPLUNK_API:
            cli_command = f"boundary connect ssh -target-id {target.id} -- -p 8089"

        logger.info(
            f"Created Boundary session {session.id} for user {user_id} "
            f"to target {target.id} (expires: {expires_at})"
        )

        return BoundaryConnectResponse(
            session_id=session.id,
            authorization_token=auth_token,
            endpoint=self._config.worker_url,
            port=target.port,
            expires_at=expires_at,
            connect_url=connect_url,
            credentials=credentials,
            cli_command=cli_command,
        )

    async def terminate_session(self, session_id: str, user_id: str) -> bool:
        """
        Terminate a Boundary session.

        Args:
            session_id: Session to terminate
            user_id: User terminating (must own the session or be admin)

        Returns:
            True if terminated, False if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Verify ownership or admin
        if session.user_id != user_id:
            # TODO: Check for admin role
            raise PermissionError("Cannot terminate another user's session")

        session.status = BoundarySessionStatus.TERMINATED
        session.terminated_at = datetime.utcnow()

        logger.info(f"Terminated Boundary session {session_id}")
        return True

    async def list_sessions(
        self,
        user_id: str | None = None,
        tenant_id: str | None = None,
        target_id: str | None = None,
        status: BoundarySessionStatus | None = None,
        include_expired: bool = False,
    ) -> BoundarySessionList:
        """
        List Boundary sessions with filtering.

        Args:
            user_id: Filter by user
            tenant_id: Filter by tenant
            target_id: Filter by target
            status: Filter by status
            include_expired: Include expired sessions

        Returns:
            List of sessions
        """
        sessions = list(self._sessions.values())

        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]

        if tenant_id:
            sessions = [s for s in sessions if s.tenant_id == tenant_id]

        if target_id:
            sessions = [s for s in sessions if s.target_id == target_id]

        if status:
            sessions = [s for s in sessions if s.status == status]

        if not include_expired:
            now = datetime.utcnow()
            sessions = [s for s in sessions if s.expires_at > now or s.status != BoundarySessionStatus.ACTIVE]

        return BoundarySessionList(sessions=sessions, total=len(sessions))

    async def get_instance_access(
        self,
        instance_id: str,
        user_id: str,
        tenant_id: str,
    ) -> BoundaryInstanceAccess | None:
        """
        Get complete access information for an instance.

        Returns targets, active sessions, and quick-connect URLs.
        """
        target_ids = self._instance_targets.get(instance_id, [])
        if not target_ids:
            return None

        targets = [self._targets[tid] for tid in target_ids if tid in self._targets]
        if not targets:
            return None

        # Get active sessions for this user
        active_sessions = [
            s for s in self._sessions.values()
            if s.user_id == user_id
            and s.target_id in target_ids
            and s.status == BoundarySessionStatus.ACTIVE
            and s.expires_at > datetime.utcnow()
        ]

        # Build quick connect URLs
        web_url = None
        api_endpoint = None

        for session in active_sessions:
            target = self._targets.get(session.target_id)
            if target:
                if target.target_type == BoundaryTargetType.SPLUNK_WEB:
                    web_url = f"https://boundary.localhost/connect/{session.id}"
                elif target.target_type == BoundaryTargetType.SPLUNK_API:
                    api_endpoint = f"https://boundary.localhost/api/{session.id}"

        first_target = targets[0]
        return BoundaryInstanceAccess(
            instance_id=instance_id,
            instance_name=first_target.name.rsplit("-", 1)[0],
            instance_status="running",  # Would get from instance manager
            instance_expires_at=first_target.expires_at,
            targets=targets,
            active_sessions=active_sessions,
            web_url=web_url,
            api_endpoint=api_endpoint,
        )

    async def cleanup_expired(self) -> int:
        """
        Clean up expired targets and sessions.

        Called periodically by the cleanup job.

        Returns:
            Number of items cleaned up
        """
        now = datetime.utcnow()
        count = 0

        # Expire active sessions
        for session in self._sessions.values():
            if session.status == BoundarySessionStatus.ACTIVE and session.expires_at <= now:
                session.status = BoundarySessionStatus.EXPIRED
                count += 1

        # Note: Targets are cleaned up when instances are destroyed

        if count > 0:
            logger.info(f"Boundary cleanup: marked {count} sessions as expired")

        return count


# Global service instance
boundary_service = BoundaryService()
