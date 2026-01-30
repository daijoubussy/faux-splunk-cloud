"""
Customer API routes.

These routes are accessible to tenant customers (non-admin users).
All operations are scoped to the customer's tenant.
"""

from fastapi import APIRouter, Depends

from faux_splunk_cloud.api.deps import require_customer

from .attacks import router as attacks_router
from .instances import router as instances_router
from .users import router as users_router

# Customer router with auth requirement at router level
router = APIRouter(
    prefix="/customer",
    tags=["customer"],
    dependencies=[Depends(require_customer)],
)

# Include sub-routers
router.include_router(instances_router, prefix="/instances", tags=["customer-instances"])
router.include_router(attacks_router, prefix="/attacks", tags=["customer-attacks"])
router.include_router(users_router, prefix="/users", tags=["customer-users"])

__all__ = ["router"]
