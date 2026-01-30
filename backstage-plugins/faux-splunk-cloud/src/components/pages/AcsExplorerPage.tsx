/**
 * ACS API Explorer page for testing Splunk Admin Config Service operations.
 * Provides an interface to test ACS API compatibility against ephemeral instances.
 */

import React, { useState } from 'react';
import { Content } from '@backstage/core-components';
import { useApi } from '@backstage/core-plugin-api';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Card, CardHeader, CardBody } from '@splunk/react-ui/Card';
import { Heading } from '@splunk/react-ui/Heading';
import { Button } from '@splunk/react-ui/Button';
import { Select } from '@splunk/react-ui/Select';
import { Text } from '@splunk/react-ui/Text';
import { TabLayout } from '@splunk/react-ui/TabLayout';
import { Code } from '@splunk/react-ui/Code';
import { fauxSplunkCloudApiRef } from '../../api';
import { Instance } from '../../types';

interface AcsEndpoint {
  name: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  path: string;
  description: string;
  category: 'indexes' | 'inputs' | 'apps' | 'users' | 'tokens';
}

const ACS_ENDPOINTS: AcsEndpoint[] = [
  // Indexes
  { name: 'List Indexes', method: 'GET', path: '/adminconfig/v2/indexes', description: 'List all indexes', category: 'indexes' },
  { name: 'Create Index', method: 'POST', path: '/adminconfig/v2/indexes', description: 'Create a new index', category: 'indexes' },
  { name: 'Get Index', method: 'GET', path: '/adminconfig/v2/indexes/{name}', description: 'Get index details', category: 'indexes' },
  { name: 'Delete Index', method: 'DELETE', path: '/adminconfig/v2/indexes/{name}', description: 'Delete an index', category: 'indexes' },

  // Inputs (HEC)
  { name: 'List HEC Tokens', method: 'GET', path: '/adminconfig/v2/inputs/http-event-collectors', description: 'List HEC tokens', category: 'inputs' },
  { name: 'Create HEC Token', method: 'POST', path: '/adminconfig/v2/inputs/http-event-collectors', description: 'Create HEC token', category: 'inputs' },
  { name: 'Get HEC Token', method: 'GET', path: '/adminconfig/v2/inputs/http-event-collectors/{name}', description: 'Get HEC token details', category: 'inputs' },
  { name: 'Delete HEC Token', method: 'DELETE', path: '/adminconfig/v2/inputs/http-event-collectors/{name}', description: 'Delete HEC token', category: 'inputs' },

  // Apps
  { name: 'List Apps', method: 'GET', path: '/adminconfig/v2/apps', description: 'List installed apps', category: 'apps' },
  { name: 'Install App', method: 'POST', path: '/adminconfig/v2/apps', description: 'Install an app', category: 'apps' },
  { name: 'Get App', method: 'GET', path: '/adminconfig/v2/apps/{app}', description: 'Get app details', category: 'apps' },
  { name: 'Uninstall App', method: 'DELETE', path: '/adminconfig/v2/apps/{app}', description: 'Uninstall an app', category: 'apps' },

  // Users
  { name: 'List Users', method: 'GET', path: '/adminconfig/v2/access-control/users', description: 'List all users', category: 'users' },
  { name: 'Create User', method: 'POST', path: '/adminconfig/v2/access-control/users', description: 'Create a user', category: 'users' },
  { name: 'Get User', method: 'GET', path: '/adminconfig/v2/access-control/users/{name}', description: 'Get user details', category: 'users' },

  // Tokens
  { name: 'List Auth Tokens', method: 'GET', path: '/adminconfig/v2/tokens', description: 'List authentication tokens', category: 'tokens' },
  { name: 'Create Auth Token', method: 'POST', path: '/adminconfig/v2/tokens', description: 'Create auth token', category: 'tokens' },
];

