"""
Faux Splunk Cloud - Ephemeral Splunk Cloud Victoria instances for development and testing.

This package provides developers with ephemeral instances of Splunk configured to operate
as close as possible to official Splunk Cloud Victoria infrastructure, including:

- ACS (Admin Config Service) API compatibility
- Victoria Experience architecture patterns
- HEC (HTTP Event Collector) endpoints
- Index management
- App management
- Splunk SDK compatibility

References:
    - Splunk Cloud Platform Service Details
    - Splunk Validated Architectures (SVA)
    - Admin Config Service (ACS) API
    - Splunk Enterprise SDK for Python
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
