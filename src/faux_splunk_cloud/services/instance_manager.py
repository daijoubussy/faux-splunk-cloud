"""
Instance lifecycle manager for ephemeral Splunk instances.

Manages the complete lifecycle of ephemeral Splunk Cloud Victoria instances:
- Creation with default.yml configuration
- Starting and stopping
- Health monitoring
- Automatic cleanup on TTL expiration
- Integration with Docker/Kubernetes orchestration
"""

import asyncio
import logging
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

from faux_splunk_cloud.config import SplunkVictoriaDefaults, settings
from faux_splunk_cloud.models.acs import ACSHECToken, ACSIndex, IndexDatatype
from faux_splunk_cloud.models.instance import (
    Instance,
    InstanceConfig,
    InstanceCreate,
    InstanceCredentials,
    InstanceEndpoints,
    InstanceStatus,
    InstanceTopology,
)
from faux_splunk_cloud.services.auth import auth_service
from faux_splunk_cloud.services.docker_orchestrator import DockerOrchestrator
from faux_splunk_cloud.services.splunk_client import SplunkClientService

logger = logging.getLogger(__name__)


class InstanceManager:
    """
    Manages the lifecycle of ephemeral Splunk instances.

    Provides:
    - Instance creation with Victoria Experience defaults
    - Configuration via default.yml (CI/CD pattern)
    - Health monitoring and status tracking
    - Automatic TTL-based cleanup
    - Integration with Splunk SDK for runtime operations
    """

    def __init__(self) -> None:
        self._orchestrator = DockerOrchestrator()
        self._instances: dict[str, Instance] = {}
        self._clients: dict[str, SplunkClientService] = {}
        self._template_env = Environment(
            loader=FileSystemLoader(
                Path(__file__).parent.parent / "templates"
            ),
            autoescape=False,
        )
        self._cleanup_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the instance manager and background tasks."""
        # Ensure data directory exists
        settings.ensure_data_dir()

        # Load existing instances from disk
        await self._load_instances()

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Instance manager started")

    async def stop(self) -> None:
        """Stop the instance manager and cleanup tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Disconnect all Splunk clients
        for client in self._clients.values():
            client.disconnect()

        logger.info("Instance manager stopped")

    async def _load_instances(self) -> None:
        """Load existing instances from disk."""
        instances_dir = settings.data_dir / "instances"
        if not instances_dir.exists():
            return

        for instance_dir in instances_dir.iterdir():
            if instance_dir.is_dir():
                state_file = instance_dir / "state.yaml"
                if state_file.exists():
                    try:
                        with open(state_file) as f:
                            data = yaml.safe_load(f)
                            instance = Instance(**data)
                            self._instances[instance.id] = instance
                            logger.info(f"Loaded instance {instance.id}")
                    except Exception as e:
                        logger.error(f"Failed to load instance from {state_file}: {e}")

    async def _save_instance(self, instance: Instance) -> None:
        """Save instance state to disk."""
        instance_dir = settings.data_dir / "instances" / instance.id
        instance_dir.mkdir(parents=True, exist_ok=True)

        state_file = instance_dir / "state.yaml"
        with open(state_file, "w") as f:
            yaml.dump(instance.model_dump(mode="json"), f, default_flow_style=False)

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup expired instances."""
        while True:
            try:
                await asyncio.sleep(settings.cleanup_interval_minutes * 60)
                await self._cleanup_expired_instances()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    async def _cleanup_expired_instances(self) -> None:
        """Remove instances that have exceeded their TTL."""
        now = datetime.utcnow()
        expired = [
            instance
            for instance in self._instances.values()
            if instance.expires_at < now and instance.status != InstanceStatus.TERMINATED
        ]

        for instance in expired:
            logger.info(f"Cleaning up expired instance {instance.id}")
            await self.destroy_instance(instance.id)

    def _generate_instance_id(self) -> str:
        """Generate a unique instance ID."""
        return f"fsc-{secrets.token_hex(8)}"

    def _generate_default_indexes(self) -> list[dict[str, Any]]:
        """Generate default indexes for Victoria Experience."""
        defaults = SplunkVictoriaDefaults.DEFAULT_INDEX_SETTINGS
        indexes = []

        for name in SplunkVictoriaDefaults.DEFAULT_INDEXES:
            if name.startswith("_"):
                continue  # Internal indexes are created automatically
            indexes.append(
                {
                    "name": name,
                    "datatype": "event",
                    "maxTotalDataSizeMB": defaults["maxTotalDataSizeMB"],
                    "frozenTimePeriodInSecs": defaults["frozenTimePeriodInSecs"],
                }
            )

        return indexes

    def _generate_default_hec_token(self) -> dict[str, Any]:
        """Generate a default HEC token for the instance."""
        return {
            "name": "default",
            "token": secrets.token_hex(32),
            "defaultIndex": "main",
            "indexes": ["main", "summary"],
            "disabled": False,
            "useACK": False,
        }

    async def _generate_defaults_yaml(
        self,
        instance: Instance,
        admin_password: str,
        hec_token: str,
    ) -> str:
        """
        Generate the default.yml configuration for a Splunk instance.

        This follows the Splunk docker project pattern of using default.yml
        for all configuration instead of environment variables.
        """
        config = instance.config
        topology = config.topology

        # Select template based on topology
        if topology == InstanceTopology.STANDALONE:
            template = self._template_env.get_template("defaults/victoria-standalone.yml.j2")
        else:
            template = self._template_env.get_template("defaults/victoria-distributed.yml.j2")

        # Generate default indexes if requested
        indexes = self._generate_default_indexes() if config.create_default_indexes else []

        # Build template context
        context = {
            "instance_id": instance.id,
            "hostname": f"{instance.id}-splunk",
            "admin_password": admin_password,
            "experience": config.experience,
            "enable_hec": config.enable_hec,
            "enable_realtime_search": config.enable_realtime_search,
            "indexes": indexes,
            "hec_tokens": [
                {
                    "name": "default",
                    "token": hec_token,
                    "defaultIndex": "main",
                    "indexes": ["main", "summary"],
                    "disabled": False,
                    "useACK": False,
                }
            ]
            if config.enable_hec
            else [],
            "max_mem_usage_mb": config.memory_mb,
            "max_result_rows": 50000,
            "preinstall_apps": config.preinstall_apps,
            "post_start_commands": [],
            "cluster_secret": secrets.token_hex(16),
        }

        # Add distributed-specific settings
        if topology != InstanceTopology.STANDALONE:
            context.update(
                {
                    "role": "standalone",  # Will be overridden per component
                    "replication_factor": config.replication_factor,
                    "search_factor": config.search_factor,
                }
            )

        return template.render(**context)

    async def create_instance(self, request: InstanceCreate) -> Instance:
        """
        Create a new ephemeral Splunk instance.

        Args:
            request: Instance creation request

        Returns:
            The created instance
        """
        instance_id = self._generate_instance_id()
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=request.ttl_hours)

        # Create instance model
        instance = Instance(
            id=instance_id,
            name=request.name,
            status=InstanceStatus.PENDING,
            config=request.config,
            created_at=now,
            expires_at=expires_at,
            labels=request.labels,
        )

        # Generate credentials
        admin_password = secrets.token_urlsafe(16)
        hec_token = secrets.token_hex(32)

        # Generate default.yml configuration
        defaults_yaml = await self._generate_defaults_yaml(
            instance, admin_password, hec_token
        )

        # Create instance directory structure
        instance_dir = settings.data_dir / "instances" / instance_id
        instance_dir.mkdir(parents=True, exist_ok=True)

        defaults_dir = instance_dir / "defaults"
        defaults_dir.mkdir(exist_ok=True)

        # Write default.yml
        defaults_file = defaults_dir / "default.yml"
        defaults_file.write_text(defaults_yaml)

        # Generate and write docker-compose.yml
        instance.status = InstanceStatus.PROVISIONING
        instance, _ = await self._orchestrator.create_instance_resources(instance)

        # Update compose file to mount defaults
        compose_file = instance_dir / "docker-compose.yml"
        if compose_file.exists():
            compose_content = compose_file.read_text()
            # Update defaults path in compose file
            compose_content = compose_content.replace(
                "{{ defaults_path }}", str(defaults_dir)
            )
            compose_file.write_text(compose_content)

        # Generate ACS token
        acs_token = auth_service.create_acs_token(
            instance_id=instance_id,
            username="admin",
        )

        # Set credentials
        instance.credentials = InstanceCredentials(
            admin_username="admin",
            admin_password=admin_password,
            acs_token=acs_token,
            hec_token=hec_token if request.config.enable_hec else None,
        )

        # Store instance
        self._instances[instance_id] = instance
        await self._save_instance(instance)

        logger.info(f"Created instance {instance_id} with topology {request.config.topology}")
        return instance

    async def start_instance(self, instance_id: str) -> Instance:
        """Start an instance."""
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        if instance.status not in [
            InstanceStatus.PENDING,
            InstanceStatus.PROVISIONING,
            InstanceStatus.STOPPED,
        ]:
            raise ValueError(f"Instance {instance_id} cannot be started from status {instance.status}")

        instance = await self._orchestrator.start_instance(instance)
        instance.started_at = datetime.utcnow()

        self._instances[instance_id] = instance
        await self._save_instance(instance)

        logger.info(f"Started instance {instance_id}")
        return instance

    async def stop_instance(self, instance_id: str) -> Instance:
        """Stop an instance."""
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        instance = await self._orchestrator.stop_instance(instance)

        # Disconnect Splunk client
        if instance_id in self._clients:
            self._clients[instance_id].disconnect()
            del self._clients[instance_id]

        self._instances[instance_id] = instance
        await self._save_instance(instance)

        logger.info(f"Stopped instance {instance_id}")
        return instance

    async def destroy_instance(self, instance_id: str) -> None:
        """Destroy an instance and all its resources."""
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        # Stop and destroy Docker resources
        await self._orchestrator.destroy_instance(instance)

        # Disconnect Splunk client
        if instance_id in self._clients:
            self._clients[instance_id].disconnect()
            del self._clients[instance_id]

        # Mark as terminated
        instance.status = InstanceStatus.TERMINATED
        await self._save_instance(instance)

        # Remove from active instances
        del self._instances[instance_id]

        logger.info(f"Destroyed instance {instance_id}")

    async def get_instance(self, instance_id: str) -> Instance | None:
        """Get an instance by ID."""
        return self._instances.get(instance_id)

    async def list_instances(
        self,
        status: InstanceStatus | None = None,
        labels: dict[str, str] | None = None,
    ) -> list[Instance]:
        """List instances with optional filtering."""
        instances = list(self._instances.values())

        if status:
            instances = [i for i in instances if i.status == status]

        if labels:
            instances = [
                i
                for i in instances
                if all(i.labels.get(k) == v for k, v in labels.items())
            ]

        return instances

    async def get_instance_health(self, instance_id: str) -> InstanceStatus:
        """Check and update instance health status."""
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        new_status = await self._orchestrator.check_instance_health(instance)

        if new_status != instance.status:
            instance.status = new_status
            self._instances[instance_id] = instance
            await self._save_instance(instance)

        return new_status

    async def wait_for_ready(
        self, instance_id: str, timeout_seconds: int = 300
    ) -> Instance:
        """Wait for an instance to become ready."""
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        start_time = datetime.utcnow()
        while (datetime.utcnow() - start_time).total_seconds() < timeout_seconds:
            status = await self.get_instance_health(instance_id)
            if status == InstanceStatus.RUNNING:
                return self._instances[instance_id]
            elif status == InstanceStatus.ERROR:
                raise RuntimeError(f"Instance {instance_id} failed to start")
            await asyncio.sleep(5)

        raise TimeoutError(f"Instance {instance_id} did not become ready within {timeout_seconds}s")

    def get_splunk_client(self, instance_id: str) -> SplunkClientService:
        """Get a Splunk SDK client for an instance."""
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        if instance.status != InstanceStatus.RUNNING:
            raise ValueError(f"Instance {instance_id} is not running")

        if instance_id not in self._clients:
            if not instance.endpoints.api_url or not instance.credentials:
                raise ValueError(f"Instance {instance_id} endpoints not available")

            # Parse host and port from API URL
            import urllib.parse

            parsed = urllib.parse.urlparse(instance.endpoints.api_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 8089

            self._clients[instance_id] = SplunkClientService(
                host=host,
                port=port,
                username="admin",
                password=instance.credentials.admin_password,
                verify_ssl=False,
            )

        return self._clients[instance_id]

    async def get_instance_logs(
        self, instance_id: str, container: str | None = None, tail: int = 100
    ) -> str:
        """Get logs from an instance's containers."""
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        return await self._orchestrator.get_container_logs(instance, container, tail)

    async def extend_ttl(self, instance_id: str, hours: int) -> Instance:
        """Extend an instance's TTL."""
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        new_expires = instance.expires_at + timedelta(hours=hours)
        max_expires = datetime.utcnow() + timedelta(hours=settings.max_ttl_hours)

        if new_expires > max_expires:
            new_expires = max_expires

        instance.expires_at = new_expires
        self._instances[instance_id] = instance
        await self._save_instance(instance)

        logger.info(f"Extended TTL for instance {instance_id} to {new_expires}")
        return instance


# Global instance manager
instance_manager = InstanceManager()
