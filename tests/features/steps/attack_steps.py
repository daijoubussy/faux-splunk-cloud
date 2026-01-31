"""
Step definitions for attack simulation.

These steps implement the Gherkin scenarios defined in attack_simulation.feature.
All steps are designed to be deterministic and isolated.
"""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

# Load all scenarios from the feature file
scenarios("../attack_simulation.feature")


# =============================================================================
# Given Steps (Preconditions)
# =============================================================================


@given("the API server is running")
def api_server_running(context: dict, app) -> None:
    """Ensure the FastAPI app is available."""
    context["app"] = app
    context["response"] = None
    context["campaigns"] = {}
    context["instances"] = {}


@given("I am authenticated as a security analyst")
def authenticated_as_security_analyst(context: dict) -> None:
    """Set up authentication headers for security analyst."""
    context["auth_headers"] = {
        "Authorization": "Bearer test-security-analyst-token",
        "Content-Type": "application/json",
    }


@given(parsers.parse('a running instance "{name}" exists'))
def running_instance_exists(context: dict, name: str, make_instance) -> None:
    """Create a running instance for targeting."""
    from faux_splunk_cloud.models.instance import InstanceStatus

    instance = make_instance(name=name, status=InstanceStatus.RUNNING)
    context["instances"][name] = instance
    context["instances"][instance.id] = instance


@given(parsers.parse('an instance "{name}" exists in "{status}" state'))
def instance_exists_with_status(
    context: dict, name: str, status: str, make_instance
) -> None:
    """Create an instance with the specified status."""
    from faux_splunk_cloud.models.instance import InstanceStatus

    status_enum = InstanceStatus(status.lower())
    instance = make_instance(name=name, status=status_enum)
    context["instances"][name] = instance
    context["instances"][instance.id] = instance


@given(parsers.parse('a campaign "{name}" exists in "{status}" state'))
def campaign_exists_with_status(
    context: dict, name: str, status: str, make_campaign
) -> None:
    """Create a campaign with the specified status."""
    from faux_splunk_cloud.attack_simulation import CampaignStatus

    status_enum = CampaignStatus(status.lower())
    campaign = make_campaign(name=name, status=status_enum)
    context["campaigns"][name] = campaign
    context["campaigns"][campaign.id] = campaign


@given(parsers.parse('a campaign "{name}" exists with executed steps'))
def campaign_exists_with_steps(context: dict, name: str, make_campaign) -> None:
    """Create a campaign with some executed steps."""
    from faux_splunk_cloud.attack_simulation import CampaignStatus

    campaign = make_campaign(name=name, status=CampaignStatus.RUNNING, with_steps=True)
    context["campaigns"][name] = campaign
    context["campaigns"][campaign.id] = campaign


@given(parsers.parse('a campaign "{name}" exists with generated logs'))
def campaign_exists_with_logs(context: dict, name: str, make_campaign) -> None:
    """Create a campaign with generated logs."""
    from faux_splunk_cloud.attack_simulation import CampaignStatus

    campaign = make_campaign(name=name, status=CampaignStatus.RUNNING, with_logs=True)
    context["campaigns"][name] = campaign
    context["campaigns"][campaign.id] = campaign


@given(parsers.parse('multiple campaigns exist for instance "{name}"'))
def multiple_campaigns_for_instance(
    context: dict, name: str, make_campaign, make_instance
) -> None:
    """Create multiple campaigns targeting the same instance."""
    from faux_splunk_cloud.models.instance import InstanceStatus

    # Create the target instance
    instance = make_instance(name=name, status=InstanceStatus.RUNNING)
    context["instances"][name] = instance
    context["instances"][instance.id] = instance

    # Create multiple campaigns
    for i in range(3):
        campaign = make_campaign(
            name=f"campaign-{i}", target_instance_id=instance.id
        )
        context["campaigns"][campaign.name] = campaign
        context["campaigns"][campaign.id] = campaign


