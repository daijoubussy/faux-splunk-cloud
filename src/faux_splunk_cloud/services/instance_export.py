"""
Instance export service for Faux Splunk Cloud.

Enables customers to export their Splunk instance configuration
for deployment on their own infrastructure (Docker, bare metal, cloud).
"""

import asyncio
import base64
import io
import json
import logging
import os
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import docker
from docker.errors import NotFound

from faux_splunk_cloud.config import settings
from faux_splunk_cloud.models.instance import Instance

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""
    DOCKER_COMPOSE = "docker-compose"
    KUBERNETES = "kubernetes"
    ANSIBLE = "ansible"
    BARE_METAL = "bare-metal"
    TERRAFORM = "terraform"


class ExportScope(str, Enum):
    """What to include in the export."""
    CONFIG_ONLY = "config-only"  # Just configs, no data
    CONFIG_AND_APPS = "config-and-apps"  # Configs + installed apps
    FULL = "full"  # Everything including indexes (large!)


@dataclass
class ExportManifest:
    """Manifest describing the export contents."""
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    instance_id: str = ""
    instance_name: str = ""
    splunk_version: str = ""
    export_format: str = ""
    export_scope: str = ""
    files: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class InstanceExportService:
    """
    Service for exporting Splunk instance configurations.

    Provides portable exports that can be used to:
    - Run the same instance locally via Docker Compose
    - Deploy to Kubernetes with Helm charts
    - Provision with Ansible playbooks
    - Set up on bare metal using scripts
    - Deploy via Terraform (cloud providers)
    """

    def __init__(self):
        self._docker_client: docker.DockerClient | None = None

    async def start(self) -> None:
        """Initialize the export service."""
        try:
            self._docker_client = docker.DockerClient(base_url=settings.docker_host)
            logger.info("Instance export service started")
        except Exception as e:
            logger.error(f"Failed to start export service: {e}")

    async def stop(self) -> None:
        """Cleanup the export service."""
        if self._docker_client:
            self._docker_client.close()
        logger.info("Instance export service stopped")

    async def export_instance(
        self,
        instance: Instance,
        format: ExportFormat = ExportFormat.DOCKER_COMPOSE,
        scope: ExportScope = ExportScope.CONFIG_AND_APPS,
        include_credentials: bool = False,
    ) -> tuple[bytes, str]:
        """
        Export an instance configuration.

        Args:
            instance: The Splunk instance to export
            format: Export format (docker-compose, kubernetes, etc.)
            scope: What to include (config-only, config-and-apps, full)
            include_credentials: Whether to include passwords/tokens

        Returns:
            Tuple of (export_bytes, filename)
        """
        logger.info(f"Exporting instance {instance.id} as {format.value}, scope={scope.value}")

        # Extract configuration from the running container
        configs = await self._extract_configs(instance, scope)

        # Generate export based on format
        if format == ExportFormat.DOCKER_COMPOSE:
            export_data = await self._generate_docker_compose_export(
                instance, configs, include_credentials
            )
            filename = f"splunk-export-{instance.id[:8]}.tar.gz"
        elif format == ExportFormat.KUBERNETES:
            export_data = await self._generate_kubernetes_export(
                instance, configs, include_credentials
            )
            filename = f"splunk-k8s-{instance.id[:8]}.tar.gz"
        elif format == ExportFormat.ANSIBLE:
            export_data = await self._generate_ansible_export(
                instance, configs, include_credentials
            )
            filename = f"splunk-ansible-{instance.id[:8]}.tar.gz"
        elif format == ExportFormat.BARE_METAL:
            export_data = await self._generate_bare_metal_export(
                instance, configs, include_credentials
            )
            filename = f"splunk-bare-metal-{instance.id[:8]}.tar.gz"
        elif format == ExportFormat.TERRAFORM:
            export_data = await self._generate_terraform_export(
                instance, configs, include_credentials
            )
            filename = f"splunk-terraform-{instance.id[:8]}.tar.gz"
        else:
            raise ValueError(f"Unsupported format: {format}")

        return export_data, filename

    async def _extract_configs(
        self,
        instance: Instance,
        scope: ExportScope,
    ) -> dict[str, Any]:
        """Extract configuration from the running container."""
        if not self._docker_client:
            raise RuntimeError("Export service not started")

        try:
            container = self._docker_client.containers.get(f"fsc-{instance.id}")
        except NotFound:
            raise ValueError(f"Instance container not found: {instance.id}")

        configs: dict[str, Any] = {
            "etc": {},
            "apps": [],
            "indexes": [],
            "users": [],
            "saved_searches": [],
            "dashboards": [],
            "server_settings": {},
        }

        # Core configuration files to extract
        config_paths = [
            "/opt/splunk/etc/system/local/server.conf",
            "/opt/splunk/etc/system/local/inputs.conf",
            "/opt/splunk/etc/system/local/outputs.conf",
            "/opt/splunk/etc/system/local/props.conf",
            "/opt/splunk/etc/system/local/transforms.conf",
            "/opt/splunk/etc/system/local/indexes.conf",
            "/opt/splunk/etc/system/local/web.conf",
            "/opt/splunk/etc/system/local/authentication.conf",
            "/opt/splunk/etc/system/local/authorize.conf",
            "/opt/splunk/etc/system/local/limits.conf",
        ]

        for path in config_paths:
            try:
                exit_code, output = container.exec_run(f"cat {path}")
                if exit_code == 0:
                    filename = os.path.basename(path)
                    configs["etc"][filename] = output.decode("utf-8")
            except Exception as e:
                logger.debug(f"Could not extract {path}: {e}")

        # Extract installed apps (excluding Splunk's built-in apps)
        if scope in (ExportScope.CONFIG_AND_APPS, ExportScope.FULL):
            configs["apps"] = await self._extract_apps(container)

        # Extract saved searches
        configs["saved_searches"] = await self._extract_saved_searches(container)

        # Extract dashboards
        configs["dashboards"] = await self._extract_dashboards(container)

        # Extract index definitions
        configs["indexes"] = await self._extract_indexes(container)

        return configs

    async def _extract_apps(self, container: Any) -> list[dict[str, Any]]:
        """Extract user-installed apps."""
        apps = []
        try:
            # List apps directory
            exit_code, output = container.exec_run(
                "ls /opt/splunk/etc/apps"
            )
            if exit_code == 0:
                app_names = output.decode().strip().split("\n")
                # Filter out built-in apps
                builtin_apps = {
                    "splunk_httpinput", "search", "splunk_instrumentation",
                    "learned", "introspection_generator_addon", "user-prefs",
                    "alert_webhook", "splunk_archiver", "splunk_metrics_workspace",
                    "SplunkForwarder", "SplunkLightForwarder",
                }
                for app_name in app_names:
                    if app_name and app_name not in builtin_apps:
                        app_info = await self._extract_app_info(container, app_name)
                        if app_info:
                            apps.append(app_info)
        except Exception as e:
            logger.warning(f"Failed to extract apps: {e}")
        return apps

    async def _extract_app_info(self, container: Any, app_name: str) -> dict[str, Any] | None:
        """Extract information about a single app."""
        app_path = f"/opt/splunk/etc/apps/{app_name}"

        try:
            # Get app.conf
            exit_code, output = container.exec_run(
                f"cat {app_path}/default/app.conf 2>/dev/null || cat {app_path}/local/app.conf 2>/dev/null"
            )
            app_conf = output.decode("utf-8") if exit_code == 0 else ""

            # Create tarball of the app
            exit_code, output = container.exec_run(
                f"tar czf - -C /opt/splunk/etc/apps {app_name}",
                stream=False
            )

            if exit_code == 0:
                return {
                    "name": app_name,
                    "config": app_conf,
                    "archive": base64.b64encode(output).decode("utf-8"),
                }
        except Exception as e:
            logger.warning(f"Failed to extract app {app_name}: {e}")

        return None

    async def _extract_saved_searches(self, container: Any) -> list[dict[str, Any]]:
        """Extract saved searches from the instance."""
        searches = []
        try:
            # Get savedsearches.conf from all locations
            exit_code, output = container.exec_run(
                "cat /opt/splunk/etc/users/*/search/local/savedsearches.conf 2>/dev/null"
            )
            if exit_code == 0 and output:
                searches.append({
                    "type": "user",
                    "content": output.decode("utf-8"),
                })

            # System-level saved searches
            exit_code, output = container.exec_run(
                "cat /opt/splunk/etc/system/local/savedsearches.conf 2>/dev/null"
            )
            if exit_code == 0 and output:
                searches.append({
                    "type": "system",
                    "content": output.decode("utf-8"),
                })
        except Exception as e:
            logger.warning(f"Failed to extract saved searches: {e}")
        return searches

    async def _extract_dashboards(self, container: Any) -> list[dict[str, Any]]:
        """Extract dashboards from the instance."""
        dashboards = []
        try:
            # Find all dashboard XML files
            exit_code, output = container.exec_run(
                "find /opt/splunk/etc -name 'data' -type d -exec find {} -name '*.xml' \\;"
            )
            if exit_code == 0 and output:
                files = output.decode().strip().split("\n")
                for filepath in files:
                    if filepath and "ui/views" in filepath:
                        exit_code, content = container.exec_run(f"cat {filepath}")
                        if exit_code == 0:
                            dashboards.append({
                                "path": filepath,
                                "content": content.decode("utf-8"),
                            })
        except Exception as e:
            logger.warning(f"Failed to extract dashboards: {e}")
        return dashboards

    async def _extract_indexes(self, container: Any) -> list[dict[str, Any]]:
        """Extract index definitions."""
        indexes = []
        try:
            # Get indexes.conf
            for path in [
                "/opt/splunk/etc/system/local/indexes.conf",
                "/opt/splunk/etc/master-apps/_cluster/local/indexes.conf",
            ]:
                exit_code, output = container.exec_run(f"cat {path} 2>/dev/null")
                if exit_code == 0 and output:
                    indexes.append({
                        "path": path,
                        "content": output.decode("utf-8"),
                    })
        except Exception as e:
            logger.warning(f"Failed to extract indexes: {e}")
        return indexes

    async def _generate_docker_compose_export(
        self,
        instance: Instance,
        configs: dict[str, Any],
        include_credentials: bool,
    ) -> bytes:
        """Generate a Docker Compose based export."""
        manifest = ExportManifest(
            instance_id=instance.id,
            instance_name=instance.name,
            splunk_version=settings.splunk_image.split(":")[-1],
            export_format=ExportFormat.DOCKER_COMPOSE.value,
            export_scope=ExportScope.CONFIG_AND_APPS.value,
        )

        # Create in-memory tar archive
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            # Add docker-compose.yml
            compose_content = self._generate_compose_yaml(instance, include_credentials)
            self._add_string_to_tar(tar, "docker-compose.yml", compose_content)
            manifest.files.append({"path": "docker-compose.yml", "type": "compose"})

            # Add .env file
            env_content = self._generate_env_file(instance, include_credentials)
            self._add_string_to_tar(tar, ".env", env_content)
            manifest.files.append({"path": ".env", "type": "env"})

            # Add configuration files
            for filename, content in configs["etc"].items():
                path = f"config/etc/system/local/{filename}"
                self._add_string_to_tar(tar, path, content)
                manifest.files.append({"path": path, "type": "config"})

            # Add apps
            for app in configs["apps"]:
                if "archive" in app:
                    app_data = base64.b64decode(app["archive"])
                    path = f"apps/{app['name']}.tar.gz"
                    self._add_bytes_to_tar(tar, path, app_data)
                    manifest.files.append({"path": path, "type": "app"})

            # Add saved searches
            for i, search in enumerate(configs["saved_searches"]):
                path = f"config/savedsearches/{search['type']}_{i}.conf"
                self._add_string_to_tar(tar, path, search["content"])
                manifest.files.append({"path": path, "type": "savedsearch"})

            # Add dashboards
            for i, dashboard in enumerate(configs["dashboards"]):
                name = os.path.basename(dashboard["path"])
                path = f"dashboards/{name}"
                self._add_string_to_tar(tar, path, dashboard["content"])
                manifest.files.append({"path": path, "type": "dashboard"})

            # Add README
            readme = self._generate_readme(instance, ExportFormat.DOCKER_COMPOSE)
            self._add_string_to_tar(tar, "README.md", readme)

            # Add setup script
            setup_script = self._generate_setup_script(instance)
            self._add_string_to_tar(tar, "setup.sh", setup_script, executable=True)

            # Add manifest
            manifest_json = json.dumps(manifest.__dict__, indent=2)
            self._add_string_to_tar(tar, "manifest.json", manifest_json)

        buffer.seek(0)
        return buffer.read()

    async def _generate_kubernetes_export(
        self,
        instance: Instance,
        configs: dict[str, Any],
        include_credentials: bool,
    ) -> bytes:
        """Generate Kubernetes manifests for the instance."""
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            # Deployment
            deployment = self._generate_k8s_deployment(instance)
            self._add_string_to_tar(tar, "kubernetes/deployment.yaml", deployment)

            # Service
            service = self._generate_k8s_service(instance)
            self._add_string_to_tar(tar, "kubernetes/service.yaml", service)

            # ConfigMap for configs
            configmap = self._generate_k8s_configmap(instance, configs)
            self._add_string_to_tar(tar, "kubernetes/configmap.yaml", configmap)

            # Secret for credentials
            if include_credentials:
                secret = self._generate_k8s_secret(instance)
                self._add_string_to_tar(tar, "kubernetes/secret.yaml", secret)

            # Kustomization
            kustomize = self._generate_kustomization()
            self._add_string_to_tar(tar, "kubernetes/kustomization.yaml", kustomize)

            # Helm chart (optional)
            helm_chart = self._generate_helm_chart(instance)
            self._add_string_to_tar(tar, "helm/Chart.yaml", helm_chart)

            helm_values = self._generate_helm_values(instance, include_credentials)
            self._add_string_to_tar(tar, "helm/values.yaml", helm_values)

            # README
            readme = self._generate_readme(instance, ExportFormat.KUBERNETES)
            self._add_string_to_tar(tar, "README.md", readme)

        buffer.seek(0)
        return buffer.read()

    async def _generate_ansible_export(
        self,
        instance: Instance,
        configs: dict[str, Any],
        include_credentials: bool,
    ) -> bytes:
        """Generate Ansible playbook for the instance."""
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            # Main playbook
            playbook = self._generate_ansible_playbook(instance)
            self._add_string_to_tar(tar, "site.yml", playbook)

            # Inventory
            inventory = self._generate_ansible_inventory()
            self._add_string_to_tar(tar, "inventory.ini", inventory)

            # Variables
            vars_content = self._generate_ansible_vars(instance, include_credentials)
            self._add_string_to_tar(tar, "group_vars/all.yml", vars_content)

            # Role structure
            self._add_string_to_tar(tar, "roles/splunk/tasks/main.yml",
                                    self._generate_ansible_tasks())
            self._add_string_to_tar(tar, "roles/splunk/handlers/main.yml",
                                    self._generate_ansible_handlers())
            self._add_string_to_tar(tar, "roles/splunk/templates/server.conf.j2",
                                    configs["etc"].get("server.conf", ""))

            # Configuration files
            for filename, content in configs["etc"].items():
                path = f"roles/splunk/files/{filename}"
                self._add_string_to_tar(tar, path, content)

            # README
            readme = self._generate_readme(instance, ExportFormat.ANSIBLE)
            self._add_string_to_tar(tar, "README.md", readme)

        buffer.seek(0)
        return buffer.read()

    async def _generate_bare_metal_export(
        self,
        instance: Instance,
        configs: dict[str, Any],
        include_credentials: bool,
    ) -> bytes:
        """Generate bare metal installation scripts."""
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            # Installation script
            install_script = self._generate_install_script(instance, include_credentials)
            self._add_string_to_tar(tar, "install.sh", install_script, executable=True)

            # Configuration files
            for filename, content in configs["etc"].items():
                path = f"config/{filename}"
                self._add_string_to_tar(tar, path, content)

            # Systemd service file
            systemd_service = self._generate_systemd_service()
            self._add_string_to_tar(tar, "splunk.service", systemd_service)

            # README
            readme = self._generate_readme(instance, ExportFormat.BARE_METAL)
            self._add_string_to_tar(tar, "README.md", readme)

        buffer.seek(0)
        return buffer.read()

    async def _generate_terraform_export(
        self,
        instance: Instance,
        configs: dict[str, Any],
        include_credentials: bool,
    ) -> bytes:
        """Generate Terraform configuration."""
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            # Main Terraform file
            main_tf = self._generate_terraform_main(instance)
            self._add_string_to_tar(tar, "main.tf", main_tf)

            # Variables
            variables_tf = self._generate_terraform_variables(instance)
            self._add_string_to_tar(tar, "variables.tf", variables_tf)

            # Terraform values
            tfvars = self._generate_terraform_tfvars(instance, include_credentials)
            self._add_string_to_tar(tar, "terraform.tfvars.example", tfvars)

            # Outputs
            outputs_tf = self._generate_terraform_outputs()
            self._add_string_to_tar(tar, "outputs.tf", outputs_tf)

            # Configuration files for user_data
            for filename, content in configs["etc"].items():
                path = f"files/{filename}"
                self._add_string_to_tar(tar, path, content)

            # README
            readme = self._generate_readme(instance, ExportFormat.TERRAFORM)
            self._add_string_to_tar(tar, "README.md", readme)

        buffer.seek(0)
        return buffer.read()

    # Helper methods for generating various formats

    def _generate_compose_yaml(self, instance: Instance, include_creds: bool) -> str:
        """Generate docker-compose.yml content."""
        password_line = f"      - SPLUNK_PASSWORD=${{SPLUNK_PASSWORD:-changeme}}"

        return f"""# Splunk Enterprise - Exported from Faux Splunk Cloud
# Instance: {instance.name} ({instance.id})
# Generated: {datetime.utcnow().isoformat()}

version: '3.8'

services:
  splunk:
    image: {settings.splunk_image}
    container_name: splunk-{instance.id[:8]}
    hostname: splunk
    environment:
      - SPLUNK_START_ARGS=--accept-license
{password_line}
      - SPLUNK_HTTP_ENABLESSL=true
    ports:
      - "8000:8000"   # Splunk Web
      - "8089:8089"   # Splunk REST API
      - "8088:8088"   # HTTP Event Collector
      - "9997:9997"   # Receiving port (forwarders)
      - "514:514/udp" # Syslog UDP
    volumes:
      - splunk-etc:/opt/splunk/etc
      - splunk-var:/opt/splunk/var
      - ./config/etc/system/local:/opt/splunk/etc/system/local:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "-k", "https://localhost:8089/services/server/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

volumes:
  splunk-etc:
  splunk-var:
"""

    def _generate_env_file(self, instance: Instance, include_creds: bool) -> str:
        """Generate .env file content."""
        if include_creds:
            password = settings.default_admin_password.get_secret_value()
        else:
            password = "changeme"

        return f"""# Environment variables for Splunk deployment
# Instance: {instance.name}

# Splunk admin password (CHANGE THIS!)
SPLUNK_PASSWORD={password}

# Optional: Splunk Enterprise license
# SPLUNK_LICENSE_URI=

# Memory limit (default: 4GB)
SPLUNK_MEMORY_LIMIT=4g
"""

    def _generate_readme(self, instance: Instance, format: ExportFormat) -> str:
        """Generate README content."""
        format_instructions = {
            ExportFormat.DOCKER_COMPOSE: """
## Quick Start (Docker Compose)

1. Install Docker and Docker Compose
2. Update `.env` with your desired password
3. Run: `docker compose up -d`
4. Access Splunk Web at https://localhost:8000
""",
            ExportFormat.KUBERNETES: """
## Quick Start (Kubernetes)

1. Apply the manifests:
   ```bash
   kubectl apply -f kubernetes/
   ```

   Or use Helm:
   ```bash
   helm install splunk ./helm
   ```

2. Port-forward to access:
   ```bash
   kubectl port-forward svc/splunk 8000:8000
   ```
""",
            ExportFormat.ANSIBLE: """
## Quick Start (Ansible)

1. Update `inventory.ini` with your target hosts
2. Update `group_vars/all.yml` with your configuration
3. Run: `ansible-playbook -i inventory.ini site.yml`
""",
            ExportFormat.BARE_METAL: """
## Quick Start (Bare Metal)

1. Run as root: `./install.sh`
2. Start Splunk: `systemctl start splunk`
3. Access Splunk Web at https://your-host:8000
""",
            ExportFormat.TERRAFORM: """
## Quick Start (Terraform)

1. Copy `terraform.tfvars.example` to `terraform.tfvars`
2. Update with your provider credentials
3. Run:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```
""",
        }

        return f"""# Splunk Enterprise Export

Exported from Faux Splunk Cloud on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

## Instance Details

- **Name**: {instance.name}
- **ID**: {instance.id}
- **Splunk Version**: {settings.splunk_image.split(':')[-1]}

{format_instructions.get(format, "")}

## Included Configuration

This export includes:
- Core configuration files (server.conf, inputs.conf, etc.)
- Custom indexes configuration
- Saved searches and reports
- Dashboards
- Installed apps (if applicable)

## Important Notes

1. **Passwords**: Default passwords are NOT production-ready. Change them immediately.
2. **Licensing**: This export does not include a Splunk license. You'll need your own.
3. **Data**: Index data is NOT included. Only configurations are exported.
4. **Apps**: Some apps may require additional licensing or configuration.

## Support

For questions about this export, visit the Faux Splunk Cloud documentation.
For Splunk Enterprise support, visit splunk.com/support.
"""

    def _generate_setup_script(self, instance: Instance) -> str:
        """Generate setup script for Docker deployment."""
        return f"""#!/bin/bash
# Setup script for Splunk export
# Instance: {instance.name}

set -e

echo "Setting up Splunk deployment..."

# Create required directories
mkdir -p config/etc/system/local

# Extract apps if present
if [ -d "apps" ]; then
    echo "Installing apps..."
    for app in apps/*.tar.gz; do
        [ -f "$app" ] || continue
        tar xzf "$app" -C apps/
    done
fi

# Start Splunk
echo "Starting Splunk..."
docker compose up -d

echo "Waiting for Splunk to start..."
sleep 30

echo "Splunk is starting up. Access it at https://localhost:8000"
echo "Default credentials: admin / (your configured password)"
"""

    def _generate_k8s_deployment(self, instance: Instance) -> str:
        """Generate Kubernetes Deployment manifest."""
        return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: splunk
  labels:
    app: splunk
    instance: {instance.id[:8]}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: splunk
  template:
    metadata:
      labels:
        app: splunk
    spec:
      containers:
      - name: splunk
        image: {settings.splunk_image}
        ports:
        - containerPort: 8000
          name: web
        - containerPort: 8089
          name: api
        - containerPort: 8088
          name: hec
        env:
        - name: SPLUNK_START_ARGS
          value: "--accept-license"
        - name: SPLUNK_PASSWORD
          valueFrom:
            secretKeyRef:
              name: splunk-secrets
              key: admin-password
        volumeMounts:
        - name: config
          mountPath: /opt/splunk/etc/system/local
        - name: splunk-data
          mountPath: /opt/splunk/var
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        readinessProbe:
          httpGet:
            path: /services/server/health
            port: 8089
            scheme: HTTPS
          initialDelaySeconds: 60
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: splunk-config
      - name: splunk-data
        persistentVolumeClaim:
          claimName: splunk-data
