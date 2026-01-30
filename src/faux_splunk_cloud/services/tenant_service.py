"""
Tenant service for multi-tenancy management.

Handles CRUD operations for tenants and enforces resource quotas.
"""

import logging
import secrets
from datetime import datetime
from pathlib import Path

import yaml

from faux_splunk_cloud.config import settings
from faux_splunk_cloud.models.tenant import (
    Tenant,
    TenantCreate,
    TenantList,
    TenantSettings,
    TenantStatus,
    TenantUpdate,
)

logger = logging.getLogger(__name__)


class TenantService:
    """
    Manages tenant lifecycle and resource quotas.

    Provides:
    - Tenant CRUD operations
    - IdP organization mapping
    - Resource usage tracking
    - Quota enforcement
    """

    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}
        self._idp_org_index: dict[str, str] = {}  # idp_org_id -> tenant_id
        self._slug_index: dict[str, str] = {}  # slug -> tenant_id

    async def start(self) -> None:
        """Start the tenant service and load existing tenants."""
        settings.ensure_data_dir()
        await self._load_tenants()
        logger.info(f"Tenant service started with {len(self._tenants)} tenants")

    async def stop(self) -> None:
        """Stop the tenant service."""
        logger.info("Tenant service stopped")

    async def _load_tenants(self) -> None:
        """Load existing tenants from disk."""
        tenants_dir = settings.data_dir / "tenants"
        if not tenants_dir.exists():
            tenants_dir.mkdir(parents=True, exist_ok=True)
            return

        for tenant_file in tenants_dir.glob("*.yaml"):
            try:
                with open(tenant_file) as f:
                    data = yaml.safe_load(f)
                    if data:
                        tenant = Tenant(**data)
                        self._tenants[tenant.id] = tenant
                        self._index_tenant(tenant)
                        logger.debug(f"Loaded tenant {tenant.id} ({tenant.name})")
            except Exception as e:
                logger.error(f"Failed to load tenant from {tenant_file}: {e}")

    def _index_tenant(self, tenant: Tenant) -> None:
        """Add tenant to lookup indexes."""
        if tenant.idp_org_id:
            self._idp_org_index[tenant.idp_org_id] = tenant.id
        self._slug_index[tenant.slug] = tenant.id

    def _unindex_tenant(self, tenant: Tenant) -> None:
        """Remove tenant from lookup indexes."""
        if tenant.idp_org_id and tenant.idp_org_id in self._idp_org_index:
            del self._idp_org_index[tenant.idp_org_id]
        if tenant.slug in self._slug_index:
            del self._slug_index[tenant.slug]

    async def _save_tenant(self, tenant: Tenant) -> None:
        """Save tenant state to disk."""
        tenants_dir = settings.data_dir / "tenants"
        tenants_dir.mkdir(parents=True, exist_ok=True)

        tenant_file = tenants_dir / f"{tenant.id}.yaml"
        with open(tenant_file, "w") as f:
            yaml.dump(tenant.model_dump(mode="json"), f, default_flow_style=False)

    async def _delete_tenant_file(self, tenant_id: str) -> None:
        """Delete tenant file from disk."""
        tenant_file = settings.data_dir / "tenants" / f"{tenant_id}.yaml"
        if tenant_file.exists():
            tenant_file.unlink()

    def _generate_tenant_id(self) -> str:
        """Generate a unique tenant ID."""
        return f"tenant-{secrets.token_hex(8)}"

    async def create_tenant(self, request: TenantCreate) -> Tenant:
        """
        Create a new tenant.

        Args:
            request: Tenant creation request

        Returns:
            The created tenant

        Raises:
            ValueError: If slug or idp_org_id already exists
        """
        # Check for duplicate slug
        if request.slug in self._slug_index:
            raise ValueError(f"Tenant with slug '{request.slug}' already exists")

        # Check for duplicate idp_org_id
        if request.idp_org_id and request.idp_org_id in self._idp_org_index:
            raise ValueError(f"Tenant with IdP org '{request.idp_org_id}' already exists")

        now = datetime.utcnow()
        tenant = Tenant(
            id=self._generate_tenant_id(),
            name=request.name,
            slug=request.slug,
            idp_org_id=request.idp_org_id,
            settings=request.settings,
            status=TenantStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            instance_count=0,
            total_memory_mb=0,
        )

        self._tenants[tenant.id] = tenant
        self._index_tenant(tenant)
        await self._save_tenant(tenant)

        logger.info(f"Created tenant {tenant.id} ({tenant.name})")
        return tenant

    async def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Get a tenant by ID."""
        return self._tenants.get(tenant_id)

    async def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        """Get a tenant by slug."""
        tenant_id = self._slug_index.get(slug)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None

    async def get_tenant_by_idp_org(self, idp_org_id: str) -> Tenant | None:
        """Get a tenant by IdP organization ID."""
        tenant_id = self._idp_org_index.get(idp_org_id)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None

    async def update_tenant(self, tenant_id: str, request: TenantUpdate) -> Tenant | None:
        """
        Update a tenant.

        Args:
            tenant_id: Tenant ID to update
            request: Update request

        Returns:
            Updated tenant or None if not found
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        if request.name is not None:
            tenant.name = request.name

        if request.settings is not None:
            tenant.settings = request.settings

        if request.status is not None:
            tenant.status = request.status

        tenant.updated_at = datetime.utcnow()

        self._tenants[tenant_id] = tenant
        await self._save_tenant(tenant)

        logger.info(f"Updated tenant {tenant_id}")
        return tenant

    async def delete_tenant(self, tenant_id: str, hard_delete: bool = False) -> bool:
        """
        Delete a tenant.

        Args:
            tenant_id: Tenant ID to delete
            hard_delete: If True, permanently delete. If False, mark as deleted.

        Returns:
            True if deleted, False if not found
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        if hard_delete:
            self._unindex_tenant(tenant)
            del self._tenants[tenant_id]
            await self._delete_tenant_file(tenant_id)
            logger.info(f"Hard deleted tenant {tenant_id}")
        else:
            tenant.status = TenantStatus.DELETED
            tenant.updated_at = datetime.utcnow()
            await self._save_tenant(tenant)
            logger.info(f"Soft deleted tenant {tenant_id}")

        return True

    async def suspend_tenant(self, tenant_id: str) -> Tenant | None:
        """Suspend a tenant."""
        return await self.update_tenant(
            tenant_id,
            TenantUpdate(status=TenantStatus.SUSPENDED)
        )

    async def activate_tenant(self, tenant_id: str) -> Tenant | None:
        """Activate a suspended tenant."""
        return await self.update_tenant(
            tenant_id,
            TenantUpdate(status=TenantStatus.ACTIVE)
        )

    async def list_tenants(
        self,
        status: TenantStatus | None = None,
        include_deleted: bool = False,
    ) -> TenantList:
        """
        List all tenants with optional filtering.

        Args:
            status: Filter by status
            include_deleted: Include deleted tenants

        Returns:
            TenantList with matching tenants
        """
        tenants = list(self._tenants.values())

        if not include_deleted:
            tenants = [t for t in tenants if t.status != TenantStatus.DELETED]

        if status:
            tenants = [t for t in tenants if t.status == status]

        # Sort by creation date (newest first)
        tenants.sort(key=lambda t: t.created_at, reverse=True)

        return TenantList(tenants=tenants, total=len(tenants))

    async def update_usage(
        self,
        tenant_id: str,
        instance_count: int | None = None,
        total_memory_mb: int | None = None,
    ) -> None:
        """
        Update tenant resource usage.

        Called by instance manager when instances change.
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return

        if instance_count is not None:
            tenant.instance_count = instance_count
        if total_memory_mb is not None:
            tenant.total_memory_mb = total_memory_mb

        tenant.updated_at = datetime.utcnow()
        self._tenants[tenant_id] = tenant
        await self._save_tenant(tenant)

    async def check_quota(
        self,
        tenant_id: str,
        additional_instances: int = 1,
        additional_memory_mb: int = 0,
    ) -> tuple[bool, str | None]:
        """
        Check if tenant has quota for additional resources.

        Args:
            tenant_id: Tenant ID
            additional_instances: Number of new instances
            additional_memory_mb: Additional memory needed

        Returns:
            Tuple of (allowed, error_message)
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False, "Tenant not found"

        if tenant.status != TenantStatus.ACTIVE:
            return False, f"Tenant is {tenant.status.value}"

        # Check instance quota
        if tenant.instance_count + additional_instances > tenant.settings.max_instances:
            return False, (
                f"Instance quota exceeded: {tenant.instance_count}/{tenant.settings.max_instances} "
                f"(requested {additional_instances} more)"
            )

        # Check memory quota
        if tenant.total_memory_mb + additional_memory_mb > tenant.settings.max_memory_mb:
            return False, (
                f"Memory quota exceeded: {tenant.total_memory_mb}/{tenant.settings.max_memory_mb} MB "
                f"(requested {additional_memory_mb} MB more)"
            )

        return True, None

    async def get_or_create_default_tenant(self) -> Tenant:
        """
        Get or create the default tenant for deployments without external IdP.

        Used when no external identity provider is configured.
        """
        default_slug = "default"
        tenant = await self.get_tenant_by_slug(default_slug)

        if not tenant:
            tenant = await self.create_tenant(
                TenantCreate(
                    name="Default Tenant",
                    slug=default_slug,
                    settings=TenantSettings(
                        max_instances=settings.default_tenant_max_instances,
                        max_memory_mb=settings.default_tenant_max_memory_mb,
                    ),
                )
            )
            logger.info("Created default tenant")

        return tenant


# Global tenant service instance
tenant_service = TenantService()
