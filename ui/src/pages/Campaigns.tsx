import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';
import {
  BoltIcon,
  PlayIcon,
  PauseIcon,
  EyeIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { attacksApi } from '../api';
import { useTenantPath } from '../hooks/useTenantPath';
import type { AttackCampaign } from '../types';

// ============================================================================
// Styled Components
// ============================================================================

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const HeaderRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
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

const LaunchButton = styled(Link)`
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

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 1.25rem;

  @media (min-width: 640px) {
    grid-template-columns: repeat(4, 1fr);
  }
`;

interface StatCardProps {
  $iconBg: string;
  $iconColor: string;
}

const StatCard = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  padding: 1.25rem;
`;

const StatCardContent = styled.div`
  display: flex;
  align-items: center;
`;

const StatIconContainer = styled.div<StatCardProps>`
  flex-shrink: 0;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background-color: ${props => props.$iconBg};
`;

const StatIcon = styled.div<StatCardProps>`
  width: 1.5rem;
  height: 1.5rem;
  color: ${props => props.$iconColor};
`;

const StatText = styled.div`
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

const FilterCard = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  padding: 1rem;
`;

const FilterRow = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;

  @media (min-width: 640px) {
    flex-direction: row;
  }
`;

const Select = styled.select`
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.375rem;
  min-width: 12rem;

  &:focus {
    outline: none;
    border-color: ${variables.accentColorPositive};
  }
`;

const FilterInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const ClearLink = styled(Link)`
  color: ${variables.accentColorPositive};
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
`;

const ResultsCount = styled.div`
  flex: 1;
  text-align: right;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
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
  overflow: hidden;
`;

const EmptyState = styled.div`
  padding: 2rem;
  text-align: center;
`;

const EmptyIcon = styled.div`
  margin: 0 auto;
  width: 3rem;
  height: 3rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const EmptyTitle = styled.h3`
  margin-top: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

const EmptyText = styled.p`
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const TableHead = styled.thead`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
  })};
`;

const TableHeader = styled.th`
  padding: 0.75rem 1.5rem;
  text-align: left;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};

  &:last-child {
    text-align: right;
  }
`;

const TableBody = styled.tbody``;

const TableRow = styled.tr`
  border-bottom: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }

  &:last-child {
    border-bottom: none;
  }
`;

const TableCell = styled.td`
  padding: 1rem 1.5rem;
  white-space: nowrap;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};

  &:last-child {
    text-align: right;
  }
`;

const CampaignInfo = styled.div`
  display: flex;
  align-items: center;
`;

const CampaignIcon = styled.div`
  flex-shrink: 0;
  background-color: rgba(239, 68, 68, 0.2);
  border-radius: 50%;
  padding: 0.5rem;
`;

const CampaignIconStyled = styled.div`
  width: 1.25rem;
  height: 1.25rem;
  color: #ef4444;
`;

const CampaignText = styled.div`
  margin-left: 1rem;
`;

const CampaignName = styled(Link)`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  text-decoration: none;

  &:hover {
    color: ${variables.accentColorPositive};
  }
`;

const CampaignId = styled.p`
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin: 0;
`;

const ProgressContainer = styled.div`
  width: 8rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const ProgressBar = styled.div`
  flex: 1;
  height: 0.5rem;
  background-color: ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 9999px;
  overflow: hidden;
`;

interface ProgressFillProps {
  $percentage: number;
}

const ProgressFill = styled.div<ProgressFillProps>`
  height: 100%;
  width: ${props => props.$percentage}%;
  background-color: #ef4444;
  border-radius: 9999px;
  transition: width 0.5s;
`;

const ProgressText = styled.span`
  font-size: 0.75rem;
  white-space: nowrap;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

interface BadgeProps {
  $color: string;
  $bgColor: string;
  $pulse?: boolean;
}

const Badge = styled.span<BadgeProps>`
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 9999px;
  background-color: ${props => props.$bgColor};
  color: ${props => props.$color};
  ${props => props.$pulse && 'animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;'}

  svg {
    width: 0.875rem;
    height: 0.875rem;
    margin-right: 0.25rem;
  }
`;

const DetectedBadge = styled.span`
  display: inline-flex;
  align-items: center;
  margin-left: 0.5rem;
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  background-color: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
  border-radius: 0.25rem;

  svg {
    width: 0.75rem;
    height: 0.75rem;
    margin-right: 0.25rem;
  }
`;

const ActionGroup = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
`;

interface ActionButtonProps {
  $color: 'green' | 'yellow' | 'default';
}

const ActionButton = styled.button<ActionButtonProps>`
  padding: 0.375rem;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background-color 0.2s;

  ${props => {
    switch (props.$color) {
      case 'green':
        return `
          color: #22c55e;
          &:hover { background-color: rgba(34, 197, 94, 0.1); }
        `;
      case 'yellow':
        return `
          color: #eab308;
          &:hover { background-color: rgba(234, 179, 8, 0.1); }
        `;
      default:
        return `
          color: ${pick({
            prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
          })};
          &:hover {
            color: ${pick({
              prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
            })};
            background-color: ${pick({
              prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
            })};
          }
        `;
    }
  }}

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  svg {
    width: 1rem;
    height: 1rem;
  }
`;

