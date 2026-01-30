/**
 * Workflows page for managing threat intelligence workflows.
 * This maps to MineMeld's graph-based miner/processor/output architecture.
 */

import React, { useState } from 'react';
import { Content } from '@backstage/core-components';
import { useApi } from '@backstage/core-plugin-api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Table, HeadCell, Row, Cell, Body, Head } from '@splunk/react-ui/Table';
import { Card, CardHeader, CardBody } from '@splunk/react-ui/Card';
import { Button } from '@splunk/react-ui/Button';
import { Badge } from '@splunk/react-ui/Badge';
import { Modal, ModalHeader, ModalBody, ModalFooter } from '@splunk/react-ui/Modal';
import { Text } from '@splunk/react-ui/Text';
import { fauxSplunkCloudApiRef } from '../../api';
import { Workflow, WorkflowPrototype } from '../../types';

type WorkflowStatusAppearance = 'success' | 'warning' | 'error' | 'default';

function WorkflowStatusBadge({ status }: { status: string }) {
  const appearances: Record<string, WorkflowStatusAppearance> = {
    active: 'success',
    draft: 'default',
    paused: 'warning',
    error: 'error',
  };

  return (
    <Badge
      appearance={appearances[status] || 'default'}
      label={status}
    />
  );
}

function PrototypeTypeBadge({ type }: { type: string }) {
  const appearances: Record<string, 'info' | 'warning' | 'success'> = {
    miner: 'info',
    processor: 'warning',
    output: 'success',
  };

  return (
    <Badge
      appearance={appearances[type] || 'info'}
      label={type}
    />
  );
}

