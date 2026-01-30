/**
 * Type definitions for Faux Splunk Cloud Backstage plugin.
 */

// =============================================================================
// Instance Types
// =============================================================================

export type InstanceStatus =
  | 'pending'
  | 'provisioning'
  | 'starting'
  | 'running'
  | 'stopping'
  | 'stopped'
  | 'error'
  | 'terminated';

export type InstanceTopology =
  | 'standalone'
  | 'distributed_minimal'
  | 'distributed_clustered'
  | 'victoria_full';

export interface InstanceConfig {
  topology: InstanceTopology;
  experience: 'victoria' | 'classic';
  splunk_version: string;
  memory_mb: number;
  cpu_cores: number;
  default_indexes?: string[];
}

export interface InstanceEndpoints {
  web_url?: string;
  api_url?: string;
  hec_url?: string;
  acs_url?: string;
  s2s_port?: number;
}

export interface InstanceCredentials {
  admin_username: string;
  admin_password: string;
  acs_token?: string;
  hec_token?: string;
}

export interface Instance {
  id: string;
  name: string;
  status: InstanceStatus;
  config: InstanceConfig;
  endpoints: InstanceEndpoints;
  credentials?: InstanceCredentials;
  created_at: string;
  expires_at: string;
  error_message?: string;
  labels?: Record<string, string>;
}

export interface InstanceCreate {
  name: string;
  ttl_hours?: number;
  config?: Partial<InstanceConfig>;
  labels?: Record<string, string>;
}

// =============================================================================
// Attack Simulation Types
// =============================================================================

export type ThreatLevel =
  | 'script_kiddie'
  | 'opportunistic'
  | 'organized_crime'
  | 'hacktivist'
  | 'insider_threat'
  | 'apt'
  | 'nation_state';

export interface ThreatActor {
  id: string;
  name: string;
  aliases: string[];
  description: string;
  threat_level: ThreatLevel;
  motivation: string[];
  techniques: string[];  // MITRE ATT&CK IDs
  attributed_country?: string;
  dwell_time_days: { min: number; max: number };
}

export type CampaignStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'detected'
  | 'failed';

export interface AttackCampaign {
  id: string;
  name: string;
  threat_actor_id: string;
  threat_actor_name: string;
  target_instance_id: string;
  status: CampaignStatus;
  current_phase: string;
  completed_steps: number;
  total_steps: number;
  detected: boolean;
  detected_at_step?: number;
  start_time?: string;
  end_time?: string;
}

export interface CampaignCreate {
  threat_actor_id: string;
  target_instance_id: string;
  start_immediately?: boolean;
  name?: string;
}

export interface AttackStep {
  id: string;
  campaign_id: string;
  technique_id: string;
  technique_name: string;
  phase: string;
  timestamp: string;
  success: boolean;
  detected: boolean;
  logs_generated: number;
}

export interface AttackScenario {
  id: string;
  name: string;
  description: string;
  threat_level: string;
  objectives: string[];
  estimated_duration_minutes: number;
}

// =============================================================================
// Workflow Types (MineMeld Successor)
// =============================================================================

export type WorkflowNodeType = 'miner' | 'processor' | 'output';

export type WorkflowStatus = 'draft' | 'active' | 'paused' | 'error';

export interface WorkflowNode {
  id: string;
  type: WorkflowNodeType;
  prototype: string;  // e.g., 'taxii.client', 'aggregator.ipv4', 'output.edl'
  name: string;
  config: Record<string, unknown>;
  position: { x: number; y: number };
}

export interface WorkflowEdge {
  id: string;
  source: string;  // Node ID
  target: string;  // Node ID
  filters?: IndicatorFilter[];
}

export interface IndicatorFilter {
  field: string;
  operator: 'eq' | 'ne' | 'contains' | 'regex' | 'gt' | 'lt';
  value: string | number;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  status: WorkflowStatus;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  schedule?: string;  // Cron expression
  last_run?: string;
  next_run?: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  indicator_count?: number;
  error_message?: string;
}

export interface WorkflowCreate {
  name: string;
  description?: string;
  nodes: Omit<WorkflowNode, 'id'>[];
  edges: Omit<WorkflowEdge, 'id'>[];
  schedule?: string;
}

// =============================================================================
// Workflow Prototypes (MineMeld-style)
// =============================================================================

export interface WorkflowPrototype {
  id: string;
  name: string;
  type: WorkflowNodeType;
  description: string;
  category: string;  // e.g., 'taxii', 'aggregator', 'output'
  config_schema: Record<string, PrototypeConfigField>;
  icon?: string;
}

export interface PrototypeConfigField {
  type: 'string' | 'number' | 'boolean' | 'select' | 'multiselect';
  label: string;
  description?: string;
  required?: boolean;
  default?: unknown;
  options?: Array<{ label: string; value: string | number }>;
}

// =============================================================================
// ACS API Types
// =============================================================================

export interface ACSIndex {
  name: string;
  datatype: 'event' | 'metric';
  searchableDays: number;
  maxTotalDataSizeMB: number;
  totalEventCount: number;
  totalRawSizeMB: number;
}

export interface ACSHECToken {
  name: string;
  token: string;
  defaultIndex: string;
  indexes: string[];
  disabled: boolean;
}

// =============================================================================
// Indicator Types (for Workflow Data)
// =============================================================================

export type IndicatorType =
  | 'ipv4'
  | 'ipv6'
  | 'domain'
  | 'url'
  | 'hash_md5'
  | 'hash_sha256'
  | 'email';

export type ShareLevel = 'white' | 'green' | 'amber' | 'red';

export interface Indicator {
  id: string;
  type: IndicatorType;
  value: string;
  confidence: number;  // 0-100
  severity: 'low' | 'medium' | 'high' | 'critical';
  first_seen: string;
  last_seen: string;
  valid_from?: string;
  valid_until?: string;
  share_level: ShareLevel;
  sources: IndicatorSource[];
  tags: string[];
  metadata: Record<string, unknown>;
}

export interface IndicatorSource {
  feed_id: string;
  feed_name: string;
  confidence: number;
  first_seen: string;
  last_seen: string;
}
