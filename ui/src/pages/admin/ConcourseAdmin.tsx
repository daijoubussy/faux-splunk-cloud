import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';
import {
  PlayIcon,
  PauseIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ServerStackIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline';

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
  display: flex;
  align-items: center;
  gap: 0.75rem;

  svg {
    width: 2rem;
    height: 2rem;
    color: ${variables.accentColorPositive};
  }
`;

const Description = styled.p`
  margin-top: 0.25rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const TabBar = styled.div`
  display: flex;
  gap: 0.25rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
`;

interface TabProps {
  $active: boolean;
}

const Tab = styled.button<TabProps>`
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  background: none;
  border: none;
  cursor: pointer;
  color: ${props => props.$active
    ? pick({ prisma: { dark: variables.contentColorActive, light: variables.contentColorActive }})
    : pick({ prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted }})};
  border-bottom: 2px solid ${props => props.$active
    ? variables.accentColorPositive
    : 'transparent'};
  margin-bottom: -1px;

  &:hover {
    color: ${pick({
      prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
    })};
  }
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
  font-weight: 600;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;

  svg {
    width: 1.25rem;
    height: 1.25rem;
    color: ${variables.accentColorPositive};
  }
`;

const StatusGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
`;

const StatusItem = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
`;

interface StatusIndicatorProps {
  $status: 'success' | 'error' | 'warning' | 'running';
}

const StatusIndicator = styled.div<StatusIndicatorProps>`
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: ${props => {
    switch (props.$status) {
      case 'success': return 'rgba(34, 197, 94, 0.1)';
      case 'error': return 'rgba(239, 68, 68, 0.1)';
      case 'warning': return 'rgba(234, 179, 8, 0.1)';
      case 'running': return 'rgba(59, 130, 246, 0.1)';
    }
  }};

  svg {
    width: 1.25rem;
    height: 1.25rem;
    color: ${props => {
      switch (props.$status) {
        case 'success': return '#22c55e';
        case 'error': return '#ef4444';
        case 'warning': return '#eab308';
        case 'running': return '#3b82f6';
      }
    }};
  }
`;

const StatusLabel = styled.div`
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const StatusValue = styled.div`
  font-weight: 600;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const TableHead = styled.thead`
  border-bottom: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
`;

const TableHeadCell = styled.th`
  text-align: left;
  padding: 0.75rem 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const TableBody = styled.tbody``;

const TableRow = styled.tr`
  border-bottom: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }
`;

const TableCell = styled.td`
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

interface StatusBadgeProps {
  $status: string;
}

const StatusBadge = styled.span<StatusBadgeProps>`
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  background-color: ${props => {
    switch (props.$status) {
      case 'succeeded': return 'rgba(34, 197, 94, 0.1)';
      case 'failed': return 'rgba(239, 68, 68, 0.1)';
      case 'started':
      case 'pending': return 'rgba(59, 130, 246, 0.1)';
      case 'paused': return 'rgba(234, 179, 8, 0.1)';
      default: return 'rgba(107, 114, 128, 0.1)';
    }
  }};
  color: ${props => {
    switch (props.$status) {
      case 'succeeded': return '#22c55e';
      case 'failed': return '#ef4444';
      case 'started':
      case 'pending': return '#3b82f6';
      case 'paused': return '#eab308';
      default: return '#6b7280';
    }
  }};
`;

const IframeContainer = styled.div`
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  overflow: hidden;
  height: 70vh;
`;

const IframeStyled = styled.iframe`
  width: 100%;
  height: 100%;
  border: none;
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 3rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const VersionText = styled.div`
  margin-top: 1rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const ActionButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 0.25rem;
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  background: none;
  cursor: pointer;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }

  svg {
    width: 0.875rem;
    height: 0.875rem;
  }
