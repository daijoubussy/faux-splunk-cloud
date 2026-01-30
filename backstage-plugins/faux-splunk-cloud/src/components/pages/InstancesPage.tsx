/**
 * Instances list page with create/manage functionality.
 */

import React from 'react';
import { Content, Link } from '@backstage/core-components';
import { useApi } from '@backstage/core-plugin-api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@splunk/react-ui/Button';
import { Table } from '@splunk/react-ui/Table';
import { Badge } from '@splunk/react-ui/Badge';
import { Heading } from '@splunk/react-ui/Heading';
import { fauxSplunkCloudApiRef } from '../../api';
import type { Instance } from '../../types';

const statusAppearance: Record<string, string> = {
  running: 'success',
  starting: 'warning',
  stopping: 'warning',
  stopped: 'default',
  error: 'error',
  pending: 'info',
  provisioning: 'info',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <Badge
      appearance={statusAppearance[status] || 'default'}
      label={status}
    />
  );
}

export function InstancesPage() {
  const api = useApi(fauxSplunkCloudApiRef);
  const queryClient = useQueryClient();

  const { data: instances = [], isLoading } = useQuery({
    queryKey: ['fsc-instances'],
    queryFn: () => api.listInstances(),
    refetchInterval: 5000,
  });

  const destroyMutation = useMutation({
    mutationFn: (id: string) => api.destroyInstance(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fsc-instances'] });
    },
  });

  const columns = [
    { key: 'name', label: 'Name' },
    {
      key: 'status',
      label: 'Status',
      render: (value: string) => <StatusBadge status={value} />,
    },
    { key: 'config.topology', label: 'Topology' },
    {
      key: 'expires_at',
      label: 'Expires',
      render: (value: string) => new Date(value).toLocaleString(),
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (_: unknown, row: Instance) => (
        <Button
          appearance="destructive"
          size="small"
          onClick={() => {
            if (window.confirm(`Destroy instance ${row.name}?`)) {
              destroyMutation.mutate(row.id);
            }
          }}
        >
          Destroy
        </Button>
      ),
    },
  ];

  if (isLoading) {
    return (
      <Content>
        <div>Loading instances...</div>
      </Content>
    );
  }

  return (
    <Content>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Heading level={2}>Splunk Instances</Heading>
        <Link to="/faux-splunk-cloud/instances/new">
          <Button appearance="primary">Create Instance</Button>
        </Link>
      </div>

      <Table
        columns={columns}
        rows={instances.map(i => ({ ...i, 'config.topology': i.config.topology }))}
        rowKey="id"
        stripeRows
      />

      {instances.length === 0 && (
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          No instances found. Click "Create Instance" to get started.
        </div>
      )}
    </Content>
  );
}

export default InstancesPage;