"""

    def _generate_k8s_service(self, instance: Instance) -> str:
        """Generate Kubernetes Service manifest."""
        return f"""apiVersion: v1
kind: Service
metadata:
  name: splunk
  labels:
    app: splunk
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
    name: web
  - port: 8089
    targetPort: 8089
    name: api
  - port: 8088
    targetPort: 8088
    name: hec
  selector:
    app: splunk
"""

    def _generate_k8s_configmap(self, instance: Instance, configs: dict[str, Any]) -> str:
        """Generate Kubernetes ConfigMap for configs."""
        config_data = ""
        for filename, content in configs["etc"].items():
            # Escape content for YAML
            escaped = content.replace("\n", "\n    ")
            config_data += f"""  {filename}: |
    {escaped}
"""

        return f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: splunk-config
data:
{config_data}"""

    def _generate_k8s_secret(self, instance: Instance) -> str:
        """Generate Kubernetes Secret for credentials."""
        password = base64.b64encode(
            settings.default_admin_password.get_secret_value().encode()
        ).decode()

        return f"""apiVersion: v1
kind: Secret
metadata:
  name: splunk-secrets
type: Opaque
data:
  admin-password: {password}
"""

    def _generate_kustomization(self) -> str:
        """Generate Kustomization file."""
        return """apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- deployment.yaml
- service.yaml
- configmap.yaml
- secret.yaml
"""

    def _generate_helm_chart(self, instance: Instance) -> str:
        """Generate Helm Chart.yaml."""
        return f"""apiVersion: v2
name: splunk
description: Splunk Enterprise deployment exported from Faux Splunk Cloud
type: application
version: 1.0.0
appVersion: "{settings.splunk_image.split(':')[-1]}"
"""

    def _generate_helm_values(self, instance: Instance, include_creds: bool) -> str:
        """Generate Helm values.yaml."""
        password = settings.default_admin_password.get_secret_value() if include_creds else "changeme"
        return f"""# Helm values for Splunk deployment

image:
  repository: splunk/splunk
  tag: "{settings.splunk_image.split(':')[-1]}"
  pullPolicy: IfNotPresent

splunk:
  password: "{password}"

resources:
  requests:
    memory: "2Gi"
    cpu: "1"
  limits:
    memory: "4Gi"
    cpu: "2"

persistence:
  enabled: true
  size: 50Gi

service:
  type: ClusterIP
"""

    def _generate_ansible_playbook(self, instance: Instance) -> str:
        """Generate Ansible playbook."""
        return f"""---
# Splunk Enterprise Deployment
# Exported from Faux Splunk Cloud
# Instance: {instance.name}

- name: Deploy Splunk Enterprise
  hosts: splunk_servers
  become: yes

  roles:
    - splunk
"""

    def _generate_ansible_inventory(self) -> str:
        """Generate Ansible inventory."""
        return """[splunk_servers]
# Add your target hosts here
# splunk1.example.com ansible_user=admin
# splunk2.example.com ansible_user=admin

[splunk_servers:vars]
ansible_python_interpreter=/usr/bin/python3
"""

    def _generate_ansible_vars(self, instance: Instance, include_creds: bool) -> str:
        """Generate Ansible variables."""
        password = settings.default_admin_password.get_secret_value() if include_creds else "changeme"
        return f"""---
# Splunk configuration variables

splunk_version: "{settings.splunk_image.split(':')[-1]}"
splunk_admin_password: "{password}"
splunk_install_path: "/opt/splunk"

# Resource limits
splunk_memory_limit: "4g"
splunk_cpu_limit: "2"

# Ports
splunk_web_port: 8000
splunk_api_port: 8089
splunk_hec_port: 8088
"""

    def _generate_ansible_tasks(self) -> str:
        """Generate Ansible tasks."""
        return """---
# Splunk installation and configuration tasks

- name: Download Splunk
  get_url:
    url: "https://download.splunk.com/products/splunk/releases/{{ splunk_version }}/linux/splunk-{{ splunk_version }}-Linux-x86_64.tgz"
    dest: "/tmp/splunk.tgz"

- name: Extract Splunk
  unarchive:
    src: "/tmp/splunk.tgz"
    dest: "{{ splunk_install_path | dirname }}"
    remote_src: yes

- name: Copy configuration files
  copy:
    src: "{{ item }}"
    dest: "{{ splunk_install_path }}/etc/system/local/"
  with_fileglob:
    - "files/*.conf"
  notify: restart splunk

- name: Set admin password
  command: "{{ splunk_install_path }}/bin/splunk edit user admin -password {{ splunk_admin_password }} -auth admin:changeme"
  ignore_errors: yes

- name: Enable Splunk to start at boot
  command: "{{ splunk_install_path }}/bin/splunk enable boot-start -user splunk --accept-license --answer-yes"

- name: Start Splunk
  service:
    name: Splunkd
    state: started
    enabled: yes
"""

    def _generate_ansible_handlers(self) -> str:
        """Generate Ansible handlers."""
        return """---
# Handlers for Splunk role

- name: restart splunk
  service:
    name: Splunkd
    state: restarted
"""

    def _generate_install_script(self, instance: Instance, include_creds: bool) -> str:
        """Generate bare metal installation script."""
        password = settings.default_admin_password.get_secret_value() if include_creds else "changeme"
        version = settings.splunk_image.split(':')[-1]

        return f"""#!/bin/bash
# Splunk Enterprise Installation Script
# Exported from Faux Splunk Cloud
# Instance: {instance.name}

set -e

SPLUNK_VERSION="{version}"
SPLUNK_HOME="/opt/splunk"
SPLUNK_USER="splunk"
SPLUNK_PASSWORD="{password}"

echo "=== Splunk Enterprise Installation ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Create splunk user
if ! id "$SPLUNK_USER" &>/dev/null; then
    useradd -m -r "$SPLUNK_USER"
fi

# Download Splunk
echo "Downloading Splunk $SPLUNK_VERSION..."
wget -q "https://download.splunk.com/products/splunk/releases/$SPLUNK_VERSION/linux/splunk-$SPLUNK_VERSION-Linux-x86_64.tgz" -O /tmp/splunk.tgz

# Extract
echo "Extracting..."
tar xzf /tmp/splunk.tgz -C /opt

# Set ownership
chown -R $SPLUNK_USER:$SPLUNK_USER $SPLUNK_HOME

# Copy configuration files
echo "Installing configuration..."
cp -r config/* $SPLUNK_HOME/etc/system/local/
chown -R $SPLUNK_USER:$SPLUNK_USER $SPLUNK_HOME/etc/system/local/

# Accept license and set password
echo "Configuring Splunk..."
sudo -u $SPLUNK_USER $SPLUNK_HOME/bin/splunk start --accept-license --answer-yes --no-prompt --seed-passwd "$SPLUNK_PASSWORD"
sudo -u $SPLUNK_USER $SPLUNK_HOME/bin/splunk stop

# Install systemd service
cp splunk.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable splunk

echo "=== Installation Complete ==="
echo "Start Splunk with: systemctl start splunk"
echo "Access Splunk at: https://$(hostname):8000"
"""

    def _generate_systemd_service(self) -> str:
        """Generate systemd service file."""
        return """[Unit]
Description=Splunk Enterprise
After=network.target

[Service]
Type=forking
User=splunk
Group=splunk
ExecStart=/opt/splunk/bin/splunk start
ExecStop=/opt/splunk/bin/splunk stop
ExecReload=/opt/splunk/bin/splunk restart
PIDFile=/opt/splunk/var/run/splunk/splunkd.pid
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    def _generate_terraform_main(self, instance: Instance) -> str:
        """Generate Terraform main.tf."""
        return f"""# Splunk Enterprise Terraform Deployment
