/**
 * Attack simulation page for managing threat actors and campaigns.
 */

import React, { useState } from 'react';
import { Content } from '@backstage/core-components';
import { useApi } from '@backstage/core-plugin-api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Table, HeadCell, Row, Cell, Body, Head } from '@splunk/react-ui/Table';
import { Card, CardHeader, CardBody } from '@splunk/react-ui/Card';
import { Heading } from '@splunk/react-ui/Heading';
import { Button } from '@splunk/react-ui/Button';
import { Badge } from '@splunk/react-ui/Badge';
import { Modal, ModalHeader, ModalBody, ModalFooter } from '@splunk/react-ui/Modal';
import { Select } from '@splunk/react-ui/Select';
import { fauxSplunkCloudApiRef } from '../../api';
import { ThreatActor, AttackCampaign, AttackScenario, Instance } from '../../types';

type ThreatLevelAppearance = 'info' | 'warning' | 'error' | 'default';

function ThreatLevelBadge({ level }: { level: string }) {
  const appearances: Record<string, ThreatLevelAppearance> = {
    nation_state: 'error',
    organized_crime: 'error',
    hacktivist: 'warning',
    insider: 'warning',
    script_kiddie: 'info',
  };

  return (
    <Badge
      appearance={appearances[level] || 'default'}
      label={level.replace('_', ' ')}
    />
  );
}

function CampaignStatusBadge({ status }: { status: string }) {
  const appearances: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
    running: 'success',
    pending: 'warning',
    paused: 'warning',
    completed: 'default',
    detected: 'error',
    failed: 'error',
  };

  return (
    <Badge
      appearance={appearances[status] || 'default'}
      label={status}
    />
  );
}

