"""
Attack Simulation Module for Faux Splunk Cloud.

Provides adversarial attack simulation capabilities for ephemeral
Splunk instances, enabling:

- Security training and CTF scenarios
- Detection rule testing and validation
- SOC analyst training
- Purple team exercises
- Threat hunting practice

Inspired by:
- MITRE Caldera: https://caldera.mitre.org/
- Splunk Attack Range: https://github.com/splunk/attack_range
- Atomic Red Team: https://atomicredteam.io/
- Boss of the SOC: https://github.com/splunk/botsv2

Key Components:
- Threat Actor Profiles: From script kiddies to nation-state APTs
- Kill Chain Engine: Orchestrates attacks through kill chain phases
- MITRE ATT&CK Integration: Technique library with detection rules
- Data Generators: Enterprise security log generation
"""

from faux_splunk_cloud.attack_simulation.data_generators import (
    EnterpriseDataGenerator,
    LogSourceType,
    NetworkEnvironment,
    data_generator,
)
from faux_splunk_cloud.attack_simulation.kill_chain_engine import (
    AttackCampaign,
    AttackPhase,
    AttackStep,
    CampaignConfig,
    CampaignStatus,
    KillChainEngine,
    kill_chain_engine,
)
from faux_splunk_cloud.attack_simulation.mitre_attack import (
    DataSource,
    Platform,
    Tactic,
    Technique,
    TECHNIQUE_LIBRARY,
    get_technique_by_id,
    get_techniques_by_data_source,
    get_techniques_by_tactic,
)
from faux_splunk_cloud.attack_simulation.threat_actors import (
    Motivation,
    TargetSector,
    ThreatActorProfile,
    ThreatLevel,
    THREAT_ACTOR_PROFILES,
    get_threat_actor_by_id,
    get_threat_actors_by_level,
    get_threat_actors_by_sector,
    list_all_threat_actors,
)

__all__ = [
    # MITRE ATT&CK
    "Tactic",
    "Platform",
    "DataSource",
    "Technique",
    "TECHNIQUE_LIBRARY",
    "get_technique_by_id",
    "get_techniques_by_tactic",
    "get_techniques_by_data_source",
    # Threat Actors
    "ThreatLevel",
    "Motivation",
    "TargetSector",
    "ThreatActorProfile",
    "THREAT_ACTOR_PROFILES",
    "get_threat_actor_by_id",
    "get_threat_actors_by_level",
    "get_threat_actors_by_sector",
    "list_all_threat_actors",
    # Kill Chain Engine
    "AttackPhase",
    "AttackStep",
    "AttackCampaign",
    "CampaignStatus",
    "CampaignConfig",
    "KillChainEngine",
    "kill_chain_engine",
    # Data Generators
    "LogSourceType",
    "NetworkEnvironment",
    "EnterpriseDataGenerator",
    "data_generator",
]
