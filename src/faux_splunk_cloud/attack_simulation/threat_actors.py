"""
Threat Actor Profiles for attack simulation.

Profiles range from script kiddies to nation-state APTs, each with
characteristic tactics, techniques, procedures, and behavioral patterns.

References:
- MITRE ATT&CK Groups: https://attack.mitre.org/groups/
- MITRE ATT&CK Software: https://attack.mitre.org/software/
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from faux_splunk_cloud.attack_simulation.mitre_attack import Tactic, Technique


class ThreatLevel(str, Enum):
    """Sophistication level of threat actors."""

    SCRIPT_KIDDIE = "script_kiddie"
    OPPORTUNISTIC = "opportunistic"
    ORGANIZED_CRIME = "organized_crime"
    HACKTIVIST = "hacktivist"
    INSIDER_THREAT = "insider_threat"
    APT = "apt"
    NATION_STATE = "nation_state"


class Motivation(str, Enum):
    """Primary motivation of threat actors."""

    CURIOSITY = "curiosity"
    NOTORIETY = "notoriety"
    FINANCIAL = "financial"
    HACKTIVISM = "hacktivism"
    ESPIONAGE = "espionage"
    SABOTAGE = "sabotage"
    INFLUENCE = "influence"


class TargetSector(str, Enum):
    """Target sectors for threat actors."""

    ANY = "any"
    GOVERNMENT = "government"
    DEFENSE = "defense"
    FINANCIAL = "financial"
    HEALTHCARE = "healthcare"
    ENERGY = "energy"
    TECHNOLOGY = "technology"
    CRITICAL_INFRASTRUCTURE = "critical_infrastructure"
    MEDIA = "media"
    TELECOMMUNICATIONS = "telecommunications"
    EDUCATION = "education"
    RETAIL = "retail"


@dataclass
class ThreatActorProfile:
    """
    Threat Actor Profile for attack simulation.

    Defines the characteristics, capabilities, and typical behaviors
    of different threat actor categories.
    """

    id: str
    name: str
    aliases: list[str]
    threat_level: ThreatLevel
    motivation: list[Motivation]
    target_sectors: list[TargetSector]
    description: str

    # Typical techniques used
    techniques: list[str]  # ATT&CK technique IDs

    # Preferred tactics (in order of use through kill chain)
    preferred_tactics: list[Tactic]

    # Behavioral characteristics
    dwell_time_days: tuple[int, int]  # (min, max) days in network
    noise_level: float  # 0.0 = stealthy, 1.0 = noisy
    persistence_likelihood: float  # 0.0-1.0
    lateral_movement_likelihood: float  # 0.0-1.0
    exfiltration_likelihood: float  # 0.0-1.0

    # Operational hours (for realistic timing)
    active_hours_utc: tuple[int, int] = (9, 17)  # Start, end hour
    active_days: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Mon-Fri

    # Tools and malware commonly used
    tools: list[str] = field(default_factory=list)
    malware: list[str] = field(default_factory=list)

    # Geographic attribution (for realistic simulation)
    attributed_country: str | None = None

    # MITRE ATT&CK Group ID if applicable
    mitre_group_id: str | None = None

    # References
    references: list[str] = field(default_factory=list)


# =============================================================================
# Threat Actor Profiles Library
# From Script Kiddies to Nation-State APTs
# =============================================================================

THREAT_ACTOR_PROFILES: dict[str, ThreatActorProfile] = {
    # =========================================================================
    # SCRIPT KIDDIE
    # =========================================================================
    "script_kiddie_generic": ThreatActorProfile(
        id="script_kiddie_generic",
        name="Generic Script Kiddie",
        aliases=["Noob", "Skid"],
        threat_level=ThreatLevel.SCRIPT_KIDDIE,
        motivation=[Motivation.CURIOSITY, Motivation.NOTORIETY],
        target_sectors=[TargetSector.ANY],
        description="""
            Low-skill attacker using pre-built tools and public exploits.
            Operates loudly with little regard for stealth or persistence.
            Typically targets low-hanging fruit and misconfigured systems.
        """,
        techniques=[
            "T1190",  # Exploit Public-Facing Application
            "T1110.001",  # Password Guessing
            "T1059.001",  # PowerShell
            "T1082",  # System Information Discovery
        ],
        preferred_tactics=[
            Tactic.INITIAL_ACCESS,
            Tactic.EXECUTION,
            Tactic.DISCOVERY,
        ],
        dwell_time_days=(0, 1),
        noise_level=0.9,
        persistence_likelihood=0.1,
        lateral_movement_likelihood=0.1,
        exfiltration_likelihood=0.2,
        tools=["Metasploit", "SQLMap", "Nmap"],
        active_hours_utc=(15, 3),  # Late night
        active_days=[0, 1, 2, 3, 4, 5, 6],  # Any day
    ),
    # =========================================================================
    # OPPORTUNISTIC ATTACKER
    # =========================================================================
    "opportunistic_ransomware": ThreatActorProfile(
        id="opportunistic_ransomware",
        name="Opportunistic Ransomware Operator",
        aliases=["Spray and Pray"],
        threat_level=ThreatLevel.OPPORTUNISTIC,
        motivation=[Motivation.FINANCIAL],
        target_sectors=[TargetSector.ANY],
        description="""
            Automated or semi-automated ransomware deployment.
            Scans for vulnerable systems and deploys ransomware quickly.
            Limited reconnaissance, focuses on rapid encryption.
        """,
        techniques=[
            "T1190",  # Exploit Public-Facing Application
            "T1566.001",  # Spearphishing Attachment
            "T1059.001",  # PowerShell
            "T1486",  # Data Encrypted for Impact
            "T1490",  # Inhibit System Recovery
            "T1082",  # System Information Discovery
        ],
        preferred_tactics=[
            Tactic.INITIAL_ACCESS,
            Tactic.EXECUTION,
            Tactic.DISCOVERY,
            Tactic.IMPACT,
        ],
        dwell_time_days=(0, 3),
        noise_level=0.7,
        persistence_likelihood=0.3,
        lateral_movement_likelihood=0.4,
        exfiltration_likelihood=0.5,
        tools=["Cobalt Strike", "Mimikatz"],
        malware=["LockBit", "REvil", "Conti"],
    ),
    # =========================================================================
    # ORGANIZED CRIME
    # =========================================================================
    "organized_crime_fin": ThreatActorProfile(
        id="organized_crime_fin",
        name="Financial Cybercrime Group",
        aliases=["eCrime", "FIN-style"],
        threat_level=ThreatLevel.ORGANIZED_CRIME,
        motivation=[Motivation.FINANCIAL],
        target_sectors=[TargetSector.FINANCIAL, TargetSector.RETAIL, TargetSector.HEALTHCARE],
        description="""
            Well-organized criminal group focused on financial theft.
            Uses a mix of commodity and custom malware.
            Persistent, patient, and methodical approach.
        """,
        techniques=[
            "T1566.001",  # Spearphishing Attachment
            "T1566.002",  # Spearphishing Link
            "T1059.001",  # PowerShell
            "T1053.005",  # Scheduled Task
            "T1003.001",  # LSASS Memory
            "T1021.001",  # Remote Desktop Protocol
            "T1021.002",  # SMB/Windows Admin Shares
            "T1071.001",  # Web Protocols
            "T1041",  # Exfiltration Over C2 Channel
        ],
        preferred_tactics=[
            Tactic.INITIAL_ACCESS,
            Tactic.EXECUTION,
            Tactic.PERSISTENCE,
            Tactic.CREDENTIAL_ACCESS,
            Tactic.LATERAL_MOVEMENT,
            Tactic.COLLECTION,
            Tactic.EXFILTRATION,
        ],
        dwell_time_days=(7, 60),
        noise_level=0.4,
        persistence_likelihood=0.8,
        lateral_movement_likelihood=0.8,
        exfiltration_likelihood=0.9,
        tools=["Cobalt Strike", "Mimikatz", "BloodHound", "PsExec"],
        malware=["TrickBot", "Emotet", "Dridex"],
        active_hours_utc=(8, 20),
        active_days=[0, 1, 2, 3, 4],
    ),
    # =========================================================================
    # HACKTIVIST
    # =========================================================================
    "hacktivist_group": ThreatActorProfile(
        id="hacktivist_group",
        name="Hacktivist Collective",
        aliases=["Anonymous-style", "po1s0n1vy"],  # BOTS reference
        threat_level=ThreatLevel.HACKTIVIST,
        motivation=[Motivation.HACKTIVISM, Motivation.NOTORIETY],
        target_sectors=[TargetSector.GOVERNMENT, TargetSector.MEDIA, TargetSector.FINANCIAL],
        description="""
            Ideologically motivated group focused on disruption and exposure.
            Primarily targets organizations perceived as unethical.
            Focus on data theft for public release and defacement.
            Reference: Boss of the SOC v1 (po1s0n1vy targeting Wayne Corp)
        """,
        techniques=[
            "T1190",  # Exploit Public-Facing Application
            "T1566.002",  # Spearphishing Link
            "T1059.003",  # Windows Command Shell
            "T1087.001",  # Local Account Discovery
            "T1567.002",  # Exfiltration to Cloud Storage
        ],
        preferred_tactics=[
            Tactic.INITIAL_ACCESS,
            Tactic.DISCOVERY,
            Tactic.COLLECTION,
            Tactic.EXFILTRATION,
            Tactic.IMPACT,
        ],
        dwell_time_days=(1, 14),
        noise_level=0.6,
        persistence_likelihood=0.3,
        lateral_movement_likelihood=0.5,
        exfiltration_likelihood=0.9,
        tools=["SQLMap", "Nmap", "LOIC"],
        active_hours_utc=(0, 24),  # 24/7
        active_days=[0, 1, 2, 3, 4, 5, 6],
    ),
    # =========================================================================
    # INSIDER THREAT
    # =========================================================================
    "insider_malicious": ThreatActorProfile(
        id="insider_malicious",
        name="Malicious Insider",
        aliases=["Trusted Insider"],
        threat_level=ThreatLevel.INSIDER_THREAT,
        motivation=[Motivation.FINANCIAL, Motivation.NOTORIETY],
        target_sectors=[TargetSector.ANY],
        description="""
            Employee or contractor with legitimate access who abuses privileges.
            Uses knowledge of internal systems to avoid detection.
            Focus on data theft or sabotage before departure.
        """,
        techniques=[
            "T1087.001",  # Local Account Discovery
            "T1083",  # File and Directory Discovery
            "T1567.002",  # Exfiltration to Cloud Storage
            "T1041",  # Exfiltration Over C2 Channel
        ],
        preferred_tactics=[
            Tactic.DISCOVERY,
            Tactic.COLLECTION,
            Tactic.EXFILTRATION,
        ],
        dwell_time_days=(30, 180),
        noise_level=0.2,
        persistence_likelihood=0.1,  # Already has access
        lateral_movement_likelihood=0.3,
        exfiltration_likelihood=0.95,
        active_hours_utc=(9, 17),  # Business hours
        active_days=[0, 1, 2, 3, 4],
    ),
    # =========================================================================
    # APT - GENERIC
    # =========================================================================
    "apt_generic": ThreatActorProfile(
        id="apt_generic",
        name="Generic APT",
        aliases=["Advanced Threat"],
        threat_level=ThreatLevel.APT,
        motivation=[Motivation.ESPIONAGE],
        target_sectors=[
            TargetSector.GOVERNMENT,
            TargetSector.DEFENSE,
            TargetSector.TECHNOLOGY,
        ],
        description="""
            Sophisticated state-sponsored or well-funded threat actor.
            Patient, methodical approach with custom tooling.
            Focus on long-term access and intelligence gathering.
        """,
        techniques=[
            "T1566.001",  # Spearphishing Attachment
            "T1190",  # Exploit Public-Facing Application
            "T1059.001",  # PowerShell
            "T1053.005",  # Scheduled Task
            "T1543.003",  # Windows Service
            "T1055",  # Process Injection
            "T1003.001",  # LSASS Memory
            "T1069.002",  # Domain Groups Discovery
            "T1021.001",  # RDP
            "T1021.006",  # Windows Remote Management
            "T1071.001",  # Web Protocols
            "T1071.004",  # DNS
            "T1041",  # Exfiltration Over C2 Channel
        ],
        preferred_tactics=[
            Tactic.RECONNAISSANCE,
            Tactic.RESOURCE_DEVELOPMENT,
            Tactic.INITIAL_ACCESS,
            Tactic.EXECUTION,
            Tactic.PERSISTENCE,
            Tactic.PRIVILEGE_ESCALATION,
            Tactic.DEFENSE_EVASION,
            Tactic.CREDENTIAL_ACCESS,
            Tactic.DISCOVERY,
            Tactic.LATERAL_MOVEMENT,
            Tactic.COLLECTION,
            Tactic.COMMAND_AND_CONTROL,
            Tactic.EXFILTRATION,
        ],
        dwell_time_days=(60, 365),
        noise_level=0.1,
        persistence_likelihood=0.95,
        lateral_movement_likelihood=0.9,
        exfiltration_likelihood=0.85,
        tools=["Custom implants", "Living off the Land"],
    ),
    # =========================================================================
    # APT29 - COZY BEAR (Russia/SVR)
    # =========================================================================
    "apt29": ThreatActorProfile(
        id="apt29",
        name="APT29",
        aliases=[
            "Cozy Bear",
            "The Dukes",
            "Midnight Blizzard",
            "NOBELIUM",
            "UNC2452",
            "Dark Halo",
        ],
        threat_level=ThreatLevel.NATION_STATE,
        motivation=[Motivation.ESPIONAGE],
        target_sectors=[
            TargetSector.GOVERNMENT,
            TargetSector.DEFENSE,
            TargetSector.TECHNOLOGY,
            TargetSector.TELECOMMUNICATIONS,
        ],
        description="""
            Russian threat group attributed to SVR (Foreign Intelligence Service).
            Known for SolarWinds supply chain attack (SUNBURST).
            Highly sophisticated with custom malware and living-off-the-land techniques.
            Focus on government and think tanks in NATO countries.
        """,
        techniques=[
            "T1566.001",  # Spearphishing Attachment
            "T1566.002",  # Spearphishing Link
            "T1195.002",  # Supply Chain Compromise
            "T1059.001",  # PowerShell
            "T1053.005",  # Scheduled Task
            "T1547.001",  # Registry Run Keys
            "T1055",  # Process Injection
            "T1003.001",  # LSASS Memory
            "T1003.002",  # SAM
            "T1087.001",  # Local Account Discovery
            "T1069.002",  # Domain Groups Discovery
            "T1021.001",  # RDP
            "T1021.006",  # WinRM
            "T1071.001",  # Web Protocols
            "T1071.004",  # DNS
            "T1567.002",  # Exfiltration to Cloud Storage
        ],
        preferred_tactics=[
            Tactic.INITIAL_ACCESS,
            Tactic.EXECUTION,
            Tactic.PERSISTENCE,
            Tactic.PRIVILEGE_ESCALATION,
            Tactic.DEFENSE_EVASION,
            Tactic.CREDENTIAL_ACCESS,
            Tactic.DISCOVERY,
            Tactic.LATERAL_MOVEMENT,
            Tactic.COLLECTION,
            Tactic.COMMAND_AND_CONTROL,
            Tactic.EXFILTRATION,
        ],
        dwell_time_days=(90, 500),
        noise_level=0.05,
        persistence_likelihood=0.98,
        lateral_movement_likelihood=0.95,
        exfiltration_likelihood=0.9,
        tools=["Cobalt Strike", "Mimikatz", "AdFind"],
        malware=["SUNBURST", "TEARDROP", "WellMess", "WellMail"],
        attributed_country="Russia",
        mitre_group_id="G0016",
        active_hours_utc=(5, 15),  # Moscow business hours
        active_days=[0, 1, 2, 3, 4],
        references=[
            "https://attack.mitre.org/groups/G0016/",
        ],
    ),
    # =========================================================================
    # APT28 - FANCY BEAR (Russia/GRU)
    # =========================================================================
    "apt28": ThreatActorProfile(
        id="apt28",
        name="APT28",
        aliases=[
            "Fancy Bear",
            "Sofacy",
            "Pawn Storm",
            "Sednit",
            "STRONTIUM",
            "Forest Blizzard",
        ],
        threat_level=ThreatLevel.NATION_STATE,
        motivation=[Motivation.ESPIONAGE, Motivation.INFLUENCE],
        target_sectors=[
            TargetSector.GOVERNMENT,
            TargetSector.DEFENSE,
            TargetSector.MEDIA,
        ],
        description="""
            Russian threat group attributed to GRU (Military Intelligence).
            Known for DNC hack (2016) and various influence operations.
            Uses zero-days and spearphishing with sophisticated malware.
        """,
        techniques=[
            "T1566.001",  # Spearphishing Attachment
            "T1566.002",  # Spearphishing Link
            "T1190",  # Exploit Public-Facing Application
            "T1059.001",  # PowerShell
            "T1053.005",  # Scheduled Task
            "T1547.001",  # Registry Run Keys
            "T1003.001",  # LSASS Memory
            "T1110.003",  # Password Spraying
            "T1021.001",  # RDP
            "T1071.001",  # Web Protocols
            "T1041",  # Exfiltration Over C2 Channel
        ],
        preferred_tactics=[
            Tactic.INITIAL_ACCESS,
            Tactic.EXECUTION,
            Tactic.PERSISTENCE,
            Tactic.CREDENTIAL_ACCESS,
            Tactic.DISCOVERY,
            Tactic.LATERAL_MOVEMENT,
            Tactic.COLLECTION,
            Tactic.EXFILTRATION,
        ],
        dwell_time_days=(30, 180),
        noise_level=0.15,
        persistence_likelihood=0.9,
        lateral_movement_likelihood=0.85,
        exfiltration_likelihood=0.9,
        tools=["Responder", "Mimikatz", "PsExec"],
        malware=["XAgent", "Seduploader", "Zebrocy"],
        attributed_country="Russia",
        mitre_group_id="G0007",
        active_hours_utc=(5, 15),  # Moscow business hours
        active_days=[0, 1, 2, 3, 4],
        references=[
            "https://attack.mitre.org/groups/G0007/",
        ],
    ),
    # =========================================================================
    # LAZARUS GROUP (North Korea)
    # =========================================================================
    "lazarus": ThreatActorProfile(
        id="lazarus",
        name="Lazarus Group",
        aliases=[
            "HIDDEN COBRA",
            "Guardians of Peace",
            "ZINC",
            "Diamond Sleet",
        ],
        threat_level=ThreatLevel.NATION_STATE,
        motivation=[Motivation.FINANCIAL, Motivation.ESPIONAGE, Motivation.SABOTAGE],
        target_sectors=[
            TargetSector.FINANCIAL,
            TargetSector.DEFENSE,
            TargetSector.TECHNOLOGY,
            TargetSector.GOVERNMENT,
        ],
        description="""
            North Korean threat group known for diverse operations.
            Sony Pictures hack (2014), WannaCry ransomware (2017).
            Unique focus on cryptocurrency theft for regime funding.
        """,
        techniques=[
            "T1566.001",  # Spearphishing Attachment
            "T1566.002",  # Spearphishing Link
            "T1059.001",  # PowerShell
            "T1059.003",  # Windows Command Shell
            "T1053.005",  # Scheduled Task
            "T1543.003",  # Windows Service
            "T1003.001",  # LSASS Memory
            "T1021.001",  # RDP
            "T1071.001",  # Web Protocols
            "T1486",  # Data Encrypted for Impact
            "T1490",  # Inhibit System Recovery
        ],
        preferred_tactics=[
            Tactic.INITIAL_ACCESS,
            Tactic.EXECUTION,
            Tactic.PERSISTENCE,
            Tactic.CREDENTIAL_ACCESS,
            Tactic.LATERAL_MOVEMENT,
            Tactic.EXFILTRATION,
            Tactic.IMPACT,
        ],
        dwell_time_days=(14, 120),
        noise_level=0.3,
        persistence_likelihood=0.85,
        lateral_movement_likelihood=0.8,
        exfiltration_likelihood=0.85,
        tools=["Mimikatz", "PsExec"],
        malware=["Destover", "WannaCry", "AppleJeus"],
        attributed_country="North Korea",
        mitre_group_id="G0032",
        active_hours_utc=(0, 10),  # Pyongyang business hours
        active_days=[0, 1, 2, 3, 4, 5],  # 6-day work week
        references=[
            "https://attack.mitre.org/groups/G0032/",
        ],
    ),
    # =========================================================================
    # APT41 (China)
    # =========================================================================
    "apt41": ThreatActorProfile(
        id="apt41",
        name="APT41",
        aliases=[
            "Double Dragon",
            "BARIUM",
            "Winnti",
            "Wicked Panda",
            "Brass Typhoon",
        ],
        threat_level=ThreatLevel.NATION_STATE,
        motivation=[Motivation.ESPIONAGE, Motivation.FINANCIAL],
        target_sectors=[
            TargetSector.TECHNOLOGY,
            TargetSector.HEALTHCARE,
            TargetSector.TELECOMMUNICATIONS,
            TargetSector.GOVERNMENT,
        ],
        description="""
            Chinese threat group with dual espionage and financial motives.
            Known for supply chain attacks and targeting gaming companies.
            Uses sophisticated malware and living-off-the-land techniques.
        """,
        techniques=[
            "T1566.001",  # Spearphishing Attachment
            "T1190",  # Exploit Public-Facing Application
            "T1195.002",  # Supply Chain Compromise
            "T1059.001",  # PowerShell
            "T1053.005",  # Scheduled Task
            "T1547.001",  # Registry Run Keys
            "T1055",  # Process Injection
            "T1003.001",  # LSASS Memory
            "T1021.001",  # RDP
            "T1021.002",  # SMB/Windows Admin Shares
            "T1071.001",  # Web Protocols
            "T1105",  # Ingress Tool Transfer
        ],
        preferred_tactics=[
            Tactic.INITIAL_ACCESS,
            Tactic.EXECUTION,
            Tactic.PERSISTENCE,
            Tactic.PRIVILEGE_ESCALATION,
            Tactic.DEFENSE_EVASION,
            Tactic.CREDENTIAL_ACCESS,
            Tactic.DISCOVERY,
            Tactic.LATERAL_MOVEMENT,
            Tactic.COLLECTION,
            Tactic.EXFILTRATION,
        ],
        dwell_time_days=(60, 300),
        noise_level=0.1,
        persistence_likelihood=0.95,
        lateral_movement_likelihood=0.9,
        exfiltration_likelihood=0.9,
        tools=["Cobalt Strike", "Mimikatz", "BloodHound"],
        malware=["ShadowPad", "PlugX", "Winnti"],
        attributed_country="China",
        mitre_group_id="G0096",
        active_hours_utc=(0, 8),  # Beijing business hours
        active_days=[0, 1, 2, 3, 4],
        references=[
            "https://attack.mitre.org/groups/G0096/",
        ],
    ),
}


def get_threat_actor_by_id(actor_id: str) -> ThreatActorProfile | None:
    """Get a threat actor profile by ID."""
    return THREAT_ACTOR_PROFILES.get(actor_id)


def get_threat_actors_by_level(level: ThreatLevel) -> list[ThreatActorProfile]:
    """Get all threat actors at a specific threat level."""
    return [
        actor
        for actor in THREAT_ACTOR_PROFILES.values()
        if actor.threat_level == level
    ]


def get_threat_actors_by_sector(sector: TargetSector) -> list[ThreatActorProfile]:
    """Get threat actors that target a specific sector."""
    return [
        actor
        for actor in THREAT_ACTOR_PROFILES.values()
        if sector in actor.target_sectors or TargetSector.ANY in actor.target_sectors
    ]


def list_all_threat_actors() -> list[ThreatActorProfile]:
    """List all available threat actor profiles."""
    return list(THREAT_ACTOR_PROFILES.values())
