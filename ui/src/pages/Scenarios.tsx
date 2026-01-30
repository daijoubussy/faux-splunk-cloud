import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import styled, { keyframes } from 'styled-components';
import { variables, pick } from '@splunk/themes';
import {
  ShieldExclamationIcon,
  BoltIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ServerIcon,
} from '@heroicons/react/24/outline';
import { attacksApi, instancesApi } from '../api';
import { useTenantPath } from '../hooks/useTenantPath';
import type { AttackScenario, Instance } from '../types';

// ============================================================================
// Animations
// ============================================================================

const spin = keyframes`
  to { transform: rotate(360deg); }
`;

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

const InfoBanner = styled.div`
  background-color: rgba(0, 157, 224, 0.1);
  border: 1px solid rgba(0, 157, 224, 0.3);
  border-radius: 0.5rem;
  padding: 1rem;
  display: flex;
  gap: 0.75rem;
`;

const InfoIcon = styled.div`
  flex-shrink: 0;
  color: #009de0;
`;

const InfoContent = styled.div``;

const InfoTitle = styled.h3`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const InfoText = styled.p`
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const EmptyState = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  padding: 2rem;
  text-align: center;
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

const ScenarioGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;

  @media (min-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (min-width: 1024px) {
    grid-template-columns: repeat(3, 1fr);
  }
`;

// Scenario Card
const Card = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  overflow: hidden;
  transition: box-shadow 0.2s, border-color 0.2s;

  &:hover {
    border-color: ${variables.accentColorPositive};
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }
`;

const CardBody = styled.div`
  padding: 1.5rem;
`;

const CardHeader = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
`;

const CardHeaderLeft = styled.div`
  display: flex;
  align-items: center;
`;

const IconBox = styled.div`
  flex-shrink: 0;
  background-color: rgba(220, 53, 69, 0.15);
  border-radius: 0.5rem;
  padding: 0.75rem;

  svg {
    width: 1.5rem;
    height: 1.5rem;
    color: #dc3545;
  }
`;

const CardTitleGroup = styled.div`
  margin-left: 1rem;
`;

const CardTitle = styled.h3`
  font-size: 1.125rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const CardDescription = styled.p`
  margin-top: 1rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const DurationInfo = styled.div`
  margin-top: 1rem;
  display: flex;
  align-items: center;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};

  svg {
    width: 1rem;
    height: 1rem;
    margin-right: 0.25rem;
  }
`;

const ObjectivesSection = styled.div`
  margin-top: 1rem;
`;

const ObjectivesTitle = styled.h4`
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin: 0 0 0.5rem;
`;

const ObjectivesList = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
`;

const ObjectiveItem = styled.li`
  display: flex;
  align-items: center;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};

  svg {
    width: 1rem;
    height: 1rem;
    color: ${variables.accentColorPositive};
    margin-right: 0.5rem;
    flex-shrink: 0;
  }
`;

const CardFooter = styled.div`
  padding: 1rem 1.5rem;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
  border-top: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
`;

const LaunchButton = styled.button`
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: white;
  background-color: #dc3545;
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
    background-color: #c82333;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

// Threat Level Indicator
const ThreatLevelContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0.25rem;
`;

interface ThreatBarProps {
  $active: boolean;
  $color: string;
  $height: number;
}

const ThreatBar = styled.div<ThreatBarProps>`
  width: 6px;
  height: ${props => props.$height}px;
  border-radius: 2px;
  background-color: ${props => props.$active ? props.$color : 'rgba(128, 128, 128, 0.3)'};
`;

const ThreatLabel = styled.span`
  margin-left: 0.5rem;
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  text-transform: capitalize;
`;

// Modal
const ModalOverlay = styled.div`
  position: fixed;
  inset: 0;
  z-index: 50;
  overflow-y: auto;
`;

const ModalBackdrop = styled.div`
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.75);
  transition: opacity 0.2s;
`;

const ModalContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 1rem;
`;

const ModalContent = styled.div`
  position: relative;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  max-width: 32rem;
  width: 100%;
  padding: 1.5rem;
`;

const ModalTitle = styled.h3`
  font-size: 1.125rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0 0 1rem;
`;

const InstanceList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 15rem;
  overflow-y: auto;
`;

interface InstanceOptionProps {
  $selected: boolean;
}

const InstanceOption = styled.label<InstanceOptionProps>`
  display: flex;
  align-items: center;
  padding: 0.75rem;
  border: 1px solid ${props => props.$selected
    ? '#dc3545'
    : pick({ prisma: { dark: variables.borderColor, light: variables.borderColor } })};
  border-radius: 0.5rem;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
  background-color: ${props => props.$selected
    ? 'rgba(220, 53, 69, 0.1)'
    : 'transparent'};

  &:hover {
    border-color: ${props => props.$selected ? '#dc3545' : variables.accentColorPositive};
  }

  input {
    width: 1rem;
    height: 1rem;
    accent-color: #dc3545;
    margin: 0;
  }
`;

