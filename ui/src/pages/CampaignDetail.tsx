import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import styled, { keyframes } from 'styled-components';
import { variables, pick } from '@splunk/themes';
import {
  ArrowLeftIcon,
  BoltIcon,
  PlayIcon,
  PauseIcon,
  EyeIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { attacksApi } from '../api';
import { useTenantPath } from '../hooks/useTenantPath';
import type { AttackCampaign, AttackStep } from '../types';

// ============================================================================
// Animations
// ============================================================================

const spin = keyframes`
  to { transform: rotate(360deg); }
`;

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
`;

// ============================================================================
// Styled Components
// ============================================================================

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
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
  border: 2px solid transparent;
  border-bottom-color: ${variables.accentColorPositive};
  border-radius: 50%;
  animation: ${spin} 1s linear infinite;
`;

const BackLink = styled(Link)`
  display: inline-flex;
  align-items: center;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  text-decoration: none;
  margin-bottom: 0.5rem;

  svg {
    width: 1rem;
    height: 1rem;
    margin-right: 0.25rem;
  }

  &:hover {
    color: ${pick({
      prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
    })};
  }
`;

const ErrorBanner = styled.div`
  background-color: rgba(220, 53, 69, 0.1);
  border: 1px solid rgba(220, 53, 69, 0.3);
  border-radius: 0.5rem;
  padding: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #dc3545;
`;

const Header = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
`;

const HeaderLeft = styled.div``;

const PageTitle = styled.h1`
  font-size: 1.5rem;
  font-weight: 700;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const CampaignId = styled.p`
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const ButtonGroup = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
`;

const StartButton = styled.button`
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: white;
  background-color: ${variables.accentColorPositive};
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background-color 0.2s;

  svg {
    width: 1rem;
    height: 1rem;
    margin-right: 0.5rem;
  }

  &:hover:not(:disabled) {
    background-color: #00a86b;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const PauseButton = styled.button`
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: white;
  background-color: #f8be34;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background-color 0.2s;

  svg {
    width: 1rem;
    height: 1rem;
    margin-right: 0.5rem;
  }

  &:hover:not(:disabled) {
    background-color: #e0a82e;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

// Status Badge
interface StatusBadgeProps {
  $status: string;
  $pulse?: boolean;
}

const StatusBadge = styled.span<StatusBadgeProps>`
  display: inline-flex;
  align-items: center;
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 9999px;
  border: 1px solid;

  ${props => {
    switch (props.$status) {
      case 'pending':
        return 'background-color: rgba(248, 190, 52, 0.1); color: #f8be34; border-color: rgba(248, 190, 52, 0.3);';
      case 'running':
        return 'background-color: rgba(220, 53, 69, 0.1); color: #dc3545; border-color: rgba(220, 53, 69, 0.3);';
      case 'paused':
        return 'background-color: rgba(128, 128, 128, 0.1); color: #808080; border-color: rgba(128, 128, 128, 0.3);';
      case 'completed':
        return 'background-color: rgba(0, 201, 125, 0.1); color: #00c97d; border-color: rgba(0, 201, 125, 0.3);';
      case 'detected':
        return 'background-color: rgba(0, 157, 224, 0.1); color: #009de0; border-color: rgba(0, 157, 224, 0.3);';
      case 'failed':
        return 'background-color: rgba(220, 53, 69, 0.1); color: #dc3545; border-color: rgba(220, 53, 69, 0.3);';
      default:
        return 'background-color: rgba(128, 128, 128, 0.1); color: #808080; border-color: rgba(128, 128, 128, 0.3);';
    }
  }}

  svg {
    width: 1rem;
    height: 1rem;
    margin-right: 0.375rem;
    ${props => props.$pulse && `animation: ${pulse} 2s ease-in-out infinite;`}
  }
`;

// Card
const Card = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  padding: 1.5rem;
`;

const OverviewGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;

  @media (min-width: 768px) {
    grid-template-columns: repeat(4, 1fr);
  }
`;

const StatBlock = styled.div``;

const StatLabel = styled.h3`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin: 0;
`;

const StatValue = styled.p`
  margin-top: 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  text-transform: capitalize;
`;

const ProgressContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const ProgressBar = styled.div`
  flex: 1;
  background-color: rgba(128, 128, 128, 0.2);
  border-radius: 9999px;
  height: 0.75rem;
  overflow: hidden;
`;

interface ProgressFillProps {
  $percent: number;
}

const ProgressFill = styled.div<ProgressFillProps>`
  width: ${props => props.$percent}%;
  height: 100%;
  background-color: #dc3545;
  border-radius: 9999px;
  transition: width 0.5s ease;
`;

const ProgressText = styled.span`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

const StepsText = styled.p`
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const DetectionAlert = styled.div`
  margin-top: 1.5rem;
  padding: 1rem;
  background-color: rgba(0, 157, 224, 0.1);
  border: 1px solid rgba(0, 157, 224, 0.3);
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;

  svg {
    width: 1.25rem;
    height: 1.25rem;
    color: #009de0;
  }
`;

const AlertContent = styled.div``;

const AlertTitle = styled.p`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const AlertText = styled.p`
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin: 0;
`;

const MetadataGrid = styled.div`
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;

  @media (min-width: 768px) {
    grid-template-columns: repeat(4, 1fr);
  }
`;

const MetadataItem = styled.div``;

const MetadataLabel = styled.h4`
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin: 0;
`;

const MetadataValue = styled.p`
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

const InstanceLink = styled(Link)`
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: ${variables.accentColorPositive};
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
`;

// Tabs
const TabsCard = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  overflow: hidden;
`;

const TabsHeader = styled.div`
  border-bottom: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
`;

const TabsNav = styled.nav`
  display: flex;
  margin-bottom: -1px;
`;

interface TabButtonProps {
  $active: boolean;
}

const TabButton = styled.button<TabButtonProps>`
  padding: 0.75rem 1.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  background: none;
  border: none;
  border-bottom: 2px solid ${props => props.$active
    ? variables.accentColorPositive
    : 'transparent'};
  color: ${props => props.$active
    ? variables.accentColorPositive
    : pick({ prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted } })};
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;

  &:hover {
    color: ${props => props.$active
      ? variables.accentColorPositive
      : pick({ prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault } })};
    border-bottom-color: ${props => props.$active
      ? variables.accentColorPositive
      : pick({ prisma: { dark: variables.borderColor, light: variables.borderColor } })};
  }

  svg {
    width: 1rem;
    height: 1rem;
    display: inline;
    margin-right: 0.5rem;
    vertical-align: text-bottom;
  }
