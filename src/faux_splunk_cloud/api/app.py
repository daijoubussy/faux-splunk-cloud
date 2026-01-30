"""
FastAPI application for Faux Splunk Cloud.

Provides:
1. Instance Management API for lifecycle operations
2. ACS API simulation for Splunk Cloud compatibility
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from faux_splunk_cloud.api.routes import acs, attacks, health, instances, workflows
from faux_splunk_cloud.config import settings
from faux_splunk_cloud.services.instance_manager import instance_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Faux Splunk Cloud API...")
    await instance_manager.start()
    logger.info("Faux Splunk Cloud API started")

    yield

    # Shutdown
    logger.info("Shutting down Faux Splunk Cloud API...")
    await instance_manager.stop()
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

### Instance Management (`/api/v1/instances`)
Create, manage, and destroy ephemeral Splunk instances.

### ACS API Simulation (`/{stack}/adminconfig/v2`)
Compatible with Splunk Cloud Admin Config Service API.
Supports index, HEC token, and app management.

### Attack Simulation (`/api/v1/attacks`)
Simulate adversarial attacks from script kiddies to nation-state APTs.
Generate realistic security logs based on MITRE ATT&CK techniques.

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
