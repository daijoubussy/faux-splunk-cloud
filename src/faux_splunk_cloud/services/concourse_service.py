"""
Concourse CI integration service.

Provides access to Concourse for managing CI/CD pipelines
and viewing build status.
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ConcourseService:
    """
    Service for interacting with Concourse CI.

    Uses the Concourse API to manage pipelines and builds.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._concourse_url = os.getenv("FSC_CONCOURSE_URL", "http://concourse-web:8080")
        self._token: str | None = None
        self._authenticated = False

    async def start(self) -> None:
        """Initialize the Concourse service."""
        self._client = httpx.AsyncClient(
            base_url=self._concourse_url,
            timeout=30.0,
        )
        logger.info(f"Concourse service started, server: {self._concourse_url}")

    async def stop(self) -> None:
        """Stop the Concourse service."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._token = None
        self._authenticated = False
        logger.info("Concourse service stopped")

    async def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate with Concourse.

        Args:
            username: Concourse username
            password: Concourse password

        Returns:
            True if authentication successful
        """
        if not self._client:
            return False

        try:
            # Get token from sky endpoint
            resp = await self._client.post(
                "/sky/issuer/token",
                data={
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                    "scope": "openid profile email federated:id groups",
                },
                auth=("fly", "Zmx5"),  # fly client credentials
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data.get("access_token")
            self._authenticated = bool(self._token)
            return self._authenticated
        except Exception as e:
            logger.error(f"Failed to authenticate with Concourse: {e}")
            return False

    def _headers(self) -> dict[str, str]:
        """Get request headers with authorization token."""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def is_healthy(self) -> bool:
        """Check if Concourse is healthy and accessible."""
        if not self._client:
            return False

        try:
            resp = await self._client.get("/api/v1/info")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Concourse health check failed: {e}")
            return False

    async def get_info(self) -> dict[str, Any]:
        """Get Concourse server info."""
        if not self._client:
            return {"error": "Concourse service not initialized"}

        try:
            resp = await self._client.get("/api/v1/info")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get Concourse info: {e}")
            return {"error": str(e)}

    async def list_teams(self) -> list[dict[str, Any]]:
        """List all teams."""
        if not self._client:
            return []

        try:
            resp = await self._client.get(
                "/api/v1/teams",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to list teams: {e}")
            return []

    async def list_pipelines(self, team: str = "main") -> list[dict[str, Any]]:
        """
        List pipelines for a team.

        Args:
            team: Team name (default: main)

        Returns:
            List of pipeline info
        """
        if not self._client:
            return []

        try:
            resp = await self._client.get(
                f"/api/v1/teams/{team}/pipelines",
                headers=self._headers(),
            )
            if resp.status_code == 401:
                logger.warning("Not authenticated to list pipelines")
                return []
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to list pipelines: {e}")
            return []

    async def get_pipeline(self, team: str, pipeline: str) -> dict[str, Any] | None:
        """
        Get pipeline details.

        Args:
            team: Team name
            pipeline: Pipeline name

        Returns:
            Pipeline info or None
        """
        if not self._client:
            return None

        try:
            resp = await self._client.get(
                f"/api/v1/teams/{team}/pipelines/{pipeline}",
                headers=self._headers(),
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get pipeline {pipeline}: {e}")
            return None

    async def get_pipeline_config(self, team: str, pipeline: str) -> dict[str, Any] | None:
        """
        Get pipeline configuration (YAML).

        Args:
            team: Team name
            pipeline: Pipeline name

        Returns:
            Pipeline config or None
        """
        if not self._client:
            return None

        try:
            resp = await self._client.get(
                f"/api/v1/teams/{team}/pipelines/{pipeline}/config",
                headers=self._headers(),
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get pipeline config {pipeline}: {e}")
            return None

    async def list_jobs(self, team: str, pipeline: str) -> list[dict[str, Any]]:
        """
        List jobs in a pipeline.

        Args:
            team: Team name
            pipeline: Pipeline name

        Returns:
            List of jobs
        """
        if not self._client:
            return []

        try:
            resp = await self._client.get(
                f"/api/v1/teams/{team}/pipelines/{pipeline}/jobs",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []

    async def list_builds(
        self,
        team: str | None = None,
        pipeline: str | None = None,
        job: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """
        List builds with optional filtering.

        Args:
            team: Filter by team
            pipeline: Filter by pipeline (requires team)
            job: Filter by job (requires team and pipeline)
            limit: Max builds to return

        Returns:
            List of builds
        """
        if not self._client:
            return []

        try:
            if team and pipeline and job:
                url = f"/api/v1/teams/{team}/pipelines/{pipeline}/jobs/{job}/builds"
            elif team and pipeline:
                url = f"/api/v1/teams/{team}/pipelines/{pipeline}/builds"
            else:
                url = "/api/v1/builds"

            resp = await self._client.get(
                url,
                headers=self._headers(),
                params={"limit": limit},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to list builds: {e}")
            return []

    async def get_build(self, build_id: int) -> dict[str, Any] | None:
        """
        Get build details.

        Args:
            build_id: Build ID

        Returns:
            Build info or None
        """
        if not self._client:
            return None

        try:
            resp = await self._client.get(
                f"/api/v1/builds/{build_id}",
                headers=self._headers(),
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get build {build_id}: {e}")
            return None

    async def trigger_job(
        self,
        team: str,
        pipeline: str,
        job: str,
    ) -> dict[str, Any] | None:
        """
        Trigger a job to create a new build.

        Args:
            team: Team name
            pipeline: Pipeline name
            job: Job name

        Returns:
            New build info or None
        """
        if not self._client or not self._authenticated:
            logger.warning("Cannot trigger job: not authenticated")
            return None

        try:
            resp = await self._client.post(
                f"/api/v1/teams/{team}/pipelines/{pipeline}/jobs/{job}/builds",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to trigger job {job}: {e}")
            return None

    async def pause_pipeline(self, team: str, pipeline: str) -> bool:
        """Pause a pipeline."""
        if not self._client or not self._authenticated:
            return False

        try:
            resp = await self._client.put(
                f"/api/v1/teams/{team}/pipelines/{pipeline}/pause",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to pause pipeline {pipeline}: {e}")
            return False

    async def unpause_pipeline(self, team: str, pipeline: str) -> bool:
        """Unpause a pipeline."""
        if not self._client or not self._authenticated:
            return False

        try:
            resp = await self._client.put(
                f"/api/v1/teams/{team}/pipelines/{pipeline}/unpause",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to unpause pipeline {pipeline}: {e}")
            return False

    async def list_workers(self) -> list[dict[str, Any]]:
        """List Concourse workers."""
        if not self._client:
            return []

        try:
            resp = await self._client.get(
                "/api/v1/workers",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to list workers: {e}")
            return []


# Global service instance
concourse_service = ConcourseService()