const ActionLink = styled(Link)`
  padding: 0.375rem;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  transition: background-color 0.2s, color 0.2s;

  &:hover {
    color: ${pick({
      prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
    })};
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }

  svg {
    width: 1rem;
    height: 1rem;
  }
`;

const LoadingContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  height: 16rem;
`;

const Spinner = styled.div`
  width: 2rem;
  height: 2rem;
  border: 2px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-top-color: ${variables.accentColorPositive};
  border-radius: 50%;
  animation: spin 1s linear infinite;
`;

const ErrorBox = styled.div`
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 0.5rem;
  padding: 1rem;
  display: flex;
  align-items: center;
  color: #ef4444;

  svg {
    width: 1.25rem;
    height: 1.25rem;
    margin-right: 0.5rem;
  }
`;

// ============================================================================
// Helper Components
// ============================================================================

const statusConfig: Record<string, { color: string; bgColor: string; icon: React.ElementType; pulse?: boolean }> = {
  pending: { color: '#eab308', bgColor: 'rgba(234, 179, 8, 0.2)', icon: ClockIcon },
  running: { color: '#ef4444', bgColor: 'rgba(239, 68, 68, 0.2)', icon: BoltIcon, pulse: true },
  paused: { color: '#9ca3af', bgColor: 'rgba(156, 163, 175, 0.2)', icon: PauseIcon },
  completed: { color: '#22c55e', bgColor: 'rgba(34, 197, 94, 0.2)', icon: CheckCircleIcon },
  detected: { color: '#3b82f6', bgColor: 'rgba(59, 130, 246, 0.2)', icon: EyeIcon },
  failed: { color: '#ef4444', bgColor: 'rgba(239, 68, 68, 0.2)', icon: ExclamationTriangleIcon },
};

function CampaignStatusBadge({ status }: { status: AttackCampaign['status'] }) {
  const config = statusConfig[status] || statusConfig.pending;
  const Icon = config.icon;

  return (
    <Badge $color={config.color} $bgColor={config.bgColor} $pulse={config.pulse}>
      <Icon />
      {status}
    </Badge>
  );
}

function Progress({ completed, total }: { completed: number; total: number }) {
  const percentage = total > 0 ? (completed / total) * 100 : 0;

  return (
    <ProgressContainer>
      <ProgressBar>
        <ProgressFill $percentage={percentage} />
      </ProgressBar>
      <ProgressText>{completed}/{total}</ProgressText>
    </ProgressContainer>
  );
}

function CampaignRow({ campaign }: { campaign: AttackCampaign }) {
  const queryClient = useQueryClient();
  const { toPath } = useTenantPath();

  const startMutation = useMutation({
    mutationFn: () => attacksApi.startCampaign(campaign.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => attacksApi.pauseCampaign(campaign.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const canStart = campaign.status === 'pending' || campaign.status === 'paused';
  const canPause = campaign.status === 'running';

  return (
    <TableRow>
      <TableCell>
        <CampaignInfo>
          <CampaignIcon>
            <CampaignIconStyled as={BoltIcon} />
          </CampaignIcon>
          <CampaignText>
            <CampaignName to={toPath(`attacks/campaigns/${campaign.id}`)}>
              {campaign.name}
            </CampaignName>
            <CampaignId>{campaign.id}</CampaignId>
          </CampaignText>
        </CampaignInfo>
      </TableCell>
      <TableCell>{campaign.threat_actor_name}</TableCell>
      <TableCell>{campaign.current_phase}</TableCell>
      <TableCell>
        <Progress completed={campaign.completed_steps} total={campaign.total_steps} />
      </TableCell>
      <TableCell>
        <CampaignStatusBadge status={campaign.status} />
        {campaign.detected && (
          <DetectedBadge>
            <EyeIcon />
            Detected
          </DetectedBadge>
        )}
      </TableCell>
      <TableCell>
        {campaign.start_time
          ? new Date(campaign.start_time).toLocaleString()
          : 'Not started'}
      </TableCell>
      <TableCell>
        <ActionGroup>
          {canStart && (
            <ActionButton
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
              $color="green"
              title="Start campaign"
            >
              <PlayIcon />
            </ActionButton>
          )}
          {canPause && (
            <ActionButton
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending}
              $color="yellow"
              title="Pause campaign"
            >
              <PauseIcon />
            </ActionButton>
          )}
          <ActionLink to={toPath(`attacks/campaigns/${campaign.id}`)} title="View details">
            <EyeIcon />
          </ActionLink>
        </ActionGroup>
      </TableCell>
    </TableRow>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function Campaigns() {
  const [searchParams] = useSearchParams();
  const threatActorFilter = searchParams.get('threat_actor') || '';
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const { toPath } = useTenantPath();

  const { data: campaigns = [], isLoading, error } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => attacksApi.listCampaigns(),
    refetchInterval: 5000,
  });

  const filteredCampaigns = campaigns.filter((campaign) => {
    if (statusFilter !== 'all' && campaign.status !== statusFilter) {
      return false;
    }
    if (threatActorFilter && campaign.threat_actor_id !== threatActorFilter) {
      return false;
    }
    return true;
  });

  const activeCampaigns = campaigns.filter((c) => c.status === 'running').length;
  const completedCampaigns = campaigns.filter((c) => c.status === 'completed').length;
  const detectedCampaigns = campaigns.filter((c) => c.detected).length;

  if (isLoading) {
    return (
      <LoadingContainer>
        <Spinner />
      </LoadingContainer>
    );
  }

  if (error) {
    return (
      <ErrorBox>
        <ExclamationTriangleIcon />
        <span>Failed to load campaigns</span>
      </ErrorBox>
    );
  }

  return (
    <PageContainer>
      <HeaderRow>
        <PageHeader>
          <PageTitle>Attack Campaigns</PageTitle>
          <PageDescription>
            Manage and monitor active attack simulations
          </PageDescription>
        </PageHeader>
        <LaunchButton to={toPath('attacks/scenarios')}>
          <BoltIcon />
          Launch New Attack
        </LaunchButton>
      </HeaderRow>

      {/* Stats */}
      <StatsGrid>
        <StatCard>
          <StatCardContent>
            <StatIconContainer $iconBg="rgba(156, 163, 175, 0.2)" $iconColor="#9ca3af">
              <StatIcon as={BoltIcon} $iconBg="" $iconColor="#9ca3af" />
            </StatIconContainer>
            <StatText>
              <dl>
                <StatLabel>Total Campaigns</StatLabel>
                <StatValue>{campaigns.length}</StatValue>
              </dl>
            </StatText>
          </StatCardContent>
        </StatCard>

        <StatCard>
          <StatCardContent>
            <StatIconContainer $iconBg="rgba(239, 68, 68, 0.2)" $iconColor="#ef4444">
              <StatIcon as={PlayIcon} $iconBg="" $iconColor="#ef4444" />
            </StatIconContainer>
            <StatText>
              <dl>
                <StatLabel>Active</StatLabel>
                <StatValue>{activeCampaigns}</StatValue>
              </dl>
            </StatText>
          </StatCardContent>
        </StatCard>

        <StatCard>
          <StatCardContent>
            <StatIconContainer $iconBg="rgba(34, 197, 94, 0.2)" $iconColor="#22c55e">
              <StatIcon as={CheckCircleIcon} $iconBg="" $iconColor="#22c55e" />
            </StatIconContainer>
            <StatText>
              <dl>
                <StatLabel>Completed</StatLabel>
                <StatValue>{completedCampaigns}</StatValue>
              </dl>
            </StatText>
          </StatCardContent>
        </StatCard>

        <StatCard>
          <StatCardContent>
            <StatIconContainer $iconBg="rgba(59, 130, 246, 0.2)" $iconColor="#3b82f6">
              <StatIcon as={EyeIcon} $iconBg="" $iconColor="#3b82f6" />
            </StatIconContainer>
            <StatText>
              <dl>
                <StatLabel>Detected</StatLabel>
                <StatValue>{detectedCampaigns}</StatValue>
              </dl>
            </StatText>
          </StatCardContent>
        </StatCard>
      </StatsGrid>

      {/* Filters */}
      <FilterCard>
        <FilterRow>
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="running">Running</option>
            <option value="pending">Pending</option>
            <option value="paused">Paused</option>
            <option value="completed">Completed</option>
            <option value="detected">Detected</option>
            <option value="failed">Failed</option>
          </Select>

          {threatActorFilter && (
            <FilterInfo>
              <span>Filtered by threat actor:</span>
              <strong>{threatActorFilter}</strong>
              <ClearLink to={toPath('attacks/campaigns')}>Clear</ClearLink>
            </FilterInfo>
          )}

          <ResultsCount>
            Showing {filteredCampaigns.length} of {campaigns.length} campaigns
          </ResultsCount>
        </FilterRow>
      </FilterCard>

      {/* Table */}
      <Card>
        {filteredCampaigns.length === 0 ? (
          <EmptyState>
            <EmptyIcon as={BoltIcon} />
            <EmptyTitle>No campaigns found</EmptyTitle>
            <EmptyText>
              {campaigns.length === 0
                ? 'Launch a new attack from the Scenarios page.'
                : 'Try adjusting your filter criteria.'}
            </EmptyText>
            <div style={{ marginTop: '1.5rem' }}>
              <LaunchButton to={toPath('attacks/scenarios')}>
                <BoltIcon />
                Launch Attack
              </LaunchButton>
            </div>
          </EmptyState>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <Table>
              <TableHead>
                <tr>
                  <TableHeader>Campaign</TableHeader>
                  <TableHeader>Threat Actor</TableHeader>
                  <TableHeader>Phase</TableHeader>
                  <TableHeader>Progress</TableHeader>
                  <TableHeader>Status</TableHeader>
                  <TableHeader>Started</TableHeader>
                  <TableHeader></TableHeader>
                </tr>
              </TableHead>
              <TableBody>
                {filteredCampaigns.map((campaign) => (
                  <CampaignRow key={campaign.id} campaign={campaign} />
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>
    </PageContainer>
  );
}
