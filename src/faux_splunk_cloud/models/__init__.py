"""
Data models for Faux Splunk Cloud.

These models are designed to be compatible with:
- Splunk ACS API request/response formats
- Splunk Enterprise REST API
- Splunk SDK for Python
- Splunk Terraform Provider
"""

from faux_splunk_cloud.models.acs import (
    ACSApp,
    ACSAppInstallRequest,
    ACSAppListResponse,
    ACSHECToken,
    ACSHECTokenCreateRequest,
    ACSHECTokenListResponse,
    ACSIndex,
    ACSIndexCreateRequest,
    ACSIndexListResponse,
    ACSIPAllowList,
    ACSIPAllowListEntry,
)
from faux_splunk_cloud.models.instance import (
    Instance,
    InstanceConfig,
    InstanceCreate,
    InstanceStatus,
    InstanceTopology,
)

__all__ = [
    # Instance models
    "Instance",
    "InstanceConfig",
    "InstanceCreate",
    "InstanceStatus",
    "InstanceTopology",
    # ACS models
    "ACSIndex",
    "ACSIndexCreateRequest",
    "ACSIndexListResponse",
    "ACSHECToken",
    "ACSHECTokenCreateRequest",
    "ACSHECTokenListResponse",
    "ACSApp",
    "ACSAppInstallRequest",
    "ACSAppListResponse",
    "ACSIPAllowList",
    "ACSIPAllowListEntry",
]
