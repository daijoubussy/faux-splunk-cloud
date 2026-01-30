import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';
import {
  KeyIcon,
  CheckCircleIcon,
  XCircleIcon,
  LockClosedIcon,
  ServerIcon,
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
  $status: 'success' | 'error' | 'warning';
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

// ============================================================================
// API
// ============================================================================

async function fetchVaultStatus() {
  const response = await fetch('/api/v1/vault/status', {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error('Failed to fetch Vault status');
  }
  return response.json();
}

async function fetchVaultHealth() {
  const response = await fetch('/api/v1/vault/health');
  if (!response.ok) {
    throw new Error('Failed to fetch Vault health');
  }
  return response.json();
}

// ============================================================================
// Components
// ============================================================================

function VaultStatus() {
  const { data: status, isLoading, error } = useQuery({
    queryKey: ['vault-status'],
    queryFn: fetchVaultStatus,
    refetchInterval: 10000,
  });

  const { data: health } = useQuery({
    queryKey: ['vault-health'],
    queryFn: fetchVaultHealth,
    refetchInterval: 5000,
  });

  if (isLoading) {
    return (
      <Card>
        <CardTitle>
          <ServerIcon />
          Vault Status
        </CardTitle>
        <EmptyState>Loading Vault status...</EmptyState>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardTitle>
          <ServerIcon />
          Vault Status
        </CardTitle>
        <EmptyState>Failed to load Vault status. Make sure you have admin privileges.</EmptyState>
      </Card>
    );
  }

  return (
    <Card>
      <CardTitle>
        <ServerIcon />
        Vault Status
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
          <StatusIndicator $status={status?.initialized ? 'success' : 'error'}>
            {status?.initialized ? <CheckCircleIcon /> : <XCircleIcon />}
          </StatusIndicator>
          <div>
            <StatusLabel>Initialized</StatusLabel>
            <StatusValue>{status?.initialized ? 'Yes' : 'No'}</StatusValue>
          </div>
        </StatusItem>
        <StatusItem>
          <StatusIndicator $status={status?.sealed ? 'error' : 'success'}>
            <LockClosedIcon />
          </StatusIndicator>
          <div>
            <StatusLabel>Seal Status</StatusLabel>
            <StatusValue>{status?.sealed ? 'Sealed' : 'Unsealed'}</StatusValue>
          </div>
        </StatusItem>
        <StatusItem>
          <StatusIndicator $status={status?.authenticated ? 'success' : 'warning'}>
            <KeyIcon />
          </StatusIndicator>
          <div>
            <StatusLabel>API Auth</StatusLabel>
            <StatusValue>{status?.authenticated ? 'Connected' : 'Disconnected'}</StatusValue>
          </div>
        </StatusItem>
      </StatusGrid>
      {status?.version && (
        <VersionText>
          Version: {status.version}
          {status.cluster_name && ` | Cluster: ${status.cluster_name}`}
        </VersionText>
      )}
    </Card>
  );
}

function VaultSecretsTab() {
  return (
    <Card>
      <CardTitle>
        <KeyIcon />
        Secrets Management
      </CardTitle>
      <Description>
        Use the Vault UI to manage secrets, policies, and authentication methods.
        Click the "Vault UI" tab to access the full Vault interface.
      </Description>
    </Card>
  );
}

function VaultUITab() {
  return (
    <IframeContainer>
      <IframeStyled
        src="/vault/ui/"
        title="Vault UI"
      />
    </IframeContainer>
  );
}

// ============================================================================
// Main Component
// ============================================================================

type TabType = 'status' | 'secrets' | 'ui';

export default function VaultAdmin() {
  const [activeTab, setActiveTab] = useState<TabType>('status');

  return (
    <Container>
      <Header>
        <Title>
          <KeyIcon />
          Vault Administration
        </Title>
        <Description>
          Manage secrets, encryption keys, and access policies with HashiCorp Vault.
        </Description>
      </Header>

      <TabBar>
        <Tab $active={activeTab === 'status'} onClick={() => setActiveTab('status')}>
          Status
        </Tab>
        <Tab $active={activeTab === 'secrets'} onClick={() => setActiveTab('secrets')}>
          Secrets
        </Tab>
        <Tab $active={activeTab === 'ui'} onClick={() => setActiveTab('ui')}>
          Vault UI
        </Tab>
      </TabBar>

      {activeTab === 'status' && <VaultStatus />}
      {activeTab === 'secrets' && <VaultSecretsTab />}
      {activeTab === 'ui' && <VaultUITab />}
    </Container>
  );
}