export function AcsExplorerPage() {
  const api = useApi(fauxSplunkCloudApiRef);
  const [selectedInstance, setSelectedInstance] = useState<string>('');
  const [selectedEndpoint, setSelectedEndpoint] = useState<AcsEndpoint | null>(null);
  const [requestBody, setRequestBody] = useState<string>('{}');
  const [pathParams, setPathParams] = useState<Record<string, string>>({});
  const [response, setResponse] = useState<string>('');
  const [responseStatus, setResponseStatus] = useState<number | null>(null);

  const { data: instances = [], isLoading } = useQuery({
    queryKey: ['fsc-instances'],
    queryFn: () => api.listInstances(),
  });

  const executeRequest = useMutation({
    mutationFn: async () => {
      if (!selectedInstance || !selectedEndpoint) {
        throw new Error('Select an instance and endpoint');
      }

      // Replace path parameters
      let path = selectedEndpoint.path;
      for (const [key, value] of Object.entries(pathParams)) {
        path = path.replace(`{${key}}`, value);
      }

      const result = await api.executeAcsOperation(
        selectedInstance,
        selectedEndpoint.method,
        path,
        selectedEndpoint.method !== 'GET' && selectedEndpoint.method !== 'DELETE'
          ? JSON.parse(requestBody)
          : undefined
      );

      return result;
    },
    onSuccess: (data) => {
      setResponse(JSON.stringify(data, null, 2));
      setResponseStatus(200);
    },
    onError: (error: Error) => {
      setResponse(JSON.stringify({ error: error.message }, null, 2));
      setResponseStatus(400);
    },
  });

  const runningInstances = instances.filter((i: Instance) => i.status === 'running');

  // Extract path parameters from selected endpoint
  const extractPathParams = (path: string): string[] => {
    const matches = path.match(/\{([^}]+)\}/g) || [];
    return matches.map((m) => m.slice(1, -1));
  };

  const handleEndpointSelect = (endpoint: AcsEndpoint) => {
    setSelectedEndpoint(endpoint);
    setResponse('');
    setResponseStatus(null);

    // Reset path params
    const params = extractPathParams(endpoint.path);
    const newPathParams: Record<string, string> = {};
    params.forEach((p) => (newPathParams[p] = ''));
    setPathParams(newPathParams);

    // Set default request body for POST/PUT
    if (endpoint.method === 'POST' || endpoint.method === 'PUT') {
      setRequestBody(getDefaultBody(endpoint));
    } else {
      setRequestBody('{}');
    }
  };

  const getDefaultBody = (endpoint: AcsEndpoint): string => {
    switch (endpoint.name) {
      case 'Create Index':
        return JSON.stringify({ name: 'test_index', datatype: 'event' }, null, 2);
      case 'Create HEC Token':
        return JSON.stringify({ name: 'test_token', indexes: ['main'] }, null, 2);
      case 'Create User':
        return JSON.stringify({ name: 'testuser', password: 'changeme123', roles: ['user'] }, null, 2);
      default:
        return '{}';
    }
  };

  if (isLoading) {
    return <Content>Loading instances...</Content>;
  }

  return (
    <Content>
      <Card>
        <CardHeader
          title="ACS API Explorer"
          subtitle="Test Splunk Admin Config Service API operations against ephemeral instances"
        />
        <CardBody>
          {/* Instance Selection */}
          <div style={{ marginBottom: '1.5rem' }}>
            <Heading level={4}>Target Instance</Heading>
            <Select
              value={selectedInstance}
              onChange={(e, { value }) => setSelectedInstance(value as string)}
              style={{ minWidth: '300px' }}
            >
              <Select.Option value="" label="Select a running instance..." />
              {runningInstances.map((instance: Instance) => (
                <Select.Option
                  key={instance.id}
                  value={instance.id}
                  label={`${instance.name} (${instance.endpoints.api_url || 'No API URL'})`}
                />
              ))}
            </Select>
            {runningInstances.length === 0 && (
              <p style={{ color: '#d94f00', marginTop: '0.5rem' }}>
                No running instances. Create and start an instance first.
              </p>
            )}
          </div>

          {/* Endpoint Categories */}
          <TabLayout defaultActivePanelId="indexes">
            {['indexes', 'inputs', 'apps', 'users', 'tokens'].map((category) => (
              <TabLayout.Panel
                key={category}
                label={category.charAt(0).toUpperCase() + category.slice(1)}
                panelId={category}
              >
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', padding: '1rem 0' }}>
                  {ACS_ENDPOINTS.filter((e) => e.category === category).map((endpoint) => (
                    <Button
                      key={endpoint.name}
                      appearance={selectedEndpoint?.name === endpoint.name ? 'primary' : 'secondary'}
                      onClick={() => handleEndpointSelect(endpoint)}
                    >
                      <span style={{ marginRight: '0.5rem', fontFamily: 'monospace' }}>
                        {endpoint.method}
                      </span>
                      {endpoint.name}
                    </Button>
                  ))}
                </div>
              </TabLayout.Panel>
            ))}
          </TabLayout>

          {/* Request Builder */}
          {selectedEndpoint && (
            <Card style={{ marginTop: '1rem' }}>
              <CardHeader
                title={selectedEndpoint.name}
                subtitle={`${selectedEndpoint.method} ${selectedEndpoint.path}`}
              />
              <CardBody>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  {/* Request Side */}
                  <div>
                    <Heading level={4}>Request</Heading>

                    {/* Path Parameters */}
                    {Object.keys(pathParams).length > 0 && (
                      <div style={{ marginBottom: '1rem' }}>
                        <Heading level={5}>Path Parameters</Heading>
                        {Object.keys(pathParams).map((param) => (
                          <Text
                            key={param}
                            label={param}
                            value={pathParams[param]}
                            onChange={(e, { value }) =>
                              setPathParams({ ...pathParams, [param]: value })
                            }
                            style={{ marginBottom: '0.5rem' }}
                          />
                        ))}
                      </div>
                    )}

                    {/* Request Body */}
                    {(selectedEndpoint.method === 'POST' ||
                      selectedEndpoint.method === 'PUT') && (
                      <div>
                        <Heading level={5}>Request Body</Heading>
                        <textarea
                          value={requestBody}
                          onChange={(e) => setRequestBody(e.target.value)}
                          style={{
                            width: '100%',
                            height: '200px',
                            fontFamily: 'monospace',
                            padding: '0.5rem',
                            border: '1px solid #ccc',
                            borderRadius: '4px',
                          }}
                        />
                      </div>
                    )}

                    <Button
                      appearance="primary"
                      onClick={() => executeRequest.mutate()}
                      disabled={!selectedInstance || executeRequest.isPending}
                      style={{ marginTop: '1rem' }}
                    >
                      {executeRequest.isPending ? 'Executing...' : 'Execute Request'}
                    </Button>
                  </div>

                  {/* Response Side */}
                  <div>
                    <Heading level={4}>
                      Response
                      {responseStatus !== null && (
                        <span
                          style={{
                            marginLeft: '1rem',
                            color: responseStatus < 400 ? '#4caf50' : '#d94f00',
                          }}
                        >
                          Status: {responseStatus}
                        </span>
                      )}
                    </Heading>
                    <Code
                      value={response || '// Response will appear here'}
                      language="json"
                      style={{ minHeight: '250px' }}
                    />
                  </div>
                </div>
              </CardBody>
            </Card>
          )}
        </CardBody>
      </Card>
    </Content>
  );
}

export default AcsExplorerPage;
