import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';
import { instancesApi } from '../api';
import { useTenantPath } from '../hooks/useTenantPath';
import type { InstanceCreate } from '../types';

// ============================================================================
// Styled Components
// ============================================================================

const PageContainer = styled.div`
  max-width: 48rem;
  margin: 0 auto;
`;

const PageHeader = styled.div`
  margin-bottom: 1.5rem;
`;

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

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
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
`;

const CardTitle = styled.h2`
  font-size: 1.125rem;
  font-weight: 600;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0 0 1rem;
`;

const FormGroup = styled.div`
  margin-top: 1rem;

  &:first-of-type {
    margin-top: 0;
  }
`;

const Label = styled.label`
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin-bottom: 0.25rem;
`;

const Input = styled.input`
  display: block;
  width: 100%;
  padding: 0.625rem 0.75rem;
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
  transition: border-color 0.2s, box-shadow 0.2s;

  &:focus {
    outline: none;
    border-color: ${variables.accentColorPositive};
    box-shadow: 0 0 0 2px rgba(0, 201, 125, 0.2);
  }

  &::placeholder {
    color: ${pick({
      prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
    })};
  }
`;

const SmallInput = styled(Input)`
  width: 8rem;
`;

const Select = styled.select`
  display: block;
  width: 100%;
  padding: 0.625rem 0.75rem;
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
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;

  &:focus {
    outline: none;
    border-color: ${variables.accentColorPositive};
    box-shadow: 0 0 0 2px rgba(0, 201, 125, 0.2);
  }
`;

const HelpText = styled.p`
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const TopologyGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;

  @media (min-width: 640px) {
    grid-template-columns: repeat(2, 1fr);
  }
`;

interface TopologyOptionProps {
  $selected: boolean;
}

const TopologyOption = styled.label<TopologyOptionProps>`
  display: flex;
  flex-direction: column;
  position: relative;
  cursor: pointer;
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid ${props => props.$selected
    ? variables.accentColorPositive
    : pick({ prisma: { dark: variables.borderColor, light: variables.borderColor } })};
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
  transition: border-color 0.2s, box-shadow 0.2s;

  ${props => props.$selected && `
    box-shadow: 0 0 0 2px rgba(0, 201, 125, 0.2);
  `}

  &:hover {
    border-color: ${variables.accentColorPositive};
  }

  input {
    position: absolute;
    opacity: 0;
    pointer-events: none;
  }
`;

const TopologyName = styled.span`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

const TopologyDescription = styled.span`
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const TopologyResources = styled.span`
  margin-top: 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

const CheckboxGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const CheckboxLabel = styled.label`
  display: flex;
  align-items: center;
  cursor: pointer;
`;

const Checkbox = styled.input`
  width: 1rem;
  height: 1rem;
  margin-right: 0.5rem;
  border-radius: 0.25rem;
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
  cursor: pointer;
  accent-color: ${variables.accentColorPositive};
`;

const CheckboxText = styled.span`
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

const TwoColumnGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;

  @media (min-width: 640px) {
    grid-template-columns: repeat(2, 1fr);
  }
`;

