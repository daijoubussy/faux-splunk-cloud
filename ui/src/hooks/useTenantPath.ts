import { useLocation } from 'react-router-dom';

/**
 * Hook to get tenant-scoped paths.
 *
 * When the app uses tenant-scoped routing (/{tenant}/...), this hook
 * provides helpers to build correct paths for navigation.
 */
export function useTenantPath() {
  const location = useLocation();

  // Extract tenant from URL path (first segment after root)
  const pathSegments = location.pathname.split('/').filter(Boolean);
  const tenant = pathSegments[0] || 'default';

  // Check if we're in admin portal (not tenant-scoped)
  const isAdmin = tenant === 'admin';

  // Base path for the current tenant
  const basePath = isAdmin ? '/admin' : `/${tenant}`;

  /**
   * Convert a path to be tenant-scoped.
   * @param path - Path like '/instances' or 'instances'
   * @returns Tenant-scoped path like '/{tenant}/instances'
   */
  function toPath(path: string): string {
    // Remove leading slash if present
    const cleanPath = path.startsWith('/') ? path.slice(1) : path;

    // Handle root path
    if (!cleanPath) {
      return basePath;
    }

    return `${basePath}/${cleanPath}`;
  }

  return {
    tenant,
    basePath,
    toPath,
    isAdmin,
  };
}
