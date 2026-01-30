/**
 * WYSIWYG Workflow Editor component for visual workflow design.
 * Implements MineMeld-style Miner → Processor → Output flow.
 *
 * This is a scaffold for the full editor which will integrate
 * React Flow or similar for node-based editing.
 */

import React, { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Content, Header, Page } from '@backstage/core-components';
import { useApi } from '@backstage/core-plugin-api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardHeader, CardBody } from '@splunk/react-ui/Card';
import { Heading } from '@splunk/react-ui/Heading';
import { Button } from '@splunk/react-ui/Button';
import { Badge } from '@splunk/react-ui/Badge';
import { Modal, ModalHeader, ModalBody, ModalFooter } from '@splunk/react-ui/Modal';
import { Select } from '@splunk/react-ui/Select';
import { Text } from '@splunk/react-ui/Text';
import { fauxSplunkCloudApiRef } from '../../api';
import {
  Workflow,
  WorkflowNode,
  WorkflowEdge,
  WorkflowPrototype,
} from '../../types';
import { SplunkThemedContent } from '../SplunkThemedContent';

interface NodePosition {
  x: number;
  y: number;
}

interface DragState {
  nodeId: string | null;
  offsetX: number;
  offsetY: number;
}

type NodeTypeAppearance = 'info' | 'warning' | 'success';

function NodeTypeBadge({ type }: { type: 'miner' | 'processor' | 'output' }) {
  const appearances: Record<string, NodeTypeAppearance> = {
    miner: 'info',
    processor: 'warning',
    output: 'success',
  };
  return <Badge appearance={appearances[type]} label={type} />;
}