`;

const TabContent = styled.div`
  padding: 1.5rem;
`;

// Step Timeline
const TimelineContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

interface PhaseCardProps {
  $active: boolean;
}

const PhaseCard = styled.div<PhaseCardProps>`
  border: 1px solid ${props => props.$active
    ? 'rgba(220, 53, 69, 0.3)'
    : pick({ prisma: { dark: variables.borderColor, light: variables.borderColor } })};
  border-radius: 0.5rem;
  background-color: ${props => props.$active
    ? 'rgba(220, 53, 69, 0.05)'
    : 'transparent'};
`;

const PhaseHeader = styled.div`
  padding: 0.75rem;
  border-bottom: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
  border-radius: 0.5rem 0.5rem 0 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const PhaseHeaderLeft = styled.div`
  display: flex;
  align-items: center;
`;

const PulsingIcon = styled.span`
  animation: ${pulse} 2s ease-in-out infinite;
  color: #dc3545;
  margin-right: 0.5rem;

  svg {
    width: 1rem;
    height: 1rem;
  }
`;

const PhaseName = styled.h4`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
  text-transform: capitalize;
`;

const PhaseStats = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
`;

const CompletedStat = styled.span`
  color: ${variables.accentColorPositive};
`;

const DetectedStat = styled.span`
  color: #009de0;
`;

const PhaseBody = styled.div`
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`;

interface StepItemProps {
  $status: 'detected' | 'success' | 'failed';
}

const StepItem = styled.div<StepItemProps>`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem;
  border-radius: 0.25rem;
  border: 1px solid;

  ${props => {
    switch (props.$status) {
      case 'detected':
        return 'background-color: rgba(0, 157, 224, 0.1); border-color: rgba(0, 157, 224, 0.3);';
      case 'success':
        return 'background-color: rgba(0, 201, 125, 0.1); border-color: rgba(0, 201, 125, 0.3);';
      default:
        return 'background-color: rgba(220, 53, 69, 0.1); border-color: rgba(220, 53, 69, 0.3);';
    }
  }}
`;

const StepInfo = styled.div`
  display: flex;
  align-items: center;
