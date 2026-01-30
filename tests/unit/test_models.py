"""
Unit tests for Pydantic models.

These tests validate model construction, validation, and serialization
without any external dependencies.
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from faux_splunk_cloud.models.instance import (
    Instance,
    InstanceConfig,
    InstanceCreate,
    InstanceCredentials,
    InstanceEndpoints,
    InstanceStatus,
    InstanceTopology,
)


class TestInstanceConfig:
    """Tests for InstanceConfig model."""

    @pytest.mark.unit
    def test_default_config_creation(self):
        """Test creating config with all defaults."""
        config = InstanceConfig()

        assert config.topology == InstanceTopology.STANDALONE
        assert config.splunk_version == "9.3.2"
        assert config.experience == "victoria"
        assert config.memory_mb == 2048
        assert config.cpu_cores == 1.0

    @pytest.mark.unit
    def test_config_with_custom_values(self):
        """Test creating config with custom values."""
        config = InstanceConfig(
            topology=InstanceTopology.DISTRIBUTED_MINIMAL,
            splunk_version="9.2.0",
            memory_mb=4096,
            cpu_cores=2.0,
        )

        assert config.topology == InstanceTopology.DISTRIBUTED_MINIMAL
        assert config.splunk_version == "9.2.0"
        assert config.memory_mb == 4096
        assert config.cpu_cores == 2.0

    @pytest.mark.unit
    def test_all_topologies_valid(self):
        """Test all topology enum values are accepted."""
        for topology in InstanceTopology:
            config = InstanceConfig(topology=topology)
            assert config.topology == topology


class TestInstanceCreate:
    """Tests for InstanceCreate request model."""

    @pytest.mark.unit
    def test_minimal_create_request(self):
        """Test creating instance with minimal fields."""
        request = InstanceCreate(name="test-instance")

        assert request.name == "test-instance"
        assert request.ttl_hours == 24  # Default
        assert request.labels == {}  # Default

    @pytest.mark.unit
    def test_create_with_ttl(self):
        """Test creating instance with custom TTL."""
        request = InstanceCreate(name="short-lived", ttl_hours=4)

        assert request.ttl_hours == 4

    @pytest.mark.unit
    def test_valid_instance_names(self):
        """Test valid instance name patterns."""
        valid_names = [
            "test",
            "test-instance",
            "my-splunk-01",
            "a" * 63,  # Max length
        ]

        for name in valid_names:
            request = InstanceCreate(name=name)
            assert request.name == name

    @pytest.mark.unit
    def test_invalid_instance_names(self):
        """Test invalid instance name patterns are rejected."""
        invalid_names = [
            "",  # Empty
            "Test",  # Uppercase
            "test_instance",  # Underscore
            "test instance",  # Space
            "-test",  # Leading hyphen
            "test-",  # Trailing hyphen
            "a" * 64,  # Too long
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError):
                InstanceCreate(name=name)

    @pytest.mark.unit
    def test_ttl_range_validation(self):
        """Test TTL must be within valid range."""
        # Valid TTLs
        InstanceCreate(name="test", ttl_hours=1)
        InstanceCreate(name="test", ttl_hours=168)

        # Invalid TTLs
        with pytest.raises(ValidationError):
            InstanceCreate(name="test", ttl_hours=0)

        with pytest.raises(ValidationError):
            InstanceCreate(name="test", ttl_hours=169)


class TestInstanceEndpoints:
    """Tests for InstanceEndpoints model."""

    @pytest.mark.unit
    def test_endpoints_creation(self):
        """Test creating endpoints with all URLs."""
        endpoints = InstanceEndpoints(
            web_url="http://localhost:8000",
            api_url="http://localhost:8089",
            hec_url="http://localhost:8088",
            acs_url="http://localhost:8899/stack/adminconfig/v2",
            s2s_port=9997,
        )

        assert endpoints.web_url == "http://localhost:8000"
        assert endpoints.s2s_port == 9997

    @pytest.mark.unit
    def test_optional_endpoints(self):
        """Test endpoints with optional fields."""
        endpoints = InstanceEndpoints()

        assert endpoints.web_url is None
        assert endpoints.s2s_port is None


class TestInstanceCredentials:
    """Tests for InstanceCredentials model."""

    @pytest.mark.unit
    def test_credentials_creation(self):
        """Test creating credentials."""
        creds = InstanceCredentials(
            admin_username="admin",
            admin_password="secret123",
            acs_token="token-abc",
            hec_token="hec-xyz",
        )

        assert creds.admin_username == "admin"
        assert creds.admin_password == "secret123"


class TestInstance:
    """Tests for complete Instance model."""

    @pytest.mark.unit
    def test_instance_creation(self, make_instance):
        """Test creating a complete instance."""
        instance = make_instance(name="full-test")

        assert instance.name == "full-test"
        assert instance.id.startswith("fsc-")
        assert instance.status == InstanceStatus.RUNNING

    @pytest.mark.unit
    def test_instance_status_transitions(self, make_instance):
        """Test instance can have different statuses."""
        for status in InstanceStatus:
            instance = make_instance(status=status)
            assert instance.status == status

    @pytest.mark.unit
    def test_instance_serialization(self, make_instance):
        """Test instance can be serialized to dict/JSON."""
        instance = make_instance(name="serialize-test")
        data = instance.model_dump()

        assert data["name"] == "serialize-test"
        assert "id" in data
        assert "status" in data
        assert "config" in data
        assert "endpoints" in data

    @pytest.mark.unit
    def test_instance_with_error(self, make_instance):
        """Test instance can record error state."""
        instance = make_instance(
            status=InstanceStatus.ERROR,
            error_message="Container failed to start",
        )

        assert instance.status == InstanceStatus.ERROR
        assert instance.error_message == "Container failed to start"


class TestInstanceStatus:
    """Tests for InstanceStatus enum."""

    @pytest.mark.unit
    def test_all_statuses_defined(self):
        """Ensure all expected statuses are defined."""
        expected = {
            "pending",
            "provisioning",
            "starting",
            "running",
            "stopping",
            "stopped",
            "error",
            "terminated",
        }

        actual = {s.value for s in InstanceStatus}
        assert expected == actual

    @pytest.mark.unit
    def test_status_from_string(self):
        """Test creating status from string value."""
        assert InstanceStatus("running") == InstanceStatus.RUNNING
        assert InstanceStatus("stopped") == InstanceStatus.STOPPED


class TestInstanceTopology:
    """Tests for InstanceTopology enum."""

    @pytest.mark.unit
    def test_all_topologies_defined(self):
        """Ensure all expected topologies are defined."""
        expected = {
            "standalone",
            "distributed_minimal",
            "distributed_clustered",
            "victoria_full",
        }

        actual = {t.value for t in InstanceTopology}
        assert expected == actual
