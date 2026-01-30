import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { format, formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';
import {
  PlusIcon,
  PlayIcon,
  StopIcon,
  TrashIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { instancesApi } from '../api';
import { useTenantPath } from '../hooks/useTenantPath';
import type { Instance } from '../types';

// ============================================================================
// Styled Components
// ============================================================================

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const PageHeaderRow = styled.div`
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

const ButtonGroup = styled.div`
  display: flex;
  gap: 0.5rem;
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
    margin-right: 0.25rem;
  }
`;

const SecondaryButton = styled.button`
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
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
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }

  svg {
    width: 1rem;
    height: 1rem;
    margin-right: 0.25rem;
  }
`;

const FilterGroup = styled.div`
  display: flex;
  gap: 0.5rem;
`;

interface FilterButtonProps {
  $active: boolean;
}

const FilterButton = styled.button<FilterButtonProps>`
  padding: 0.25rem 0.75rem;
  font-size: 0.875rem;
  border-radius: 9999px;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;

  background-color: ${props => props.$active
    ? pick({ prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault } })
    : pick({ prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover } })};
  color: ${props => props.$active
    ? pick({ prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage } })
    : pick({ prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted } })};

  &:hover {
    background-color: ${props => props.$active
      ? pick({ prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault } })
      : pick({ prisma: { dark: variables.borderColor, light: variables.borderColor } })};
  }
`;

const FilterCount = styled.span`
  margin-left: 0.25rem;
  font-size: 0.75rem;
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

const LoadingMessage = styled.div`
  padding: 2rem;
  text-align: center;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const EmptyMessage = styled.div`
  padding: 2rem;
  text-align: center;
`;

const EmptyText = styled.p`
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin-bottom: 1rem;
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

const InstanceLink = styled(Link)`
  display: block;
  text-decoration: none;
`;

const InstanceName = styled.div`
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};

  &:hover {
    color: ${variables.accentColorPositive};
  }
`;

const InstanceId = styled.div`
  font-size: 0.75rem;
  font-family: monospace;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

interface BadgeProps {
  $variant: 'success' | 'warning' | 'error' | 'info' | 'default';
  $pulse?: boolean;
}

const Badge = styled.span<BadgeProps>`
  display: inline-flex;
  padding: 0.125rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 9999px;
  ${props => props.$pulse && 'animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;'}

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

const TopologyBadge = styled.span`
  display: inline-flex;
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 0.25rem;
  background-color: rgba(168, 85, 247, 0.2);
  color: #a855f7;
`;

const ExternalLink = styled.a`
  color: ${variables.accentColorPositive};
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
`;

const MutedText = styled.span`
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const ExpiredText = styled.div`
  color: #ef4444;
`;

const ActionGroup = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
`;

interface ActionButtonProps {
  $color: 'green' | 'yellow' | 'red';
}