# Exported from Faux Splunk Cloud
# Instance: {instance.name}

terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = var.aws_region
}}

resource "aws_security_group" "splunk" {{
  name        = "splunk-sg"
  description = "Security group for Splunk"
  vpc_id      = var.vpc_id

  ingress {{
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }}

  ingress {{
    from_port   = 8089
    to_port     = 8089
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }}

  ingress {{
    from_port   = 8088
    to_port     = 8088
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }}

  egress {{
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }}
}}

resource "aws_instance" "splunk" {{
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.splunk.id]
  subnet_id              = var.subnet_id

  root_block_device {{
    volume_size = var.root_volume_size
    volume_type = "gp3"
  }}

  ebs_block_device {{
    device_name = "/dev/sdf"
    volume_size = var.data_volume_size
    volume_type = "gp3"
  }}

  user_data = file("${{path.module}}/files/user_data.sh")

  tags = {{
    Name        = "splunk-{instance.id[:8]}"
    Environment = var.environment
  }}
}}
"""

    def _generate_terraform_variables(self, instance: Instance) -> str:
        """Generate Terraform variables.tf."""
        return """variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID"
  type        = string
}

variable "ami_id" {
  description = "AMI ID (Amazon Linux 2)"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "m5.large"
}

variable "key_name" {
  description = "SSH key pair name"
  type        = string
}

