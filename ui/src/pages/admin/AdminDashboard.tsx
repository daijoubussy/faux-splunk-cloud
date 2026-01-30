import { useQuery } from '@tanstack/react-query';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';
import {
  BuildingOfficeIcon,
  ServerIcon,
  UsersIcon,
  ChartBarIcon,
  KeyIcon,
  ServerStackIcon,
} from '@heroicons/react/24/outline';
import { Link } from 'react-router-dom';

// ============================================================================
// Styled Components
// ============================================================================

const Container = styled.div`
  max-width: 80rem;
  margin: 0 auto;
`;

const Header = styled.div`
  margin-bottom: 2rem;
`;

const Title = styled.h1`
  font-size: 1.5rem;
  font-weight: bold;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

const Description = styled.p`
  margin-top: 0.25rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 1.5rem;
  margin-bottom: 2rem;

  @media (min-width: 640px) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (min-width: 1024px) {
    grid-template-columns: repeat(4, 1fr);
  }
`;

const StatCard = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  padding: 1.5rem;
`;

const StatContent = styled.div`
  display: flex;
  align-items: center;
`;

const StatIconContainer = styled.div`
  flex-shrink: 0;

  svg {
    width: 2rem;
    height: 2rem;
    color: ${pick({
      prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
    })};
  }
`;

const StatText = styled.div`
  margin-left: 1rem;
`;

const StatLabel = styled.p`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const StatValue = styled.p`
  font-size: 1.5rem;
  font-weight: 600;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

const Card = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  padding: 1.5rem;
  margin-bottom: 1rem;
`;

const CardTitle = styled.h2`
  font-size: 1.125rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin-bottom: 1rem;
`;

const QuickActionsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 1rem;

  @media (min-width: 640px) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (min-width: 1024px) {
    grid-template-columns: repeat(3, 1fr);
  }
`;

const QuickAction = styled(Link)`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
  })};
  border-radius: 0.5rem;
  text-decoration: none;
  transition: background-color 0.2s;

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorPopup, light: variables.backgroundColorPopup },
    })};
  }

  svg {
    width: 1.5rem;
    height: 1.5rem;
    color: ${variables.accentColorPositive};
  }
`;

const QuickActionText = styled.span`
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

// ============================================================================
// API
// ============================================================================

async function fetchVaultHealth() {
  try {
    const response = await fetch('/api/v1/vault/health');
    if (response.ok) {
      return response.json();
    }
  } catch {
    // Vault might not be running
  }
  return { healthy: false };
}

async function fetchConcourseHealth() {
  try {
    const response = await fetch('/api/v1/concourse/health');
    if (response.ok) {
      return response.json();
    }
  } catch {
    // Concourse might not be running
  }
  return { healthy: false };
}

// ============================================================================
// Main Component
// ============================================================================

export default function AdminDashboard() {
  const { data: vaultHealth } = useQuery({
    queryKey: ['vault-health-dash'],
    queryFn: fetchVaultHealth,
    refetchInterval: 30000,
  });

  const { data: concourseHealth } = useQuery({
    queryKey: ['concourse-health-dash'],
    queryFn: fetchConcourseHealth,
    refetchInterval: 30000,
  });

  const stats = [
    { name: 'Total Tenants', value: '0', icon: BuildingOfficeIcon },
    { name: 'Active Instances', value: '0', icon: ServerIcon },
    { name: 'Total Users', value: '0', icon: UsersIcon },
    { name: 'Attack Campaigns', value: '0', icon: ChartBarIcon },
  ];

  return (
    <Container>
      <Header>
        <Title>Platform Administration</Title>
        <Description>
          Manage tenants, view platform statistics, and configure system settings.
        </Description>
      </Header>

      <StatsGrid>
        {stats.map((stat) => (
          <StatCard key={stat.name}>
            <StatContent>
              <StatIconContainer>
                <stat.icon />
              </StatIconContainer>
              <StatText>
                <StatLabel>{stat.name}</StatLabel>
                <StatValue>{stat.value}</StatValue>
              </StatText>
            </StatContent>
          </StatCard>
        ))}
      </StatsGrid>

      <Card>
        <CardTitle>Quick Actions</CardTitle>
        <QuickActionsGrid>
          <QuickAction to="/admin/vault">
            <KeyIcon />
            <QuickActionText>
              Vault {vaultHealth?.healthy ? '(Online)' : '(Offline)'}
            </QuickActionText>
          </QuickAction>
          <QuickAction to="/admin/concourse">
            <ServerStackIcon />
            <QuickActionText>
              Concourse {concourseHealth?.healthy ? '(Online)' : '(Offline)'}
            </QuickActionText>
          </QuickAction>
          <QuickAction to="/">
            <ServerIcon />
            <QuickActionText>Customer Portal</QuickActionText>
          </QuickAction>
        </QuickActionsGrid>
      </Card>
    </Container>
  );
}