const ActionButton = styled.button<ActionButtonProps>`
  padding: 0.25rem;
  background: transparent;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: color 0.2s;

  ${props => {
    switch (props.$color) {
      case 'green':
        return `
          color: #22c55e;
          &:hover { color: #16a34a; }
        `;
      case 'yellow':
        return `
          color: #eab308;
          &:hover { color: #ca8a04; }
        `;
      case 'red':
        return `
          color: #ef4444;
          &:hover { color: #dc2626; }
        `;
    }
  }}

  svg {
    width: 1.25rem;
    height: 1.25rem;
  }
`;

// ============================================================================
// Helper Components
// ============================================================================

function getStatusVariant(status: string): BadgeProps['$variant'] {
  switch (status) {
    case 'running':
      return 'success';
    case 'starting':
    case 'provisioning':
    case 'stopping':
      return 'warning';
    case 'pending':
      return 'info';
    case 'error':
      return 'error';
    case 'stopped':
    case 'terminated':
    default:
      return 'default';
  }
}

function shouldPulse(status: string): boolean {
  return ['starting', 'provisioning', 'stopping'].includes(status);
}

function StatusBadge({ status }: { status: Instance['status'] }) {
  return (
    <Badge $variant={getStatusVariant(status)} $pulse={shouldPulse(status)}>
      {status}
    </Badge>
  );
}

function TopologyLabel({ topology }: { topology: string }) {
  const labels: Record<string, string> = {
    standalone: 'Standalone',
    distributed_minimal: 'Distributed',
    distributed_clustered: 'Clustered',
    victoria_full: 'Victoria Full',
  };

  return <TopologyBadge>{labels[topology] || topology}</TopologyBadge>;
}

function InstanceRow({
  instance,
  onStart,
  onStop,
  onDestroy,
  toPath,
}: {
  instance: Instance;
  onStart: (id: string) => void;
  onStop: (id: string) => void;
  onDestroy: (id: string) => void;
  toPath: (path: string) => string;
}) {
  const canStart = ['pending', 'stopped', 'provisioning'].includes(instance.status);
  const canStop = ['running', 'starting'].includes(instance.status);
  const canDestroy = !['terminated'].includes(instance.status);
  const isExpired = new Date(instance.expires_at) < new Date();

  return (
    <TableRow>
      <TableCell>
        <InstanceLink to={toPath(`instances/${instance.id}`)}>
          <InstanceName>{instance.name}</InstanceName>
          <InstanceId>{instance.id}</InstanceId>
        </InstanceLink>
      </TableCell>
      <TableCell>
        <StatusBadge status={instance.status} />
      </TableCell>
      <TableCell>
        <TopologyLabel topology={instance.config.topology} />
      </TableCell>
      <TableCell>
        {instance.endpoints.web_url ? (
          <ExternalLink
            href={instance.endpoints.web_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open Web UI
          </ExternalLink>
        ) : (
          <MutedText>-</MutedText>
        )}
      </TableCell>
      <TableCell title={format(new Date(instance.created_at), 'PPpp')}>
        {formatDistanceToNow(new Date(instance.created_at), { addSuffix: true })}
      </TableCell>
      <TableCell>
        {isExpired ? (
          <ExpiredText title={format(new Date(instance.expires_at), 'PPpp')}>
            {formatDistanceToNow(new Date(instance.expires_at), { addSuffix: true })}
          </ExpiredText>
        ) : (
          <span title={format(new Date(instance.expires_at), 'PPpp')}>
            {formatDistanceToNow(new Date(instance.expires_at), { addSuffix: true })}
          </span>
        )}
      </TableCell>
      <TableCell>
        <ActionGroup>
          {canStart && (
            <ActionButton
              onClick={() => onStart(instance.id)}
              $color="green"
              title="Start"
            >
              <PlayIcon />
            </ActionButton>
          )}
          {canStop && (
            <ActionButton
              onClick={() => onStop(instance.id)}
              $color="yellow"
              title="Stop"
            >
              <StopIcon />
            </ActionButton>
          )}
          {canDestroy && (
            <ActionButton
              onClick={() => onDestroy(instance.id)}
              $color="red"
              title="Destroy"
            >
              <TrashIcon />
            </ActionButton>
          )}
        </ActionGroup>
      </TableCell>
    </TableRow>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function Instances() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<string>('all');
  const { toPath } = useTenantPath();

  const { data: instances = [], isLoading, refetch } = useQuery({
    queryKey: ['instances'],
    queryFn: instancesApi.list,
    refetchInterval: 5000,
  });

  const startMutation = useMutation({
    mutationFn: instancesApi.start,
    onSuccess: () => {
      toast.success('Instance starting...');
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
    onError: (err: Error) => toast.error(`Failed to start: ${err.message}`),
  });

  const stopMutation = useMutation({
    mutationFn: instancesApi.stop,
    onSuccess: () => {
      toast.success('Instance stopping...');
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
    onError: (err: Error) => toast.error(`Failed to stop: ${err.message}`),
  });

  const destroyMutation = useMutation({
    mutationFn: instancesApi.destroy,
    onSuccess: () => {
      toast.success('Instance destroyed');
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
    onError: (err: Error) => toast.error(`Failed to destroy: ${err.message}`),
  });

  const handleDestroy = (id: string) => {
    if (window.confirm('Are you sure you want to destroy this instance? This cannot be undone.')) {
      destroyMutation.mutate(id);
    }
  };

  const filteredInstances = filter === 'all'
    ? instances
    : instances.filter((i) => i.status === filter);

  return (
    <PageContainer>
      <PageHeaderRow>
        <PageHeader>
          <PageTitle>Instances</PageTitle>
          <PageDescription>
            Manage your ephemeral Splunk Cloud Victoria instances
          </PageDescription>
        </PageHeader>
        <ButtonGroup>
          <SecondaryButton onClick={() => refetch()}>
            <ArrowPathIcon />
            Refresh
          </SecondaryButton>
          <PrimaryButton to={toPath('instances/new')}>
            <PlusIcon />
            New Instance
          </PrimaryButton>
        </ButtonGroup>
      </PageHeaderRow>

      {/* Filters */}
      <FilterGroup>
        {['all', 'running', 'stopped', 'pending', 'error'].map((status) => (
          <FilterButton
            key={status}
            onClick={() => setFilter(status)}
            $active={filter === status}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
            {status !== 'all' && (
              <FilterCount>
                ({instances.filter((i) => i.status === status).length})
              </FilterCount>
            )}
          </FilterButton>
        ))}
      </FilterGroup>

      {/* Table */}
      <Card>
        {isLoading ? (
          <LoadingMessage>Loading instances...</LoadingMessage>
        ) : filteredInstances.length === 0 ? (
          <EmptyMessage>
            <EmptyText>
              {filter === 'all' ? 'No instances yet' : `No ${filter} instances`}
            </EmptyText>
            {filter === 'all' && (
              <PrimaryButton to={toPath('instances/new')}>
                <PlusIcon />
                Create your first instance
              </PrimaryButton>
            )}
          </EmptyMessage>
        ) : (
          <Table>
            <TableHead>
              <tr>
                <TableHeader>Name</TableHeader>
                <TableHeader>Status</TableHeader>
                <TableHeader>Topology</TableHeader>
                <TableHeader>URL</TableHeader>
                <TableHeader>Created</TableHeader>
                <TableHeader>Expires</TableHeader>
                <TableHeader>Actions</TableHeader>
              </tr>
            </TableHead>
            <TableBody>
              {filteredInstances.map((instance) => (
                <InstanceRow
                  key={instance.id}
                  instance={instance}
                  onStart={(id) => startMutation.mutate(id)}
                  onStop={(id) => stopMutation.mutate(id)}
                  onDestroy={handleDestroy}
                  toPath={toPath}
                />
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
    </PageContainer>
  );
}
