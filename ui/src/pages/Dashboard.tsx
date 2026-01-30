import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';
import {
  ServerIcon,
  ShieldExclamationIcon,
  PlayIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { instancesApi, attacksApi } from '../api';
import { useTenantPath } from '../hooks/useTenantPath';
import type { Instance, AttackCampaign } from '../types';

// ============================================================================
// Styled Components
// ============================================================================

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const PageHeader = styled.div``;

const PageTitle = styled.h1`
  font-size: 1.5rem;
  font-weight: 700;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const PageDescription = styled.p`
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 1.25rem;

  @media (min-width: 640px) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (min-width: 1024px) {
    grid-template-columns: repeat(4, 1fr);
  }
`;

interface StatCardContainerProps {
  $color: string;
}

const StatCardContainer = styled(Link)<StatCardContainerProps>`
  display: block;
  text-decoration: none;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;

  &:hover {
    border-color: ${variables.accentColorPositive};
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
  }
`;

const StatCardContent = styled.div`
  padding: 1.25rem;
  display: flex;
  align-items: center;
`;

const StatIconContainer = styled.div<StatCardContainerProps>`
  flex-shrink: 0;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background-color: ${props => props.$color};
`;

const StatIcon = styled.div`
  width: 1.5rem;
  height: 1.5rem;
  color: white;
`;

const StatTextContainer = styled.div`
  margin-left: 1.25rem;
  flex: 1;
`;

const StatLabel = styled.dt`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const StatValue = styled.dd`
  font-size: 1.5rem;
  font-weight: 600;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const Card = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
`;

const CardHeader = styled.div`
  padding: 1rem 1.25rem;
  border-bottom: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const CardTitle = styled.h3`
  font-size: 1rem;
  font-weight: 600;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const CardBody = styled.div`
  padding: 1.5rem;
`;

const CardLink = styled(Link)`
  font-size: 0.875rem;
  color: ${variables.accentColorPositive};
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
`;

const ButtonGroup = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
`;

const PrimaryButton = styled(Link)`
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: white;
  background-color: ${variables.accentColorPositive};
  border: none;
  border-radius: 0.375rem;
  text-decoration: none;
  transition: background-color 0.2s;

  &:hover {
    background-color: #00a86b;
  }

  svg {
    width: 1rem;
    height: 1rem;
    margin-right: 0.5rem;
  }
`;

const DangerButton = styled(Link)`
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: white;
  background-color: #dc2626;
  border: none;
  border-radius: 0.375rem;
  text-decoration: none;
  transition: background-color 0.2s;

  &:hover {
    background-color: #b91c1c;
  }

  svg {
    width: 1rem;
    height: 1rem;
    margin-right: 0.5rem;
  }
`;

const SecondaryButton = styled(Link)`
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  background-color: transparent;
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.375rem;
  text-decoration: none;
  transition: background-color 0.2s;

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }
`;

const TwoColumnGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;

  @media (min-width: 1024px) {
    grid-template-columns: repeat(2, 1fr);
  }
`;

const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
`;

const ListItem = styled.li`
  border-bottom: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};

  &:last-child {
    border-bottom: none;
  }
`;

const ListItemLink = styled(Link)`
  display: block;
  padding: 1rem 1.25rem;
  text-decoration: none;
  transition: background-color 0.2s;

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }
`;

const ListItemContent = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const ListItemLeft = styled.div`
  display: flex;
  align-items: center;