`;

const StepIcon = styled.span<{ $color: string }>`
  margin-right: 0.5rem;
  color: ${props => props.$color};

  svg {
    width: 1rem;
    height: 1rem;
  }
`;

const StepDetails = styled.div``;

const TechniqueName = styled.p`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const TechniqueLink = styled.a`
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  text-decoration: none;

  &:hover {
    color: ${variables.accentColorPositive};
  }
`;

const StepTime = styled.span`
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

// Log Viewer
const LogHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
`;

const LogCount = styled.span`
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const AutoScrollLabel = styled.label`
  display: flex;
  align-items: center;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  cursor: pointer;

  input {
    margin-right: 0.5rem;
    width: 1rem;
    height: 1rem;
    accent-color: ${variables.accentColorPositive};
  }
`;

const LogContainer = styled.div`
  background-color: #1a1a2e;
  border-radius: 0.5rem;
  padding: 1rem;
  height: 24rem;
  overflow-y: auto;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.75rem;
`;

const LogEntry = styled.div`
  color: #d4d4d4;
  margin-bottom: 0.25rem;
  padding: 0.125rem 0.25rem;
  border-radius: 0.125rem;

  &:hover {
    background-color: rgba(255, 255, 255, 0.05);
  }
`;

const LogTime = styled.span`
  color: #6a6a6a;
`;

interface LogSourceProps {
  $severity?: string;
}

const LogSource = styled.span<LogSourceProps>`
  color: ${props => {
    switch (props.$severity) {
      case 'high': return '#dc3545';
      case 'medium': return '#f8be34';
      default: return '#00c97d';
    }
  }};
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 2rem;
`;

const EmptyIcon = styled.div`
  margin: 0 auto;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};

  svg {
    width: 3rem;
    height: 3rem;
  }
`;

const EmptyTitle = styled.h3`
  margin-top: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

const EmptyDescription = styled.p`
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const EmptyLogs = styled.p`
  color: #6a6a6a;
`;

// ============================================================================
// Helper Components
// ============================================================================

function CampaignStatusBadge({ status }: { status: AttackCampaign['status'] }) {
  const config: Record<string, { icon: React.ElementType; pulse?: boolean }> = {
    pending: { icon: ClockIcon },
    running: { icon: BoltIcon, pulse: true },
    paused: { icon: PauseIcon },
    completed: { icon: CheckCircleIcon },
    detected: { icon: EyeIcon },
    failed: { icon: ExclamationTriangleIcon },
  };

  const { icon: Icon, pulse: shouldPulse } = config[status] || config.pending;

  return (
    <StatusBadge $status={status} $pulse={shouldPulse}>
      <Icon />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </StatusBadge>
  );
}

function StepTimeline({ steps, currentPhase }: { steps: AttackStep[]; currentPhase: string }) {
  const phases = ['reconnaissance', 'initial_access', 'execution', 'persistence', 'privilege_escalation', 'defense_evasion', 'credential_access', 'discovery', 'lateral_movement', 'collection', 'command_and_control', 'exfiltration', 'impact'];

  const stepsByPhase = steps.reduce((acc, step) => {
    if (!acc[step.phase]) {
      acc[step.phase] = [];
    }
    acc[step.phase].push(step);
    return acc;
  }, {} as Record<string, AttackStep[]>);

  const activePhases = phases.filter((p) => stepsByPhase[p]?.length > 0);

  return (
    <TimelineContainer>
      {activePhases.map((phase) => {
        const phaseSteps = stepsByPhase[phase] || [];
        const isActive = phase === currentPhase;
        const completedSteps = phaseSteps.filter((s) => s.success).length;
        const detectedSteps = phaseSteps.filter((s) => s.detected).length;

        return (
          <PhaseCard key={phase} $active={isActive}>
            <PhaseHeader>
              <PhaseHeaderLeft>
                {isActive && (
                  <PulsingIcon>
                    <BoltIcon />
                  </PulsingIcon>
                )}
                <PhaseName>{phase.replace(/_/g, ' ')}</PhaseName>
              </PhaseHeaderLeft>
              <PhaseStats>
                <CompletedStat>{completedSteps} completed</CompletedStat>
                {detectedSteps > 0 && (
                  <DetectedStat>{detectedSteps} detected</DetectedStat>
                )}
              </PhaseStats>
            </PhaseHeader>
            <PhaseBody>
              {phaseSteps.map((step) => (
                <StepItem
                  key={step.id}
                  $status={step.detected ? 'detected' : step.success ? 'success' : 'failed'}
                >
                  <StepInfo>
                    <StepIcon $color={step.detected ? '#009de0' : step.success ? '#00c97d' : '#dc3545'}>
                      {step.detected ? (
                        <EyeIcon />
                      ) : step.success ? (
                        <CheckCircleIcon />
                      ) : (
                        <XCircleIcon />
                      )}
                    </StepIcon>
                    <StepDetails>
                      <TechniqueName>{step.technique_name}</TechniqueName>
                      <TechniqueLink
                        href={`https://attack.mitre.org/techniques/${step.technique_id.replace('.', '/')}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {step.technique_id}
                      </TechniqueLink>
                    </StepDetails>
                  </StepInfo>
                  <StepTime>
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </StepTime>
                </StepItem>
              ))}
            </PhaseBody>
          </PhaseCard>
        );
      })}
    </TimelineContainer>
  );
}

