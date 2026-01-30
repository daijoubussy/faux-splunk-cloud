"""
Configuration export service for Splunk instances.

Allows tenants to export their Splunk configurations as installable app packages.
"""

import io
import logging
import os
import tarfile
import tempfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from faux_splunk_cloud.services.splunk_client import SplunkClientService

logger = logging.getLogger(__name__)


class ExportableConfigType(str, Enum):
    """Types of configurations that can be exported."""

    INDEXES = "indexes"
    HEC_TOKENS = "hec_tokens"
    SAVED_SEARCHES = "saved_searches"
    DASHBOARDS = "dashboards"
    MACROS = "macros"
    EVENTTYPES = "eventtypes"
    TAGS = "tags"
    FIELD_EXTRACTIONS = "field_extractions"
    FIELD_ALIASES = "field_aliases"
    LOOKUPS = "lookups"
    PROPS = "props"
    TRANSFORMS = "transforms"
    ALERTS = "alerts"
    REPORTS = "reports"


class ExportRequest(BaseModel):
    """Request model for configuration export."""

    app_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Name for the exported app",
    )
    app_label: str = Field(
        default="",
        max_length=200,
        description="Human-readable label for the app",
    )
    app_version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="App version",
    )
    app_description: str = Field(
        default="",
        max_length=1000,
        description="App description",
    )
    config_types: list[ExportableConfigType] = Field(
        default_factory=lambda: [ExportableConfigType.INDEXES],
        description="Configuration types to export",
    )
    include_default_configs: bool = Field(
        default=False,
        description="Include default/system configurations",
    )


class ExportResult(BaseModel):
    """Result of a configuration export."""

    app_name: str
    filename: str
    size_bytes: int
    exported_configs: dict[str, int]  # config_type -> count
    created_at: datetime


