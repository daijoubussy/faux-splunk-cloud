import { createContext, useContext, useEffect, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';

interface SAMLUser {
  user_id: string;
  email: string | null;
  name: string | null;
  tenant_id: string | null;
  roles: string[];
}

interface SAMLContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: SAMLUser | null;
  login: (returnTo?: string) => void;
  logout: () => Promise<void>;
  hasRole: (role: string) => boolean;
  isAdmin: boolean;
}

const SAMLContext = createContext<SAMLContextType | null>(null);

export function SAMLProvider({ children }: { children: ReactNode }) {
  // Check session status
  const { data: session, isLoading } = useQuery({
    queryKey: ['saml', 'session'],
    queryFn: async () => {
      const response = await fetch('/api/v1/auth/saml/session', {
        credentials: 'include',
      });
      if (!response.ok) {
        return { authenticated: false };
      }
      return response.json();
    },
    refetchInterval: 60000, // Check every minute
    refetchOnWindowFocus: true,
  });

  const login = (returnTo?: string) => {
    const params = new URLSearchParams();
    if (returnTo) {
      params.set('return_to', returnTo);
    }
    // Redirect to SAML login endpoint
    window.location.href = `/api/v1/auth/saml/login?${params.toString()}`;
  };

  const logout = async () => {
    // Redirect to SAML Single Logout - this logs out from both the app AND Keycloak
    // This ensures the user can re-enter credentials on next login
    window.location.href = '/api/v1/auth/saml/slo';
  };

  const hasRole = (role: string): boolean => {
    if (!session?.authenticated || !session.roles) return false;
    return session.roles.includes(role);
  };

  const isAdmin =
    hasRole('platform_admin') ||
    hasRole('admin') ||
    hasRole('splunk_admin');

  const user: SAMLUser | null = session?.authenticated
    ? {
        user_id: session.user_id,
        email: session.email,
        name: session.name,
        tenant_id: session.tenant_id,
        roles: session.roles || [],
      }
    : null;

  const contextValue: SAMLContextType = {
    isAuthenticated: session?.authenticated ?? false,
    isLoading,
    user,
    login,
    logout,
    hasRole,
    isAdmin,
  };

  return (
    <SAMLContext.Provider value={contextValue}>{children}</SAMLContext.Provider>
  );
}

export function useSAML() {
  const context = useContext(SAMLContext);
  if (!context) {
    throw new Error('useSAML must be used within a SAMLProvider');
  }
  return context;
}

// Protected route component
export function SAMLProtectedRoute({
  children,
  requiredRoles,
}: {
  children: ReactNode;
  requiredRoles?: string[];
}) {
  const { isAuthenticated, isLoading, login, hasRole } = useSAML();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      login(window.location.pathname);
    }
  }, [isLoading, isAuthenticated, login]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-splunk-green mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-gray-600">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  // Check required roles
  if (requiredRoles && requiredRoles.length > 0) {
    const hasRequiredRole = requiredRoles.some((role) => hasRole(role));
    if (!hasRequiredRole) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900">Access Denied</h1>
            <p className="mt-2 text-gray-600">
              You don't have the required role to access this page.
            </p>
            <p className="mt-1 text-sm text-gray-500">
              Required: {requiredRoles.join(' or ')}
            </p>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
}

export default SAMLProvider;