export function AttacksPage() {
  const api = useApi(fauxSplunkCloudApiRef);
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedThreatActor, setSelectedThreatActor] = useState<string>('');
  const [selectedInstance, setSelectedInstance] = useState<string>('');

  const { data: threatActors = [], isLoading: loadingActors } = useQuery({
    queryKey: ['fsc-threat-actors'],
    queryFn: () => api.listThreatActors(),
  });

  const { data: campaigns = [], isLoading: loadingCampaigns } = useQuery({
    queryKey: ['fsc-campaigns'],
    queryFn: () => api.listCampaigns(),
    refetchInterval: 5000,
  });

  const { data: scenarios = [] } = useQuery({
    queryKey: ['fsc-scenarios'],
    queryFn: () => api.listScenarios(),
  });

  const { data: instances = [] } = useQuery({
    queryKey: ['fsc-instances'],
    queryFn: () => api.listInstances(),
  });

  const createCampaign = useMutation({
    mutationFn: (params: { threatActorId: string; instanceId: string }) =>
      api.createCampaign(params.threatActorId, params.instanceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fsc-campaigns'] });
      setShowCreateModal(false);
    },
  });

  const startCampaign = useMutation({
    mutationFn: (id: string) => api.startCampaign(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fsc-campaigns'] }),
  });

  const pauseCampaign = useMutation({
    mutationFn: (id: string) => api.pauseCampaign(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fsc-campaigns'] }),
  });

  const runningInstances = instances.filter((i: Instance) => i.status === 'running');

  if (loadingActors || loadingCampaigns) {
    return <Content>Loading attack simulation data...</Content>;
  }

  return (
    <Content>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* Threat Actors Section */}
        <Card>
          <CardHeader title="Threat Actors" />
          <CardBody>
            <Table stripeRows>
              <Head>
                <HeadCell>Name</HeadCell>
                <HeadCell>Threat Level</HeadCell>
                <HeadCell>Techniques</HeadCell>
              </Head>
              <Body>
                {threatActors.map((actor: ThreatActor) => (
                  <Row key={actor.id}>
                    <Cell>{actor.name}</Cell>
                    <Cell>
                      <ThreatLevelBadge level={actor.threat_level} />
                    </Cell>
                    <Cell>{actor.techniques.length}</Cell>
                  </Row>
                ))}
              </Body>
            </Table>
          </CardBody>
        </Card>

        {/* Attack Scenarios Section */}
        <Card>
          <CardHeader title="Predefined Scenarios" />
          <CardBody>
            <Table stripeRows>
              <Head>
                <HeadCell>Scenario</HeadCell>
                <HeadCell>Threat Level</HeadCell>
                <HeadCell>Duration</HeadCell>
              </Head>
              <Body>
                {scenarios.map((scenario: AttackScenario) => (
                  <Row key={scenario.id}>
                    <Cell>{scenario.name}</Cell>
                    <Cell>
                      <ThreatLevelBadge level={scenario.threat_level} />
                    </Cell>
                    <Cell>{scenario.estimated_duration_minutes} min</Cell>
                  </Row>
                ))}
              </Body>
            </Table>
          </CardBody>
        </Card>
      </div>

      {/* Active Campaigns Section */}
      <Card style={{ marginTop: '1.5rem' }}>
        <CardHeader
          title="Attack Campaigns"
          actions={
            <Button
              appearance="primary"
              onClick={() => setShowCreateModal(true)}
              disabled={runningInstances.length === 0}
            >
              New Campaign
            </Button>
          }
        />
        <CardBody>
          {campaigns.length === 0 ? (
            <p>No campaigns. Create one to start attack simulation.</p>
          ) : (
            <Table stripeRows>
              <Head>
                <HeadCell>ID</HeadCell>
                <HeadCell>Target</HeadCell>
                <HeadCell>Threat Actor</HeadCell>
                <HeadCell>Status</HeadCell>
                <HeadCell>Phase</HeadCell>
                <HeadCell>Progress</HeadCell>
                <HeadCell>Actions</HeadCell>
              </Head>
              <Body>
                {campaigns.map((campaign: AttackCampaign) => (
                  <Row key={campaign.id}>
                    <Cell>{campaign.id.slice(0, 8)}...</Cell>
                    <Cell>{campaign.target_instance_id.slice(0, 8)}...</Cell>
                    <Cell>{campaign.threat_actor_id}</Cell>
                    <Cell>
                      <CampaignStatusBadge status={campaign.status} />
                    </Cell>
                    <Cell>{campaign.current_phase || 'N/A'}</Cell>
                    <Cell>
                      {campaign.completed_steps}/{campaign.total_steps}
                    </Cell>
                    <Cell>
                      {campaign.status === 'pending' && (
                        <Button
                          appearance="primary"
                          onClick={() => startCampaign.mutate(campaign.id)}
                        >
                          Start
                        </Button>
                      )}
                      {campaign.status === 'running' && (
                        <Button
                          appearance="secondary"
                          onClick={() => pauseCampaign.mutate(campaign.id)}
                        >
                          Pause
                        </Button>
                      )}
                      {campaign.status === 'paused' && (
                        <Button
                          appearance="primary"
                          onClick={() => startCampaign.mutate(campaign.id)}
                        >
                          Resume
                        </Button>
                      )}
                    </Cell>
                  </Row>
                ))}
              </Body>
            </Table>
          )}
        </CardBody>
      </Card>

      {/* Create Campaign Modal */}
      {showCreateModal && (
        <Modal onRequestClose={() => setShowCreateModal(false)}>
          <ModalHeader title="Create Attack Campaign" />
          <ModalBody>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <Heading level={4}>Target Instance</Heading>
                <Select
                  value={selectedInstance}
                  onChange={(e, { value }) => setSelectedInstance(value as string)}
                >
                  <Select.Option value="" label="Select instance..." />
                  {runningInstances.map((instance: Instance) => (
                    <Select.Option
                      key={instance.id}
                      value={instance.id}
                      label={instance.name}
                    />
                  ))}
                </Select>
              </div>
              <div>
                <Heading level={4}>Threat Actor</Heading>
                <Select
                  value={selectedThreatActor}
                  onChange={(e, { value }) => setSelectedThreatActor(value as string)}
                >
                  <Select.Option value="" label="Select threat actor..." />
                  {threatActors.map((actor: ThreatActor) => (
                    <Select.Option
                      key={actor.id}
                      value={actor.id}
                      label={`${actor.name} (${actor.threat_level})`}
                    />
                  ))}
                </Select>
              </div>
            </div>
          </ModalBody>
          <ModalFooter>
            <Button
              appearance="secondary"
              onClick={() => setShowCreateModal(false)}
            >
              Cancel
            </Button>
            <Button
              appearance="primary"
              onClick={() =>
                createCampaign.mutate({
                  threatActorId: selectedThreatActor,
                  instanceId: selectedInstance,
                })
              }
              disabled={!selectedThreatActor || !selectedInstance}
            >
              Create Campaign
            </Button>
          </ModalFooter>
        </Modal>
      )}
    </Content>
  );
}

export default AttacksPage;
