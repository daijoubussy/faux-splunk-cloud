"""
FastAPI application for Faux Splunk Cloud.

Provides:
1. Instance Management API for lifecycle operations
2. ACS API simulation for Splunk Cloud compatibility
3. Admin API for tenant and platform management
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from faux_splunk_cloud.api.routes import acs, admin, attacks, audit, boundary, concourse, export, health, idp, impersonation, instances, saml, siem, vault, workflows
from faux_splunk_cloud.api.routes import customer
from faux_splunk_cloud.config import settings
from faux_splunk_cloud.services.audit_service import audit_service
from faux_splunk_cloud.services.concourse_service import concourse_service
from faux_splunk_cloud.services.impersonation_service import impersonation_service
from faux_splunk_cloud.services.instance_export import instance_export_service
from faux_splunk_cloud.services.instance_manager import instance_manager
from faux_splunk_cloud.services.siem_service import siem_service
from faux_splunk_cloud.services.tenant_service import tenant_service
from faux_splunk_cloud.services.vault_service import vault_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Faux Splunk Cloud API...")
    await audit_service.start()
    await tenant_service.start()
    await impersonation_service.start()
    await instance_manager.start()
    await instance_export_service.start()
    await siem_service.start()
    await vault_service.start()
    await concourse_service.start()
    logger.info("Faux Splunk Cloud API started")

    yield

    # Shutdown
    logger.info("Shutting down Faux Splunk Cloud API...")
    await concourse_service.stop()
    await vault_service.stop()
    await siem_service.stop()
    await instance_export_service.stop()
    await instance_manager.stop()
    await impersonation_service.stop()
    await tenant_service.stop()
    await audit_service.stop()
    logger.info("Faux Splunk Cloud API stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Faux Splunk Cloud",
        description="""
Ephemeral Splunk Cloud Victoria instances for development and testing.

## Features

- **Ephemeral Instances**: Spin up Victoria-like Splunk environments on demand
- **ACS API Compatible**: Full compatibility with Splunk Terraform Provider and SDK
- **HEC Support**: HTTP Event Collector endpoints for data ingestion
- **Backstage Integration**: Software templates for developer self-service
- **Attack Simulation**: Adversarial attack simulation for security training

## API Surfaces

### Customer Portal (`/api/v1/customer`)
Tenant-scoped operations for customers:
- Instance management (create, start, stop, destroy)
- Attack simulations against customer instances
- Tenant-scoped audit logs and configuration

### Admin Portal (`/api/v1/admin`)
Platform administration (admin-only):
- Tenant management
- SIEM integration
- Platform-wide audit logs and statistics

### ACS API Simulation (`/{stack}/adminconfig/v2`)
Compatible with Splunk Cloud Admin Config Service API.
Supports index, HEC token, and app management.

## References

- [Splunk ACS API](https://help.splunk.com/en/splunk-cloud-platform/administer/admin-config-service-manual/)
- [Splunk Validated Architectures](https://help.splunk.com/en/splunk-cloud-platform/splunk-validated-architectures/)
- [Splunk SDK for Python](https://github.com/splunk/splunk-sdk-python)
        """,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(health.router, tags=["Health"])
    app.include_router(
        instances.router,
        prefix="/api/v1/instances",
        tags=["Instances"],
    )
    app.include_router(
        acs.router,
        prefix="/{stack}/adminconfig/v2",
        tags=["ACS API"],
    )
    app.include_router(
        attacks.router,
        prefix="/api/v1/attacks",
        tags=["Attack Simulation"],
    )
    app.include_router(
        workflows.router,
        prefix="/api/v1",
        tags=["Workflows"],
    )
    app.include_router(
        admin.router,
        prefix="/api/v1/admin",
        tags=["Admin"],
    )
    app.include_router(
        impersonation.router,
        prefix="/api/v1/impersonation",
        tags=["Impersonation"],
    )
    app.include_router(
        audit.router,
        prefix="/api/v1/audit",
        tags=["Audit"],
    )
    app.include_router(
        export.router,
        prefix="/api/v1/export",
        tags=["Config Export"],
    )
    app.include_router(
        siem.router,
        prefix="/api/v1/siem",
        tags=["SIEM"],
    )
    app.include_router(
        saml.router,
        prefix="/api/v1/auth/saml",
        tags=["SAML Authentication"],
    )
    app.include_router(
        idp.router,
        prefix="/api/v1/idp",
        tags=["Identity Provider Configuration"],
    )
    app.include_router(
        boundary.router,
        prefix="/api/v1/boundary",
        tags=["Boundary Access Control"],
    )
    app.include_router(
        vault.router,
        prefix="/api/v1/vault",
        tags=["Vault Secrets Management"],
    )
    app.include_router(
        concourse.router,
        prefix="/api/v1/concourse",
        tags=["Concourse CI/CD"],
    )

    # Customer routes - tenant-scoped operations for customers
    app.include_router(
        customer.router,
        prefix="/api/v1",
        tags=["Customer Portal"],
    )

    # Exception handlers
    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        return JSONResponse(
            status_code=400,
            content={"code": "BAD_REQUEST", "message": str(exc)},
        )

    @app.exception_handler(KeyError)
    async def key_error_handler(request, exc):
        return JSONResponse(
            status_code=404,
            content={"code": "NOT_FOUND", "message": str(exc)},
        )

    return app


# Create app instance for uvicorn
app = create_app()