`;

const ListItemIcon = styled.div<{ $color?: string }>`
  width: 1.25rem;
  height: 1.25rem;
  margin-right: 0.75rem;
  color: ${props => props.$color || pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const ListItemText = styled.div``;

const ListItemTitle = styled.p`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const ListItemSubtitle = styled.p`
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin: 0.125rem 0 0;
`;

const ListItemRight = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const ProgressText = styled.span`
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const EmptyMessage = styled.li`
  padding: 1rem 1.25rem;
  text-align: center;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

interface BadgeProps {
  $variant: 'success' | 'warning' | 'error' | 'info' | 'default';
}

const Badge = styled.span<BadgeProps>`
  display: inline-flex;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 9999px;

  ${props => {
    switch (props.$variant) {
      case 'success':
        return `
          background-color: rgba(34, 197, 94, 0.2);
          color: #22c55e;
        `;
      case 'warning':
        return `
          background-color: rgba(234, 179, 8, 0.2);
          color: #eab308;
        `;
      case 'error':
        return `
          background-color: rgba(239, 68, 68, 0.2);
          color: #ef4444;
        `;
      case 'info':
        return `
          background-color: rgba(59, 130, 246, 0.2);
          color: #3b82f6;
        `;
      default:
        return `
          background-color: rgba(156, 163, 175, 0.2);
          color: #9ca3af;
        `;
    }
  }}
`;

// ============================================================================
// Helper Components
// ============================================================================

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  href,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
  href: string;
}) {
  return (
    <StatCardContainer to={href} $color={color}>
      <StatCardContent>
        <StatIconContainer $color={color}>
          <StatIcon as={Icon} />
        </StatIconContainer>
        <StatTextContainer>
          <dl>
            <StatLabel>{title}</StatLabel>
            <StatValue>{value}</StatValue>
          </dl>
        </StatTextContainer>
      </StatCardContent>
    </StatCardContainer>
  );
}

function getStatusVariant(status: string): BadgeProps['$variant'] {
  switch (status) {
    case 'running':
      return 'success';
    case 'starting':
    case 'provisioning':
    case 'pending':
      return 'info';
    case 'stopped':
      return 'default';
    case 'error':
      return 'error';
    default:
      return 'default';
  }
}

function getCampaignStatusVariant(status: string): BadgeProps['$variant'] {
  switch (status) {
    case 'running':
      return 'error';
    case 'pending':
      return 'warning';
    case 'completed':
      return 'success';
    case 'detected':
      return 'info';
    case 'paused':
    case 'failed':
    default:
      return 'default';
  }
}

function StatusBadge({ status }: { status: Instance['status'] }) {
  return <Badge $variant={getStatusVariant(status)}>{status}</Badge>;
}

function CampaignStatusBadge({ status }: { status: AttackCampaign['status'] }) {
  return <Badge $variant={getCampaignStatusVariant(status)}>{status}</Badge>;
}

function InstanceList({ instances, toPath }: { instances: Instance[]; toPath: (path: string) => string }) {
  const recentInstances = instances.slice(0, 5);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Instances</CardTitle>
        <CardLink to={toPath('instances')}>View all</CardLink>
      </CardHeader>
      <List>
        {recentInstances.length === 0 ? (
          <EmptyMessage>No instances yet</EmptyMessage>
        ) : (
          recentInstances.map((instance) => (
            <ListItem key={instance.id}>
              <ListItemLink to={toPath(`instances/${instance.id}`)}>
                <ListItemContent>
                  <ListItemLeft>
                    <ListItemIcon>
                      <ServerIcon />
                    </ListItemIcon>
                    <ListItemText>
                      <ListItemTitle>{instance.name}</ListItemTitle>
                      <ListItemSubtitle>{instance.id}</ListItemSubtitle>
                    </ListItemText>
                  </ListItemLeft>
                  <StatusBadge status={instance.status} />
                </ListItemContent>
              </ListItemLink>
            </ListItem>
          ))
        )}
      </List>
    </Card>
  );
}

function CampaignList({ campaigns, toPath }: { campaigns: AttackCampaign[]; toPath: (path: string) => string }) {
  const recentCampaigns = campaigns.slice(0, 5);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active Campaigns</CardTitle>
        <CardLink to={toPath('attacks/campaigns')}>View all</CardLink>
      </CardHeader>
      <List>
        {recentCampaigns.length === 0 ? (
          <EmptyMessage>No campaigns running</EmptyMessage>
        ) : (
          recentCampaigns.map((campaign) => (
            <ListItem key={campaign.id}>
              <ListItemLink to={toPath(`attacks/campaigns/${campaign.id}`)}>
                <ListItemContent>
                  <ListItemLeft>
                    <ListItemIcon $color="#ef4444">
                      <ShieldExclamationIcon />
                    </ListItemIcon>
                    <ListItemText>
                      <ListItemTitle>{campaign.name}</ListItemTitle>
                      <ListItemSubtitle>{campaign.threat_actor_name}</ListItemSubtitle>
                    </ListItemText>
                  </ListItemLeft>
                  <ListItemRight>
                    <ProgressText>
                      {campaign.completed_steps}/{campaign.total_steps} steps
                    </ProgressText>
                    <CampaignStatusBadge status={campaign.status} />
                  </ListItemRight>
                </ListItemContent>
              </ListItemLink>
            </ListItem>
          ))
        )}
      </List>
    </Card>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function Dashboard() {
  const { toPath } = useTenantPath();

  const { data: instances = [], isLoading: loadingInstances } = useQuery({
    queryKey: ['instances'],
    queryFn: instancesApi.list,
  });

  const { data: campaigns = [], isLoading: loadingCampaigns } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => attacksApi.listCampaigns(),
  });

  const runningInstances = instances.filter((i) => i.status === 'running').length;
  const activeCampaigns = campaigns.filter((c) => c.status === 'running').length;
  const errorInstances = instances.filter((i) => i.status === 'error').length;

  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>Dashboard</PageTitle>
        <PageDescription>
          Overview of your ephemeral Splunk Cloud instances and attack simulations
        </PageDescription>
      </PageHeader>

      {/* Stats */}
      <StatsGrid>
        <StatCard
          title="Total Instances"
          value={loadingInstances ? '...' : instances.length}
          icon={ServerIcon}
          color="#3b82f6"
          href={toPath('instances')}
        />
        <StatCard
          title="Running"
          value={loadingInstances ? '...' : runningInstances}
          icon={PlayIcon}
          color="#22c55e"
          href={toPath('instances?status=running')}
        />
        <StatCard
          title="Active Attacks"
          value={loadingCampaigns ? '...' : activeCampaigns}
          icon={ShieldExclamationIcon}
          color="#ef4444"
          href={toPath('attacks/campaigns')}
        />
        <StatCard
          title="Errors"
          value={loadingInstances ? '...' : errorInstances}
          icon={ExclamationTriangleIcon}
          color="#eab308"
          href={toPath('instances?status=error')}
        />
      </StatsGrid>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardBody>
          <ButtonGroup>
            <PrimaryButton to={toPath('instances/new')}>
              <ServerIcon />
              New Instance
            </PrimaryButton>
            <DangerButton to={toPath('attacks/scenarios')}>
              <ShieldExclamationIcon />
              Run Attack Scenario
            </DangerButton>
            <SecondaryButton to={toPath('attacks/threat-actors')}>
              Browse Threat Actors
            </SecondaryButton>
          </ButtonGroup>
        </CardBody>
      </Card>

      {/* Recent Activity */}
      <TwoColumnGrid>
        <InstanceList instances={instances} toPath={toPath} />
        <CampaignList campaigns={campaigns} toPath={toPath} />
      </TwoColumnGrid>
    </PageContainer>
  );
}
