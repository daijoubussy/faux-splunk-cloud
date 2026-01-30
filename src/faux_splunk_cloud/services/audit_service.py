"""
Audit logging service with Splunk HEC integration.

Provides comprehensive audit trails with real-time export to Splunk
for the SIEM-lite portal.
"""

import asyncio
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

import httpx

from faux_splunk_cloud.config import settings
from faux_splunk_cloud.models.audit import (
    AuditAction,
    AuditLog,
    AuditLogList,
    AuditLogQuery,
    ResourceType,
)
from faux_splunk_cloud.models.impersonation import ActorContext

logger = logging.getLogger(__name__)


class SplunkHECHandler(logging.Handler):
    """
    Custom logging handler that sends logs to Splunk HEC.

    Used for both audit logs and general application logs.
    """

    def __init__(
        self,
        hec_url: str,
        hec_token: str,
        index: str = "fsc_audit",
        sourcetype: str = "fsc:audit",
        verify_ssl: bool = False,
    ):
        super().__init__()
        self.hec_url = hec_url
        self.hec_token = hec_token
        self.index = index
        self.sourcetype = sourcetype
        self.verify_ssl = verify_ssl
        self._queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=10000)
        self._client: httpx.AsyncClient | None = None
        self._send_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the async sender."""
        self._client = httpx.AsyncClient(verify=self.verify_ssl, timeout=10.0)
        self._running = True
        self._send_task = asyncio.create_task(self._sender_loop())
        logger.info(f"Splunk HEC handler started: {self.hec_url}")

    async def stop(self) -> None:
        """Stop the async sender and flush remaining logs."""
        self._running = False
        if self._send_task:
            try:
                await asyncio.wait_for(self._queue.join(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for audit queue to drain")

            self._send_task.cancel()
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass

        if self._client:
            await self._client.aclose()

    async def _sender_loop(self) -> None:
        """Background task that sends logs to HEC."""
        batch: list[dict] = []
        batch_timeout = 1.0

        while self._running or not self._queue.empty():
            try:
                try:
                    event = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=batch_timeout
                    )
                    batch.append(event)
                    self._queue.task_done()

                    while len(batch) < 100:
                        try:
                            event = self._queue.get_nowait()
                            batch.append(event)
                            self._queue.task_done()
                        except asyncio.QueueEmpty:
                            break

                except asyncio.TimeoutError:
                    pass

                if batch:
                    await self._send_batch(batch)
                    batch = []

            except asyncio.CancelledError:
                if batch:
                    await self._send_batch(batch)
                raise
            except Exception as e:
                logger.error(f"Error in HEC sender: {e}")
                await asyncio.sleep(1)

    async def _send_batch(self, events: list[dict]) -> None:
        """Send a batch of events to HEC."""
        if not self._client or not events:
            return

        payload = ""
        for event in events:
            timestamp = event.pop("_time", datetime.utcnow().timestamp())
            hec_event = {
                "time": timestamp,
                "index": self.index,
                "sourcetype": self.sourcetype,
                "source": "faux-splunk-cloud",
                "event": event,
            }
            payload += json.dumps(hec_event)

        try:
            response = await self._client.post(
                self.hec_url,
                content=payload,
                headers={
                    "Authorization": f"Splunk {self.hec_token}",
                    "Content-Type": "application/json",
                },
            )
            if response.status_code != 200:
                logger.debug(f"HEC returned {response.status_code}: {response.text}")
        except httpx.ConnectError:
            logger.debug("HEC not available, logs stored locally only")
        except Exception as e:
            logger.debug(f"HEC send error: {e}")

    def queue_event(self, event: dict) -> None:
        """Queue an event for async sending."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Audit queue full, dropping event")


