import { Routes, Route, NavLink, useLocation, Navigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';
import {
  ServerIcon,
  ShieldExclamationIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { healthApi } from './api';
import { UserMenu, useSAML } from './auth';

// Customer Pages
import Dashboard from './pages/Dashboard';
import Instances from './pages/Instances';
import InstanceDetail from './pages/InstanceDetail';
import CreateInstance from './pages/CreateInstance';
import Attacks from './pages/Attacks';
import ThreatActors from './pages/ThreatActors';
import Campaigns from './pages/Campaigns';
import CampaignDetail from './pages/CampaignDetail';
import Scenarios from './pages/Scenarios';
import Login from './pages/Login';

// Admin Pages
import AdminDashboard from './pages/admin/AdminDashboard';
import VaultAdmin from './pages/admin/VaultAdmin';
import ConcourseAdmin from './pages/admin/ConcourseAdmin';

// Auth Pages
import Register from './pages/Register';

// ============================================================================
// Styled Components with Splunk Theme
// ============================================================================

const SidebarContainer = styled.aside`
  display: none;

  @media (min-width: 1024px) {
    display: flex;
    flex-direction: column;
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    width: 16rem;
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorNavigation, light: variables.backgroundColorNavigation },
    })};
  }
`;

const SidebarContent = styled.div`
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow-y: auto;
  padding-top: 1.25rem;
  padding-bottom: 1rem;
`;

const LogoContainer = styled.div`
  display: flex;
  flex-shrink: 0;
  align-items: center;
  padding: 0 1rem;
  gap: 0.5rem;
`;

const LogoIcon = styled.div`
  width: 2rem;
  height: 2rem;
  background-color: ${variables.accentColorPositive};
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 1rem;
`;

const LogoText = styled.span`
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  font-weight: 600;
  font-size: 1.125rem;
`;

const TenantBadge = styled.div`
  padding: 0 1rem;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  text-transform: uppercase;
  letter-spacing: 0.05em;
`;

const NavContainer = styled.nav`
  margin-top: 1.5rem;
  flex: 1;
  padding: 0 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
`;

interface NavItemProps {
  $isActive: boolean;
}

const NavItem = styled(NavLink)<NavItemProps>`
  display: flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 0.375rem;
  text-decoration: none;
  transition: background-color 0.2s;

  background-color: ${props => props.$isActive
    ? pick({ prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover }})
    : 'transparent'};
  color: ${props => props.$isActive
    ? pick({ prisma: { dark: variables.contentColorActive, light: variables.contentColorActive }})
    : pick({ prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault }})};

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }

  svg {
    margin-right: 0.75rem;
    width: 1.25rem;
    height: 1.25rem;
    flex-shrink: 0;
    color: ${props => props.$isActive
      ? variables.accentColorPositive
      : pick({ prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted }})};
  }
`;

const SidebarFooter = styled.div`
  flex-shrink: 0;
  border-top: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  padding: 1rem;
`;

const StatusContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  margin-bottom: 1rem;
`;

interface StatusDotProps {
  $status: 'loading' | 'error' | 'online';
}

const StatusDot = styled.div<StatusDotProps>`
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background-color: ${props => {
    switch (props.$status) {
      case 'loading': return '#eab308';
      case 'error': return '#ef4444';
      default: return '#22c55e';
    }
  }};
`;

const StatusText = styled.span`
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const MobileNavContainer = styled.div`
  display: block;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorNavigation, light: variables.backgroundColorNavigation },
  })};
  border-top: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};

  @media (min-width: 1024px) {
    display: none;
  }
`;

const MobileNav = styled.nav`
  display: flex;
  justify-content: space-around;
`;

const MobileNavItem = styled(NavLink)<NavItemProps>`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  text-decoration: none;
  color: ${props => props.$isActive
    ? variables.accentColorPositive
    : pick({ prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted }})};

  svg {
    width: 1.5rem;
    height: 1.5rem;
  }

  span {
    margin-top: 0.25rem;
  }
`;

const PortalContainer = styled.div`
  min-height: 100vh;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
`;

const MainContent = styled.main`
  padding: 1.5rem 1rem;
  padding-bottom: 5rem;

  @media (min-width: 640px) {
    padding: 1.5rem;
  }

  @media (min-width: 1024px) {
    margin-left: 16rem;
    padding-bottom: 1.5rem;
  }
`;

const LoadingContainer = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
`;

const LoadingContent = styled.div`
  text-align: center;
`;

const LoadingIcon = styled.div`
  width: 3rem;
  height: 3rem;
  background-color: ${variables.accentColorPositive};
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
`;

const LoadingText = styled.p`
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const AccessDeniedContainer = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
`;

const AccessDeniedContent = styled.div`
  text-align: center;
`;

const AccessDeniedTitle = styled.h1`
  font-size: 1.5rem;
  font-weight: bold;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin-bottom: 0.5rem;
`;

const AccessDeniedText = styled.p`
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin-bottom: 1rem;
`;

const AccessDeniedLink = styled.a`
  color: ${variables.accentColorPositive};
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
`;

// ============================================================================
// Navigation Config
// ============================================================================

const customerNavigation = [
  { name: 'Dashboard', href: '/', icon: ChartBarIcon },
  { name: 'Instances', href: '/instances', icon: ServerIcon },
  { name: 'Attacks', href: '/attacks', icon: ShieldExclamationIcon },
];

// ============================================================================
// Components
// ============================================================================

function Sidebar({ tenantSlug }: { tenantSlug: string }) {
  const location = useLocation();
  const basePath = `/${tenantSlug}`;

  const navigation = customerNavigation.map((item) => ({
    ...item,
    href: item.href === '/' ? basePath : `${basePath}${item.href}`,
  }));

  return (
    <SidebarContainer>
      <SidebarContent>
        <LogoContainer>
          <LogoIcon>S</LogoIcon>
          <LogoText>Faux Splunk Cloud</LogoText>
        </LogoContainer>
        <TenantBadge>{tenantSlug}</TenantBadge>
        <NavContainer>
          {navigation.map((item) => {
            const isActive = location.pathname === item.href ||
              (item.href !== basePath && location.pathname.startsWith(item.href));
            return (
              <NavItem
                key={item.name}
                to={item.href}
                $isActive={isActive}
              >
                <item.icon />
                {item.name}
              </NavItem>
            );
          })}
        </NavContainer>
      </SidebarContent>
      <SidebarFooter>
        <ApiStatus />
        <UserMenu />
      </SidebarFooter>
    </SidebarContainer>
  );
}

function ApiStatus() {
  const { isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.check,
    refetchInterval: 10000,
  });

  const status = isLoading ? 'loading' : isError ? 'error' : 'online';
  const statusText = isLoading ? 'Checking...' : isError ? 'Offline' : 'Online';

  return (
    <StatusContainer>
      <StatusDot $status={status} />
      <StatusText>API: {statusText}</StatusText>
    </StatusContainer>
  );
}

function MobileNavigation({ tenantSlug }: { tenantSlug: string }) {
  const location = useLocation();
  const basePath = `/${tenantSlug}`;

  const navigation = customerNavigation.map((item) => ({
    ...item,
    href: item.href === '/' ? basePath : `${basePath}${item.href}`,
  }));

  return (
    <MobileNavContainer>
      <MobileNav>
        {navigation.map((item) => {
          const isActive = location.pathname === item.href ||
            (item.href !== basePath && location.pathname.startsWith(item.href));
          return (
            <MobileNavItem
              key={item.name}
              to={item.href}
              $isActive={isActive}
            >
              <item.icon />
              <span>{item.name}</span>
            </MobileNavItem>
          );
        })}
      </MobileNav>
    </MobileNavContainer>
  );
}

function CustomerPortal({ tenantSlug }: { tenantSlug: string }) {
  const basePath = `/${tenantSlug}`;

  return (
    <PortalContainer>
      <Sidebar tenantSlug={tenantSlug} />
      <MobileNavigation tenantSlug={tenantSlug} />

      <MainContent>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/instances" element={<Instances />} />
          <Route path="/instances/new" element={<CreateInstance />} />
          <Route path="/instances/:id" element={<InstanceDetail />} />
          <Route path="/attacks" element={<Attacks />} />
          <Route path="/attacks/threat-actors" element={<ThreatActors />} />
          <Route path="/attacks/campaigns" element={<Campaigns />} />
          <Route path="/attacks/campaigns/:id" element={<CampaignDetail />} />
          <Route path="/attacks/scenarios" element={<Scenarios />} />
          <Route path="*" element={<Navigate to={basePath} replace />} />
        </Routes>
      </MainContent>
    </PortalContainer>
  );
}

function AdminPortal() {
  const { isAdmin } = useSAML();
  const location = useLocation();

  if (!isAdmin) {
    return (
      <AccessDeniedContainer>
        <AccessDeniedContent>
          <AccessDeniedTitle>Access Denied</AccessDeniedTitle>
          <AccessDeniedText>You need admin privileges to access this portal.</AccessDeniedText>
          <AccessDeniedLink href="/">
            Return to Customer Portal
          </AccessDeniedLink>
        </AccessDeniedContent>
      </AccessDeniedContainer>
    );
  }

  const adminNavigation = [
    { name: 'Dashboard', href: '/admin', icon: ChartBarIcon },
    { name: 'Vault', href: '/admin/vault', icon: ServerIcon },
    { name: 'Concourse', href: '/admin/concourse', icon: ServerIcon },
  ];

  return (
    <PortalContainer>
      <SidebarContainer>
        <SidebarContent>
          <LogoContainer>
            <LogoIcon style={{ backgroundColor: '#dc2626' }}>A</LogoIcon>
            <LogoText>Admin Portal</LogoText>
          </LogoContainer>
          <TenantBadge>PLATFORM ADMIN</TenantBadge>
          <NavContainer>
            {adminNavigation.map((item) => {
              const isActive = location.pathname === item.href ||
                (item.href !== '/admin' && location.pathname.startsWith(item.href));
              return (
                <NavItem
                  key={item.name}
                  to={item.href}
                  $isActive={isActive}
                >
                  <item.icon />
                  {item.name}
                </NavItem>
              );
            })}
          </NavContainer>
        </SidebarContent>
        <SidebarFooter>
          <AccessDeniedLink href="/" style={{ fontSize: '0.875rem' }}>
            Back to Customer Portal
          </AccessDeniedLink>
          <div style={{ marginTop: '0.5rem' }}>
            <UserMenu />
          </div>
        </SidebarFooter>
      </SidebarContainer>

      <MainContent>
        <Routes>
          <Route path="/" element={<AdminDashboard />} />
          <Route path="/vault" element={<VaultAdmin />} />
          <Route path="/concourse" element={<ConcourseAdmin />} />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </MainContent>
    </PortalContainer>
  );
}

export default function App() {
  const { isAuthenticated, isLoading, user } = useSAML();
  const location = useLocation();

  if (isLoading) {
    return (
      <LoadingContainer>
        <LoadingContent>
          <LoadingIcon>
            <span style={{ color: 'white', fontWeight: 'bold', fontSize: '1.5rem' }}>S</span>
          </LoadingIcon>
          <LoadingText>Loading...</LoadingText>
        </LoadingContent>
      </LoadingContainer>
    );
  }

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/register" element={<Register />} />
        <Route path="*" element={<Login />} />
      </Routes>
    );
  }

  if (location.pathname.startsWith('/admin')) {
    return (
      <Routes>
        <Route path="/admin/*" element={<AdminPortal />} />
      </Routes>
    );
  }

  const pathSegments = location.pathname.split('/').filter(Boolean);
  const urlTenant = pathSegments[0];

  if (location.pathname === '/' || !urlTenant) {
    const targetTenant = user?.tenant_id || 'default';
    return <Navigate to={`/${targetTenant}`} replace />;
  }

  return (
    <Routes>
      <Route path={`/${urlTenant}/*`} element={<CustomerPortal tenantSlug={urlTenant} />} />
    </Routes>
  );
}