export function WorkflowsPage() {
  const api = useApi(fauxSplunkCloudApiRef);
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWorkflowName, setNewWorkflowName] = useState('');
  const [newWorkflowDescription, setNewWorkflowDescription] = useState('');

  const { data: workflows = [], isLoading: loadingWorkflows } = useQuery({
    queryKey: ['fsc-workflows'],
    queryFn: () => api.listWorkflows(),
    refetchInterval: 10000,
  });

  const { data: prototypes = [], isLoading: loadingPrototypes } = useQuery({
    queryKey: ['fsc-prototypes'],
    queryFn: () => api.listPrototypes(),
  });

  const createWorkflow = useMutation({
    mutationFn: (params: { name: string; description: string }) =>
      api.createWorkflow(params.name, params.description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fsc-workflows'] });
      setShowCreateModal(false);
      setNewWorkflowName('');
      setNewWorkflowDescription('');
    },
  });

  const executeWorkflow = useMutation({
    mutationFn: (id: string) => api.executeWorkflow(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fsc-workflows'] }),
  });

  const pauseWorkflow = useMutation({
    mutationFn: (id: string) => api.pauseWorkflow(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fsc-workflows'] }),
  });

  const deleteWorkflow = useMutation({
    mutationFn: (id: string) => api.deleteWorkflow(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fsc-workflows'] }),
  });

  // Group prototypes by type
  const prototypesByType = prototypes.reduce(
    (acc: Record<string, WorkflowPrototype[]>, proto: WorkflowPrototype) => {
      if (!acc[proto.type]) acc[proto.type] = [];
      acc[proto.type].push(proto);
      return acc;
    },
    {} as Record<string, WorkflowPrototype[]>
  );

  if (loadingWorkflows || loadingPrototypes) {
    return <Content>Loading workflows...</Content>;
  }

  return (
    <Content>
      {/* Workflows Table */}
      <Card>
        <CardHeader
          title="Threat Intelligence Workflows"
          subtitle="MineMeld-compatible workflow definitions"
          actions={
            <Button appearance="primary" onClick={() => setShowCreateModal(true)}>
              New Workflow
            </Button>
          }
        />
        <CardBody>
          {workflows.length === 0 ? (
            <p>No workflows defined. Create one to start processing threat intel.</p>
          ) : (
            <Table stripeRows>
              <Head>
                <HeadCell>Name</HeadCell>
                <HeadCell>Description</HeadCell>
                <HeadCell>Status</HeadCell>
                <HeadCell>Nodes</HeadCell>
                <HeadCell>Schedule</HeadCell>
                <HeadCell>Actions</HeadCell>
              </Head>
              <Body>
                {workflows.map((workflow: Workflow) => (
                  <Row key={workflow.id}>
                    <Cell>{workflow.name}</Cell>
                    <Cell>{workflow.description}</Cell>
                    <Cell>
                      <WorkflowStatusBadge status={workflow.status} />
                    </Cell>
                    <Cell>{workflow.nodes.length}</Cell>
                    <Cell>{workflow.schedule || 'Manual'}</Cell>
                    <Cell>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <Button
                          appearance="secondary"
                          onClick={() => {
                            // Navigate to workflow editor
                            window.location.href = `/faux-splunk-cloud/workflows/${workflow.id}/edit`;
                          }}
                        >
                          Edit
                        </Button>
                        {workflow.status === 'draft' || workflow.status === 'paused' ? (
                          <Button
                            appearance="primary"
                            onClick={() => executeWorkflow.mutate(workflow.id)}
                          >
                            Start
                          </Button>
                        ) : workflow.status === 'active' ? (
                          <Button
                            appearance="secondary"
                            onClick={() => pauseWorkflow.mutate(workflow.id)}
                          >
                            Pause
                          </Button>
                        ) : null}
                        <Button
                          appearance="destructive"
                          onClick={() => {
                            if (confirm(`Delete workflow "${workflow.name}"?`)) {
                              deleteWorkflow.mutate(workflow.id);
                            }
                          }}
                        >
                          Delete
                        </Button>
                      </div>
                    </Cell>
                  </Row>
                ))}
              </Body>
            </Table>
          )}
        </CardBody>
      </Card>

      {/* Available Prototypes */}
      <Card style={{ marginTop: '1.5rem' }}>
        <CardHeader
          title="Available Prototypes"
          subtitle="Node types for building workflows (MineMeld compatible)"
        />
        <CardBody>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
            {/* Miners */}
            <Card>
              <CardHeader title="Miners" subtitle="Input nodes - fetch from external sources" />
              <CardBody>
                {(prototypesByType['miner'] || []).map((proto: WorkflowPrototype) => (
                  <div
                    key={proto.id}
                    style={{
                      padding: '0.5rem',
                      borderBottom: '1px solid #eee',
                    }}
                  >
                    <strong>{proto.name}</strong>
                    <p style={{ margin: '0.25rem 0', fontSize: '0.875rem', color: '#666' }}>
                      {proto.description}
                    </p>
                  </div>
                ))}
                {!prototypesByType['miner']?.length && (
                  <p style={{ color: '#666' }}>No miner prototypes available</p>
                )}
              </CardBody>
            </Card>

            {/* Processors */}
            <Card>
              <CardHeader title="Processors" subtitle="Transform nodes - aggregate, filter, enrich" />
              <CardBody>
                {(prototypesByType['processor'] || []).map((proto: WorkflowPrototype) => (
                  <div
                    key={proto.id}
                    style={{
                      padding: '0.5rem',
                      borderBottom: '1px solid #eee',
                    }}
                  >
                    <strong>{proto.name}</strong>
                    <p style={{ margin: '0.25rem 0', fontSize: '0.875rem', color: '#666' }}>
                      {proto.description}
                    </p>
                  </div>
                ))}
                {!prototypesByType['processor']?.length && (
                  <p style={{ color: '#666' }}>No processor prototypes available</p>
                )}
              </CardBody>
            </Card>

            {/* Outputs */}
            <Card>
              <CardHeader title="Outputs" subtitle="Export nodes - send to consumers" />
              <CardBody>
                {(prototypesByType['output'] || []).map((proto: WorkflowPrototype) => (
                  <div
                    key={proto.id}
                    style={{
                      padding: '0.5rem',
                      borderBottom: '1px solid #eee',
                    }}
                  >
                    <strong>{proto.name}</strong>
                    <p style={{ margin: '0.25rem 0', fontSize: '0.875rem', color: '#666' }}>
                      {proto.description}
                    </p>
                  </div>
                ))}
                {!prototypesByType['output']?.length && (
                  <p style={{ color: '#666' }}>No output prototypes available</p>
                )}
              </CardBody>
            </Card>
          </div>
        </CardBody>
      </Card>

      {/* Create Workflow Modal */}
      {showCreateModal && (
        <Modal onRequestClose={() => setShowCreateModal(false)}>
          <ModalHeader title="Create New Workflow" />
          <ModalBody>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <Text
                label="Workflow Name"
                value={newWorkflowName}
                onChange={(e, { value }) => setNewWorkflowName(value)}
                placeholder="e.g., threat-intel-aggregation"
              />
              <Text
                label="Description"
                value={newWorkflowDescription}
                onChange={(e, { value }) => setNewWorkflowDescription(value)}
                placeholder="Brief description of the workflow purpose"
                multiline
              />
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
                createWorkflow.mutate({
                  name: newWorkflowName,
                  description: newWorkflowDescription,
                })
              }
              disabled={!newWorkflowName}
            >
              Create Workflow
            </Button>
          </ModalFooter>
        </Modal>
      )}
    </Content>
  );
}

export default WorkflowsPage;