function LogViewer({ campaignId }: { campaignId: string }) {
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const { data: logs = [], isLoading } = useQuery({
    queryKey: ['campaign-logs', campaignId],
    queryFn: () => attacksApi.getCampaignLogs(campaignId, 500),
    refetchInterval: 2000,
  });

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  if (isLoading) {
    return (
      <LoadingContainer style={{ height: '12rem' }}>
        <Spinner style={{ width: '1.5rem', height: '1.5rem' }} />
      </LoadingContainer>
    );
  }

  return (
    <div>
      <LogHeader>
        <LogCount>{logs.length} log entries</LogCount>
        <AutoScrollLabel>
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
          />
          Auto-scroll
        </AutoScrollLabel>
      </LogHeader>

      <LogContainer>
        {logs.length === 0 ? (
          <EmptyLogs>No logs yet...</EmptyLogs>
        ) : (
          logs.map((log, index) => (
            <LogEntry key={index}>
              <LogTime>{new Date(log._time as string || Date.now()).toLocaleTimeString()}</LogTime>
              {' '}
              <LogSource $severity={log.severity as string}>
                [{String(log.sourcetype || 'attack')}]
              </LogSource>
              {' '}
              <span>{JSON.stringify(log, null, 0)}</span>
            </LogEntry>
          ))
        )}
        <div ref={logsEndRef} />
      </LogContainer>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function CampaignDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { toPath } = useTenantPath();
  const [activeTab, setActiveTab] = useState<'steps' | 'logs'>('steps');

  const { data: campaign, isLoading, error } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => attacksApi.getCampaign(id!),
    enabled: !!id,
    refetchInterval: 3000,
  });

  const { data: steps = [] } = useQuery({
    queryKey: ['campaign-steps', id],
    queryFn: () => attacksApi.getCampaignSteps(id!),
    enabled: !!id,
    refetchInterval: 3000,
  });

  const startMutation = useMutation({
    mutationFn: () => attacksApi.startCampaign(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', id] });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => attacksApi.pauseCampaign(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', id] });
    },
  });

  if (isLoading) {
    return (
      <LoadingContainer>
        <Spinner />
      </LoadingContainer>
    );
  }

  if (error || !campaign) {
    return (
      <PageContainer>
        <BackLink to={toPath('attacks/campaigns')}>
          <ArrowLeftIcon />
          Back to campaigns
        </BackLink>
        <ErrorBanner>
          <ExclamationTriangleIcon style={{ width: '1.25rem', height: '1.25rem' }} />
          <span>Campaign not found</span>
        </ErrorBanner>
      </PageContainer>
    );
  }

  const canStart = campaign.status === 'pending' || campaign.status === 'paused';
  const canPause = campaign.status === 'running';
  const progressPercent = campaign.total_steps > 0
    ? Math.round((campaign.completed_steps / campaign.total_steps) * 100)
    : 0;

  return (
    <PageContainer>
      {/* Header */}
      <Header>
        <HeaderLeft>
          <BackLink to={toPath('attacks/campaigns')}>
            <ArrowLeftIcon />
            Back to campaigns
          </BackLink>
          <PageTitle>{campaign.name}</PageTitle>
          <CampaignId>Campaign ID: {campaign.id}</CampaignId>
        </HeaderLeft>
        <ButtonGroup>
          {canStart && (
            <StartButton
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
            >
              <PlayIcon />
              {campaign.status === 'paused' ? 'Resume' : 'Start'} Campaign
            </StartButton>
          )}
          {canPause && (
            <PauseButton
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending}
            >
              <PauseIcon />
              Pause Campaign
            </PauseButton>
          )}
        </ButtonGroup>
      </Header>

      {/* Status Overview */}
      <Card>
        <OverviewGrid>
          <StatBlock>
            <StatLabel>Status</StatLabel>
            <div style={{ marginTop: '0.5rem' }}>
              <CampaignStatusBadge status={campaign.status} />
            </div>
          </StatBlock>

          <StatBlock>
            <StatLabel>Threat Actor</StatLabel>
            <StatValue>{campaign.threat_actor_name}</StatValue>
          </StatBlock>

          <StatBlock>
            <StatLabel>Current Phase</StatLabel>
            <StatValue>{campaign.current_phase.replace(/_/g, ' ')}</StatValue>
          </StatBlock>

          <StatBlock>
            <StatLabel>Progress</StatLabel>
            <div style={{ marginTop: '0.5rem' }}>
              <ProgressContainer>
                <ProgressBar>
                  <ProgressFill $percent={progressPercent} />
                </ProgressBar>
                <ProgressText>{progressPercent}%</ProgressText>
              </ProgressContainer>
              <StepsText>
                {campaign.completed_steps} of {campaign.total_steps} steps completed
              </StepsText>
            </div>
          </StatBlock>
        </OverviewGrid>

        {/* Detection Alert */}
        {campaign.detected && (
          <DetectionAlert>
            <EyeIcon />
            <AlertContent>
              <AlertTitle>Attack Detected!</AlertTitle>
              <AlertText>
                Detection occurred at step {campaign.detected_at_step} of {campaign.total_steps}
              </AlertText>
            </AlertContent>
          </DetectionAlert>
        )}

        {/* Timestamps */}
        <MetadataGrid>
          <MetadataItem>
            <MetadataLabel>Target Instance</MetadataLabel>
            <InstanceLink to={toPath(`instances/${campaign.target_instance_id}`)}>
              {campaign.target_instance_id}
            </InstanceLink>
          </MetadataItem>
          <MetadataItem>
            <MetadataLabel>Started</MetadataLabel>
            <MetadataValue>
              {campaign.start_time ? new Date(campaign.start_time).toLocaleString() : 'Not started'}
            </MetadataValue>
          </MetadataItem>
          <MetadataItem>
            <MetadataLabel>Ended</MetadataLabel>
            <MetadataValue>
              {campaign.end_time ? new Date(campaign.end_time).toLocaleString() : '-'}
            </MetadataValue>
          </MetadataItem>
          <MetadataItem>
            <MetadataLabel>Duration</MetadataLabel>
            <MetadataValue>
              {campaign.start_time && campaign.end_time
                ? `${Math.round((new Date(campaign.end_time).getTime() - new Date(campaign.start_time).getTime()) / 60000)} minutes`
                : campaign.start_time
                  ? 'In progress...'
                  : '-'}
            </MetadataValue>
          </MetadataItem>
        </MetadataGrid>
      </Card>

      {/* Tabs */}
      <TabsCard>
        <TabsHeader>
          <TabsNav>
            <TabButton
              $active={activeTab === 'steps'}
              onClick={() => setActiveTab('steps')}
            >
              <BoltIcon />
              Attack Steps ({steps.length})
            </TabButton>
            <TabButton
              $active={activeTab === 'logs'}
              onClick={() => setActiveTab('logs')}
            >
              <DocumentTextIcon />
              Generated Logs
            </TabButton>
          </TabsNav>
        </TabsHeader>

        <TabContent>
          {activeTab === 'steps' ? (
            steps.length === 0 ? (
              <EmptyState>
                <EmptyIcon>
                  <BoltIcon />
                </EmptyIcon>
                <EmptyTitle>No steps executed yet</EmptyTitle>
                <EmptyDescription>
                  Start the campaign to begin the attack simulation.
                </EmptyDescription>
              </EmptyState>
            ) : (
              <StepTimeline steps={steps} currentPhase={campaign.current_phase} />
            )
          ) : (
            <LogViewer campaignId={campaign.id} />
          )}
        </TabContent>
      </TabsCard>
    </PageContainer>
  );
}
