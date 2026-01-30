"""
Impersonation service for admin support access.

Manages impersonation requests, approvals, and active sessions.
"""

import logging
import secrets
from datetime import datetime, timedelta

import yaml

from faux_splunk_cloud.config import settings
from faux_splunk_cloud.models.impersonation import (
    ActorContext,
    ImpersonationRequest,
    ImpersonationRequestCreate,
    ImpersonationRequestStatus,
    ImpersonationSession,
)

logger = logging.getLogger(__name__)


class ImpersonationService:
    """
    Manages impersonation workflow.

    Flow:
    1. Tenant user creates an impersonation request
    2. Tenant admin approves/rejects the request
    3. Platform admin starts an impersonation session using approved request
    4. Session is time-limited and fully audited
    """

    def __init__(self) -> None:
        self._requests: dict[str, ImpersonationRequest] = {}
        self._sessions: dict[str, ImpersonationSession] = {}
        self._tenant_requests_index: dict[str, list[str]] = {}  # tenant_id -> request_ids

    async def start(self) -> None:
        """Start the impersonation service and load existing data."""
        settings.ensure_data_dir()
        await self._load_data()
        logger.info("Impersonation service started")

    async def stop(self) -> None:
        """Stop the impersonation service."""
        logger.info("Impersonation service stopped")

    async def _load_data(self) -> None:
        """Load existing requests and sessions from disk."""
        data_dir = settings.data_dir / "impersonation"
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            return

        # Load requests
        requests_dir = data_dir / "requests"
        if requests_dir.exists():
            for req_file in requests_dir.glob("*.yaml"):
                try:
                    with open(req_file) as f:
                        data = yaml.safe_load(f)
                        if data:
                            request = ImpersonationRequest(**data)
                            self._requests[request.id] = request
                            self._index_request(request)
                except Exception as e:
                    logger.error(f"Failed to load request from {req_file}: {e}")

        # Load active sessions
        sessions_dir = data_dir / "sessions"
        if sessions_dir.exists():
            for sess_file in sessions_dir.glob("*.yaml"):
                try:
                    with open(sess_file) as f:
                        data = yaml.safe_load(f)
                        if data:
                            session = ImpersonationSession(**data)
                            # Only load non-expired, non-ended sessions
                            if session.ended_at is None and session.expires_at > datetime.utcnow():
                                self._sessions[session.id] = session
                except Exception as e:
                    logger.error(f"Failed to load session from {sess_file}: {e}")

    def _index_request(self, request: ImpersonationRequest) -> None:
        """Add request to tenant index."""
        if request.tenant_id not in self._tenant_requests_index:
            self._tenant_requests_index[request.tenant_id] = []
        if request.id not in self._tenant_requests_index[request.tenant_id]:
            self._tenant_requests_index[request.tenant_id].append(request.id)

    async def _save_request(self, request: ImpersonationRequest) -> None:
        """Save request to disk."""
        requests_dir = settings.data_dir / "impersonation" / "requests"
        requests_dir.mkdir(parents=True, exist_ok=True)

        req_file = requests_dir / f"{request.id}.yaml"
        with open(req_file, "w") as f:
            yaml.dump(request.model_dump(mode="json"), f, default_flow_style=False)

    async def _save_session(self, session: ImpersonationSession) -> None:
        """Save session to disk."""
        sessions_dir = settings.data_dir / "impersonation" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        sess_file = sessions_dir / f"{session.id}.yaml"
        with open(sess_file, "w") as f:
            yaml.dump(session.model_dump(mode="json"), f, default_flow_style=False)

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID."""
        return f"{prefix}-{secrets.token_hex(12)}"

    async def create_request(
        self,
        tenant_id: str,
        user_id: str,
        user_email: str,
        data: ImpersonationRequestCreate,
    ) -> ImpersonationRequest:
        """
        Create a new impersonation request.

        Called by a tenant user to request admin support access.
        """
        request = ImpersonationRequest(
            id=self._generate_id("impreq"),
            tenant_id=tenant_id,
            requested_by_user_id=user_id,
            requested_by_email=user_email,
            reason=data.reason,
            duration_hours=data.duration_hours,
            status=ImpersonationRequestStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        self._requests[request.id] = request
        self._index_request(request)
        await self._save_request(request)

        logger.info(f"Created impersonation request {request.id} for tenant {tenant_id}")
        return request

    async def get_request(self, request_id: str) -> ImpersonationRequest | None:
        """Get a request by ID."""
        return self._requests.get(request_id)

    async def list_requests_for_tenant(
        self,
        tenant_id: str,
        status: ImpersonationRequestStatus | None = None,
    ) -> list[ImpersonationRequest]:
        """List all requests for a tenant."""
        request_ids = self._tenant_requests_index.get(tenant_id, [])
        requests = [self._requests[rid] for rid in request_ids if rid in self._requests]

        if status:
            requests = [r for r in requests if r.status == status]

        # Sort by creation date (newest first)
        requests.sort(key=lambda r: r.created_at, reverse=True)
        return requests

    async def approve_request(
        self,
        request_id: str,
        approver_user_id: str,
        approver_email: str,
    ) -> ImpersonationRequest | None:
        """
        Approve an impersonation request.

        Called by a tenant admin.
        """
        request = self._requests.get(request_id)
        if not request:
            return None

        if request.status != ImpersonationRequestStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending")

        now = datetime.utcnow()
        request.status = ImpersonationRequestStatus.APPROVED
        request.approved_by_user_id = approver_user_id
        request.approved_by_email = approver_email
        request.approved_at = now
        request.expires_at = now + timedelta(hours=request.duration_hours)

        self._requests[request_id] = request
        await self._save_request(request)

        logger.info(f"Approved impersonation request {request_id} by {approver_email}")
        return request

    async def reject_request(
        self,
        request_id: str,
        rejector_user_id: str,
        rejector_email: str,
        reason: str,
    ) -> ImpersonationRequest | None:
        """
        Reject an impersonation request.

        Called by a tenant admin.
        """
        request = self._requests.get(request_id)
        if not request:
            return None

        if request.status != ImpersonationRequestStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending")

        request.status = ImpersonationRequestStatus.REJECTED
        request.approved_by_user_id = rejector_user_id
        request.approved_by_email = rejector_email
        request.rejected_reason = reason

        self._requests[request_id] = request
        await self._save_request(request)

        logger.info(f"Rejected impersonation request {request_id} by {rejector_email}")
        return request

    async def start_session(
        self,
        request_id: str,
        admin_user_id: str,
        admin_email: str,
        target_tenant_name: str,
    ) -> ImpersonationSession:
        """
        Start an impersonation session.

        Called by a platform admin using an approved request.
        """
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        if request.status != ImpersonationRequestStatus.APPROVED:
            raise ValueError(f"Request {request_id} is not approved")

        now = datetime.utcnow()
        if request.expires_at and request.expires_at < now:
            request.status = ImpersonationRequestStatus.EXPIRED
            await self._save_request(request)
            raise ValueError(f"Request {request_id} has expired")

        # Mark request as used
        request.status = ImpersonationRequestStatus.USED
        await self._save_request(request)

        # Create session
        session = ImpersonationSession(
            id=self._generate_id("impsess"),
            request_id=request_id,
            admin_user_id=admin_user_id,
            admin_email=admin_email,
            target_user_id=request.requested_by_user_id,
            target_user_email=request.requested_by_email,
            target_tenant_id=request.tenant_id,
            target_tenant_name=target_tenant_name,
            started_at=now,
            expires_at=request.expires_at or (now + timedelta(hours=request.duration_hours)),
        )

        self._sessions[session.id] = session
        await self._save_session(session)

        logger.info(
            f"Started impersonation session {session.id}: "
            f"{admin_email} -> {request.requested_by_email}"
        )
        return session

    async def get_session(self, session_id: str) -> ImpersonationSession | None:
        """Get a session by ID."""
        session = self._sessions.get(session_id)
        if session:
            # Check if expired
            if session.expires_at < datetime.utcnow() and session.ended_at is None:
                session.ended_at = session.expires_at
                session.end_reason = "expired"
                await self._save_session(session)
        return session

    async def validate_session(self, session_id: str) -> ImpersonationSession | None:
        """
        Validate a session is still active.

        Returns the session if valid, None otherwise.
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        if session.ended_at:
            return None

        if session.expires_at < datetime.utcnow():
            session.ended_at = datetime.utcnow()
            session.end_reason = "expired"
            await self._save_session(session)
            return None

        return session

    async def end_session(
        self,
        session_id: str,
        reason: str = "user_ended",
    ) -> ImpersonationSession | None:
        """End an active impersonation session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        if session.ended_at:
            return session

        session.ended_at = datetime.utcnow()
        session.end_reason = reason
        await self._save_session(session)

        logger.info(f"Ended impersonation session {session_id}: {reason}")
        return session

    async def list_active_sessions(
        self,
        admin_user_id: str | None = None,
    ) -> list[ImpersonationSession]:
        """List all active impersonation sessions."""
        now = datetime.utcnow()
        active = []

        for session in self._sessions.values():
            if session.ended_at:
                continue
            if session.expires_at < now:
                # Auto-expire
                session.ended_at = now
                session.end_reason = "expired"
                await self._save_session(session)
                continue

            if admin_user_id and session.admin_user_id != admin_user_id:
                continue

            active.append(session)

        return active

    async def get_actor_context_for_session(
        self,
        session_id: str,
    ) -> ActorContext | None:
        """
        Get the actor context for an impersonation session.

        Returns None if session is invalid.
        """
        session = await self.validate_session(session_id)
        if not session:
            return None

        return ActorContext(
            real_user_id=session.admin_user_id,
            real_email=session.admin_email,
            effective_user_id=session.target_user_id,
            effective_email=session.target_user_email,
            effective_tenant_id=session.target_tenant_id,
            is_impersonating=True,
            impersonation_session_id=session.id,
            permissions=[],  # Will be populated by caller
            roles=[],
        )


# Global impersonation service instance
impersonation_service = ImpersonationService()
