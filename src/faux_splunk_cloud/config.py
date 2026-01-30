"""
Configuration management for Faux Splunk Cloud.

This module provides configuration settings that align with Splunk Cloud Victoria
platform operation standards.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SplunkVictoriaDefaults:
    """
    Default configurations that mirror Splunk Cloud Victoria Experience.

    Based on Splunk Cloud Platform Service Details and SVA documentation.
    """

    # Splunk version to use (should be recent stable)
    SPLUNK_VERSION = "9.3.2"

    # Default index settings per Victoria Experience
    DEFAULT_INDEX_SETTINGS = {
        "maxDataSizeMB": 500000,  # 500GB default
        "searchableDays": 90,
        "maxTotalDataSizeMB": 500000,
        "frozenTimePeriodInSecs": 7776000,  # 90 days
        "datatype": "event",
    }

    # Victoria Experience enables real-time search by default
    REALTIME_SEARCH_ENABLED = True

    # Default HEC settings
    HEC_DEFAULT_SETTINGS = {
        "useACK": False,
        "disabled": False,
        "enableSSL": True,
    }

    # Default roles available in Splunk Cloud
    DEFAULT_ROLES = [
        "admin",
        "sc_admin",  # Splunk Cloud admin
        "power",
        "user",
        "can_delete",
    ]

    # ACS API version
    ACS_API_VERSION = "v2"

    # Default indexes created in Victoria Experience
    DEFAULT_INDEXES = [
        "main",
        "summary",
        "_internal",
        "_introspection",
        "_audit",
        "_metrics",
        "_telemetry",
    ]


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="FSC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server configuration
    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8800, description="API server port")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Data directory for instance state
    data_dir: Path = Field(
        default=Path.home() / ".faux-splunk-cloud",
        description="Directory for storing instance data",
    )

    # Docker configuration
    docker_network_prefix: str = Field(
        default="fsc", description="Prefix for Docker networks"
    )
    splunk_image: str = Field(
        default="splunk/splunk:9.3.2",
        description="Splunk Enterprise Docker image to use",
    )

    # Default Splunk admin credentials for ephemeral instances
    default_admin_password: SecretStr = Field(
        default=SecretStr("FauxSplunk123!"),
        description="Default admin password for new instances",
    )

    # Instance lifecycle
    default_ttl_hours: int = Field(
        default=24, description="Default time-to-live for instances in hours"
    )
    max_ttl_hours: int = Field(
        default=168, description="Maximum TTL (1 week)"  # 1 week
    )
    cleanup_interval_minutes: int = Field(
        default=5, description="Interval for cleanup job"
    )

    # Resource limits per instance
    max_memory_mb: int = Field(
        default=4096, description="Maximum memory per Splunk container"
    )
    max_cpu_count: float = Field(
        default=2.0, description="Maximum CPU cores per container"
    )

    # ACS API simulation
    acs_base_url: str = Field(
        default="http://localhost:8800",
        description="Base URL for ACS API (mimics admin.splunk.com)",
    )
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("faux-splunk-cloud-dev-secret-change-in-production"),
        description="Secret key for JWT token generation",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(
        default=24, description="JWT token expiration in hours"
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///~/.faux-splunk-cloud/fsc.db",
        description="Database connection URL",
    )

    # Experience mode
    experience: Literal["victoria", "classic"] = Field(
        default="victoria",
        description="Splunk Cloud Experience mode (victoria recommended)",
    )

    def get_database_url(self) -> str:
        """Get expanded database URL with home directory resolved."""
        return self.database_url.replace("~", str(Path.home()))

    def ensure_data_dir(self) -> Path:
        """Ensure data directory exists and return it."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir


# Global settings instance
settings = Settings()