`;

// ============================================================================
// API
// ============================================================================

async function fetchConcourseInfo() {
  const response = await fetch('/api/v1/concourse/info');
  if (!response.ok) {
    throw new Error('Failed to fetch Concourse info');
  }
  return response.json();
}

async function fetchConcourseHealth() {
  const response = await fetch('/api/v1/concourse/health');
  if (!response.ok) {
    throw new Error('Failed to fetch Concourse health');
  }
  return response.json();
}

async function fetchPipelines() {
  const response = await fetch('/api/v1/concourse/pipelines', {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error('Failed to fetch pipelines');
  }
  return response.json();
}

async function fetchBuilds() {
  const response = await fetch('/api/v1/concourse/builds?limit=10', {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error('Failed to fetch builds');
  }
  return response.json();
}

async function fetchWorkers() {
  const response = await fetch('/api/v1/concourse/workers', {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error('Failed to fetch workers');
  }
  return response.json();
}

// ============================================================================
// Components
// ============================================================================

function ConcourseStatus() {
  const { data: info, isLoading } = useQuery({
    queryKey: ['concourse-info'],
    queryFn: fetchConcourseInfo,
    refetchInterval: 10000,
  });

  const { data: health } = useQuery({
    queryKey: ['concourse-health'],
    queryFn: fetchConcourseHealth,
    refetchInterval: 5000,
  });

  const { data: workers } = useQuery({
    queryKey: ['concourse-workers'],
    queryFn: fetchWorkers,
    refetchInterval: 10000,
  });

  if (isLoading) {
    return (
      <Card>
        <CardTitle>
          <ServerStackIcon />
          Concourse Status
        </CardTitle>
        <EmptyState>Loading Concourse status...</EmptyState>
      </Card>
    );
  }

  const workerCount = workers?.workers?.length || 0;
  const runningWorkers = workers?.workers?.filter((w: any) => w.state === 'running').length || 0;

  return (
    <Card>
      <CardTitle>
        <ServerStackIcon />
        Concourse Status
      </CardTitle>
      <StatusGrid>
        <StatusItem>
          <StatusIndicator $status={health?.healthy ? 'success' : 'error'}>
            {health?.healthy ? <CheckCircleIcon /> : <XCircleIcon />}
          </StatusIndicator>
          <div>
            <StatusLabel>Health</StatusLabel>
            <StatusValue>{health?.healthy ? 'Healthy' : 'Unhealthy'}</StatusValue>
          </div>
        </StatusItem>
        <StatusItem>
          <StatusIndicator $status={workerCount > 0 ? 'success' : 'warning'}>
            <CpuChipIcon />
          </StatusIndicator>
          <div>
            <StatusLabel>Workers</StatusLabel>
            <StatusValue>{runningWorkers}/{workerCount} Running</StatusValue>
          </div>
        </StatusItem>
      </StatusGrid>
      {info?.version && (
        <VersionText>
          Version: {info.version}
          {info.cluster_name && ` | Cluster: ${info.cluster_name}`}
        </VersionText>
      )}
    </Card>
  );
}

function PipelinesTab() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['concourse-pipelines'],
    queryFn: fetchPipelines,
    refetchInterval: 10000,
  });

  if (isLoading) {
    return <EmptyState>Loading pipelines...</EmptyState>;
  }

  if (error) {
    return <EmptyState>Failed to load pipelines. Make sure you have admin privileges.</EmptyState>;
  }

  const pipelines = data?.pipelines || [];

  if (pipelines.length === 0) {
    return (
      <Card>
        <CardTitle>Pipelines</CardTitle>
        <EmptyState>No pipelines found. Create one using the fly CLI or Concourse UI.</EmptyState>
      </Card>
    );
  }

  return (
    <Card>
      <CardTitle>Pipelines</CardTitle>
      <Table>
        <TableHead>
          <tr>
            <TableHeadCell>Name</TableHeadCell>
            <TableHeadCell>Team</TableHeadCell>
            <TableHeadCell>Status</TableHeadCell>
            <TableHeadCell>Actions</TableHeadCell>
          </tr>
        </TableHead>
        <TableBody>
          {pipelines.map((pipeline: any) => (
            <TableRow key={`${pipeline.team_name}-${pipeline.name}`}>
              <TableCell>{pipeline.name}</TableCell>
              <TableCell>{pipeline.team_name}</TableCell>
              <TableCell>
                <StatusBadge $status={pipeline.paused ? 'paused' : 'running'}>
                  {pipeline.paused ? (
                    <>
                      <PauseIcon style={{ width: '0.75rem', height: '0.75rem' }} />
                      Paused
                    </>
                  ) : (
                    <>
                      <PlayIcon style={{ width: '0.75rem', height: '0.75rem' }} />
                      Active
                    </>
                  )}
                </StatusBadge>
              </TableCell>
              <TableCell>
                <ActionButton>View</ActionButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

function BuildsTab() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['concourse-builds'],
    queryFn: fetchBuilds,
    refetchInterval: 5000,
  });

  if (isLoading) {
    return <EmptyState>Loading builds...</EmptyState>;
  }

  if (error) {
    return <EmptyState>Failed to load builds. Make sure you have admin privileges.</EmptyState>;
  }

  const builds = data?.builds || [];

  if (builds.length === 0) {
    return (
      <Card>
        <CardTitle>Recent Builds</CardTitle>
        <EmptyState>No builds found.</EmptyState>
      </Card>
    );
  }

  return (
    <Card>
      <CardTitle>Recent Builds</CardTitle>
      <Table>
        <TableHead>
          <tr>
            <TableHeadCell>ID</TableHeadCell>
            <TableHeadCell>Pipeline</TableHeadCell>
            <TableHeadCell>Job</TableHeadCell>
            <TableHeadCell>Status</TableHeadCell>
            <TableHeadCell>Started</TableHeadCell>
          </tr>
        </TableHead>
        <TableBody>
          {builds.map((build: any) => (
            <TableRow key={build.id}>
              <TableCell>#{build.id}</TableCell>
              <TableCell>{build.pipeline_name || '-'}</TableCell>
              <TableCell>{build.job_name || '-'}</TableCell>
              <TableCell>
                <StatusBadge $status={build.status}>
                  {build.status === 'succeeded' && <CheckCircleIcon style={{ width: '0.75rem', height: '0.75rem' }} />}
                  {build.status === 'failed' && <XCircleIcon style={{ width: '0.75rem', height: '0.75rem' }} />}
                  {(build.status === 'started' || build.status === 'pending') && <ClockIcon style={{ width: '0.75rem', height: '0.75rem' }} />}
                  {build.status}
                </StatusBadge>
              </TableCell>
              <TableCell>
                {build.start_time
                  ? new Date(build.start_time * 1000).toLocaleString()
                  : '-'}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

function ConcourseUITab() {
  return (
    <IframeContainer>
      <IframeStyled
        src="/concourse/"
        title="Concourse UI"
      />
    </IframeContainer>
  );
}

// ============================================================================
// Main Component
// ============================================================================

type TabType = 'pipelines' | 'builds' | 'ui';

export default function ConcourseAdmin() {
  const [activeTab, setActiveTab] = useState<TabType>('pipelines');

  return (
    <Container>
      <Header>
        <Title>
          <ServerStackIcon />
          Concourse CI
        </Title>
        <Description>
          Manage CI/CD pipelines and monitor build status.
        </Description>
      </Header>

      <ConcourseStatus />

      <TabBar>
        <Tab $active={activeTab === 'pipelines'} onClick={() => setActiveTab('pipelines')}>
          Pipelines
        </Tab>
        <Tab $active={activeTab === 'builds'} onClick={() => setActiveTab('builds')}>
          Builds
        </Tab>
        <Tab $active={activeTab === 'ui'} onClick={() => setActiveTab('ui')}>
          Concourse UI
        </Tab>
      </TabBar>

      {activeTab === 'pipelines' && <PipelinesTab />}
      {activeTab === 'builds' && <BuildsTab />}
      {activeTab === 'ui' && <ConcourseUITab />}
    </Container>
  );
}