class AuditService:
    """
    Manages audit logging with Splunk HEC integration.

    Features:
    - Full action tracking with before/after changes
    - Impersonation context preservation
    - Real-time export to Splunk HEC
    - In-memory cache for fast recent queries
    - SIEM-lite portal integration via Splunk search
    """

    def __init__(self) -> None:
        self._logs: dict[str, AuditLog] = {}
        self._tenant_index: dict[str, list[str]] = {}
        self._resource_index: dict[str, list[str]] = {}
        self._user_index: dict[str, list[str]] = {}
        self._hec_handler: SplunkHECHandler | None = None
        self._max_memory_logs = 5000

    async def start(self) -> None:
        """Start the audit service with Splunk HEC integration."""
        settings.ensure_data_dir()

        # Setup HEC handler for SIEM integration (use HTTPS for security)
        hec_url = f"https://{settings.siem_host}:8088/services/collector/event"

        self._hec_handler = SplunkHECHandler(
            hec_url=hec_url,
            hec_token="fsc-audit-token",
            index="fsc_audit",
            sourcetype="fsc:audit",
            verify_ssl=settings.siem_verify_ssl,
        )

        await self._hec_handler.start()
        logger.info("Audit service started with Splunk HEC integration")

    async def stop(self) -> None:
        """Stop the audit service and flush pending logs."""
        if self._hec_handler:
            await self._hec_handler.stop()
        logger.info("Audit service stopped")

    def _generate_id(self) -> str:
        """Generate a unique audit log ID."""
        return f"audit-{secrets.token_hex(12)}"

    def _index_log(self, log: AuditLog) -> None:
        """Add log to in-memory indexes with LRU eviction."""
        # Tenant index
        if log.tenant_id not in self._tenant_index:
            self._tenant_index[log.tenant_id] = []
        self._tenant_index[log.tenant_id].append(log.id)

        # Resource index
        if log.resource_id not in self._resource_index:
            self._resource_index[log.resource_id] = []
        self._resource_index[log.resource_id].append(log.id)

        # User index
        if log.actor_user_id not in self._user_index:
            self._user_index[log.actor_user_id] = []
        self._user_index[log.actor_user_id].append(log.id)

        # Evict old logs if over limit
        if len(self._logs) > self._max_memory_logs:
            oldest = sorted(self._logs.values(), key=lambda x: x.timestamp)[:100]
            for old_log in oldest:
                self._logs.pop(old_log.id, None)

    async def log(
        self,
        action: AuditAction,
        resource_type: ResourceType,
        resource_id: str,
        actor: ActorContext,
        tenant_name: str | None = None,
        details: dict[str, Any] | None = None,
        changes: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Logs to both in-memory store and Splunk HEC.
        """
        now = datetime.utcnow()

        log_entry = AuditLog(
            id=self._generate_id(),
            timestamp=now,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_user_id=actor.real_user_id,
            actor_email=actor.real_email,
            impersonated_user_id=actor.effective_user_id if actor.is_impersonating else None,
            impersonated_email=actor.effective_email if actor.is_impersonating else None,
            impersonation_session_id=actor.impersonation_session_id,
            tenant_id=actor.effective_tenant_id,
            tenant_name=tenant_name,
            details=details or {},
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=success,
            error_message=error_message,
        )

        # Store in memory
        self._logs[log_entry.id] = log_entry
        self._index_log(log_entry)

        # Send to Splunk HEC
        if self._hec_handler:
            hec_event = {
                "_time": now.timestamp(),
                "audit_id": log_entry.id,
                "action": log_entry.action.value,
                "resource_type": log_entry.resource_type.value,
                "resource_id": log_entry.resource_id,
                "actor_user_id": log_entry.actor_user_id,
                "actor_email": log_entry.actor_email,
                "tenant_id": log_entry.tenant_id,
                "tenant_name": log_entry.tenant_name,
                "success": log_entry.success,
                "is_impersonation": actor.is_impersonating,
            }

            if actor.is_impersonating:
                hec_event["impersonated_user_id"] = log_entry.impersonated_user_id
                hec_event["impersonated_email"] = log_entry.impersonated_email
                hec_event["impersonation_session_id"] = log_entry.impersonation_session_id

            if log_entry.details:
                hec_event["details"] = json.dumps(log_entry.details)

            if log_entry.changes:
                hec_event["changes"] = json.dumps(log_entry.changes)

            if log_entry.ip_address:
                hec_event["src_ip"] = log_entry.ip_address

            if log_entry.user_agent:
                hec_event["user_agent"] = log_entry.user_agent

            if log_entry.error_message:
                hec_event["error_message"] = log_entry.error_message

            self._hec_handler.queue_event(hec_event)

        # Standard logging
        if success:
            logger.info(
                f"AUDIT: {action.value} on {resource_type.value}/{resource_id} "
                f"by {actor.real_email}"
                + (f" (as {actor.effective_email})" if actor.is_impersonating else "")
            )
        else:
            logger.warning(
                f"AUDIT FAILED: {action.value} on {resource_type.value}/{resource_id} "
                f"by {actor.real_email}: {error_message}"
            )

        return log_entry

    async def query(self, query: AuditLogQuery) -> AuditLogList:
        """
        Query audit logs.

        For recent logs, queries in-memory.
        For historical, should query via SIEM portal (Splunk search).
        """
        if query.resource_id:
            log_ids = self._resource_index.get(query.resource_id, [])
        elif query.tenant_id:
            log_ids = self._tenant_index.get(query.tenant_id, [])
        elif query.actor_user_id:
            log_ids = self._user_index.get(query.actor_user_id, [])
        else:
            log_ids = list(self._logs.keys())

        logs = [self._logs[lid] for lid in log_ids if lid in self._logs]

        if query.resource_type:
            logs = [l for l in logs if l.resource_type == query.resource_type]

        if query.action:
            logs = [l for l in logs if l.action == query.action]

        if query.tenant_id and not query.resource_id:
            logs = [l for l in logs if l.tenant_id == query.tenant_id]

        if query.actor_user_id and not query.resource_id and not query.tenant_id:
            logs = [l for l in logs if l.actor_user_id == query.actor_user_id]

        if not query.include_impersonation:
            logs = [l for l in logs if not l.impersonation_session_id]

        if query.start_time:
            logs = [l for l in logs if l.timestamp >= query.start_time]

        if query.end_time:
            logs = [l for l in logs if l.timestamp <= query.end_time]

        logs.sort(key=lambda l: l.timestamp, reverse=True)
        total = len(logs)
        logs = logs[query.offset : query.offset + query.limit]

        return AuditLogList(
            logs=logs,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )

    async def get_log(self, log_id: str) -> AuditLog | None:
        """Get a specific audit log entry."""
        return self._logs.get(log_id)

    async def get_resource_history(
        self,
        resource_type: ResourceType,
        resource_id: str,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Get audit history for a specific resource."""
        result = await self.query(
            AuditLogQuery(
                resource_id=resource_id,
                resource_type=resource_type,
                limit=limit,
            )
        )
        return result.logs

    async def get_user_activity(
        self,
        user_id: str,
        include_impersonation: bool = True,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit history for a specific user."""
        result = await self.query(
            AuditLogQuery(
                actor_user_id=user_id,
                include_impersonation=include_impersonation,
                limit=limit,
            )
        )
        return result.logs


# Global audit service instance
audit_service = AuditService()
