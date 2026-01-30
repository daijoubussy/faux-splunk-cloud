"""
Docker orchestration service for ephemeral Splunk instances.

This service manages the lifecycle of Docker containers that make up
each ephemeral Splunk Cloud Victoria instance.
"""

import asyncio
import logging
import secrets
from pathlib import Path
from typing import Any

import docker
import yaml
from docker.errors import APIError, NotFound
from jinja2 import Environment, FileSystemLoader

from faux_splunk_cloud.config import settings
from faux_splunk_cloud.models.instance import (
    Instance,
    InstanceConfig,
    InstanceCredentials,
    InstanceEndpoints,
    InstanceStatus,
    InstanceTopology,
)

logger = logging.getLogger(__name__)


class DockerOrchestrator:
    """
    Orchestrates Docker resources for Splunk instances.

    Manages:
    - Docker networks
    - Docker volumes
    - Docker containers (via docker-compose)
    - Port allocation
    """

    # Port ranges for instance allocation
    WEB_PORT_START = 18000
    API_PORT_START = 18089
    HEC_PORT_START = 18088
    S2S_PORT_START = 19997

    def __init__(self) -> None:
        self._client = docker.from_env()
        self._template_env = Environment(
            loader=FileSystemLoader(
                Path(__file__).parent.parent / "templates"
            ),
            autoescape=False,
        )
        self._allocated_ports: set[int] = set()

    def _allocate_port(self, start: int, count: int = 1) -> list[int]:
        """Allocate available ports starting from a base port."""
        ports = []
        current = start
        while len(ports) < count:
            if current not in self._allocated_ports and self._is_port_available(current):
                self._allocated_ports.add(current)
                ports.append(current)
            current += 1
            if current > start + 1000:  # Safety limit
                raise RuntimeError("Unable to allocate ports")
        return ports

    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available on the host."""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return True
            except OSError:
                return False

    def _get_template_name(self, topology: InstanceTopology) -> str:
        """Get the Docker Compose template filename for a topology."""
        template_map = {
            InstanceTopology.STANDALONE: "docker-compose.standalone.yml.j2",
            InstanceTopology.DISTRIBUTED_MINIMAL: "docker-compose.distributed-minimal.yml.j2",
            InstanceTopology.DISTRIBUTED_CLUSTERED: "docker-compose.victoria-full.yml.j2",
            InstanceTopology.VICTORIA_FULL: "docker-compose.victoria-full.yml.j2",
        }
        return template_map.get(topology, "docker-compose.standalone.yml.j2")

    def _generate_compose_config(
        self,
        instance: Instance,
        admin_password: str,
    ) -> str:
        """Generate Docker Compose configuration from template."""
        template_name = self._get_template_name(instance.config.topology)
        template = self._template_env.get_template(template_name)

        # Allocate ports based on topology
        config = instance.config
        topology = config.topology

        if topology == InstanceTopology.STANDALONE:
            web_port, api_port, hec_port, s2s_port = (
                self._allocate_port(self.WEB_PORT_START)[0],
                self._allocate_port(self.API_PORT_START)[0],
                self._allocate_port(self.HEC_PORT_START)[0],
                self._allocate_port(self.S2S_PORT_START)[0],
            )
            context = {
                "instance_id": instance.id,
                "network_name": f"{settings.docker_network_prefix}_{instance.id}",
                "splunk_image": settings.splunk_image,
                "admin_password": admin_password,
                "web_port": web_port,
                "api_port": api_port,
                "hec_port": hec_port,
                "s2s_port": s2s_port,
                "memory_limit": config.memory_mb,
                "cpu_limit": config.cpu_cores,
                "experience": config.experience,
                "created_at": instance.created_at.isoformat(),
                "expires_at": instance.expires_at.isoformat(),
                "custom_configs_path": None,
            }
        elif topology == InstanceTopology.DISTRIBUTED_MINIMAL:
            web_port, api_port, hec_port, s2s_port, idx_api_port = (
                self._allocate_port(self.WEB_PORT_START)[0],
                self._allocate_port(self.API_PORT_START)[0],
                self._allocate_port(self.HEC_PORT_START)[0],
                self._allocate_port(self.S2S_PORT_START)[0],
                self._allocate_port(self.API_PORT_START + 100)[0],
            )
            context = {
                "instance_id": instance.id,
                "network_name": f"{settings.docker_network_prefix}_{instance.id}",
                "splunk_image": settings.splunk_image,
                "admin_password": admin_password,
                "web_port": web_port,
                "api_port": api_port,
                "hec_port": hec_port,
                "s2s_port": s2s_port,
                "idx_api_port": idx_api_port,
                "memory_limit": config.memory_mb,
                "cpu_limit": config.cpu_cores,
                "experience": config.experience,
                "enable_realtime_search": config.enable_realtime_search,
                "custom_configs_path": None,
            }
        else:  # Victoria Full or Distributed Clustered
            sh_count = config.search_head_count
            idx_count = config.indexer_count

            web_ports = self._allocate_port(self.WEB_PORT_START, sh_count)
            api_ports = self._allocate_port(self.API_PORT_START, sh_count)
            hec_ports = self._allocate_port(self.HEC_PORT_START, idx_count)
            s2s_ports = self._allocate_port(self.S2S_PORT_START, idx_count)
            idx_api_ports = self._allocate_port(self.API_PORT_START + 200, idx_count)
            cm_port = self._allocate_port(self.API_PORT_START + 300)[0]
            deployer_port = self._allocate_port(self.API_PORT_START + 400)[0]

            context = {
                "instance_id": instance.id,
                "network_name": f"{settings.docker_network_prefix}_{instance.id}",
                "splunk_image": settings.splunk_image,
                "admin_password": admin_password,
                "web_port": web_ports[0],
                "api_port": api_ports[0],
                "hec_port": hec_ports[0],
                "s2s_port": s2s_ports[0],
                "idx_api_port": idx_api_ports[0],
                "cm_port": cm_port,
                "deployer_port": deployer_port,
                "search_head_count": sh_count,
                "indexer_count": idx_count,
                "replication_factor": config.replication_factor,
                "search_factor": config.search_factor,
                "memory_limit": config.memory_mb,
                "cpu_limit": config.cpu_cores,
                "experience": config.experience,
                "custom_configs_path": None,
            }

        return template.render(**context)

    async def create_instance_resources(
        self,
        instance: Instance,
    ) -> tuple[Instance, str]:
        """
        Create all Docker resources for an instance.

        Args:
            instance: The instance model to create resources for

        Returns:
            Tuple of (updated instance, admin password)
        """
        # Generate admin password
        admin_password = secrets.token_urlsafe(16)

        # Generate Docker Compose config
        compose_config = self._generate_compose_config(instance, admin_password)

        # Create instance directory
        instance_dir = settings.ensure_data_dir() / "instances" / instance.id
        instance_dir.mkdir(parents=True, exist_ok=True)

        # Write compose file
        compose_file = instance_dir / "docker-compose.yml"
        compose_file.write_text(compose_config)

        # Parse compose config to extract port mappings
        compose_data = yaml.safe_load(compose_config)
        services = compose_data.get("services", {})

        # Extract endpoints based on topology
        endpoints = InstanceEndpoints()
        config = instance.config

        if config.topology == InstanceTopology.STANDALONE:
            splunk_service = services.get("splunk", {})
            ports = splunk_service.get("ports", [])
            for port_mapping in ports:
                host_port, container_port = port_mapping.split(":")
                if container_port == "8000":
                    endpoints.web_url = f"http://localhost:{host_port}"
                elif container_port == "8089":
                    endpoints.api_url = f"https://localhost:{host_port}"
                elif container_port == "8088":
                    endpoints.hec_url = f"https://localhost:{host_port}"
                elif container_port == "9997":
                    endpoints.s2s_port = int(host_port)
        else:
            # For distributed topologies, use search head for web/api
            for name, service in services.items():
                if "search-head" in name or name == "search-head":
                    ports = service.get("ports", [])
                    for port_mapping in ports:
                        host_port, container_port = port_mapping.split(":")
                        if container_port == "8000" and not endpoints.web_url:
                            endpoints.web_url = f"http://localhost:{host_port}"
                        elif container_port == "8089" and not endpoints.api_url:
                            endpoints.api_url = f"https://localhost:{host_port}"
                    break

            # HEC from first indexer
            for name, service in services.items():
                if "indexer" in name:
                    ports = service.get("ports", [])
                    for port_mapping in ports:
                        host_port, container_port = port_mapping.split(":")
                        if container_port == "8088" and not endpoints.hec_url:
                            endpoints.hec_url = f"https://localhost:{host_port}"
                        elif container_port == "9997" and not endpoints.s2s_port:
                            endpoints.s2s_port = int(host_port)
                    break

        # ACS API URL (our simulation)
        endpoints.acs_url = f"{settings.acs_base_url}/{instance.id}/adminconfig/v2"

        # Update instance
        instance.endpoints = endpoints
        instance.network_id = f"{settings.docker_network_prefix}_{instance.id}"

        return instance, admin_password

    async def start_instance(self, instance: Instance) -> Instance:
        """
        Start the Docker containers for an instance.

        Args:
            instance: The instance to start

        Returns:
            Updated instance with running status
        """
        instance_dir = settings.data_dir / "instances" / instance.id
        compose_file = instance_dir / "docker-compose.yml"

        if not compose_file.exists():
            raise FileNotFoundError(f"Compose file not found for instance {instance.id}")

        # Run docker-compose up
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "compose",
            "-f",
            str(compose_file),
            "up",
            "-d",
            cwd=str(instance_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(f"Failed to start instance {instance.id}: {stderr.decode()}")
            instance.status = InstanceStatus.ERROR
            instance.error_message = stderr.decode()
            return instance

        # Get container IDs
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "compose",
            "-f",
            str(compose_file),
            "ps",
            "-q",
            cwd=str(instance_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        container_ids = stdout.decode().strip().split("\n")
        instance.container_ids = [cid for cid in container_ids if cid]

        instance.status = InstanceStatus.STARTING
        return instance

    async def stop_instance(self, instance: Instance) -> Instance:
        """Stop all containers for an instance."""
        instance_dir = settings.data_dir / "instances" / instance.id
        compose_file = instance_dir / "docker-compose.yml"

        if compose_file.exists():
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "compose",
                "-f",
                str(compose_file),
                "down",
                cwd=str(instance_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

        instance.status = InstanceStatus.STOPPED
        return instance

    async def destroy_instance(self, instance: Instance) -> None:
        """Destroy all resources for an instance."""
        instance_dir = settings.data_dir / "instances" / instance.id
        compose_file = instance_dir / "docker-compose.yml"

        if compose_file.exists():
            # Stop and remove containers, networks, volumes
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "compose",
                "-f",
                str(compose_file),
                "down",
                "-v",
                "--remove-orphans",
                cwd=str(instance_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

        # Release allocated ports
        for port in list(self._allocated_ports):
            self._allocated_ports.discard(port)

        # Clean up instance directory
        if instance_dir.exists():
            import shutil

            shutil.rmtree(instance_dir)

    async def check_instance_health(self, instance: Instance) -> InstanceStatus:
        """Check the health status of an instance."""
        if not instance.container_ids:
            return InstanceStatus.ERROR

        try:
            all_healthy = True
            any_running = False

            for container_id in instance.container_ids:
                try:
                    container = self._client.containers.get(container_id)
                    state = container.attrs.get("State", {})

                    if state.get("Running", False):
                        any_running = True
                        health = state.get("Health", {})
                        if health and health.get("Status") != "healthy":
                            all_healthy = False
                    else:
                        all_healthy = False
                except NotFound:
                    all_healthy = False

            if all_healthy and any_running:
                return InstanceStatus.RUNNING
            elif any_running:
                return InstanceStatus.STARTING
            else:
                return InstanceStatus.STOPPED

        except APIError as e:
            logger.error(f"Docker API error checking health: {e}")
            return InstanceStatus.ERROR

    async def get_container_logs(
        self, instance: Instance, container_name: str | None = None, tail: int = 100
    ) -> str:
        """Get logs from instance containers."""
        logs = []

        for container_id in instance.container_ids:
            try:
                container = self._client.containers.get(container_id)
                if container_name and container_name not in container.name:
                    continue
                container_logs = container.logs(tail=tail).decode()
                logs.append(f"=== {container.name} ===\n{container_logs}")
            except NotFound:
                continue

        return "\n\n".join(logs)
