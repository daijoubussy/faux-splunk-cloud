import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format, formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';
import {
  PlayIcon,
  StopIcon,
  TrashIcon,
  ClockIcon,
  ClipboardIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';
import { instancesApi, attacksApi } from '../api';
import { useTenantPath } from '../hooks/useTenantPath';
import { SplunkViewer } from '../components/SplunkViewer';
import type { Instance } from '../types';

// ============================================================================
// Styled Components
// ============================================================================

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const HeaderLeft = styled.div``;

const TitleRow = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
`;

const PageTitle = styled.h1`
  font-size: 1.5rem;
  font-weight: 700;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const InstanceId = styled.p`
  margin-top: 0.25rem;
  font-size: 0.875rem;
  font-family: monospace;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 0.5rem;
`;

interface ActionButtonProps {
  $variant: 'success' | 'warning' | 'danger';
}

const ActionButton = styled.button<ActionButtonProps>`
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: white;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background-color 0.2s;

  ${props => {
    switch (props.$variant) {
      case 'success':
        return `
          background-color: #22c55e;
          &:hover:not(:disabled) { background-color: #16a34a; }
        `;
      case 'warning':
        return `
          background-color: #eab308;
          &:hover:not(:disabled) { background-color: #ca8a04; }
        `;
      case 'danger':
        return `
          background-color: #ef4444;
          &:hover:not(:disabled) { background-color: #dc2626; }
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
    margin-right: 0.25rem;
  }
`;

interface BadgeProps {
  $variant: 'success' | 'warning' | 'error' | 'info' | 'default';
  $pulse?: boolean;
}

const Badge = styled.span<BadgeProps>`
  display: inline-flex;
  padding: 0.25rem 0.75rem;
  font-size: 0.875rem;
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

const TwoColumnGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;

  @media (min-width: 1024px) {
    grid-template-columns: repeat(2, 1fr);
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
`;

const CardHeader = styled.div`
  padding: 1rem 1.5rem;
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

const InfoList = styled.dl``;

const InfoRow = styled.div`
  padding: 0.75rem 0;
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1rem;
  align-items: center;
  border-bottom: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};

  &:last-child {
    border-bottom: none;
  }
`;

const InfoLabel = styled.dt`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const InfoValue = styled.dd`
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: monospace;
  word-break: break-all;
  margin: 0;
`;

const CopyBtn = styled.button`
  padding: 0.25rem;
  background: transparent;
  border: none;
  cursor: pointer;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  transition: color 0.2s;

  &:hover {
    color: ${pick({
      prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
    })};
  }

  svg {
    width: 1rem;
    height: 1rem;
  }
`;

const SmallBtn = styled.button`
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  background-color: transparent;
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.25rem;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }

  svg {
    width: 0.75rem;
    height: 0.75rem;
    margin-right: 0.25rem;
  }
`;

const Description = styled.p`
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin-bottom: 1rem;
`;

const AttackButtonGroup = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
`;

interface AttackButtonProps {
  $color: string;
}

const AttackButton = styled.button<AttackButtonProps>`
  display: inline-flex;
  align-items: center;
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: white;
  background-color: ${props => props.$color};
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: opacity 0.2s;

  &:hover:not(:disabled) {
    opacity: 0.9;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  svg {
    width: 0.75rem;
    height: 0.75rem;
    margin-right: 0.25rem;
  }
`;

const CardLink = styled(Link)`
  display: inline-block;
  margin-top: 0.75rem;
  font-size: 0.875rem;
  color: ${variables.accentColorPositive};
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
`;

const ToggleButton = styled.button`
  font-size: 0.875rem;
  color: ${variables.accentColorPositive};
  background: transparent;
  border: none;
  cursor: pointer;

  &:hover {
    text-decoration: underline;
  }
`;

const LogsCard = styled(Card)``;

const LogsHeader = styled(CardHeader)`
  flex-wrap: wrap;
  gap: 0.5rem;
`;

const LogsControls = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const LogsSelect = styled.select`
  padding: 0.25rem 0.5rem;
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
`;

const LogsContent = styled.pre`
  font-size: 0.75rem;
  font-family: monospace;
  background-color: #111;
  color: #f5f5f5;
  padding: 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  max-height: 24rem;
  margin: 0;
`;

const LoadingText = styled.div`
  padding: 2rem;
  text-align: center;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const ErrorText = styled.p`
  color: #ef4444;
`;

const BackLink = styled(Link)`
  margin-top: 0.5rem;
  display: inline-block;
  color: ${variables.accentColorPositive};
  text-decoration: none;

  &:hover {
    text-decoration: underline;
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
      return 'warning';
    case 'pending':
      return 'info';
    case 'error':
      return 'error';
    default:
      return 'default';
  }
}

function shouldPulse(status: string): boolean {
  return ['starting', 'provisioning'].includes(status);
}

function StatusBadge({ status }: { status: Instance['status'] }) {
  return (
    <Badge $variant={getStatusVariant(status)} $pulse={shouldPulse(status)}>
      {status}
    </Badge>
  );
}

function CopyButton({ value, label }: { value: string; label: string }) {
  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    toast.success(`${label} copied to clipboard`);
  };

  return (
    <CopyBtn onClick={handleCopy} title={`Copy ${label}`}>
      <ClipboardIcon />
    </CopyBtn>
  );
}

function InfoItem({ label, value, copyable = false }: { label: string; value: string | null; copyable?: boolean }) {
  if (!value) return null;

  return (
    <InfoRow>
      <InfoLabel>{label}</InfoLabel>
      <InfoValue>
        <span>{value}</span>
        {copyable && <CopyButton value={value} label={label} />}
      </InfoValue>
    </InfoRow>
  );
}

function LogViewer({ instanceId }: { instanceId: string }) {
  const [tail, setTail] = useState(100);

  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ['instance-logs', instanceId, tail],
    queryFn: () => instancesApi.getLogs(instanceId, tail),
    refetchInterval: 5000,
  });

  return (
    <LogsCard>
      <LogsHeader>
        <CardTitle>Container Logs</CardTitle>
        <LogsControls>
          <LogsSelect value={tail} onChange={(e) => setTail(parseInt(e.target.value))}>
            <option value={50}>Last 50 lines</option>
            <option value={100}>Last 100 lines</option>
            <option value={500}>Last 500 lines</option>
          </LogsSelect>
          <SmallBtn onClick={() => refetch()}>Refresh</SmallBtn>
        </LogsControls>
      </LogsHeader>
      <CardBody>
        {isLoading ? (
          <LoadingText>Loading logs...</LoadingText>
        ) : (
          <LogsContent>{logs || 'No logs available'}</LogsContent>
        )}
      </CardBody>
    </LogsCard>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function InstanceDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showLogs, setShowLogs] = useState(false);
  const { toPath } = useTenantPath();

  const { data: instance, isLoading, error } = useQuery({
    queryKey: ['instance', id],
    queryFn: () => instancesApi.get(id!),
    enabled: !!id,
    refetchInterval: 5000,
  });

  const startMutation = useMutation({
    mutationFn: () => instancesApi.start(id!),
    onSuccess: () => {
      toast.success('Instance starting...');
      queryClient.invalidateQueries({ queryKey: ['instance', id] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const stopMutation = useMutation({
    mutationFn: () => instancesApi.stop(id!),
    onSuccess: () => {
      toast.success('Instance stopping...');
      queryClient.invalidateQueries({ queryKey: ['instance', id] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const destroyMutation = useMutation({
    mutationFn: () => instancesApi.destroy(id!),
    onSuccess: () => {
      toast.success('Instance destroyed');
      navigate(toPath('instances'));
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const extendMutation = useMutation({
    mutationFn: (hours: number) => instancesApi.extend(id!, hours),
    onSuccess: () => {
      toast.success('TTL extended');
      queryClient.invalidateQueries({ queryKey: ['instance', id] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const launchAttackMutation = useMutation({
    mutationFn: (threatActorId: string) =>
      attacksApi.createCampaign({
        threat_actor_id: threatActorId,
        target_instance_id: id!,
        start_immediately: true,
      }),
    onSuccess: (campaign) => {
      toast.success('Attack campaign started!');
      navigate(toPath(`attacks/campaigns/${campaign.id}`));
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (isLoading) {
    return <LoadingText>Loading...</LoadingText>;
  }

  if (error || !instance) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <ErrorText>Failed to load instance</ErrorText>
        <BackLink to={toPath('instances')}>Back to instances</BackLink>
      </div>
    );
  }

  const canStart = ['pending', 'stopped', 'provisioning'].includes(instance.status);
  const canStop = ['running', 'starting'].includes(instance.status);

  return (
    <PageContainer>
      {/* Header */}
      <Header>
        <HeaderLeft>
          <TitleRow>
            <PageTitle>{instance.name}</PageTitle>
            <StatusBadge status={instance.status} />
          </TitleRow>
          <InstanceId>{instance.id}</InstanceId>
        </HeaderLeft>
        <ButtonGroup>
          {canStart && (
            <ActionButton
              $variant="success"
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
            >
              <PlayIcon />
              Start
            </ActionButton>
          )}
          {canStop && (
            <ActionButton
              $variant="warning"
              onClick={() => stopMutation.mutate()}
              disabled={stopMutation.isPending}
            >
              <StopIcon />
              Stop
            </ActionButton>
          )}
          <ActionButton
            $variant="danger"
            onClick={() => {
              if (window.confirm('Destroy this instance?')) destroyMutation.mutate();
            }}
            disabled={destroyMutation.isPending}
          >
            <TrashIcon />
            Destroy
          </ActionButton>
        </ButtonGroup>
      </Header>

      {/* Splunk Access Options */}
      {instance.status === 'running' && instance.endpoints.web_url && (
        <SplunkViewer
          webUrl={instance.endpoints.web_url}
          instanceId={instance.id}
          instanceName={instance.name}
        />
      )}

      <TwoColumnGrid>
        {/* Instance Info */}
        <Card>
          <CardHeader>
            <CardTitle>Instance Information</CardTitle>
          </CardHeader>
          <CardBody>
            <InfoList>
              <InfoItem label="Topology" value={instance.config.topology} />
              <InfoItem label="Experience" value={instance.config.experience} />
              <InfoItem label="Memory" value={`${instance.config.memory_mb} MB`} />
              <InfoItem label="CPU" value={`${instance.config.cpu_cores} cores`} />
              <InfoItem label="Created" value={format(new Date(instance.created_at), 'PPpp')} />
              <InfoRow>
                <InfoLabel>Expires</InfoLabel>
                <InfoValue>
                  <span>{formatDistanceToNow(new Date(instance.expires_at), { addSuffix: true })}</span>
                  <SmallBtn onClick={() => extendMutation.mutate(24)}>
                    <ClockIcon />
                    +24h
                  </SmallBtn>
                </InfoValue>
              </InfoRow>
            </InfoList>
          </CardBody>
        </Card>

        {/* Endpoints */}
        <Card>
          <CardHeader>
            <CardTitle>Endpoints</CardTitle>
          </CardHeader>
          <CardBody>
            <InfoList>
              <InfoItem label="Web UI" value={instance.endpoints.web_url} copyable />
              <InfoItem label="REST API" value={instance.endpoints.api_url} copyable />
              <InfoItem label="HEC" value={instance.endpoints.hec_url} copyable />
              <InfoItem label="ACS API" value={instance.endpoints.acs_url} copyable />
            </InfoList>
          </CardBody>
        </Card>

        {/* Credentials */}
        {instance.credentials && (
          <Card>
            <CardHeader>
              <CardTitle>Credentials</CardTitle>
            </CardHeader>
            <CardBody>
              <InfoList>
                <InfoItem label="Username" value={instance.credentials.admin_username} copyable />
                <InfoItem label="Password" value={instance.credentials.admin_password} copyable />
                <InfoItem label="HEC Token" value={instance.credentials.hec_token} copyable />
                <InfoItem label="ACS Token" value={instance.credentials.acs_token} copyable />
              </InfoList>
            </CardBody>
          </Card>
        )}

        {/* Attack Simulation */}
        <Card>
          <CardHeader>
            <CardTitle>Attack Simulation</CardTitle>
          </CardHeader>
          <CardBody>
            <Description>Launch a simulated attack against this instance</Description>
            <AttackButtonGroup>
              {[
                { id: 'script_kiddie_generic', label: 'Script Kiddie', color: '#6b7280' },
                { id: 'apt_generic', label: 'Generic APT', color: '#f97316' },
                { id: 'apt29', label: 'APT29 (Cozy Bear)', color: '#dc2626' },
                { id: 'lazarus', label: 'Lazarus Group', color: '#b91c1c' },
              ].map((actor) => (
                <AttackButton
                  key={actor.id}
                  $color={actor.color}
                  onClick={() => launchAttackMutation.mutate(actor.id)}
                  disabled={instance.status !== 'running' || launchAttackMutation.isPending}
                >
                  <ShieldExclamationIcon />
                  {actor.label}
                </AttackButton>
              ))}
            </AttackButtonGroup>
            <CardLink to={toPath('attacks/scenarios')}>
              View all attack scenarios →
            </CardLink>
          </CardBody>
        </Card>
      </TwoColumnGrid>

      {/* Logs Toggle */}
      <div>
        <ToggleButton onClick={() => setShowLogs(!showLogs)}>
          {showLogs ? 'Hide Logs' : 'Show Container Logs'}
        </ToggleButton>
      </div>

      {showLogs && id && <LogViewer instanceId={id} />}
    </PageContainer>
  );
}
