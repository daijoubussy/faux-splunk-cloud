/**
 * Dashboard overview page showing instance and campaign stats.
 */

import React from 'react';
import { Content } from '@backstage/core-components';
import { useApi } from '@backstage/core-plugin-api';
import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardBody } from '@splunk/react-ui/Card';
import { Heading } from '@splunk/react-ui/Heading';
import { fauxSplunkCloudApiRef } from '../../api';

export function DashboardPage() {
  const api = useApi(fauxSplunkCloudApiRef);

  const { data: instances = [], isLoading: instancesLoading } = useQuery({
    queryKey: ['fsc-instances'],
    queryFn: () => api.listInstances(),
  });

  const { data: campaigns = [], isLoading: campaignsLoading } = useQuery({
    queryKey: ['fsc-campaigns'],
    queryFn: () => api.listCampaigns(),
  });

  const runningInstances = instances.filter(i => i.status === 'running').length;
  const activeCampaigns = campaigns.filter(c => c.status === 'running').length;

  if (instancesLoading || campaignsLoading) {
    return (
      <Content>
        <div>Loading dashboard...</div>
      </Content>
    );
  }

  return (
    <Content>
      <Heading level={2}>Overview</Heading>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginTop: '1rem' }}>
        <Card>
          <CardHeader title="Total Instances" />
          <CardBody>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{instances.length}</div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Running" />
          <CardBody>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'green' }}>
              {runningInstances}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Active Campaigns" />
          <CardBody>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'red' }}>
              {activeCampaigns}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Total Campaigns" />
          <CardBody>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{campaigns.length}</div>
          </CardBody>
        </Card>
      </div>

      <Heading level={3} style={{ marginTop: '2rem' }}>Recent Instances</Heading>
      {instances.slice(0, 5).map(instance => (
        <Card key={instance.id} style={{ marginBottom: '0.5rem' }}>
          <CardBody>
            <strong>{instance.name}</strong> - {instance.status}
          </CardBody>
        </Card>
      ))}

      {instances.length === 0 && (
        <Card>
          <CardBody>No instances yet. Create one to get started.</CardBody>
        </Card>
      )}
    </Content>
  );
}

export default DashboardPage;
