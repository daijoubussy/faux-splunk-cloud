"""
Faux Splunk Cloud API.

This module provides two API surfaces:

1. Instance Management API (/api/v1/instances)
   - Create, list, start, stop, destroy ephemeral instances
   - Designed for integration with Backstage and CI/CD systems

2. ACS API Simulation (/{stack}/adminconfig/v2)
   - Compatible with Splunk ACS API
   - Supports Terraform Provider and SDK
   - Index, HEC, app management
"""

from faux_splunk_cloud.api.app import create_app

__all__ = ["create_app"]
