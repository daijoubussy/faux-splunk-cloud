"""
Workflow prototype definitions.

These prototypes define the available node types for building workflows,
mapping to MineMeld's prototype system.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class PrototypeType(str, Enum):
    """Type of workflow prototype."""

    MINER = "miner"
    PROCESSOR = "processor"
    OUTPUT = "output"


class ConfigSchema(BaseModel):
    """Schema for a configuration field."""

    type: str  # string, number, boolean, array, object
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[list[Any]] = None  # For select fields


class WorkflowPrototype(BaseModel):
    """
    Definition of a workflow node type.

    Equivalent to a MineMeld prototype.
    """

    id: str
    name: str
    type: PrototypeType
    description: str
    category: str  # Grouping for UI
    config_schema: dict[str, ConfigSchema] = Field(default_factory=dict)
    default_config: dict[str, Any] = Field(default_factory=dict)

    # Capabilities
    supported_indicator_types: list[str] = Field(default_factory=list)
    output_indicator_types: list[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


# =============================================================================
# MINER PROTOTYPES - Input nodes that fetch indicators
# =============================================================================

MINER_PROTOTYPES: list[WorkflowPrototype] = [
    WorkflowPrototype(
        id="taxii.client",
        name="TAXII Client",
        type=PrototypeType.MINER,
        description="Fetch indicators from a TAXII 2.x server",
        category="Feed Connectors",
        config_schema={
            "url": ConfigSchema(type="string", description="TAXII server URL", required=True),
            "collection": ConfigSchema(type="string", description="Collection ID", required=True),
            "username": ConfigSchema(type="string", description="Username for authentication"),
            "password": ConfigSchema(type="string", description="Password for authentication"),
            "api_key": ConfigSchema(type="string", description="API key for authentication"),
            "poll_interval": ConfigSchema(
                type="number",
                description="Poll interval in minutes",
                default=60,
            ),
        },
        default_config={"poll_interval": 60},
        supported_indicator_types=["*"],
        output_indicator_types=["*"],
    ),
    WorkflowPrototype(
        id="rest.client",
        name="REST API Client",
        type=PrototypeType.MINER,
        description="Fetch indicators from a REST API endpoint",
        category="Feed Connectors",
        config_schema={
            "url": ConfigSchema(type="string", description="API endpoint URL", required=True),
            "method": ConfigSchema(
                type="string",
                description="HTTP method",
                default="GET",
                enum=["GET", "POST"],
            ),
            "headers": ConfigSchema(type="object", description="HTTP headers"),
            "auth_type": ConfigSchema(
                type="string",
                description="Authentication type",
                enum=["none", "basic", "bearer", "api_key"],
            ),
            "response_path": ConfigSchema(
                type="string",
                description="JSONPath to indicators in response",
            ),
            "indicator_field": ConfigSchema(
                type="string",
                description="Field containing indicator value",
                default="value",
            ),
            "type_field": ConfigSchema(
                type="string",
                description="Field containing indicator type",
                default="type",
            ),
        },
        default_config={"method": "GET", "auth_type": "none"},
        supported_indicator_types=["*"],
        output_indicator_types=["*"],
    ),
    WorkflowPrototype(
        id="csv.file",
        name="CSV File",
        type=PrototypeType.MINER,
        description="Read indicators from a CSV file or URL",
        category="Feed Connectors",
        config_schema={
            "source": ConfigSchema(type="string", description="File path or URL", required=True),
            "delimiter": ConfigSchema(type="string", description="CSV delimiter", default=","),
            "indicator_column": ConfigSchema(
                type="string",
                description="Column containing indicator values",
                required=True,
            ),
            "type_column": ConfigSchema(
                type="string",
                description="Column containing indicator types",
            ),
            "skip_header": ConfigSchema(type="boolean", description="Skip header row", default=True),
            "comment_char": ConfigSchema(type="string", description="Comment character", default="#"),
        },
        default_config={"delimiter": ",", "skip_header": True, "comment_char": "#"},
        supported_indicator_types=["*"],
        output_indicator_types=["*"],
    ),
    WorkflowPrototype(
        id="localdb",
        name="Local Database",
        type=PrototypeType.MINER,
        description="Manual indicator list stored locally",
        category="Local Storage",
        config_schema={
            "indicators": ConfigSchema(
                type="array",
                description="List of indicators",
                default=[],
            ),
        },
        default_config={"indicators": []},
        supported_indicator_types=["*"],
        output_indicator_types=["*"],
    ),
    WorkflowPrototype(
        id="alienvault.otx",
        name="AlienVault OTX",
        type=PrototypeType.MINER,
        description="Fetch indicators from AlienVault OTX",
        category="Threat Intelligence Platforms",
        config_schema={
            "api_key": ConfigSchema(type="string", description="OTX API key", required=True),
            "pulse_ids": ConfigSchema(type="array", description="Specific pulse IDs to fetch"),
            "subscribed_only": ConfigSchema(
                type="boolean",
                description="Only fetch subscribed pulses",
                default=True,
            ),
        },
        default_config={"subscribed_only": True},
        supported_indicator_types=["*"],
        output_indicator_types=["*"],
    ),
    WorkflowPrototype(
        id="misp.feed",
        name="MISP Feed",
        type=PrototypeType.MINER,
        description="Fetch indicators from a MISP instance",
        category="Threat Intelligence Platforms",
        config_schema={
            "url": ConfigSchema(type="string", description="MISP instance URL", required=True),
            "api_key": ConfigSchema(type="string", description="MISP API key", required=True),
            "verify_ssl": ConfigSchema(type="boolean", description="Verify SSL certificates", default=True),
            "event_filter": ConfigSchema(type="object", description="Event filter criteria"),
        },
        default_config={"verify_ssl": True},
        supported_indicator_types=["*"],
        output_indicator_types=["*"],
    ),
]

# =============================================================================
# PROCESSOR PROTOTYPES - Transform nodes
# =============================================================================

PROCESSOR_PROTOTYPES: list[WorkflowPrototype] = [
    WorkflowPrototype(
        id="aggregator.generic",
        name="Generic Aggregator",
        type=PrototypeType.PROCESSOR,
        description="Aggregate and deduplicate indicators from multiple sources",
        category="Aggregation",
        config_schema={
            "dedup_key": ConfigSchema(
                type="string",
                description="Field to use for deduplication",
                default="value",
            ),
            "merge_sources": ConfigSchema(
                type="boolean",
                description="Merge source information",
                default=True,
            ),
            "confidence_method": ConfigSchema(
                type="string",
                description="Method to combine confidence scores",
                default="max",
                enum=["max", "min", "avg", "sum"],
            ),
        },
        default_config={"dedup_key": "value", "merge_sources": True, "confidence_method": "max"},
        supported_indicator_types=["*"],
        output_indicator_types=["*"],
    ),
    WorkflowPrototype(
        id="aggregator.ipv4",
        name="IPv4 Aggregator",
        type=PrototypeType.PROCESSOR,
        description="Aggregate and CIDR-merge IPv4 indicators",
        category="Aggregation",
        config_schema={
            "merge_cidr": ConfigSchema(
                type="boolean",
                description="Merge adjacent CIDR blocks",
                default=False,
            ),
            "whitelist": ConfigSchema(
                type="array",
                description="CIDR ranges to exclude",
                default=[],
            ),
        },
        default_config={"merge_cidr": False, "whitelist": []},
        supported_indicator_types=["ipv4"],
        output_indicator_types=["ipv4"],
    ),
    WorkflowPrototype(
        id="filter.confidence",
        name="Confidence Filter",
        type=PrototypeType.PROCESSOR,
        description="Filter indicators by confidence score",
        category="Filtering",
        config_schema={
            "min_confidence": ConfigSchema(
                type="number",
                description="Minimum confidence score (0-100)",
                default=50,
            ),
            "max_confidence": ConfigSchema(
                type="number",
                description="Maximum confidence score (0-100)",
                default=100,
            ),
        },
        default_config={"min_confidence": 50, "max_confidence": 100},
        supported_indicator_types=["*"],
        output_indicator_types=["*"],
    ),
    WorkflowPrototype(
        id="filter.age",
        name="Age Filter",
        type=PrototypeType.PROCESSOR,
        description="Filter indicators by age (time since last seen)",
        category="Filtering",
        config_schema={
            "max_age_days": ConfigSchema(
                type="number",
                description="Maximum age in days",
                default=30,
            ),
            "use_first_seen": ConfigSchema(
                type="boolean",
                description="Use first_seen instead of last_seen",
                default=False,
            ),
        },
        default_config={"max_age_days": 30, "use_first_seen": False},
        supported_indicator_types=["*"],
        output_indicator_types=["*"],
    ),
    WorkflowPrototype(
        id="filter.type",
        name="Type Filter",
        type=PrototypeType.PROCESSOR,
        description="Filter indicators by type",
        category="Filtering",
        config_schema={
            "include_types": ConfigSchema(
                type="array",
                description="Types to include (empty = all)",
                default=[],
            ),
            "exclude_types": ConfigSchema(
                type="array",
                description="Types to exclude",
                default=[],
            ),
        },
        default_config={"include_types": [], "exclude_types": []},
        supported_indicator_types=["*"],
        output_indicator_types=["*"],
    ),
    WorkflowPrototype(
        id="enricher.whois",
        name="WHOIS Enricher",
        type=PrototypeType.PROCESSOR,
        description="Enrich IP and domain indicators with WHOIS data",
        category="Enrichment",
        config_schema={
            "cache_ttl": ConfigSchema(
                type="number",
                description="Cache TTL in hours",
                default=24,
            ),
            "add_fields": ConfigSchema(
                type="array",
                description="WHOIS fields to add",
                default=["registrar", "creation_date", "country"],
            ),
        },
        default_config={"cache_ttl": 24, "add_fields": ["registrar", "creation_date", "country"]},
        supported_indicator_types=["ipv4", "ipv6", "domain"],
        output_indicator_types=["ipv4", "ipv6", "domain"],
    ),
    WorkflowPrototype(
        id="enricher.geoip",
        name="GeoIP Enricher",
        type=PrototypeType.PROCESSOR,
        description="Add geolocation data to IP indicators",
        category="Enrichment",
        config_schema={
            "database": ConfigSchema(
                type="string",
                description="GeoIP database type",
                default="maxmind_city",
                enum=["maxmind_city", "maxmind_country", "ipinfo"],
            ),
            "api_key": ConfigSchema(type="string", description="API key for online services"),
        },
        default_config={"database": "maxmind_city"},
        supported_indicator_types=["ipv4", "ipv6"],
        output_indicator_types=["ipv4", "ipv6"],
    ),
    WorkflowPrototype(
        id="tagger",
        name="Tag Manager",
        type=PrototypeType.PROCESSOR,
        description="Add or remove tags from indicators",
        category="Enrichment",
        config_schema={
            "add_tags": ConfigSchema(
                type="array",
                description="Tags to add",
                default=[],
            ),
            "remove_tags": ConfigSchema(
                type="array",
                description="Tags to remove",
                default=[],
            ),
            "replace_all": ConfigSchema(
                type="boolean",
                description="Replace all existing tags",
                default=False,
            ),
        },
        default_config={"add_tags": [], "remove_tags": [], "replace_all": False},
        supported_indicator_types=["*"],
        output_indicator_types=["*"],
    ),
]

# =============================================================================
# OUTPUT PROTOTYPES - Export nodes
# =============================================================================

OUTPUT_PROTOTYPES: list[WorkflowPrototype] = [
    WorkflowPrototype(
        id="edl.paloalto",
        name="Palo Alto EDL",
        type=PrototypeType.OUTPUT,
        description="External Dynamic List for Palo Alto firewalls",
        category="Firewall Integration",
        config_schema={
            "format": ConfigSchema(
                type="string",
                description="Output format",
                default="plain",
                enum=["plain", "json"],
            ),
            "include_type": ConfigSchema(
                type="string",
                description="Indicator type to include",
                required=True,
                enum=["ipv4", "domain", "url"],
            ),
            "max_entries": ConfigSchema(
                type="number",
                description="Maximum entries in list",
                default=10000,
            ),
        },
        default_config={"format": "plain", "max_entries": 10000},
        supported_indicator_types=["ipv4", "domain", "url"],
        output_indicator_types=[],
    ),
    WorkflowPrototype(
        id="taxii.server",
        name="TAXII Server",
        type=PrototypeType.OUTPUT,
        description="Serve indicators via TAXII 2.x protocol",
        category="Protocol Servers",
        config_schema={
            "collection_title": ConfigSchema(
                type="string",
                description="TAXII collection title",
                required=True,
            ),
            "collection_description": ConfigSchema(
                type="string",
                description="TAXII collection description",
            ),
            "max_content_length": ConfigSchema(
                type="number",
                description="Max content length per request",
                default=10000,
            ),
        },
        default_config={"max_content_length": 10000},
        supported_indicator_types=["*"],
        output_indicator_types=[],
    ),
    WorkflowPrototype(
        id="splunk.hec",
        name="Splunk HEC",
        type=PrototypeType.OUTPUT,
        description="Send indicators to Splunk via HTTP Event Collector",
        category="SIEM Integration",
        config_schema={
            "url": ConfigSchema(type="string", description="HEC endpoint URL", required=True),
            "token": ConfigSchema(type="string", description="HEC token", required=True),
            "index": ConfigSchema(type="string", description="Target index", default="threat_intel"),
            "sourcetype": ConfigSchema(
                type="string",
                description="Sourcetype for events",
                default="threat_intel:indicator",
            ),
            "verify_ssl": ConfigSchema(type="boolean", description="Verify SSL", default=True),
            "batch_size": ConfigSchema(type="number", description="Batch size", default=100),
        },
        default_config={
            "index": "threat_intel",
            "sourcetype": "threat_intel:indicator",
            "verify_ssl": True,
            "batch_size": 100,
        },
        supported_indicator_types=["*"],
        output_indicator_types=[],
    ),
    WorkflowPrototype(
        id="stix.bundle",
        name="STIX Bundle",
        type=PrototypeType.OUTPUT,
        description="Export indicators as STIX 2.1 bundle",
        category="Export Formats",
        config_schema={
            "output_path": ConfigSchema(
                type="string",
                description="Output file path or URL",
                required=True,
            ),
            "include_relationships": ConfigSchema(
                type="boolean",
                description="Include relationship objects",
                default=True,
            ),
            "bundle_id_prefix": ConfigSchema(
                type="string",
                description="Prefix for bundle IDs",
                default="bundle--",
            ),
        },
        default_config={"include_relationships": True, "bundle_id_prefix": "bundle--"},
        supported_indicator_types=["*"],
        output_indicator_types=[],
    ),
    WorkflowPrototype(
        id="csv.export",
        name="CSV Export",
        type=PrototypeType.OUTPUT,
        description="Export indicators to CSV file",
        category="Export Formats",
        config_schema={
            "output_path": ConfigSchema(type="string", description="Output file path", required=True),
            "delimiter": ConfigSchema(type="string", description="CSV delimiter", default=","),
            "fields": ConfigSchema(
                type="array",
                description="Fields to include",
                default=["type", "value", "confidence", "first_seen", "last_seen"],
            ),
            "include_header": ConfigSchema(type="boolean", description="Include header row", default=True),
        },
        default_config={
            "delimiter": ",",
            "fields": ["type", "value", "confidence", "first_seen", "last_seen"],
            "include_header": True,
        },
        supported_indicator_types=["*"],
        output_indicator_types=[],
    ),
    WorkflowPrototype(
        id="webhook",
        name="Webhook",
        type=PrototypeType.OUTPUT,
        description="Send indicators to a webhook endpoint",
        category="Integration",
        config_schema={
            "url": ConfigSchema(type="string", description="Webhook URL", required=True),
            "method": ConfigSchema(
                type="string",
                description="HTTP method",
                default="POST",
                enum=["POST", "PUT"],
            ),
            "headers": ConfigSchema(type="object", description="Custom headers"),
            "auth_type": ConfigSchema(
                type="string",
                description="Authentication type",
                enum=["none", "basic", "bearer"],
            ),
            "batch_size": ConfigSchema(type="number", description="Batch size", default=100),
            "retry_count": ConfigSchema(type="number", description="Retry count on failure", default=3),
        },
        default_config={"method": "POST", "auth_type": "none", "batch_size": 100, "retry_count": 3},
        supported_indicator_types=["*"],
        output_indicator_types=[],
    ),
]

# =============================================================================
# Helper Functions
# =============================================================================

ALL_PROTOTYPES = MINER_PROTOTYPES + PROCESSOR_PROTOTYPES + OUTPUT_PROTOTYPES


def get_prototype(prototype_id: str) -> WorkflowPrototype | None:
    """Get a prototype by ID."""
    for proto in ALL_PROTOTYPES:
        if proto.id == prototype_id:
            return proto
    return None


def list_prototypes(
    prototype_type: PrototypeType | None = None,
    category: str | None = None,
) -> list[WorkflowPrototype]:
    """
    List available prototypes.

    Args:
        prototype_type: Filter by type (miner, processor, output)
        category: Filter by category

    Returns:
        List of matching prototypes
    """
    result = ALL_PROTOTYPES

    if prototype_type:
        result = [p for p in result if p.type == prototype_type]

    if category:
        result = [p for p in result if p.category == category]

    return result
