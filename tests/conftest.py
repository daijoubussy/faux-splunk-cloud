"""
Global pytest configuration and fixtures for Faux Splunk Cloud.

This module ensures 100% deterministic test execution through:
1. Fixed random seeds for all random operations
2. Frozen time for time-dependent tests
3. Isolated Docker containers per session
4. Transaction rollback for database operations
"""

import asyncio
import os
import random
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from faker import Faker
from httpx import ASGITransport, AsyncClient

# Set deterministic seeds BEFORE any other imports that might use random
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
Faker.seed(RANDOM_SEED)

# Import application modules after seeding
from faux_splunk_cloud.api.app import create_app
from faux_splunk_cloud.config import Settings
from faux_splunk_cloud.models.instance import (
    Instance,
    InstanceConfig,
    InstanceCreate,
    InstanceCredentials,
    InstanceEndpoints,
    InstanceStatus,
    InstanceTopology,
)


# =============================================================================
# Session-Scoped Fixtures (Run once per test session)
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def faker() -> Faker:
    """Seeded Faker instance for deterministic fake data."""
    fake = Faker()
    Faker.seed(RANDOM_SEED)
    return fake


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Temporary directory for test data that persists across the session."""
    return tmp_path_factory.mktemp("fsc_test_data")


@pytest.fixture(scope="session")
def test_settings(test_data_dir: Path) -> Settings:
    """Test-specific settings with isolated data directory."""
    return Settings(
        host="127.0.0.1",
        port=8899,
        debug=True,
        data_dir=test_data_dir,
        database_url=f"sqlite+aiosqlite:///{test_data_dir}/test.db",
        jwt_secret_key="test-secret-key-for-testing-only",
        default_ttl_hours=1,
        max_ttl_hours=24,
    )


# =============================================================================
# Function-Scoped Fixtures (Fresh per test)
# =============================================================================


@pytest.fixture
def frozen_time():
    """
    Fixture to freeze time at a known point.

    Usage:
        def test_something(frozen_time):
            with frozen_time("2025-01-30 12:00:00"):
                # Time is frozen here
                pass
    """
    from freezegun import freeze_time

    return freeze_time


@pytest.fixture
def fixed_datetime() -> datetime:
    """A fixed datetime for deterministic time-based tests."""
    return datetime(2025, 1, 30, 12, 0, 0)


@pytest.fixture
def app():
    """Create a fresh FastAPI application for testing."""
    return create_app()


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for API testing.

    Uses ASGI transport to test without network calls.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_docker_client() -> MagicMock:
    """Mock Docker client for unit tests that don't need real Docker."""
    mock = MagicMock()
    mock.containers.list.return_value = []
    mock.networks.list.return_value = []
    mock.volumes.list.return_value = []
    return mock


@pytest.fixture
def mock_instance_manager() -> AsyncMock:
    """Mock instance manager for isolated API testing."""
    mock = AsyncMock()
    mock.list_instances.return_value = []
    mock.get_instance.return_value = None
    mock.create_instance.return_value = None
    return mock


@pytest.fixture
def mock_splunk_client() -> MagicMock:
    """Mock Splunk SDK client for tests without real Splunk."""
    mock = MagicMock()
    mock.check_health.return_value = True
    mock.list_indexes.return_value = []
    mock.list_hec_tokens.return_value = []
    return mock


# =============================================================================
# Factory Fixtures (Deterministic Test Data)
# =============================================================================


@pytest.fixture
def make_instance_config():
    """Factory for creating InstanceConfig with defaults."""

    def _make(
        topology: InstanceTopology = InstanceTopology.STANDALONE,
        splunk_version: str = "9.3.2",
        memory_mb: int = 2048,
        cpu_cores: float = 1.0,
        **kwargs,
    ) -> InstanceConfig:
        return InstanceConfig(
            topology=topology,
            splunk_version=splunk_version,
            memory_mb=memory_mb,
            cpu_cores=cpu_cores,
            **kwargs,
        )

    return _make


@pytest.fixture
def make_instance_create(make_instance_config):
    """Factory for creating InstanceCreate requests."""

    def _make(
        name: str = "test-instance",
        ttl_hours: int = 24,
        labels: dict | None = None,
        config: InstanceConfig | None = None,
    ) -> InstanceCreate:
        return InstanceCreate(
            name=name,
            ttl_hours=ttl_hours,
            labels=labels or {},
            config=config or make_instance_config(),
        )

    return _make


@pytest.fixture
def make_instance(fixed_datetime, make_instance_config):
    """Factory for creating complete Instance objects."""
    counter = 0

    def _make(
        name: str | None = None,
        status: InstanceStatus = InstanceStatus.RUNNING,
        **kwargs,
    ) -> Instance:
        nonlocal counter
        counter += 1

        instance_id = kwargs.pop("id", f"fsc-test-{counter:04d}")
        instance_name = name or f"test-instance-{counter}"

        return Instance(
            id=instance_id,
            name=instance_name,
            status=status,
            config=kwargs.pop("config", make_instance_config()),
            created_at=fixed_datetime,
            expires_at=fixed_datetime.replace(hour=fixed_datetime.hour + 24),
            endpoints=InstanceEndpoints(
                web_url=f"http://localhost:{8000 + counter}",
                api_url=f"http://localhost:{8089 + counter}",
                hec_url=f"http://localhost:{8088 + counter}",
                acs_url=f"http://localhost:8899/{instance_id}/adminconfig/v2",
            ),
            credentials=InstanceCredentials(
                admin_username="admin",
                admin_password="TestPassword123!",
                acs_token=f"test-acs-token-{counter}",
                hec_token=f"test-hec-token-{counter}",
            ),
            **kwargs,
        )

    return _make


# =============================================================================
# BDD Step Fixtures
# =============================================================================


@pytest.fixture
def context():
    """
    Shared context dictionary for BDD scenarios.

    Allows steps to share state without global variables.
    """
    return {}


# =============================================================================
# Cleanup Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_random_seed():
    """Reset random seed before each test for determinism."""
    random.seed(RANDOM_SEED)
    Faker.seed(RANDOM_SEED)
    yield


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean environment variables for each test."""
    # Store original env vars
    original_env = os.environ.copy()

    # Remove any FSC_ prefixed vars that might interfere
    for key in list(os.environ.keys()):
        if key.startswith("FSC_"):
            del os.environ[key]

    yield

    # Restore original env vars
    os.environ.clear()
    os.environ.update(original_env)


# =============================================================================
# Markers Registration
# =============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Fast isolated unit tests")
    config.addinivalue_line("markers", "integration: Tests requiring external services")
    config.addinivalue_line("markers", "e2e: End-to-end workflow tests")
    config.addinivalue_line("markers", "slow: Tests taking >5 seconds")
    config.addinivalue_line("markers", "docker: Tests requiring Docker daemon")
    config.addinivalue_line("markers", "critical: Must pass for deployment")
    config.addinivalue_line("markers", "wip: Work in progress, may be skipped")