const ButtonGroup = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
`;

const PrimaryButton = styled.button`
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

  &:hover:not(:disabled) {
    background-color: #00a86b;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const SecondaryButton = styled.button`
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
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }
`;

// ============================================================================
// Config
// ============================================================================

const topologies = [
  {
    id: 'standalone',
    name: 'Standalone',
    description: 'Single Splunk instance. Quick startup, minimal resources.',
    resources: '~2GB RAM',
  },
  {
    id: 'distributed_minimal',
    name: 'Distributed Minimal',
    description: 'Separate Search Head and Indexer. Better for testing distributed features.',
    resources: '~4GB RAM',
  },
  {
    id: 'distributed_clustered',
    name: 'Distributed Clustered',
    description: 'Search Head Cluster + Indexer Cluster. Production-like setup.',
    resources: '~8GB RAM',
  },
  {
    id: 'victoria_full',
    name: 'Victoria Full',
    description: 'Full Victoria Experience with all components. Most realistic.',
    resources: '~12GB RAM',
  },
];

// ============================================================================
// Main Component
// ============================================================================

export default function CreateInstance() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toPath } = useTenantPath();

  const [formData, setFormData] = useState({
    name: '',
    topology: 'standalone',
    ttl_hours: 24,
    enable_hec: true,
    enable_realtime_search: true,
    create_default_indexes: true,
    memory_mb: 2048,
    cpu_cores: 1.0,
  });

  const createMutation = useMutation({
    mutationFn: (data: InstanceCreate) => instancesApi.create(data),
    onSuccess: (instance) => {
      toast.success('Instance created! Starting...');
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      navigate(toPath(`instances/${instance.id}`));
    },
    onError: (err: Error) => {
      toast.error(`Failed to create instance: ${err.message}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.match(/^[a-z][a-z0-9-]*[a-z0-9]$/)) {
      toast.error('Name must be lowercase, alphanumeric, and can contain hyphens');
      return;
    }

    createMutation.mutate({
      name: formData.name,
      config: {
        topology: formData.topology as InstanceCreate['config']['topology'],
        enable_hec: formData.enable_hec,
        enable_realtime_search: formData.enable_realtime_search,
        create_default_indexes: formData.create_default_indexes,
        memory_mb: formData.memory_mb,
        cpu_cores: formData.cpu_cores,
      },
      ttl_hours: formData.ttl_hours,
    });
  };

  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>Create New Instance</PageTitle>
        <PageDescription>
          Provision an ephemeral Splunk Cloud Victoria instance
        </PageDescription>
      </PageHeader>

      <Form onSubmit={handleSubmit}>
        {/* Name */}
        <Card>
          <CardTitle>Basic Information</CardTitle>

          <FormGroup>
            <Label htmlFor="name">Instance Name</Label>
            <Input
              type="text"
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value.toLowerCase() })}
              placeholder="my-test-splunk"
              pattern="^[a-z][a-z0-9-]*[a-z0-9]$"
              required
            />
            <HelpText>Lowercase letters, numbers, and hyphens only</HelpText>
          </FormGroup>

          <FormGroup>
            <Label htmlFor="ttl">Time to Live (hours)</Label>
            <SmallInput
              type="number"
              id="ttl"
              value={formData.ttl_hours}
              onChange={(e) => setFormData({ ...formData, ttl_hours: parseInt(e.target.value) })}
              min={1}
              max={168}
            />
            <HelpText>
              Instance will be automatically destroyed after this time (max 168 hours / 1 week)
            </HelpText>
          </FormGroup>
        </Card>

        {/* Topology */}
        <Card>
          <CardTitle>Topology</CardTitle>

          <TopologyGrid>
            {topologies.map((topology) => (
              <TopologyOption
                key={topology.id}
                $selected={formData.topology === topology.id}
              >
                <input
                  type="radio"
                  name="topology"
                  value={topology.id}
                  checked={formData.topology === topology.id}
                  onChange={(e) => setFormData({ ...formData, topology: e.target.value })}
                />
                <TopologyName>{topology.name}</TopologyName>
                <TopologyDescription>{topology.description}</TopologyDescription>
                <TopologyResources>{topology.resources}</TopologyResources>
              </TopologyOption>
            ))}
          </TopologyGrid>
        </Card>

        {/* Victoria Options */}
        <Card>
          <CardTitle>Victoria Experience Options</CardTitle>

          <CheckboxGroup>
            <CheckboxLabel>
              <Checkbox
                type="checkbox"
                checked={formData.enable_hec}
                onChange={(e) => setFormData({ ...formData, enable_hec: e.target.checked })}
              />
              <CheckboxText>Enable HTTP Event Collector (HEC)</CheckboxText>
            </CheckboxLabel>

            <CheckboxLabel>
              <Checkbox
                type="checkbox"
                checked={formData.enable_realtime_search}
                onChange={(e) => setFormData({ ...formData, enable_realtime_search: e.target.checked })}
              />
              <CheckboxText>Enable Real-time Search</CheckboxText>
            </CheckboxLabel>

            <CheckboxLabel>
              <Checkbox
                type="checkbox"
                checked={formData.create_default_indexes}
                onChange={(e) => setFormData({ ...formData, create_default_indexes: e.target.checked })}
              />
              <CheckboxText>Create Default Indexes (main, summary, etc.)</CheckboxText>
            </CheckboxLabel>
          </CheckboxGroup>
        </Card>

        {/* Resources */}
        <Card>
          <CardTitle>Resources</CardTitle>

          <TwoColumnGrid>
            <FormGroup>
              <Label htmlFor="memory">Memory (MB)</Label>
              <Select
                id="memory"
                value={formData.memory_mb}
                onChange={(e) => setFormData({ ...formData, memory_mb: parseInt(e.target.value) })}
              >
                <option value={512}>512 MB</option>
                <option value={1024}>1 GB</option>
                <option value={2048}>2 GB</option>
                <option value={4096}>4 GB</option>
                <option value={8192}>8 GB</option>
              </Select>
            </FormGroup>

            <FormGroup>
              <Label htmlFor="cpu">CPU Cores</Label>
              <Select
                id="cpu"
                value={formData.cpu_cores}
                onChange={(e) => setFormData({ ...formData, cpu_cores: parseFloat(e.target.value) })}
              >
                <option value={0.5}>0.5 cores</option>
                <option value={1.0}>1.0 cores</option>
                <option value={2.0}>2.0 cores</option>
                <option value={4.0}>4.0 cores</option>
              </Select>
            </FormGroup>
          </TwoColumnGrid>
        </Card>

        {/* Submit */}
        <ButtonGroup>
          <SecondaryButton type="button" onClick={() => navigate(toPath('instances'))}>
            Cancel
          </SecondaryButton>
          <PrimaryButton type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? 'Creating...' : 'Create Instance'}
          </PrimaryButton>
        </ButtonGroup>
      </Form>
    </PageContainer>
  );
}
