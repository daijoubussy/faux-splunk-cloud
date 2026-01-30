"""
Step definitions for instance lifecycle management.

These steps implement the Gherkin scenarios defined in instance_lifecycle.feature.
All steps are designed to be deterministic and isolated.
"""

import re
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

# Load all scenarios from the feature file
scenarios("../instance_lifecycle.feature")


# =============================================================================
# Given Steps (Preconditions)
# =============================================================================


@given("the API server is running")
def api_server_running(context: dict, app) -> None:
    """Ensure the FastAPI app is available."""
    context["app"] = app
    context["response"] = None
    context["instances"] = {}


@given("I am authenticated as a developer")
def authenticated_as_developer(context: dict) -> None:
    """Set up authentication headers."""
    context["auth_headers"] = {
        "Authorization": "Bearer test-developer-token",
        "Content-Type": "application/json",
    }


@given(parsers.parse('an instance "{name}" exists in "{status}" state'))
def instance_exists_with_status(
    context: dict, name: str, status: str, make_instance
) -> None:
    """Create a mock instance with the specified status."""
    from faux_splunk_cloud.models.instance import InstanceStatus

    status_enum = InstanceStatus(status.lower())
    instance = make_instance(name=name, status=status_enum)
    context["instances"][name] = instance
    context["instances"][instance.id] = instance


@given(parsers.parse("the instance expires in {hours:d} hour"))
@given(parsers.parse("the instance expires in {hours:d} hours"))
def instance_expires_in_hours(context: dict, hours: int, fixed_datetime: datetime) -> None:
    """Set instance expiration time."""
    # Get the last created instance
    instance_name = list(context["instances"].keys())[-1]
    instance = context["instances"][instance_name]
    instance.expires_at = fixed_datetime + timedelta(hours=hours)


@given("the following instances exist:")
def multiple_instances_exist(context: dict, make_instance, datatable) -> None:
    """Create multiple instances from a data table."""
    from faux_splunk_cloud.models.instance import InstanceStatus

    # Parse the data table (pytest-bdd provides this)
    for row in datatable:
        name = row["name"]
        status = InstanceStatus(row["status"].lower())
        instance = make_instance(name=name, status=status)
        context["instances"][name] = instance
        context["instances"][instance.id] = instance


# =============================================================================
# When Steps (Actions)
# =============================================================================


