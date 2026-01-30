"""
Pytest-BDD specific configuration and fixtures.

This module provides fixtures specific to BDD step definitions.
"""

import pytest
from pytest_bdd import given


@pytest.fixture
def datatable():
    """
    Fixture to handle Gherkin data tables.

    Note: pytest-bdd handles data tables through step arguments.
    This fixture provides a list-based fallback for table parsing.
    """
    return []


# Re-export fixtures from main conftest for step files
from tests.conftest import (
    async_client,
    context,
    faker,
    fixed_datetime,
    frozen_time,
    make_instance,
    make_instance_config,
    make_instance_create,
    mock_docker_client,
    mock_instance_manager,
    mock_splunk_client,
)

__all__ = [
    "async_client",
    "context",
    "datatable",
    "faker",
    "fixed_datetime",
    "frozen_time",
    "make_instance",
    "make_instance_config",
    "make_instance_create",
    "mock_docker_client",
    "mock_instance_manager",
    "mock_splunk_client",
]