variable "root_volume_size" {
  description = "Root volume size in GB"
  type        = number
  default     = 50
}

variable "data_volume_size" {
  description = "Data volume size in GB"
  type        = number
  default     = 100
}

variable "allowed_cidrs" {
  description = "CIDR blocks allowed to access Splunk"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "production"
}

variable "splunk_password" {
  description = "Splunk admin password"
  type        = string
  sensitive   = true
}
"""

    def _generate_terraform_tfvars(self, instance: Instance, include_creds: bool) -> str:
        """Generate terraform.tfvars.example."""
        password = settings.default_admin_password.get_secret_value() if include_creds else "changeme"
        return f"""# Terraform variables example
# Copy this to terraform.tfvars and update values

aws_region = "us-west-2"
vpc_id     = "vpc-xxxxxxxx"
subnet_id  = "subnet-xxxxxxxx"
ami_id     = "ami-xxxxxxxx"  # Amazon Linux 2
key_name   = "your-key-pair"

instance_type    = "m5.large"
root_volume_size = 50
data_volume_size = 100

allowed_cidrs = ["10.0.0.0/8"]
environment   = "production"

splunk_password = "{password}"
"""

    def _generate_terraform_outputs(self) -> str:
        """Generate Terraform outputs.tf."""
        return """output "splunk_public_ip" {
  description = "Public IP of Splunk instance"
  value       = aws_instance.splunk.public_ip
}

output "splunk_web_url" {
  description = "Splunk Web URL"
  value       = "https://${aws_instance.splunk.public_ip}:8000"
}

output "splunk_api_url" {
  description = "Splunk REST API URL"
  value       = "https://${aws_instance.splunk.public_ip}:8089"
}
"""

    # Tar helper methods

    def _add_string_to_tar(
        self,
        tar: tarfile.TarFile,
        name: str,
        content: str,
        executable: bool = False,
    ) -> None:
        """Add a string as a file to the tar archive."""
        data = content.encode("utf-8")
        info = tarfile.TarInfo(name=name)
        info.size = len(data)
        info.mtime = int(datetime.utcnow().timestamp())
        info.mode = 0o755 if executable else 0o644
        tar.addfile(info, io.BytesIO(data))

    def _add_bytes_to_tar(
        self,
        tar: tarfile.TarFile,
        name: str,
        data: bytes,
    ) -> None:
        """Add bytes as a file to the tar archive."""
        info = tarfile.TarInfo(name=name)
        info.size = len(data)
        info.mtime = int(datetime.utcnow().timestamp())
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(data))


# Global instance export service
instance_export_service = InstanceExportService()
