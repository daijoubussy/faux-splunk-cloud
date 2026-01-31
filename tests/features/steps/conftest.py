"""
Pytest-BDD specific configuration and fixtures.

This module provides fixtures specific to BDD step definitions.
"""

import pytest


# Re-export fixtures from main conftest for step files
from tests.conftest import (
    async_client,
    context,
    faker,
    fixed_datetime,
    frozen_time,
    make_attack_step,
    make_campaign,
    make_instance,
    make_instance_config,
    make_instance_create,
    make_threat_actor,
    mock_docker_client,
    mock_instance_manager,
    mock_kill_chain_engine,
    mock_splunk_client,
)

__all__ = [
    "async_client",
    "context",
    "faker",
    "fixed_datetime",
    "frozen_time",
    "make_attack_step",
    "make_campaign",
    "make_instance",
    "make_instance_config",
    "make_instance_create",
    "make_threat_actor",
    "mock_docker_client",
    "mock_instance_manager",
    "mock_kill_chain_engine",
    "mock_splunk_client",
]