export function WorkflowEditor() {
  const { workflowId } = useParams<{ workflowId: string }>();
  const navigate = useNavigate();
  const api = useApi(fauxSplunkCloudApiRef);
  const queryClient = useQueryClient();

  // Editor state
  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [edges, setEdges] = useState<WorkflowEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null);
  const [showAddNodeModal, setShowAddNodeModal] = useState(false);
  const [newNodePrototype, setNewNodePrototype] = useState<string>('');
  const [dragState, setDragState] = useState<DragState>({
    nodeId: null,
    offsetX: 0,
    offsetY: 0,
  });
  const [connectionStart, setConnectionStart] = useState<string | null>(null);

  // Load workflow
  const { data: workflow, isLoading } = useQuery({
    queryKey: ['fsc-workflow', workflowId],
    queryFn: () => api.getWorkflow(workflowId!),
    enabled: !!workflowId,
    onSuccess: (data: Workflow) => {
      setNodes(data.nodes || []);
      setEdges(data.edges || []);
    },
  });

  // Load prototypes
  const { data: prototypes = [] } = useQuery({
    queryKey: ['fsc-prototypes'],
    queryFn: () => api.listPrototypes(),
  });

  // Save workflow
  const saveWorkflow = useMutation({
    mutationFn: () =>
      api.updateWorkflow(workflowId!, { nodes, edges }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fsc-workflow', workflowId] });
    },
  });

  // Add node handler
  const handleAddNode = useCallback(() => {
    const prototype = prototypes.find((p: WorkflowPrototype) => p.id === newNodePrototype);
    if (!prototype) return;

    const newNode: WorkflowNode = {
      id: `node-${Date.now()}`,
      type: prototype.type,
      prototype: prototype.id,
      config: prototype.default_config || {},
      inputs: [],
      outputs: [],
      position: {
        x: 100 + nodes.length * 50,
        y: 100 + (nodes.filter((n) => n.type === prototype.type).length * 80),
      },
    };

    setNodes([...nodes, newNode]);
    setShowAddNodeModal(false);
    setNewNodePrototype('');
  }, [nodes, prototypes, newNodePrototype]);

  // Delete node handler
  const handleDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes(nodes.filter((n) => n.id !== nodeId));
      setEdges(edges.filter((e) => e.source !== nodeId && e.target !== nodeId));
      if (selectedNode?.id === nodeId) {
        setSelectedNode(null);
      }
    },
    [nodes, edges, selectedNode]
  );

  // Connection handlers
  const handleStartConnection = useCallback((nodeId: string) => {
    setConnectionStart(nodeId);
  }, []);

  const handleEndConnection = useCallback(
    (targetId: string) => {
      if (connectionStart && connectionStart !== targetId) {
        // Validate connection (miners can connect to processors, processors to outputs)
        const sourceNode = nodes.find((n) => n.id === connectionStart);
        const targetNode = nodes.find((n) => n.id === targetId);

        if (sourceNode && targetNode) {
          const validConnections: Record<string, string[]> = {
            miner: ['processor'],
            processor: ['processor', 'output'],
            output: [],
          };

          if (validConnections[sourceNode.type]?.includes(targetNode.type)) {
            const newEdge: WorkflowEdge = {
              id: `edge-${Date.now()}`,
              source: connectionStart,
              target: targetId,
            };
            setEdges([...edges, newEdge]);
          }
        }
      }
      setConnectionStart(null);
    },
    [connectionStart, nodes, edges]
  );

  // Drag handlers
  const handleDragStart = useCallback(
    (nodeId: string, e: React.MouseEvent) => {
      const node = nodes.find((n) => n.id === nodeId);
      if (node) {
        setDragState({
          nodeId,
          offsetX: e.clientX - node.position.x,
          offsetY: e.clientY - node.position.y,
        });
      }
    },
    [nodes]
  );

  const handleDrag = useCallback(
    (e: React.MouseEvent) => {
      if (dragState.nodeId) {
        setNodes(
          nodes.map((n) =>
            n.id === dragState.nodeId
              ? {
                  ...n,
                  position: {
                    x: e.clientX - dragState.offsetX,
                    y: e.clientY - dragState.offsetY,
                  },
                }
              : n
          )
        );
      }
    },
    [dragState, nodes]
  );

  const handleDragEnd = useCallback(() => {
    setDragState({ nodeId: null, offsetX: 0, offsetY: 0 });
  }, []);

  if (isLoading) {
    return (
      <SplunkThemedContent>
        <Page themeId="tool">
          <Header title="Loading Workflow..." />
          <Content>Loading...</Content>
        </Page>
      </SplunkThemedContent>
    );
  }

  // Group prototypes by type for the add modal
  const prototypesByType = prototypes.reduce(
    (acc: Record<string, WorkflowPrototype[]>, p: WorkflowPrototype) => {
      if (!acc[p.type]) acc[p.type] = [];
      acc[p.type].push(p);
      return acc;
    },
    {}
  );

  return (
    <SplunkThemedContent>
      <Page themeId="tool">
        <Header
          title={`Edit Workflow: ${workflow?.name || 'Untitled'}`}
          subtitle={workflow?.description}
        />
        <Content>
          {/* Toolbar */}
          <Card style={{ marginBottom: '1rem' }}>
            <CardBody>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <Button appearance="primary" onClick={() => setShowAddNodeModal(true)}>
                  Add Node
                </Button>
                <Button
                  appearance="secondary"
                  onClick={() => saveWorkflow.mutate()}
                  disabled={saveWorkflow.isPending}
                >
                  {saveWorkflow.isPending ? 'Saving...' : 'Save Workflow'}
                </Button>
                <div style={{ flex: 1 }} />
                <span style={{ color: '#666' }}>
                  {nodes.length} nodes, {edges.length} connections
                </span>
                <Button appearance="secondary" onClick={() => navigate('/faux-splunk-cloud/workflows')}>
                  Back to Workflows
                </Button>
              </div>
            </CardBody>
          </Card>

          {/* Canvas */}
          <Card>
            <CardHeader title="Workflow Canvas" subtitle="Drag nodes to position, click output ports to connect" />
            <CardBody>
              <div
                style={{
                  position: 'relative',
                  width: '100%',
                  height: '600px',
                  backgroundColor: '#f5f5f5',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  overflow: 'hidden',
                }}
                onMouseMove={handleDrag}
                onMouseUp={handleDragEnd}
                onMouseLeave={handleDragEnd}
              >
                {/* Grid background */}
                <svg
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    pointerEvents: 'none',
                  }}
                >
                  <defs>
                    <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e0e0e0" strokeWidth="0.5" />
                    </pattern>
                  </defs>
                  <rect width="100%" height="100%" fill="url(#grid)" />

                  {/* Connection lines */}
                  {edges.map((edge) => {
                    const source = nodes.find((n) => n.id === edge.source);
                    const target = nodes.find((n) => n.id === edge.target);
                    if (!source || !target) return null;

                    return (
                      <line
                        key={edge.id}
                        x1={source.position.x + 120}
                        y1={source.position.y + 40}
                        x2={target.position.x}
                        y2={target.position.y + 40}
                        stroke="#666"
                        strokeWidth="2"
                        markerEnd="url(#arrowhead)"
                      />
                    );
                  })}

                  {/* Arrowhead marker */}
                  <defs>
                    <marker
                      id="arrowhead"
                      markerWidth="10"
                      markerHeight="7"
                      refX="9"
                      refY="3.5"
                      orient="auto"
                    >
                      <polygon points="0 0, 10 3.5, 0 7" fill="#666" />
                    </marker>
                  </defs>
                </svg>

                {/* Nodes */}
                {nodes.map((node) => {
                  const prototype = prototypes.find((p: WorkflowPrototype) => p.id === node.prototype);
                  const bgColors: Record<string, string> = {
                    miner: '#e3f2fd',
                    processor: '#fff3e0',
                    output: '#e8f5e9',
                  };

                  return (
                    <div
                      key={node.id}
                      style={{
                        position: 'absolute',
                        left: node.position.x,
                        top: node.position.y,
                        width: '200px',
                        backgroundColor: bgColors[node.type] || '#fff',
                        border: selectedNode?.id === node.id ? '2px solid #1976d2' : '1px solid #ccc',
                        borderRadius: '8px',
                        padding: '0.5rem',
                        cursor: dragState.nodeId === node.id ? 'grabbing' : 'grab',
                        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                      }}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        handleDragStart(node.id, e);
                        setSelectedNode(node);
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <NodeTypeBadge type={node.type} />
                        <Button
                          appearance="destructive"
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteNode(node.id);
                          }}
                        >
                          ×
                        </Button>
                      </div>
                      <div style={{ fontWeight: 'bold', marginTop: '0.5rem' }}>
                        {prototype?.name || node.prototype}
                      </div>

                      {/* Connection ports */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem' }}>
                        {/* Input port */}
                        {node.type !== 'miner' && (
                          <div
                            style={{
                              width: '12px',
                              height: '12px',
                              backgroundColor: connectionStart ? '#4caf50' : '#666',
                              borderRadius: '50%',
                              cursor: 'pointer',
                            }}
                            onClick={(e) => {
                              e.stopPropagation();
                              if (connectionStart) {
                                handleEndConnection(node.id);
                              }
                            }}
                            title="Input"
                          />
                        )}
                        <div style={{ flex: 1 }} />
                        {/* Output port */}
                        {node.type !== 'output' && (
                          <div
                            style={{
                              width: '12px',
                              height: '12px',
                              backgroundColor: connectionStart === node.id ? '#ff9800' : '#666',
                              borderRadius: '50%',
                              cursor: 'pointer',
                            }}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStartConnection(node.id);
                            }}
                            title="Output - Click to connect"
                          />
                        )}
                      </div>
                    </div>
                  );
                })}

                {/* Empty state */}
                {nodes.length === 0 && (
                  <div
                    style={{
                      position: 'absolute',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)',
                      textAlign: 'center',
                      color: '#666',
                    }}
                  >
                    <Heading level={3}>Empty Workflow</Heading>
                    <p>Click "Add Node" to start building your workflow</p>
                  </div>
                )}
              </div>
            </CardBody>
          </Card>

          {/* Node Properties Panel */}
          {selectedNode && (
            <Card style={{ marginTop: '1rem' }}>
              <CardHeader title="Node Properties" subtitle={selectedNode.prototype} />
              <CardBody>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <strong>Node ID:</strong> {selectedNode.id}
                  </div>
                  <div>
                    <strong>Type:</strong> <NodeTypeBadge type={selectedNode.type} />
                  </div>
                  <div>
                    <strong>Prototype:</strong> {selectedNode.prototype}
                  </div>
                  <div>
                    <strong>Position:</strong> ({Math.round(selectedNode.position.x)}, {Math.round(selectedNode.position.y)})
                  </div>
                </div>
                <div style={{ marginTop: '1rem' }}>
                  <strong>Configuration:</strong>
                  <pre style={{ backgroundColor: '#f5f5f5', padding: '0.5rem', borderRadius: '4px', overflow: 'auto' }}>
                    {JSON.stringify(selectedNode.config, null, 2)}
                  </pre>
                </div>
              </CardBody>
            </Card>
          )}

          {/* Add Node Modal */}
          {showAddNodeModal && (
            <Modal onRequestClose={() => setShowAddNodeModal(false)}>
              <ModalHeader title="Add Workflow Node" />
              <ModalBody>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <Heading level={4}>Select Prototype</Heading>

                  {/* Miners */}
                  <div>
                    <Heading level={5}>Miners (Input)</Heading>
                    <Select
                      value={newNodePrototype}
                      onChange={(e, { value }) => setNewNodePrototype(value as string)}
                    >
                      <Select.Option value="" label="Select a miner..." />
                      {(prototypesByType['miner'] || []).map((p: WorkflowPrototype) => (
                        <Select.Option key={p.id} value={p.id} label={p.name} />
                      ))}
                    </Select>
                  </div>

                  {/* Processors */}
                  <div>
                    <Heading level={5}>Processors (Transform)</Heading>
                    <Select
                      value={newNodePrototype}
                      onChange={(e, { value }) => setNewNodePrototype(value as string)}
                    >
                      <Select.Option value="" label="Select a processor..." />
                      {(prototypesByType['processor'] || []).map((p: WorkflowPrototype) => (
                        <Select.Option key={p.id} value={p.id} label={p.name} />
                      ))}
                    </Select>
                  </div>

                  {/* Outputs */}
                  <div>
                    <Heading level={5}>Outputs (Export)</Heading>
                    <Select
                      value={newNodePrototype}
                      onChange={(e, { value }) => setNewNodePrototype(value as string)}
                    >
                      <Select.Option value="" label="Select an output..." />
                      {(prototypesByType['output'] || []).map((p: WorkflowPrototype) => (
                        <Select.Option key={p.id} value={p.id} label={p.name} />
                      ))}
                    </Select>
                  </div>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button appearance="secondary" onClick={() => setShowAddNodeModal(false)}>
                  Cancel
                </Button>
                <Button
                  appearance="primary"
                  onClick={handleAddNode}
                  disabled={!newNodePrototype}
                >
                  Add Node
                </Button>
              </ModalFooter>
            </Modal>
          )}
        </Content>
      </Page>
    </SplunkThemedContent>
  );
}

export default WorkflowEditor;