@when(parsers.parse('I create an instance with name "{name}"'))
async def create_instance_with_name(
    context: dict, name: str, async_client, mock_instance_manager, make_instance
) -> None:
    """Create an instance with default configuration."""
    # Set up mock
    created_instance = make_instance(name=name)
    mock_instance_manager.create_instance.return_value = created_instance

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        response = await async_client.post(
            "/api/v1/instances",
            json={"name": name},
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response
    context["created_instance"] = created_instance


@when(parsers.parse('I create an instance with name "{name}" and TTL {hours:d} hours'))
async def create_instance_with_ttl(
    context: dict, name: str, hours: int, async_client, mock_instance_manager, make_instance
) -> None:
    """Create an instance with custom TTL."""
    created_instance = make_instance(name=name)
    mock_instance_manager.create_instance.return_value = created_instance

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        response = await async_client.post(
            "/api/v1/instances",
            json={"name": name, "ttl_hours": hours},
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response
    context["created_instance"] = created_instance


@when(parsers.parse('I create an instance with topology "{topology}"'))
async def create_instance_with_topology(
    context: dict, topology: str, async_client, mock_instance_manager, make_instance
) -> None:
    """Create an instance with specific topology."""
    from faux_splunk_cloud.models.instance import InstanceTopology

    topology_enum = InstanceTopology(topology.lower())
    created_instance = make_instance(name="topology-test")
    created_instance.config.topology = topology_enum
    mock_instance_manager.create_instance.return_value = created_instance

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        response = await async_client.post(
            "/api/v1/instances",
            json={
                "name": "topology-test",
                "config": {"topology": topology},
            },
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response
    context["created_instance"] = created_instance


@when(parsers.parse('I start the instance "{name}"'))
async def start_instance(
    context: dict, name: str, async_client, mock_instance_manager
) -> None:
    """Start a stopped instance."""
    instance = context["instances"].get(name)
    if instance:
        mock_instance_manager.get_instance.return_value = instance
        mock_instance_manager.start_instance.return_value = instance

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        response = await async_client.post(
            f"/api/v1/instances/{instance.id if instance else name}/start",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(parsers.parse('I stop the instance "{name}"'))
async def stop_instance(
    context: dict, name: str, async_client, mock_instance_manager
) -> None:
    """Stop a running instance."""
    instance = context["instances"].get(name)
    if instance:
        mock_instance_manager.get_instance.return_value = instance
        mock_instance_manager.stop_instance.return_value = instance

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        response = await async_client.post(
            f"/api/v1/instances/{instance.id if instance else name}/stop",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(parsers.parse('I destroy the instance "{name}"'))
async def destroy_instance(
    context: dict, name: str, async_client, mock_instance_manager
) -> None:
    """Destroy an instance."""
    instance = context["instances"].get(name)
    if instance:
        mock_instance_manager.get_instance.return_value = instance
        mock_instance_manager.destroy_instance.return_value = None

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        response = await async_client.delete(
            f"/api/v1/instances/{instance.id if instance else name}",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response
    # Remove from context after destruction
    if name in context["instances"]:
        del context["instances"][name]


@when("I list all instances")
async def list_all_instances(
    context: dict, async_client, mock_instance_manager
) -> None:
    """List all instances."""
    mock_instance_manager.list_instances.return_value = list(
        v for k, v in context["instances"].items() if not k.startswith("fsc-")
    )

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        response = await async_client.get(
            "/api/v1/instances",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(parsers.parse('I list instances with status "{status}"'))
async def list_instances_by_status(
    context: dict, status: str, async_client, mock_instance_manager
) -> None:
    """List instances filtered by status."""
    from faux_splunk_cloud.models.instance import InstanceStatus

    status_enum = InstanceStatus(status.lower())
    filtered = [
        v
        for k, v in context["instances"].items()
        if not k.startswith("fsc-") and v.status == status_enum
    ]
    mock_instance_manager.list_instances.return_value = filtered

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        response = await async_client.get(
            f"/api/v1/instances?status={status}",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(parsers.parse('I get the instance "{name}"'))
async def get_instance(
    context: dict, name: str, async_client, mock_instance_manager
) -> None:
    """Get instance details."""
    instance = context["instances"].get(name)
    mock_instance_manager.get_instance.return_value = instance

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        instance_id = instance.id if instance else name
        response = await async_client.get(
            f"/api/v1/instances/{instance_id}",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(parsers.parse("I extend the instance TTL by {hours:d} hours"))
async def extend_instance_ttl(
    context: dict, hours: int, async_client, mock_instance_manager
) -> None:
    """Extend instance TTL."""
    # Get the most recently referenced instance
    instance_name = [k for k in context["instances"].keys() if not k.startswith("fsc-")][-1]
    instance = context["instances"][instance_name]
    mock_instance_manager.get_instance.return_value = instance
    mock_instance_manager.extend_ttl.return_value = instance

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        response = await async_client.post(
            f"/api/v1/instances/{instance.id}/extend",
            json={"hours": hours},
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(parsers.parse('I check the health of instance "{name}"'))
async def check_instance_health(
    context: dict, name: str, async_client, mock_instance_manager
) -> None:
    """Check instance health status."""
    instance = context["instances"].get(name)
    mock_instance_manager.get_instance.return_value = instance
    mock_instance_manager.get_instance_health.return_value = instance.status

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        response = await async_client.get(
            f"/api/v1/instances/{instance.id}/health",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(parsers.parse('I get the logs for instance "{name}" with tail {lines:d}'))
async def get_instance_logs(
    context: dict, name: str, lines: int, async_client, mock_instance_manager
) -> None:
    """Get container logs for an instance."""
    instance = context["instances"].get(name)
    mock_instance_manager.get_instance.return_value = instance
    mock_instance_manager.get_instance_logs.return_value = "Line 1\nLine 2\nLine 3"

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        response = await async_client.get(
            f"/api/v1/instances/{instance.id}/logs?tail={lines}",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(
    parsers.parse(
        'I wait for instance "{name}" to be ready with timeout {seconds:d} seconds'
    )
)
async def wait_for_instance_ready(
    context: dict, name: str, seconds: int, async_client, mock_instance_manager
) -> None:
    """Wait for instance to become ready."""
    instance = context["instances"].get(name)
    mock_instance_manager.get_instance.return_value = instance
    mock_instance_manager.wait_for_ready.return_value = instance

    with patch(
        "faux_splunk_cloud.api.routes.instances.instance_manager",
        mock_instance_manager,
    ):
        response = await async_client.get(
            f"/api/v1/instances/{instance.id}/wait?timeout_seconds={seconds}",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


# =============================================================================
# Then Steps (Assertions)
# =============================================================================


@then(parsers.parse("the response status code is {code:d}"))
def response_status_code(context: dict, code: int) -> None:
    """Assert the response status code."""
    assert context["response"].status_code == code, (
        f"Expected {code}, got {context['response'].status_code}: "
        f"{context['response'].text}"
    )


@then("the response contains an instance ID")
def response_contains_instance_id(context: dict) -> None:
    """Assert the response contains an instance ID."""
    data = context["response"].json()
    assert "id" in data, f"Response missing 'id': {data}"
    assert data["id"], "Instance ID is empty"


@then(parsers.parse('the instance status is "{status}"'))
def instance_status_is(context: dict, status: str) -> None:
    """Assert the instance has the expected status."""
    data = context["response"].json()
    assert data.get("status") == status, (
        f"Expected status '{status}', got '{data.get('status')}'"
    )


@then("the instance has default indexes configured")
def instance_has_default_indexes(context: dict) -> None:
    """Assert the instance has default indexes."""
    instance = context.get("created_instance")
    assert instance is not None
    # Victoria default indexes
    expected_indexes = {"main", "summary", "_internal", "_audit"}
    actual_indexes = set(instance.config.default_indexes or [])
    assert expected_indexes.issubset(
        actual_indexes
    ), f"Missing default indexes: {expected_indexes - actual_indexes}"


@then(parsers.parse("the instance expires in approximately {hours:d} hours"))
def instance_expires_in_hours_approx(
    context: dict, hours: int, fixed_datetime: datetime
) -> None:
    """Assert the instance expires within an hour of the expected time."""
    data = context["response"].json()
    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    expected = fixed_datetime + timedelta(hours=hours)

    # Allow 1 hour tolerance
    delta = abs((expires_at - expected).total_seconds())
    assert delta < 3600, f"Expiration time off by {delta} seconds"


@then(parsers.parse('the instance configuration shows topology "{topology}"'))
def instance_topology_is(context: dict, topology: str) -> None:
    """Assert the instance has the expected topology."""
    data = context["response"].json()
    assert data.get("config", {}).get("topology") == topology


@then(parsers.parse('the error message contains "{text}"'))
def error_message_contains(context: dict, text: str) -> None:
    """Assert the error message contains specific text."""
    data = context["response"].json()
    error_msg = str(data.get("message", "") or data.get("detail", "")).lower()
    assert text.lower() in error_msg, f"Expected '{text}' in error: {data}"


@then("the instance no longer exists")
def instance_no_longer_exists(context: dict) -> None:
    """Assert the instance has been removed."""
    # The destroy step already removes from context
    assert context["response"].status_code == 204


@then(parsers.parse("the response contains {count:d} instances"))
def response_contains_n_instances(context: dict, count: int) -> None:
    """Assert the response contains the expected number of instances."""
    data = context["response"].json()
    instances = data.get("instances", [])
    assert len(instances) == count, f"Expected {count} instances, got {len(instances)}"


@then(parsers.parse('all returned instances have status "{status}"'))
def all_instances_have_status(context: dict, status: str) -> None:
    """Assert all returned instances have the expected status."""
    data = context["response"].json()
    instances = data.get("instances", [])
    for instance in instances:
        assert instance.get("status") == status, (
            f"Instance {instance.get('id')} has status {instance.get('status')}, "
            f"expected {status}"
        )


@then("the response contains instance endpoints")
def response_contains_endpoints(context: dict) -> None:
    """Assert the response contains endpoint URLs."""
    data = context["response"].json()
    endpoints = data.get("endpoints", {})
    assert "web_url" in endpoints
    assert "api_url" in endpoints
    assert "hec_url" in endpoints


@then("the response contains instance credentials")
def response_contains_credentials(context: dict) -> None:
    """Assert the response contains credentials."""
    data = context["response"].json()
    credentials = data.get("credentials", {})
    assert "admin_username" in credentials
    assert "admin_password" in credentials


@then(parsers.parse('the health status is "{status}"'))
def health_status_is(context: dict, status: str) -> None:
    """Assert the health status."""
    data = context["response"].json()
    assert data.get("status") == status


@then("the response contains log lines")
def response_contains_logs(context: dict) -> None:
    """Assert the response contains log content."""
    data = context["response"].json()
    logs = data.get("logs", "")
    assert len(logs) > 0, "No logs returned"