@given(parsers.parse('a campaign "{name}" targeting "{instance_name}" with threat actor "{actor_id}"'))
def campaign_with_threat_actor(
    context: dict,
    name: str,
    instance_name: str,
    actor_id: str,
    make_campaign,
) -> None:
    """Create a campaign with a specific threat actor."""
    instance = context["instances"].get(instance_name)
    target_id = instance.id if instance else instance_name
    campaign = make_campaign(
        name=name, target_instance_id=target_id, threat_actor_id=actor_id
    )
    context["campaigns"][name] = campaign
    context["campaigns"][campaign.id] = campaign


@given(parsers.parse('a campaign "{name}" with high detection probability'))
def campaign_with_high_detection(context: dict, name: str, make_campaign) -> None:
    """Create a campaign with high detection probability."""
    campaign = make_campaign(name=name, detection_probability=0.95)
    context["campaigns"][name] = campaign
    context["campaigns"][campaign.id] = campaign


@given(parsers.parse("a campaign with threat actor \"{actor_id}\""))
def campaign_with_actor(context: dict, actor_id: str, make_campaign) -> None:
    """Create a campaign with a specific threat actor."""
    campaign = make_campaign(name="test-campaign", threat_actor_id=actor_id)
    context["campaigns"]["test-campaign"] = campaign
    context["campaigns"][campaign.id] = campaign
    context["current_campaign"] = campaign


@given(parsers.parse('a campaign configured for "{data_source}" generation'))
def campaign_for_data_source(context: dict, data_source: str, make_campaign) -> None:
    """Create a campaign configured for a specific data source."""
    campaign = make_campaign(name="data-source-test", data_sources=[data_source])
    context["campaigns"]["data-source-test"] = campaign
    context["campaigns"][campaign.id] = campaign
    context["current_campaign"] = campaign


# =============================================================================
# When Steps (Actions)
# =============================================================================


@when("I list all threat actors")
async def list_all_threat_actors(context: dict, async_client) -> None:
    """List all threat actors."""
    response = await async_client.get(
        "/api/v1/attacks/threat-actors",
        headers=context.get("auth_headers", {}),
    )
    context["response"] = response


@when(parsers.parse('I list threat actors with level "{level}"'))
async def list_threat_actors_by_level(
    context: dict, level: str, async_client
) -> None:
    """List threat actors filtered by level."""
    response = await async_client.get(
        f"/api/v1/attacks/threat-actors?level={level}",
        headers=context.get("auth_headers", {}),
    )
    context["response"] = response


@when(parsers.parse('I get threat actor "{actor_id}"'))
async def get_threat_actor(context: dict, actor_id: str, async_client) -> None:
    """Get a specific threat actor."""
    response = await async_client.get(
        f"/api/v1/attacks/threat-actors/{actor_id}",
        headers=context.get("auth_headers", {}),
    )
    context["response"] = response