class ConfigExportService:
    """
    Exports Splunk configurations as installable app packages.

    Supports exporting:
    - Index configurations
    - HEC token configurations
    - Saved searches and reports
    - Dashboards (SimpleXML and HTML)
    - Macros
    - Event types and tags
    - Field extractions and aliases
    - Lookups (definitions and files)
    - Props and transforms
    """

    def __init__(self) -> None:
        pass

    async def export_configs(
        self,
        splunk_client: SplunkClientService,
        request: ExportRequest,
    ) -> tuple[bytes, ExportResult]:
        """
        Export configurations from a Splunk instance.

        Args:
            splunk_client: Connected Splunk client
            request: Export request parameters

        Returns:
            Tuple of (tar.gz bytes, export result metadata)
        """
        exported_counts: dict[str, int] = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir) / request.app_name

            # Create app structure
            self._create_app_structure(app_dir, request)

            # Export each requested config type
            for config_type in request.config_types:
                try:
                    count = await self._export_config_type(
                        splunk_client,
                        app_dir,
                        config_type,
                        request.include_default_configs,
                    )
                    exported_counts[config_type.value] = count
                except Exception as e:
                    logger.warning(f"Failed to export {config_type.value}: {e}")
                    exported_counts[config_type.value] = 0

            # Create the tarball
            tar_bytes = self._create_tarball(app_dir, request.app_name)

        result = ExportResult(
            app_name=request.app_name,
            filename=f"{request.app_name}.spl",
            size_bytes=len(tar_bytes),
            exported_configs=exported_counts,
            created_at=datetime.utcnow(),
        )

        return tar_bytes, result

    def _create_app_structure(self, app_dir: Path, request: ExportRequest) -> None:
        """Create the basic Splunk app directory structure."""
        # Create directories
        (app_dir / "default").mkdir(parents=True, exist_ok=True)
        (app_dir / "local").mkdir(exist_ok=True)
        (app_dir / "metadata").mkdir(exist_ok=True)
        (app_dir / "lookups").mkdir(exist_ok=True)

        # Create app.conf
        app_conf = f"""[install]
is_configured = 0

[ui]
is_visible = 1
label = {request.app_label or request.app_name}

[launcher]
author = Faux Splunk Cloud Export
description = {request.app_description or f'Exported configurations from Faux Splunk Cloud'}
version = {request.app_version}

[package]
id = {request.app_name}
check_for_updates = 0
"""
        (app_dir / "default" / "app.conf").write_text(app_conf)

        # Create default.meta for permissions
        default_meta = """[]
export = system

[eventtypes]
export = system

[props]
export = system

[transforms]
export = system

[macros]
export = system

[savedsearches]
export = system
"""
        (app_dir / "metadata" / "default.meta").write_text(default_meta)

    async def _export_config_type(
        self,
        client: SplunkClientService,
        app_dir: Path,
        config_type: ExportableConfigType,
        include_defaults: bool,
    ) -> int:
        """Export a specific configuration type."""
        exporters = {
            ExportableConfigType.INDEXES: self._export_indexes,
            ExportableConfigType.HEC_TOKENS: self._export_hec_tokens,
            ExportableConfigType.SAVED_SEARCHES: self._export_saved_searches,
            ExportableConfigType.DASHBOARDS: self._export_dashboards,
            ExportableConfigType.MACROS: self._export_macros,
            ExportableConfigType.EVENTTYPES: self._export_eventtypes,
            ExportableConfigType.TAGS: self._export_tags,
            ExportableConfigType.FIELD_EXTRACTIONS: self._export_field_extractions,
            ExportableConfigType.PROPS: self._export_props,
            ExportableConfigType.TRANSFORMS: self._export_transforms,
            ExportableConfigType.LOOKUPS: self._export_lookups,
            ExportableConfigType.ALERTS: self._export_alerts,
            ExportableConfigType.REPORTS: self._export_reports,
        }

        exporter = exporters.get(config_type)
        if exporter:
            return await exporter(client, app_dir, include_defaults)
        return 0

    async def _export_indexes(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export index configurations."""
        indexes_conf = ""
        count = 0

        try:
            indexes = client.list_indexes()
            for idx in indexes:
                name = idx.get("name", "")

                # Skip internal indexes unless defaults requested
                if not include_defaults and name.startswith("_"):
                    continue

                # Skip default indexes
                if not include_defaults and name in ["main", "summary", "history"]:
                    continue

                indexes_conf += f"[{name}]\n"

                # Add common settings
                if idx.get("datatype"):
                    indexes_conf += f"datatype = {idx['datatype']}\n"
                if idx.get("frozenTimePeriodInSecs"):
                    indexes_conf += f"frozenTimePeriodInSecs = {idx['frozenTimePeriodInSecs']}\n"
                if idx.get("maxTotalDataSizeMB"):
                    indexes_conf += f"maxTotalDataSizeMB = {idx['maxTotalDataSizeMB']}\n"
                if idx.get("homePath"):
                    indexes_conf += f"homePath = $SPLUNK_DB/{name}/db\n"
                if idx.get("coldPath"):
                    indexes_conf += f"coldPath = $SPLUNK_DB/{name}/colddb\n"
                if idx.get("thawedPath"):
                    indexes_conf += f"thawedPath = $SPLUNK_DB/{name}/thaweddb\n"

                indexes_conf += "\n"
                count += 1

        except Exception as e:
            logger.warning(f"Error exporting indexes: {e}")

        if indexes_conf:
            (app_dir / "default" / "indexes.conf").write_text(indexes_conf)

        return count

    async def _export_hec_tokens(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export HEC token configurations (without actual tokens)."""
        inputs_conf = ""
        count = 0

        try:
            tokens = client.list_hec_tokens()
            for token in tokens:
                name = token.get("name", "")
                if not name:
                    continue

                inputs_conf += f"[http://{name}]\n"
                inputs_conf += "disabled = 0\n"

                if token.get("index"):
                    inputs_conf += f"index = {token['index']}\n"
                if token.get("indexes"):
                    inputs_conf += f"indexes = {','.join(token['indexes'])}\n"
                if token.get("sourcetype"):
                    inputs_conf += f"sourcetype = {token['sourcetype']}\n"
                if token.get("source"):
                    inputs_conf += f"source = {token['source']}\n"

                # Don't export actual token value for security
                inputs_conf += "# token = <regenerate after import>\n"
                inputs_conf += "\n"
                count += 1

        except Exception as e:
            logger.warning(f"Error exporting HEC tokens: {e}")

        if inputs_conf:
            (app_dir / "default" / "inputs.conf").write_text(inputs_conf)

        return count

    async def _export_saved_searches(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export saved searches."""
        searches_conf = ""
        count = 0

        try:
            service = client._service
            if not service:
                return 0

            for search in service.saved_searches:
                name = search.name

                # Skip if it's a built-in
                if not include_defaults and search.access.get("app") == "system":
                    continue

                searches_conf += f"[{name}]\n"

                # Core search properties
                if hasattr(search, "search") and search.search:
                    searches_conf += f"search = {search.search}\n"
                if hasattr(search, "description") and search.description:
                    searches_conf += f"description = {search.description}\n"

                # Scheduling
                if hasattr(search, "cron_schedule") and search.cron_schedule:
                    searches_conf += f"cron_schedule = {search.cron_schedule}\n"
                if hasattr(search, "is_scheduled"):
                    searches_conf += f"enableSched = {1 if search.is_scheduled else 0}\n"

                # Time range
                if hasattr(search, "dispatch_earliest_time") and search.dispatch_earliest_time:
                    searches_conf += f"dispatch.earliest_time = {search.dispatch_earliest_time}\n"
                if hasattr(search, "dispatch_latest_time") and search.dispatch_latest_time:
                    searches_conf += f"dispatch.latest_time = {search.dispatch_latest_time}\n"

                searches_conf += "\n"
                count += 1

        except Exception as e:
            logger.warning(f"Error exporting saved searches: {e}")

        if searches_conf:
            (app_dir / "default" / "savedsearches.conf").write_text(searches_conf)

        return count

    async def _export_dashboards(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export dashboards."""
        count = 0
        views_dir = app_dir / "default" / "data" / "ui" / "views"
        views_dir.mkdir(parents=True, exist_ok=True)

        try:
            service = client._service
            if not service:
                return 0

            for dashboard in service.dashboards:
                name = dashboard.name

                if not include_defaults and dashboard.access.get("app") == "system":
                    continue

                # Get the dashboard XML
                if hasattr(dashboard, "content"):
                    content = dashboard.content
                    if content:
                        (views_dir / f"{name}.xml").write_text(content)
                        count += 1

        except Exception as e:
            logger.warning(f"Error exporting dashboards: {e}")

        return count

    async def _export_macros(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export search macros."""
        macros_conf = ""
        count = 0

        try:
            service = client._service
            if not service:
                return 0

            # Get macros via REST endpoint
            response = service.get("configs/conf-macros")
            for macro in response.body.entry:
                name = macro.title

                if not include_defaults and macro.access.get("app") == "system":
                    continue

                macros_conf += f"[{name}]\n"

                content = macro.content
                if content.get("definition"):
                    macros_conf += f"definition = {content['definition']}\n"
                if content.get("args"):
                    macros_conf += f"args = {content['args']}\n"
                if content.get("description"):
                    macros_conf += f"description = {content['description']}\n"
                if content.get("validation"):
                    macros_conf += f"validation = {content['validation']}\n"

                macros_conf += "\n"
                count += 1

        except Exception as e:
            logger.warning(f"Error exporting macros: {e}")

        if macros_conf:
            (app_dir / "default" / "macros.conf").write_text(macros_conf)

        return count

    async def _export_eventtypes(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export event types."""
        eventtypes_conf = ""
        count = 0

        try:
            service = client._service
            if not service:
                return 0

            response = service.get("saved/eventtypes")
            for et in response.body.entry:
                name = et.title

                if not include_defaults and et.access.get("app") == "system":
                    continue

                eventtypes_conf += f"[{name}]\n"
                content = et.content

                if content.get("search"):
                    eventtypes_conf += f"search = {content['search']}\n"
                if content.get("description"):
                    eventtypes_conf += f"description = {content['description']}\n"
                if content.get("priority"):
                    eventtypes_conf += f"priority = {content['priority']}\n"

                eventtypes_conf += "\n"
                count += 1

        except Exception as e:
            logger.warning(f"Error exporting eventtypes: {e}")

        if eventtypes_conf:
            (app_dir / "default" / "eventtypes.conf").write_text(eventtypes_conf)

        return count

    async def _export_tags(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export tags."""
        tags_conf = ""
        count = 0

        try:
            service = client._service
            if not service:
                return 0

            response = service.get("configs/conf-tags")
            for tag in response.body.entry:
                name = tag.title

                tags_conf += f"[{name}]\n"
                content = tag.content

                for key, value in content.items():
                    if not key.startswith("eai:"):
                        tags_conf += f"{key} = {value}\n"

                tags_conf += "\n"
                count += 1

        except Exception as e:
            logger.warning(f"Error exporting tags: {e}")

        if tags_conf:
            (app_dir / "default" / "tags.conf").write_text(tags_conf)

        return count

    async def _export_field_extractions(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export field extractions (combined with props export)."""
        # Field extractions are part of props.conf
        return 0

    async def _export_props(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export props.conf settings."""
        props_conf = ""
        count = 0

        try:
            service = client._service
            if not service:
                return 0

            response = service.get("configs/conf-props")
            for stanza in response.body.entry:
                name = stanza.title

                if not include_defaults and stanza.access.get("app") == "system":
                    continue

                props_conf += f"[{name}]\n"
                content = stanza.content

                for key, value in content.items():
                    if not key.startswith("eai:"):
                        props_conf += f"{key} = {value}\n"

                props_conf += "\n"
                count += 1

        except Exception as e:
            logger.warning(f"Error exporting props: {e}")

        if props_conf:
            (app_dir / "default" / "props.conf").write_text(props_conf)

        return count

    async def _export_transforms(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export transforms.conf settings."""
        transforms_conf = ""
        count = 0

        try:
            service = client._service
            if not service:
                return 0

            response = service.get("configs/conf-transforms")
            for stanza in response.body.entry:
                name = stanza.title

                if not include_defaults and stanza.access.get("app") == "system":
                    continue

                transforms_conf += f"[{name}]\n"
                content = stanza.content

                for key, value in content.items():
                    if not key.startswith("eai:"):
                        transforms_conf += f"{key} = {value}\n"

                transforms_conf += "\n"
                count += 1

        except Exception as e:
            logger.warning(f"Error exporting transforms: {e}")

        if transforms_conf:
            (app_dir / "default" / "transforms.conf").write_text(transforms_conf)

        return count

    async def _export_lookups(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export lookup definitions and files."""
        count = 0

        try:
            service = client._service
            if not service:
                return 0

            # Export lookup table files
            lookups_dir = app_dir / "lookups"
            response = service.get("data/lookup-table-files")

            for lookup in response.body.entry:
                name = lookup.title
                if name.endswith(".csv") or name.endswith(".csv.gz"):
                    try:
                        # Download the lookup file
                        content = service.get(f"data/lookup-table-files/{name}")
                        if hasattr(content, "body"):
                            (lookups_dir / name).write_bytes(content.body.read())
                            count += 1
                    except Exception:
                        pass

        except Exception as e:
            logger.warning(f"Error exporting lookups: {e}")

        return count

    async def _export_alerts(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export alerts (saved searches with alerts)."""
        # Alerts are part of saved searches
        return 0

    async def _export_reports(
        self,
        client: SplunkClientService,
        app_dir: Path,
        include_defaults: bool,
    ) -> int:
        """Export reports (saved searches without scheduling)."""
        # Reports are part of saved searches
        return 0

    def _create_tarball(self, app_dir: Path, app_name: str) -> bytes:
        """Create a .spl (tar.gz) file from the app directory."""
        buffer = io.BytesIO()

        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            # Add all files from app directory
            for file_path in app_dir.rglob("*"):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(app_dir.parent))
                    tar.add(file_path, arcname=arcname)

        buffer.seek(0)
        return buffer.read()


# Global instance
config_export_service = ConfigExportService()