const InstanceInfo = styled.div`
  margin-left: 0.75rem;
`;

const InstanceName = styled.p`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const InstanceId = styled.p`
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin: 0;
`;

const ModalButtonGroup = styled.div`
  margin-top: 1.5rem;
  display: flex;
  gap: 0.75rem;
`;

const CancelButton = styled.button`
  flex: 1;
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
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }
`;

const ConfirmButton = styled.button`
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: white;
  background-color: #dc3545;
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
    background-color: #c82333;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const CreateInstanceLink = styled.a`
  margin-top: 1rem;
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: white;
  background-color: ${variables.accentColorPositive};
  border-radius: 0.375rem;
  text-decoration: none;
  transition: background-color 0.2s;

  &:hover {
    background-color: #00a86b;
  }
`;

const ErrorToast = styled.div`
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  background-color: rgba(220, 53, 69, 0.1);
  border: 1px solid rgba(220, 53, 69, 0.3);
  border-radius: 0.5rem;
  padding: 1rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #dc3545;
`;

// ============================================================================
// Helper Components
// ============================================================================

function ThreatLevelIndicator({ level }: { level: string }) {
  const levels: Record<string, { color: string; bars: number }> = {
    low: { color: '#00c97d', bars: 1 },
    medium: { color: '#f8be34', bars: 2 },
    high: { color: '#ff6b35', bars: 3 },
    critical: { color: '#dc3545', bars: 4 },
  };

  const config = levels[level] || levels.medium;

  return (
    <ThreatLevelContainer>
      {[1, 2, 3, 4].map((bar) => (
        <ThreatBar
          key={bar}
          $active={bar <= config.bars}
          $color={config.color}
          $height={(bar + 2) * 3}
        />
      ))}
      <ThreatLabel>{level}</ThreatLabel>
    </ThreatLevelContainer>
  );
}

function ScenarioCard({
  scenario,
  onLaunch,
  isLaunching,
}: {
  scenario: AttackScenario;
  onLaunch: (scenarioId: string) => void;
  isLaunching: boolean;
}) {
  const icons: Record<string, React.ElementType> = {
    apt_intrusion: ShieldExclamationIcon,
    ransomware_attack: BoltIcon,
    insider_threat: ExclamationTriangleIcon,
    web_app_attack: ShieldExclamationIcon,
    credential_theft: ShieldExclamationIcon,
  };

  const Icon = icons[scenario.id] || ShieldExclamationIcon;

  return (
    <Card>
      <CardBody>
        <CardHeader>
          <CardHeaderLeft>
            <IconBox>
              <Icon />
            </IconBox>
            <CardTitleGroup>
              <CardTitle>{scenario.name}</CardTitle>
              <ThreatLevelIndicator level={scenario.threat_level} />
            </CardTitleGroup>
          </CardHeaderLeft>
        </CardHeader>

        <CardDescription>{scenario.description}</CardDescription>

        <DurationInfo>
          <ClockIcon />
          <span>~{scenario.estimated_duration_minutes} minutes</span>
        </DurationInfo>

        <ObjectivesSection>
          <ObjectivesTitle>Objectives</ObjectivesTitle>
          <ObjectivesList>
            {scenario.objectives.map((objective, index) => (
              <ObjectiveItem key={index}>
                <CheckCircleIcon />
                <span style={{ textTransform: 'capitalize' }}>{objective.replace(/_/g, ' ')}</span>
              </ObjectiveItem>
            ))}
          </ObjectivesList>
        </ObjectivesSection>
      </CardBody>

      <CardFooter>
        <LaunchButton onClick={() => onLaunch(scenario.id)} disabled={isLaunching}>
          <BoltIcon />
          {isLaunching ? 'Launching...' : 'Launch Scenario'}
        </LaunchButton>
      </CardFooter>
    </Card>
  );
}

function LaunchModal({
  isOpen,
  onClose,
  instances,
  onConfirm,
  isLaunching,
  basePath,
}: {
  isOpen: boolean;
  onClose: () => void;
  instances: Instance[];
  onConfirm: (instanceId: string) => void;
  isLaunching: boolean;
  basePath: string;
}) {
  const [selectedInstance, setSelectedInstance] = useState<string>('');

  const runningInstances = instances.filter((i) => i.status === 'running');

  if (!isOpen) return null;

  return (
    <ModalOverlay>
      <ModalContainer>
        <ModalBackdrop onClick={onClose} />

        <ModalContent>
          <ModalTitle>Select Target Instance</ModalTitle>

          {runningInstances.length === 0 ? (
            <EmptyState>
              <EmptyIcon>
                <ServerIcon />
              </EmptyIcon>
              <EmptyTitle>No running instances</EmptyTitle>
              <EmptyDescription>
                You need at least one running Splunk instance to launch an attack scenario.
              </EmptyDescription>
              <CreateInstanceLink href={`${basePath}/instances/new`}>
                Create Instance
              </CreateInstanceLink>
            </EmptyState>
          ) : (
            <>
              <InstanceList>
                {runningInstances.map((instance) => (
                  <InstanceOption
                    key={instance.id}
                    $selected={selectedInstance === instance.id}
                  >
                    <input
                      type="radio"
                      name="instance"
                      value={instance.id}
                      checked={selectedInstance === instance.id}
                      onChange={(e) => setSelectedInstance(e.target.value)}
                    />
                    <InstanceInfo>
                      <InstanceName>{instance.name}</InstanceName>
                      <InstanceId>{instance.id}</InstanceId>
                    </InstanceInfo>
                  </InstanceOption>
                ))}
              </InstanceList>

              <ModalButtonGroup>
                <CancelButton onClick={onClose}>Cancel</CancelButton>
                <ConfirmButton
                  onClick={() => onConfirm(selectedInstance)}
                  disabled={!selectedInstance || isLaunching}
                >
                  <BoltIcon />
                  {isLaunching ? 'Launching...' : 'Launch Attack'}
                </ConfirmButton>
              </ModalButtonGroup>
            </>
          )}
        </ModalContent>
      </ModalContainer>
    </ModalOverlay>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function Scenarios() {
  const { toPath, basePath } = useTenantPath();
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);

  const { data: scenarios = [], isLoading: loadingScenarios, error } = useQuery({
    queryKey: ['scenarios'],
    queryFn: attacksApi.listScenarios,
  });

  const { data: instances = [] } = useQuery({
    queryKey: ['instances'],
    queryFn: instancesApi.list,
  });

  const executeMutation = useMutation({
    mutationFn: ({ scenarioId, instanceId }: { scenarioId: string; instanceId: string }) =>
      attacksApi.executeScenario(scenarioId, instanceId),
    onSuccess: (campaign) => {
      setSelectedScenario(null);
      window.location.href = toPath(`attacks/campaigns/${campaign.id}`);
    },
  });

  const handleLaunch = (scenarioId: string) => {
    setSelectedScenario(scenarioId);
  };

  const handleConfirmLaunch = (instanceId: string) => {
    if (selectedScenario) {
      executeMutation.mutate({ scenarioId: selectedScenario, instanceId });
    }
  };

  if (loadingScenarios) {
    return (
      <LoadingContainer>
        <Spinner />
      </LoadingContainer>
    );
  }

  if (error) {
    return (
      <ErrorBanner>
        <ExclamationTriangleIcon style={{ width: '1.25rem', height: '1.25rem' }} />
        <span>Failed to load scenarios</span>
      </ErrorBanner>
    );
  }

  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>Attack Scenarios</PageTitle>
        <PageDescription>
          Pre-built attack scenarios based on real-world TTPs (Tactics, Techniques, and Procedures)
        </PageDescription>
      </PageHeader>

      {/* Info banner */}
      <InfoBanner>
        <InfoIcon>
          <ShieldExclamationIcon style={{ width: '1.25rem', height: '1.25rem' }} />
        </InfoIcon>
        <InfoContent>
          <InfoTitle>About Attack Scenarios</InfoTitle>
          <InfoText>
            These scenarios simulate real attack patterns mapped to the MITRE ATT&CK framework.
            Each scenario generates realistic security logs for detection engineering and SOC training.
            Scenarios are inspired by the Boss of the SOC (BOTS) dataset format.
          </InfoText>
        </InfoContent>
      </InfoBanner>

      {/* Scenarios grid */}
      {scenarios.length === 0 ? (
        <EmptyState>
          <EmptyIcon>
            <ShieldExclamationIcon />
          </EmptyIcon>
          <EmptyTitle>No scenarios available</EmptyTitle>
          <EmptyDescription>
            Attack scenarios are not configured yet.
          </EmptyDescription>
        </EmptyState>
      ) : (
        <ScenarioGrid>
          {scenarios.map((scenario) => (
            <ScenarioCard
              key={scenario.id}
              scenario={scenario}
              onLaunch={handleLaunch}
              isLaunching={executeMutation.isPending && selectedScenario === scenario.id}
            />
          ))}
        </ScenarioGrid>
      )}

      {/* Launch Modal */}
      <LaunchModal
        isOpen={selectedScenario !== null}
        onClose={() => setSelectedScenario(null)}
        instances={instances}
        onConfirm={handleConfirmLaunch}
        isLaunching={executeMutation.isPending}
        basePath={basePath}
      />

      {/* Error toast */}
      {executeMutation.isError && (
        <ErrorToast>
          <ExclamationTriangleIcon style={{ width: '1.25rem', height: '1.25rem' }} />
          <span>Failed to launch scenario. Please try again.</span>
        </ErrorToast>
      )}
    </PageContainer>
  );
}
