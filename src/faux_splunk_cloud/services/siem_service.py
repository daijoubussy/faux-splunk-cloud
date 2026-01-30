"""
SIEM service for the admin portal.

Provides search, dashboarding, alerting, and reporting capabilities
using the Splunk Enterprise backend.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import splunklib.client as splunk_client
import splunklib.results as splunk_results

from faux_splunk_cloud.config import settings

logger = logging.getLogger(__name__)


class SearchStatus(str, Enum):
    """Status of a search job."""

    QUEUED = "queued"
    RUNNING = "running"
    FINALIZING = "finalizing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SIEMService:
    """
    SIEM integration service for the admin portal.

    Provides:
    - Ad-hoc search execution
    - Saved search management
    - Dashboard retrieval
    - Alert configuration
    - Reporting
    """

    def __init__(self) -> None:
        self._service: splunk_client.Service | None = None
        self._connected = False

    async def start(self) -> None:
        """Start the SIEM service and connect to Splunk."""
        try:
            await self._connect()
            logger.info("SIEM service started")
        except Exception as e:
            logger.warning(f"SIEM service started without connection: {e}")

    async def stop(self) -> None:
        """Stop the SIEM service."""
        if self._service:
            try:
                self._service.logout()
            except Exception:
                pass
        self._connected = False
        logger.info("SIEM service stopped")

    async def _connect(self) -> None:
        """Connect to the Splunk SIEM backend."""
        try:
            self._service = splunk_client.connect(
                host=settings.siem_host,
                port=settings.siem_port,
                username=settings.siem_username,
                password=settings.siem_password.get_secret_value(),
                scheme="https" if settings.siem_verify_ssl else "http",
            )
            self._connected = True
            logger.info(f"Connected to Splunk SIEM at {settings.siem_host}")
        except Exception as e:
            logger.error(f"Failed to connect to Splunk SIEM: {e}")
            self._connected = False
            raise

    def is_connected(self) -> bool:
        """Check if connected to Splunk."""
        return self._connected and self._service is not None

    async def ensure_connected(self) -> None:
        """Ensure connection to Splunk, reconnecting if needed."""
        if not self.is_connected():
            await self._connect()

    # ==================== Search ====================

    async def search(
        self,
        query: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        max_results: int = 1000,
        timeout_seconds: int = 60,
    ) -> dict[str, Any]:
        """
        Execute a search query and return results.

        Args:
            query: SPL search query
            earliest_time: Start time (e.g., "-24h", "-7d", "2024-01-01T00:00:00")
            latest_time: End time (e.g., "now", "-1h")
            max_results: Maximum number of results
            timeout_seconds: Search timeout

        Returns:
            Dict with results, metadata, and statistics
        """
        await self.ensure_connected()

        # Ensure query starts with 'search' command if not a generating command
        if not query.strip().startswith("|") and not query.strip().lower().startswith("search "):
            query = f"search {query}"

        search_kwargs = {
            "earliest_time": earliest_time,
            "latest_time": latest_time,
            "exec_mode": "blocking",
            "max_count": max_results,
        }

        try:
            job = self._service.jobs.create(query, **search_kwargs)

            # Wait for completion with timeout
            start_time = time.time()
            while not job.is_done():
                if time.time() - start_time > timeout_seconds:
                    job.cancel()
                    raise TimeoutError(f"Search timed out after {timeout_seconds}s")
                await asyncio.sleep(0.5)
                job.refresh()

            # Get results
            results = []
            for result in splunk_results.JSONResultsReader(job.results(output_mode="json")):
                if isinstance(result, dict):
                    results.append(result)

            # Get job stats
            stats = {
                "event_count": int(job["eventCount"]),
                "result_count": int(job["resultCount"]),
                "scan_count": int(job["scanCount"]),
                "run_duration": float(job["runDuration"]),
                "earliest_time": job.get("earliestTime", ""),
                "latest_time": job.get("latestTime", ""),
            }

            return {
                "status": "success",
                "results": results[:max_results],
                "statistics": stats,
                "query": query,
            }

        except TimeoutError:
            raise
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "results": [],
                "query": query,
            }

    async def search_async(
        self,
        query: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
    ) -> str:
        """
        Start an async search and return the job ID.

        Use get_search_status() to check progress and get_search_results() to retrieve results.
        """
        await self.ensure_connected()

        if not query.strip().startswith("|") and not query.strip().lower().startswith("search "):
            query = f"search {query}"

        job = self._service.jobs.create(
            query,
            earliest_time=earliest_time,
            latest_time=latest_time,
            exec_mode="normal",
        )

        return job.sid

    async def get_search_status(self, job_id: str) -> dict[str, Any]:
        """Get the status of an async search job."""
        await self.ensure_connected()

        try:
            job = self._service.jobs[job_id]
            job.refresh()

            return {
                "job_id": job_id,
                "status": SearchStatus.DONE.value if job.is_done() else SearchStatus.RUNNING.value,
                "progress": float(job.get("doneProgress", 0)) * 100,
                "event_count": int(job.get("eventCount", 0)),
                "result_count": int(job.get("resultCount", 0)),
                "is_done": job.is_done(),
            }
        except KeyError:
            return {
                "job_id": job_id,
                "status": SearchStatus.FAILED.value,
                "error": "Job not found",
            }

    async def get_search_results(
        self,
        job_id: str,
        offset: int = 0,
        count: int = 100,
    ) -> dict[str, Any]:
        """Get results from a completed search job."""
        await self.ensure_connected()

        try:
            job = self._service.jobs[job_id]

            if not job.is_done():
                return {
                    "status": "pending",
                    "message": "Search still running",
                }

            results = []
            reader = splunk_results.JSONResultsReader(
                job.results(output_mode="json", offset=offset, count=count)
            )
            for result in reader:
                if isinstance(result, dict):
                    results.append(result)

            return {
                "status": "success",
                "results": results,
                "offset": offset,
                "count": len(results),
                "total": int(job["resultCount"]),
            }

        except KeyError:
            return {"status": "error", "error": "Job not found"}

    async def cancel_search(self, job_id: str) -> bool:
        """Cancel a running search job."""
        await self.ensure_connected()

        try:
            job = self._service.jobs[job_id]
            job.cancel()
            return True
        except Exception:
            return False

    # ==================== Saved Searches ====================

    async def list_saved_searches(self, app: str | None = None) -> list[dict[str, Any]]:
        """List all saved searches."""
        await self.ensure_connected()

        searches = []
        for search in self._service.saved_searches:
            if app and search.access.get("app") != app:
                continue

            searches.append({
                "name": search.name,
                "description": getattr(search, "description", ""),
                "search": getattr(search, "search", ""),
                "is_scheduled": getattr(search, "is_scheduled", False),
                "cron_schedule": getattr(search, "cron_schedule", ""),
                "next_scheduled_time": getattr(search, "next_scheduled_time", ""),
                "app": search.access.get("app", ""),
            })

        return searches

    async def get_saved_search(self, name: str) -> dict[str, Any] | None:
        """Get a specific saved search."""
        await self.ensure_connected()

        try:
            search = self._service.saved_searches[name]
            return {
                "name": search.name,
                "description": getattr(search, "description", ""),
                "search": getattr(search, "search", ""),
                "is_scheduled": getattr(search, "is_scheduled", False),
                "cron_schedule": getattr(search, "cron_schedule", ""),
                "dispatch_earliest_time": getattr(search, "dispatch_earliest_time", "-24h"),
                "dispatch_latest_time": getattr(search, "dispatch_latest_time", "now"),
                "actions": getattr(search, "actions", ""),
            }
        except KeyError:
            return None

    async def run_saved_search(self, name: str) -> str:
        """Run a saved search and return the job ID."""
        await self.ensure_connected()

        search = self._service.saved_searches[name]
        job = search.dispatch()
        return job.sid

    async def create_saved_search(
        self,
        name: str,
        query: str,
        description: str = "",
        cron_schedule: str | None = None,
        earliest_time: str = "-24h",
        latest_time: str = "now",
    ) -> dict[str, Any]:
        """Create a new saved search."""
        await self.ensure_connected()

        kwargs = {
            "search": query,
            "description": description,
            "dispatch.earliest_time": earliest_time,
            "dispatch.latest_time": latest_time,
        }

        if cron_schedule:
            kwargs["cron_schedule"] = cron_schedule
            kwargs["is_scheduled"] = True

        search = self._service.saved_searches.create(name, **kwargs)

        return {
            "name": search.name,
            "created": True,
        }

    # ==================== Dashboards ====================

    async def list_dashboards(self, app: str | None = None) -> list[dict[str, Any]]:
        """List all dashboards."""
        await self.ensure_connected()

        dashboards = []
        for dashboard in self._service.dashboards:
            if app and dashboard.access.get("app") != app:
                continue

            dashboards.append({
                "name": dashboard.name,
                "label": getattr(dashboard, "label", dashboard.name),
                "app": dashboard.access.get("app", ""),
                "is_visible": getattr(dashboard, "isVisible", True),
            })

        return dashboards

    async def get_dashboard(self, name: str) -> dict[str, Any] | None:
        """Get a specific dashboard with its XML definition."""
        await self.ensure_connected()

        try:
            dashboard = self._service.dashboards[name]
            return {
                "name": dashboard.name,
                "label": getattr(dashboard, "label", dashboard.name),
                "content": dashboard.content if hasattr(dashboard, "content") else "",
                "app": dashboard.access.get("app", ""),
            }
        except KeyError:
            return None

    async def create_dashboard(
        self,
        name: str,
        label: str,
        xml_content: str,
    ) -> dict[str, Any]:
        """Create a new dashboard."""
        await self.ensure_connected()

        dashboard = self._service.dashboards.create(
            name,
            eai_data=xml_content,
        )

        return {
            "name": dashboard.name,
            "created": True,
        }

    # ==================== Alerts ====================

    async def list_alerts(self) -> list[dict[str, Any]]:
        """List all triggered alerts."""
        await self.ensure_connected()

        alerts = []
        try:
            fired_alerts = self._service.fired_alerts
            for alert in fired_alerts:
                alerts.append({
                    "name": alert.name,
                    "severity": getattr(alert, "severity", "unknown"),
                    "trigger_time": getattr(alert, "trigger_time", ""),
                    "trigger_actions": getattr(alert, "triggered_alert_count", 0),
                })
        except Exception as e:
            logger.warning(f"Could not list alerts: {e}")

        return alerts

    async def get_alert_history(
        self,
        saved_search_name: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get alert history for a saved search."""
        await self.ensure_connected()

        # Query the triggered alerts index
        query = f"""
        search index=_audit action=alert_fired ss_name="{saved_search_name}"
        | head {limit}
        | table _time, ss_name, trigger_time, severity
        """

        result = await self.search(query, earliest_time="-7d")
        return result.get("results", [])

    # ==================== Reports ====================

    async def list_reports(self) -> list[dict[str, Any]]:
        """List all scheduled reports."""
        await self.ensure_connected()

        reports = []
        for search in self._service.saved_searches:
            # Reports are saved searches that are scheduled
            if getattr(search, "is_scheduled", False):
                reports.append({
                    "name": search.name,
                    "description": getattr(search, "description", ""),
                    "cron_schedule": getattr(search, "cron_schedule", ""),
                    "next_scheduled_time": getattr(search, "next_scheduled_time", ""),
                    "actions": getattr(search, "actions", ""),
                })

        return reports

    # ==================== Quick Queries ====================

    async def get_event_count(
        self,
        index: str = "*",
        earliest_time: str = "-24h",
    ) -> int:
        """Get total event count for an index."""
        result = await self.search(
            f"index={index} | stats count",
            earliest_time=earliest_time,
            max_results=1,
        )
        if result["results"]:
            return int(result["results"][0].get("count", 0))
        return 0

    async def get_top_sources(
        self,
        index: str = "*",
        limit: int = 10,
        earliest_time: str = "-24h",
    ) -> list[dict[str, Any]]:
        """Get top sources by event count."""
        result = await self.search(
            f"index={index} | top limit={limit} source",
            earliest_time=earliest_time,
        )
        return result.get("results", [])

    async def get_top_sourcetypes(
        self,
        index: str = "*",
        limit: int = 10,
        earliest_time: str = "-24h",
    ) -> list[dict[str, Any]]:
        """Get top sourcetypes by event count."""
        result = await self.search(
            f"index={index} | top limit={limit} sourcetype",
            earliest_time=earliest_time,
        )
        return result.get("results", [])

    async def get_timeline(
        self,
        index: str = "*",
        span: str = "1h",
        earliest_time: str = "-24h",
    ) -> list[dict[str, Any]]:
        """Get event timeline for visualization."""
        result = await self.search(
            f"index={index} | timechart span={span} count",
            earliest_time=earliest_time,
        )
        return result.get("results", [])


# Global SIEM service instance
siem_service = SIEMService()
