"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready"}


@router.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Faux Splunk Cloud",
        "version": "0.1.0",
        "description": "Ephemeral Splunk Cloud Victoria instances for development",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
