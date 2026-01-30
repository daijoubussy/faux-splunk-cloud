"""
Attack Simulation API endpoints.

Provides REST API for managing attack simulations against
ephemeral Splunk instances.

Integrates with:
- Backstage templates for self-service attack scenarios
- CI/CD pipelines for automated security testing
- Security training platforms
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from faux_splunk_cloud.api.deps import require_auth
from faux_splunk_cloud.attack_simulation import (
    AttackCampaign,
    AttackPhase,
    CampaignConfig,
    CampaignStatus,
    ThreatActorProfile,
    ThreatLevel,
    get_threat_actor_by_id,
    kill_chain_engine,
    list_all_threat_actors,
)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class ThreatActorResponse(BaseModel):
    """Response model for threat actor profiles."""

    id: str
    name: str
    aliases: list[str]
    threat_level: str
    motivation: list[str]
    description: str
    techniques: list[str]
    attributed_country: str | None


class ThreatActorListResponse(BaseModel):
    """Response model for listing threat actors."""

    threat_actors: list[ThreatActorResponse]
    total: int


class CampaignCreateRequest(BaseModel):
    """Request model for creating an attack campaign."""

    threat_actor_id: str = Field(description="ID of the threat actor profile")
    target_instance_id: str = Field(description="Target Splunk instance ID")
    name: str | None = Field(default=None, description="Campaign name")
    speed_multiplier: float = Field(
        default=60.0,
        ge=1.0,
        le=3600.0,
        description="Simulation speed (60 = 1 minute = 1 hour of attack)",
    )
    include_phases: list[str] | None = Field(
        default=None,
        description="Kill chain phases to include (default: all)",
    )
    start_immediately: bool = Field(default=True, description="Start campaign immediately")
    objectives: list[str] = Field(
        default=["establish_persistence", "harvest_credentials", "data_exfiltration"],
        description="Campaign objectives",
    )


class CampaignResponse(BaseModel):
    """Response model for attack campaigns."""

    id: str
    name: str
    threat_actor_id: str
    threat_actor_name: str
    target_instance_id: str
    status: str
    current_phase: str
    total_steps: int
    completed_steps: int
    start_time: str | None
    end_time: str | None
    detected: bool
    detected_at_step: int | None


class CampaignListResponse(BaseModel):
    """Response model for listing campaigns."""

    campaigns: list[CampaignResponse]
    total: int


class AttackStepResponse(BaseModel):
    """Response model for individual attack steps."""

    id: str
    technique_id: str
    technique_name: str
    phase: str
    tactic: str
    timestamp: str
    success: bool
    detected: bool


class CampaignLogsResponse(BaseModel):
    """Response model for campaign logs."""

    campaign_id: str
    logs: list[dict]
    total: int


class ScenarioResponse(BaseModel):
    """Response model for available scenarios."""

    id: str
    name: str
    description: str
    threat_level: str
    estimated_duration_minutes: int
    objectives: list[str]


# =============================================================================
# Threat Actor Endpoints
# =============================================================================


@router.get("/threat-actors", response_model=ThreatActorListResponse)
async def list_threat_actors(
    level: ThreatLevel | None = Query(default=None, description="Filter by threat level"),
) -> ThreatActorListResponse:
    """
    List all available threat actor profiles.

    Profiles range from script kiddies to nation-state APTs like APT29 and APT28.
    """
    actors = list_all_threat_actors()

    if level:
        actors = [a for a in actors if a.threat_level == level]

    responses = [
        ThreatActorResponse(
            id=a.id,
            name=a.name,
            aliases=a.aliases,
            threat_level=a.threat_level.value,
            motivation=[m.value for m in a.motivation],
            description=a.description.strip(),
            techniques=a.techniques,
            attributed_country=a.attributed_country,
        )
        for a in actors
    ]

    return ThreatActorListResponse(threat_actors=responses, total=len(responses))


@router.get("/threat-actors/{actor_id}", response_model=ThreatActorResponse)
async def get_threat_actor(actor_id: str) -> ThreatActorResponse:
    """Get a specific threat actor profile."""
    actor = get_threat_actor_by_id(actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail=f"Threat actor {actor_id} not found")

    return ThreatActorResponse(
        id=actor.id,
        name=actor.name,
        aliases=actor.aliases,
        threat_level=actor.threat_level.value,
        motivation=[m.value for m in actor.motivation],
        description=actor.description.strip(),
        techniques=actor.techniques,
        attributed_country=actor.attributed_country,
    )


# =============================================================================
# Campaign Endpoints
# =============================================================================


@router.post("/campaigns", response_model=CampaignResponse)
async def create_campaign(
    request: CampaignCreateRequest,
    _: Annotated[str, Depends(require_auth)],
) -> CampaignResponse:
    """
    Create a new attack campaign.

    Campaigns simulate realistic attack sequences based on threat actor profiles,
    generating security logs that are ingested into the target Splunk instance.
    """
    # Validate threat actor
    actor = get_threat_actor_by_id(request.threat_actor_id)
    if not actor:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown threat actor: {request.threat_actor_id}",
        )

    # Parse phases
    phases = None
    if request.include_phases:
        try:
            phases = [AttackPhase(p) for p in request.include_phases]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid phase: {e}")

    # Create campaign config
    config = CampaignConfig(
        threat_actor_id=request.threat_actor_id,
        target_instance_id=request.target_instance_id,
        name=request.name,
        speed_multiplier=request.speed_multiplier,
        include_phases=phases,
        start_immediately=request.start_immediately,
        objectives=request.objectives,
    )

    try:
        campaign = kill_chain_engine.create_campaign(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _campaign_to_response(campaign)


@router.get("/campaigns", response_model=CampaignListResponse)
async def list_campaigns(
    instance_id: str | None = Query(default=None, description="Filter by instance"),
    status: CampaignStatus | None = Query(default=None, description="Filter by status"),
) -> CampaignListResponse:
    """List all attack campaigns."""
    campaigns = kill_chain_engine.list_campaigns(instance_id)

    if status:
        campaigns = [c for c in campaigns if c.status == status]

    responses = [_campaign_to_response(c) for c in campaigns]
    return CampaignListResponse(campaigns=responses, total=len(responses))


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str) -> CampaignResponse:
    """Get a specific attack campaign."""
    campaign = kill_chain_engine.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    return _campaign_to_response(campaign)


@router.post("/campaigns/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(
    campaign_id: str,
    _: Annotated[str, Depends(require_auth)],
) -> CampaignResponse:
    """Start a paused or pending campaign."""
    campaign = kill_chain_engine.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    try:
        kill_chain_engine.start_campaign(campaign_id)
        campaign = kill_chain_engine.get_campaign(campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _campaign_to_response(campaign)


@router.post("/campaigns/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: str,
    _: Annotated[str, Depends(require_auth)],
) -> CampaignResponse:
    """Pause a running campaign."""
    campaign = kill_chain_engine.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    kill_chain_engine.pause_campaign(campaign_id)
    campaign = kill_chain_engine.get_campaign(campaign_id)

    return _campaign_to_response(campaign)


@router.get("/campaigns/{campaign_id}/steps", response_model=list[AttackStepResponse])
async def get_campaign_steps(campaign_id: str) -> list[AttackStepResponse]:
    """Get all steps in an attack campaign."""
    campaign = kill_chain_engine.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    return [
        AttackStepResponse(
            id=step.id,
            technique_id=step.technique.id,
            technique_name=step.technique.name,
            phase=step.phase.value,
            tactic=step.tactic.value,
            timestamp=step.timestamp.isoformat(),
            success=step.success,
            detected=step.detected,
        )
        for step in campaign.steps
    ]


@router.get("/campaigns/{campaign_id}/logs", response_model=CampaignLogsResponse)
async def get_campaign_logs(
    campaign_id: str,
    limit: int = Query(default=1000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
) -> CampaignLogsResponse:
    """Get logs generated by an attack campaign."""
    campaign = kill_chain_engine.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    all_logs = kill_chain_engine.get_campaign_logs(campaign_id)
    paginated_logs = all_logs[offset : offset + limit]

    return CampaignLogsResponse(
        campaign_id=campaign_id,
        logs=paginated_logs,
        total=len(all_logs),
    )


# =============================================================================
# Scenario Endpoints
# =============================================================================


@router.get("/scenarios", response_model=list[ScenarioResponse])
async def list_scenarios() -> list[ScenarioResponse]:
    """
    List available attack scenarios.

    Scenarios are pre-built attack sequences based on real-world incidents
    and BOTS-style CTF challenges.
    """
    scenarios = [
        ScenarioResponse(
            id="apt_intrusion",
            name="APT Intrusion",
            description="Advanced persistent threat intrusion with spearphishing, "
            "lateral movement, and data exfiltration. Based on BOTSv2.",
            threat_level="nation_state",
            estimated_duration_minutes=30,
            objectives=[
                "establish_persistence",
                "harvest_credentials",
                "lateral_movement",
                "data_exfiltration",
            ],
        ),
        ScenarioResponse(
            id="ransomware_attack",
            name="Ransomware Attack",
            description="Rapid ransomware deployment with RDP brute force, "
            "shadow copy deletion, and mass file encryption.",
            threat_level="organized_crime",
            estimated_duration_minutes=15,
            objectives=["initial_access", "inhibit_recovery", "encrypt_data"],
        ),
        ScenarioResponse(
            id="insider_threat",
            name="Insider Threat",
            description="Malicious insider stealing data before departure. "
            "Unusual access patterns and cloud exfiltration.",
            threat_level="insider_threat",
            estimated_duration_minutes=60,
            objectives=["access_sensitive_data", "exfiltrate_to_cloud"],
        ),
        ScenarioResponse(
            id="web_app_attack",
            name="Web Application Attack",
            description="Web application reconnaissance and exploitation "
            "including SQL injection and XSS attempts.",
            threat_level="opportunistic",
            estimated_duration_minutes=20,
            objectives=["recon", "exploit_webapp", "extract_data"],
        ),
        ScenarioResponse(
            id="credential_theft",
            name="Credential Theft",
            description="Kerberoasting and pass-the-hash attacks targeting "
            "service accounts and domain credentials.",
            threat_level="apt",
            estimated_duration_minutes=25,
            objectives=["kerberoast", "pass_the_hash", "privilege_escalation"],
        ),
    ]
    return scenarios


@router.post("/scenarios/{scenario_id}/execute")
async def execute_scenario(
    scenario_id: str,
    target_instance_id: str,
    _: Annotated[str, Depends(require_auth)],
) -> CampaignResponse:
    """
    Execute a predefined attack scenario against a Splunk instance.

    This creates and starts a campaign using the scenario's configuration.
    """
    # Map scenarios to threat actors
    scenario_actors = {
        "apt_intrusion": "apt29",
        "ransomware_attack": "opportunistic_ransomware",
        "insider_threat": "insider_malicious",
        "web_app_attack": "script_kiddie_generic",
        "credential_theft": "apt_generic",
    }

    if scenario_id not in scenario_actors:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {scenario_id}")

    config = CampaignConfig(
        threat_actor_id=scenario_actors[scenario_id],
        target_instance_id=target_instance_id,
        name=f"Scenario: {scenario_id}",
        speed_multiplier=60.0,
        start_immediately=True,
    )

    campaign = kill_chain_engine.create_campaign(config)
    return _campaign_to_response(campaign)


# =============================================================================
# Helper Functions
# =============================================================================


def _campaign_to_response(campaign: AttackCampaign) -> CampaignResponse:
    """Convert campaign to response model."""
    completed = sum(1 for s in campaign.steps if s.success)

    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        threat_actor_id=campaign.threat_actor.id,
        threat_actor_name=campaign.threat_actor.name,
        target_instance_id=campaign.target_instance_id,
        status=campaign.status.value,
        current_phase=campaign.current_phase.value,
        total_steps=len(campaign.steps),
        completed_steps=completed,
        start_time=campaign.start_time.isoformat() if campaign.start_time else None,
        end_time=campaign.end_time.isoformat() if campaign.end_time else None,
        detected=campaign.detected_at_step is not None,
        detected_at_step=campaign.detected_at_step,
    )
