/**
 * Entity card component for displaying Faux Splunk Cloud instance status
 * on Backstage entity pages.
 */

import React from 'react';
import { useEntity } from '@backstage/plugin-catalog-react';
import { useApi } from '@backstage/core-plugin-api';
import { useQuery } from '@tanstack/react-query';
import { InfoCard, Progress, StatusOK, StatusError, StatusWarning, StatusPending } from '@backstage/core-components';
import { Card, CardBody } from '@splunk/react-ui/Card';
import { Badge } from '@splunk/react-ui/Badge';
import { Button } from '@splunk/react-ui/Button';
import { fauxSplunkCloudApiRef } from '../api';
import { Instance, InstanceStatus } from '../types';

const ANNOTATION_INSTANCE_ID = 'faux-splunk-cloud.io/instance-id';
const ANNOTATION_INSTANCE_NAME = 'faux-splunk-cloud.io/instance-name';

function StatusIcon({ status }: { status: InstanceStatus }) {
  switch (status) {
    case 'running':
      return <StatusOK />;
    case 'stopped':
    case 'destroyed':
      return <StatusError />;
    case 'creating':
    case 'starting':
    case 'stopping':
      return <StatusPending />;
    case 'error':
      return <StatusError />;
    default:
      return <StatusWarning />;
  }
}

export function EntityFauxSplunkCloudCard() {
  const { entity } = useEntity();
  const api = useApi(fauxSplunkCloudApiRef);

  const instanceId = entity.metadata.annotations?.[ANNOTATION_INSTANCE_ID];
  const instanceName = entity.metadata.annotations?.[ANNOTATION_INSTANCE_NAME];

  const { data: instance, isLoading, error } = useQuery({
    queryKey: ['fsc-entity-instance', instanceId, instanceName],
    queryFn: async () => {
      if (instanceId) {
        return api.getInstance(instanceId);
      }
      if (instanceName) {
        const instances = await api.listInstances();
        return instances.find((i: Instance) => i.name === instanceName);
      }
      return null;
    },
    enabled: !!(instanceId || instanceName),
    refetchInterval: 10000,
  });

  if (!instanceId && !instanceName) {
    return (
      <InfoCard title="Faux Splunk Cloud">
        <p>
          No Faux Splunk Cloud instance associated with this entity.
        </p>
        <p style={{ fontSize: '0.875rem', color: '#666' }}>
          Add annotation <code>{ANNOTATION_INSTANCE_ID}</code> or{' '}
          <code>{ANNOTATION_INSTANCE_NAME}</code> to link an instance.
        </p>
      </InfoCard>
    );
  }

  if (isLoading) {
    return (
      <InfoCard title="Faux Splunk Cloud">
        <Progress />
      </InfoCard>
    );
  }

  if (error || !instance) {
    return (
      <InfoCard title="Faux Splunk Cloud">
        <StatusError />
        <span style={{ marginLeft: '0.5rem' }}>
          Instance not found: {instanceId || instanceName}
        </span>
      </InfoCard>
    );
  }

  const formatExpiration = (expiresAt: string) => {
    const expiry = new Date(expiresAt);
    const now = new Date();
    const hoursRemaining = Math.max(0, (expiry.getTime() - now.getTime()) / (1000 * 60 * 60));

    if (hoursRemaining < 1) {
      return `${Math.round(hoursRemaining * 60)} minutes`;
    }
    return `${Math.round(hoursRemaining)} hours`;
  };

  return (
    <InfoCard
      title="Faux Splunk Cloud"
      subheader={instance.name}
      action={
        <Badge
          appearance={instance.status === 'running' ? 'success' : 'default'}
          label={instance.status}
        />
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {/* Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <StatusIcon status={instance.status} />
          <span>
            {instance.status === 'running' ? 'Instance is running' : `Status: ${instance.status}`}
          </span>
        </div>

        {/* Configuration */}
        <div>
          <strong>Configuration:</strong>
          <ul style={{ margin: '0.25rem 0 0 1.5rem', padding: 0 }}>
            <li>Topology: {instance.config.topology}</li>
            <li>Version: {instance.config.splunk_version}</li>
            <li>Memory: {instance.config.memory_mb} MB</li>
          </ul>
        </div>

        {/* Expiration */}
        <div>
          <strong>Expires in:</strong> {formatExpiration(instance.expires_at)}
        </div>

        {/* Endpoints */}
        {instance.status === 'running' && instance.endpoints.web_url && (
          <div>
            <Button
              appearance="secondary"
              onClick={() => window.open(instance.endpoints.web_url, '_blank')}
            >
              Open Splunk Web
            </Button>
          </div>
        )}

        {/* Credentials */}
        {instance.credentials && (
          <div style={{ fontSize: '0.875rem', color: '#666' }}>
            <strong>Quick Access:</strong>{' '}
            <code>{instance.credentials.admin_username}</code> /{' '}
            <code>{instance.credentials.admin_password}</code>
          </div>
        )}

        {/* Link to full details */}
        <div>
          <Button
            appearance="primary"
            onClick={() => {
              window.location.href = `/faux-splunk-cloud/instances/${instance.id}`;
            }}
          >
            View Details
          </Button>
        </div>
      </div>
    </InfoCard>
  );
}

export default EntityFauxSplunkCloudCard;