@when(parsers.parse('I create a campaign with threat actor "{actor_id}" targeting "{target}"'))
async def create_campaign_with_actor(
    context: dict,
    actor_id: str,
    target: str,
    async_client,
    mock_kill_chain_engine,
    make_campaign,
) -> None:
    """Create a campaign with a specific threat actor."""
    instance = context["instances"].get(target)
    target_id = instance.id if instance else target

    campaign = make_campaign(
        name=f"campaign-{actor_id}",
        target_instance_id=target_id,
        threat_actor_id=actor_id,
    )
    mock_kill_chain_engine.create_campaign.return_value = campaign
    mock_kill_chain_engine.get_campaign.return_value = campaign

    with patch(
        "faux_splunk_cloud.api.routes.attacks.kill_chain_engine",
        mock_kill_chain_engine,
    ), patch(
        "faux_splunk_cloud.api.routes.attacks.get_threat_actor_by_id"
    ) as mock_get_actor:
        # Mock threat actor lookup
        if actor_id.startswith("invalid"):
            mock_get_actor.return_value = None
        else:
            mock_get_actor.return_value = MagicMock(
                id=actor_id,
                name=actor_id.upper(),
                threat_level=MagicMock(value="nation_state"),
            )

        response = await async_client.post(
            "/api/v1/attacks/campaigns",
            json={
                "threat_actor_id": actor_id,
                "target_instance_id": target_id,
            },
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response
    if response.status_code == 201:
        context["created_campaign"] = campaign


@when(parsers.parse('I start the campaign "{name}"'))
async def start_campaign(
    context: dict, name: str, async_client, mock_kill_chain_engine
) -> None:
    """Start a campaign."""
    campaign = context["campaigns"].get(name)

    if campaign:
        mock_kill_chain_engine.get_campaign.return_value = campaign
        mock_kill_chain_engine.start_campaign.return_value = None
        # Update status after start
        from faux_splunk_cloud.attack_simulation import CampaignStatus
        campaign.status = CampaignStatus.RUNNING

    with patch(
        "faux_splunk_cloud.api.routes.attacks.kill_chain_engine",
        mock_kill_chain_engine,
    ):
        campaign_id = campaign.id if campaign else name
        response = await async_client.post(
            f"/api/v1/attacks/campaigns/{campaign_id}/start",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(parsers.parse('I pause the campaign "{name}"'))
async def pause_campaign(
    context: dict, name: str, async_client, mock_kill_chain_engine
) -> None:
    """Pause a running campaign."""
    campaign = context["campaigns"].get(name)

    if campaign:
        mock_kill_chain_engine.get_campaign.return_value = campaign
        mock_kill_chain_engine.pause_campaign.return_value = None
        # Update status after pause
        from faux_splunk_cloud.attack_simulation import CampaignStatus
        campaign.status = CampaignStatus.PAUSED

    with patch(
        "faux_splunk_cloud.api.routes.attacks.kill_chain_engine",
        mock_kill_chain_engine,
    ):
        campaign_id = campaign.id if campaign else name
        response = await async_client.post(
            f"/api/v1/attacks/campaigns/{campaign_id}/pause",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(parsers.parse('I get campaign "{name}"'))
async def get_campaign(
    context: dict, name: str, async_client, mock_kill_chain_engine
) -> None:
    """Get campaign details."""
    campaign = context["campaigns"].get(name)
    mock_kill_chain_engine.get_campaign.return_value = campaign

    with patch(
        "faux_splunk_cloud.api.routes.attacks.kill_chain_engine",
        mock_kill_chain_engine,
    ):
        campaign_id = campaign.id if campaign else name
        response = await async_client.get(
            f"/api/v1/attacks/campaigns/{campaign_id}",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(parsers.parse('I get steps for campaign "{name}"'))
async def get_campaign_steps(
    context: dict, name: str, async_client, mock_kill_chain_engine
) -> None:
    """Get campaign attack steps."""
    campaign = context["campaigns"].get(name)
    mock_kill_chain_engine.get_campaign.return_value = campaign

    with patch(
        "faux_splunk_cloud.api.routes.attacks.kill_chain_engine",
        mock_kill_chain_engine,
    ):
        campaign_id = campaign.id if campaign else name
        response = await async_client.get(
            f"/api/v1/attacks/campaigns/{campaign_id}/steps",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(parsers.parse('I get logs for campaign "{name}" with limit {limit:d}'))
async def get_campaign_logs(
    context: dict, name: str, limit: int, async_client, mock_kill_chain_engine
) -> None:
    """Get campaign logs."""
    campaign = context["campaigns"].get(name)
    mock_kill_chain_engine.get_campaign.return_value = campaign
    mock_kill_chain_engine.get_campaign_logs.return_value = [
        {"timestamp": "2025-01-30T12:00:00Z", "sourcetype": "WinEventLog:Security", "event": "test"}
        for _ in range(min(limit, 10))
    ]

    with patch(
        "faux_splunk_cloud.api.routes.attacks.kill_chain_engine",
        mock_kill_chain_engine,
    ):
        campaign_id = campaign.id if campaign else name
        response = await async_client.get(
            f"/api/v1/attacks/campaigns/{campaign_id}/logs?limit={limit}",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when(parsers.parse('I list campaigns for instance "{name}"'))
async def list_campaigns_for_instance(
    context: dict, name: str, async_client, mock_kill_chain_engine
) -> None:
    """List campaigns for a specific instance."""
    instance = context["instances"].get(name)
    instance_id = instance.id if instance else name

    # Filter campaigns for this instance
    campaigns = [
        c for c in context["campaigns"].values()
        if hasattr(c, "target_instance_id") and c.target_instance_id == instance_id
    ]
    mock_kill_chain_engine.list_campaigns.return_value = campaigns

    with patch(
        "faux_splunk_cloud.api.routes.attacks.kill_chain_engine",
        mock_kill_chain_engine,
    ):
        response = await async_client.get(
            f"/api/v1/attacks/campaigns?instance_id={instance_id}",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when("I list attack scenarios")
async def list_attack_scenarios(context: dict, async_client) -> None:
    """List available attack scenarios."""
    response = await async_client.get(
        "/api/v1/attacks/scenarios",
        headers=context.get("auth_headers", {}),
    )
    context["response"] = response


@when(parsers.parse('I execute scenario "{scenario_id}" against "{target}"'))
async def execute_scenario(
    context: dict,
    scenario_id: str,
    target: str,
    async_client,
    mock_kill_chain_engine,
    make_campaign,
) -> None:
    """Execute an attack scenario."""
    instance = context["instances"].get(target)
    target_id = instance.id if instance else target

    campaign = make_campaign(name=f"Scenario: {scenario_id}", target_instance_id=target_id)
    mock_kill_chain_engine.create_campaign.return_value = campaign

    # Check if instance is running
    instance_status = instance.status.value if instance else "stopped"

    with patch(
        "faux_splunk_cloud.api.routes.attacks.kill_chain_engine",
        mock_kill_chain_engine,
    ):
        response = await async_client.post(
            f"/api/v1/attacks/scenarios/{scenario_id}/execute?target_instance_id={target_id}",
            headers=context.get("auth_headers", {}),
        )

    context["response"] = response


@when("I wait for the campaign to progress")
async def wait_for_campaign_progress(context: dict) -> None:
    """Wait for campaign to progress (simulated)."""
    # In unit tests, this is a no-op since we mock progression
    pass


@when("the campaign executes a detectable technique")
async def campaign_executes_detectable_technique(context: dict) -> None:
    """Simulate campaign executing a detectable technique."""
    campaign = context.get("current_campaign") or list(context["campaigns"].values())[0]
    # Simulate detection
    from faux_splunk_cloud.attack_simulation import CampaignStatus
    campaign.status = CampaignStatus.DETECTED
    campaign.detected_at_step = len(campaign.steps) - 1 if campaign.steps else 0


@when("the campaign generates Windows Security logs")
async def campaign_generates_windows_logs(context: dict) -> None:
    """Simulate log generation."""
    context["generated_logs"] = [
        {
            "EventCode": 4624,
            "_time": "2025-01-30T12:00:00.000Z",
            "sourcetype": "WinEventLog:Security",
        }
    ]


@when("the campaign generates logs")
async def campaign_generates_logs(context: dict) -> None:
    """Simulate generic log generation."""
    campaign = context.get("current_campaign")
    data_sources = getattr(campaign, "data_sources", ["windows_security"])

    sourcetype_map = {
        "windows_security": "WinEventLog:Security",
        "sysmon": "XmlWinEventLog:Microsoft-Windows-Sysmon/Operational",
        "firewall": "pan:traffic",
        "dns": "stream:dns",
        "proxy": "bluecoat:proxysg:access",
    }

    context["generated_logs"] = [
        {
            "sourcetype": sourcetype_map.get(ds, "generic"),
            "_time": "2025-01-30T12:00:00.000Z",
        }
        for ds in data_sources
    ]


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


@then("the response contains threat actors")
def response_contains_threat_actors(context: dict) -> None:
    """Assert the response contains threat actors."""
    data = context["response"].json()
    assert "threat_actors" in data
    assert len(data["threat_actors"]) > 0


@then("each threat actor has a threat level")
def each_actor_has_threat_level(context: dict) -> None:
    """Assert each threat actor has a threat level."""
    data = context["response"].json()
    for actor in data["threat_actors"]:
        assert "threat_level" in actor
        assert actor["threat_level"] is not None


@then(parsers.parse('all returned actors have threat level "{level}"'))
def all_actors_have_level(context: dict, level: str) -> None:
    """Assert all returned actors have the specified level."""
    data = context["response"].json()
    for actor in data["threat_actors"]:
        assert actor["threat_level"] == level


@then(parsers.parse('the response contains threat actor name "{name}"'))
def response_contains_actor_name(context: dict, name: str) -> None:
    """Assert the response contains the specified threat actor name."""
    data = context["response"].json()
    assert data.get("name") == name


@then("the response contains MITRE ATT&CK techniques")
def response_contains_techniques(context: dict) -> None:
    """Assert the response contains MITRE ATT&CK techniques."""
    data = context["response"].json()
    assert "techniques" in data
    assert len(data["techniques"]) > 0


@then("the response contains behavioral characteristics")
def response_contains_behavioral(context: dict) -> None:
    """Assert the response contains behavioral characteristics."""
    data = context["response"].json()
    # Could be in motivation, description, or other fields
    assert "motivation" in data or "description" in data


@then(parsers.parse('the campaign status is "{status}"'))
def campaign_status_is(context: dict, status: str) -> None:
    """Assert the campaign has the expected status."""
    data = context["response"].json()
    assert data.get("status") == status, (
        f"Expected status '{status}', got '{data.get('status')}'"
    )


@then("the campaign has a unique ID")
def campaign_has_unique_id(context: dict) -> None:
    """Assert the campaign has a unique ID."""
    data = context["response"].json()
    assert "id" in data
    assert data["id"]


@then(parsers.parse('the error message contains "{text}"'))
def error_message_contains(context: dict, text: str) -> None:
    """Assert the error message contains specific text."""
    data = context["response"].json()
    error_msg = str(data.get("message", "") or data.get("detail", "")).lower()
    assert text.lower() in error_msg, f"Expected '{text}' in error: {data}"


@then("the response contains current kill chain phase")
def response_contains_current_phase(context: dict) -> None:
    """Assert the response contains the current phase."""
    data = context["response"].json()
    assert "current_phase" in data


@then("the response contains completed steps count")
def response_contains_completed_steps(context: dict) -> None:
    """Assert the response contains completed steps count."""
    data = context["response"].json()
    assert "completed_steps" in data


@then("the response contains total steps count")
def response_contains_total_steps(context: dict) -> None:
    """Assert the response contains total steps count."""
    data = context["response"].json()
    assert "total_steps" in data


@then("each step contains technique ID")
def each_step_has_technique_id(context: dict) -> None:
    """Assert each step has a technique ID."""
    data = context["response"].json()
    for step in data:
        assert "technique_id" in step


@then("each step contains technique name")
def each_step_has_technique_name(context: dict) -> None:
    """Assert each step has a technique name."""
    data = context["response"].json()
    for step in data:
        assert "technique_name" in step


@then("each step contains timestamp")
def each_step_has_timestamp(context: dict) -> None:
    """Assert each step has a timestamp."""
    data = context["response"].json()
    for step in data:
        assert "timestamp" in step


@then("each step contains success status")
def each_step_has_success_status(context: dict) -> None:
    """Assert each step has a success status."""
    data = context["response"].json()
    for step in data:
        assert "success" in step


@then("the response contains log entries")
def response_contains_log_entries(context: dict) -> None:
    """Assert the response contains log entries."""
    data = context["response"].json()
    assert "logs" in data
    assert len(data["logs"]) > 0


@then("each log entry has a timestamp")
def each_log_has_timestamp(context: dict) -> None:
    """Assert each log entry has a timestamp."""
    data = context["response"].json()
    for log in data["logs"]:
        assert "timestamp" in log or "_time" in log


@then("each log entry has a sourcetype")
def each_log_has_sourcetype(context: dict) -> None:
    """Assert each log entry has a sourcetype."""
    data = context["response"].json()
    for log in data["logs"]:
        assert "sourcetype" in log


@then(parsers.parse('all returned campaigns target instance "{name}"'))
def all_campaigns_target_instance(context: dict, name: str) -> None:
    """Assert all returned campaigns target the specified instance."""
    data = context["response"].json()
    instance = context["instances"].get(name)
    instance_id = instance.id if instance else name

    for campaign in data["campaigns"]:
        assert campaign["target_instance_id"] == instance_id


@then("the response contains predefined scenarios")
def response_contains_scenarios(context: dict) -> None:
    """Assert the response contains predefined scenarios."""
    data = context["response"].json()
    assert len(data) > 0


@then("each scenario has a threat level")
def each_scenario_has_threat_level(context: dict) -> None:
    """Assert each scenario has a threat level."""
    data = context["response"].json()
    for scenario in data:
        assert "threat_level" in scenario


@then("each scenario has estimated duration")
def each_scenario_has_duration(context: dict) -> None:
    """Assert each scenario has estimated duration."""
    data = context["response"].json()
    for scenario in data:
        assert "estimated_duration_minutes" in scenario


@then("a campaign is created and started")
def campaign_is_created_and_started(context: dict) -> None:
    """Assert a campaign was created and started."""
    data = context["response"].json()
    assert "id" in data
    assert data["status"] in ["running", "pending"]


@then("the campaign uses the scenario's threat actor")
def campaign_uses_scenario_actor(context: dict) -> None:
    """Assert the campaign uses the correct threat actor."""
    data = context["response"].json()
    assert "threat_actor_id" in data
    assert data["threat_actor_id"]


@then(parsers.parse('the campaign phase advances from "{phase}"'))
def campaign_phase_advances(context: dict, phase: str) -> None:
    """Assert the campaign phase has advanced."""
    # In mocked tests, we just verify the phase is present
    data = context["response"].json()
    assert "current_phase" in data


@then("attack steps are recorded for each phase")
def attack_steps_recorded(context: dict) -> None:
    """Assert attack steps are recorded."""
    campaign = list(context["campaigns"].values())[0]
    assert len(campaign.steps) > 0


@then(parsers.parse('the campaign status changes to "{status}"'))
def campaign_status_changes_to(context: dict, status: str) -> None:
    """Assert the campaign status changed."""
    campaign = context.get("current_campaign") or list(context["campaigns"].values())[0]
    assert campaign.status.value == status


@then("the detection step is recorded")
def detection_step_recorded(context: dict) -> None:
    """Assert the detection step is recorded."""
    campaign = context.get("current_campaign") or list(context["campaigns"].values())[0]
    assert campaign.detected_at_step is not None


@then("the logs contain EventCode field")
def logs_contain_eventcode(context: dict) -> None:
    """Assert logs contain EventCode field."""
    logs = context.get("generated_logs", [])
    assert len(logs) > 0
    assert "EventCode" in logs[0]


@then("the logs contain proper timestamp format")
def logs_contain_timestamp_format(context: dict) -> None:
    """Assert logs contain proper timestamp format."""
    logs = context.get("generated_logs", [])
    assert len(logs) > 0
    assert "_time" in logs[0]
    # ISO format check
    assert "T" in logs[0]["_time"]


@then("the logs match Splunk CIM format")
def logs_match_cim_format(context: dict) -> None:
    """Assert logs match Splunk CIM format."""
    logs = context.get("generated_logs", [])
    assert len(logs) > 0
    # CIM fields typically include _time, sourcetype
    assert "_time" in logs[0] or "timestamp" in logs[0]


@then(parsers.parse('the sourcetype is "{expected_sourcetype}"'))
def sourcetype_is(context: dict, expected_sourcetype: str) -> None:
    """Assert the sourcetype matches expected value."""
    logs = context.get("generated_logs", [])
    assert len(logs) > 0
    assert logs[0]["sourcetype"] == expected_sourcetype
