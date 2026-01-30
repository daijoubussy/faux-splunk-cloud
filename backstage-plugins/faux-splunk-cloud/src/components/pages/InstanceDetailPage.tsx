/**
 * Instance detail page showing endpoints, credentials, and logs.
 */

import React from 'react';
import { useParams } from 'react-router-dom';
import { Content } from '@backstage/core-components';
import { useApi } from '@backstage/core-plugin-api';
import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardBody } from '@splunk/react-ui/Card';
import { Heading } from '@splunk/react-ui/Heading';
import { Button } from '@splunk/react-ui/Button';
import { Badge } from '@splunk/react-ui/Badge';
import { fauxSplunkCloudApiRef } from '../../api';

export function InstanceDetailPage() {
  const { instanceId } = useParams<{ instanceId: string }>();
  const api = useApi(fauxSplunkCloudApiRef);

  const { data: instance, isLoading, error } = useQuery({
    queryKey: ['fsc-instance', instanceId],
    queryFn: () => api.getInstance(instanceId!),
    enabled: !!instanceId,
    refetchInterval: 5000,
  });

  if (isLoading) {
    return <Content>Loading instance details...</Content>;
  }

  if (error || !instance) {
    return <Content>Instance not found</Content>;
  }

  return (
    <Content>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <Heading level={2}>{instance.name}</Heading>
        <Badge
          appearance={instance.status === 'running' ? 'success' : 'default'}
          label={instance.status}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginTop: '1rem' }}>
        <Card>
          <CardHeader title="Configuration" />
          <CardBody>
            <dl>
              <dt>Topology</dt>
              <dd>{instance.config.topology}</dd>
              <dt>Splunk Version</dt>
              <dd>{instance.config.splunk_version}</dd>
              <dt>Memory</dt>
              <dd>{instance.config.memory_mb} MB</dd>
              <dt>CPU Cores</dt>
              <dd>{instance.config.cpu_cores}</dd>
            </dl>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Endpoints" />
          <CardBody>
            <dl>
              {instance.endpoints.web_url && (
                <>
                  <dt>Web UI</dt>
                  <dd>
                    <a href={instance.endpoints.web_url} target="_blank" rel="noopener noreferrer">
                      {instance.endpoints.web_url}
                    </a>
                  </dd>
                </>
              )}
              {instance.endpoints.api_url && (
                <>
                  <dt>REST API</dt>
                  <dd>{instance.endpoints.api_url}</dd>
                </>
              )}
              {instance.endpoints.hec_url && (
                <>
                  <dt>HEC</dt>
                  <dd>{instance.endpoints.hec_url}</dd>
                </>
              )}
            </dl>
          </CardBody>
        </Card>

        {instance.credentials && (
          <Card>
            <CardHeader title="Credentials" />
            <CardBody>
              <dl>
                <dt>Username</dt>
                <dd>{instance.credentials.admin_username}</dd>
                <dt>Password</dt>
                <dd>
                  <code>{instance.credentials.admin_password}</code>
                </dd>
                {instance.credentials.hec_token && (
                  <>
                    <dt>HEC Token</dt>
                    <dd>
                      <code>{instance.credentials.hec_token}</code>
                    </dd>
                  </>
                )}
              </dl>
            </CardBody>
          </Card>
        )}

        <Card>
          <CardHeader title="Lifecycle" />
          <CardBody>
            <dl>
              <dt>Created</dt>
              <dd>{new Date(instance.created_at).toLocaleString()}</dd>
              <dt>Expires</dt>
              <dd>{new Date(instance.expires_at).toLocaleString()}</dd>
            </dl>
            <Button appearance="secondary" style={{ marginTop: '1rem' }}>
              Extend TTL (+24h)
            </Button>
          </CardBody>
        </Card>
      </div>
    </Content>
  );
}

export default InstanceDetailPage;
