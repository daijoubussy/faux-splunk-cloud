// Instance types
export interface InstanceConfig {
  topology: 'standalone' | 'distributed_minimal' | 'distributed_clustered' | 'victoria_full';
  experience: string;
  enable_hec: boolean;
  enable_realtime_search: boolean;
  create_default_indexes: boolean;
  memory_mb: number;
  cpu_cores: number;
  search_head_count: number;
  indexer_count: number;
  replication_factor: number;
  search_factor: number;
  preinstall_apps: string[];
}

export interface InstanceEndpoints {
  web_url: string | null;
  api_url: string | null;
  hec_url: string | null;
  acs_url: string | null;
  s2s_port: number | null;
}

export interface InstanceCredentials {
  admin_username: string;
  admin_password: string;
  acs_token: string | null;
  hec_token: string | null;
}

export interface Instance {
  id: string;
  name: string;
  status: 'pending' | 'provisioning' | 'starting' | 'running' | 'stopping' | 'stopped' | 'error' | 'terminated';
  config: InstanceConfig;
  endpoints: InstanceEndpoints;
  credentials: InstanceCredentials | null;
  network_id: string | null;
  container_ids: string[];
  created_at: string;
  started_at: string | null;
  expires_at: string;
  error_message: string | null;
  labels: Record<string, string>;
}

export interface InstanceCreate {
  name: string;
  config: Partial<InstanceConfig>;
  ttl_hours: number;
  labels?: Record<string, string>;
}

// ACS types
export interface ACSIndex {
  name: string;
  datatype: 'event' | 'metric';
  searchableDays: number;
  maxDataSizeMB: number;
  totalEventCount: number;
  totalRawSizeMB: number;
  frozenTimePeriodInSecs: number;
}

export interface ACSHECToken {
  name: string;
  token: string;
  defaultIndex: string;
  defaultSource: string | null;
  defaultSourcetype: string | null;
  indexes: string[];
  disabled: boolean;
  useACK: boolean;
}

// Attack simulation types
export interface ThreatActor {
  id: string;
  name: string;
  aliases: string[];
  threat_level: string;
  motivation: string[];
  description: string;
  techniques: string[];
  attributed_country: string | null;
}

export interface AttackCampaign {
  id: string;
  name: string;
  threat_actor_id: string;
  threat_actor_name: string;
  target_instance_id: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'detected' | 'failed';
  current_phase: string;
  total_steps: number;
  completed_steps: number;
  start_time: string | null;
  end_time: string | null;
  detected: boolean;
  detected_at_step: number | null;
}

export interface AttackStep {
  id: string;
  technique_id: string;
  technique_name: string;
  phase: string;
  tactic: string;
  timestamp: string;
  success: boolean;
  detected: boolean;
}

export interface AttackScenario {
  id: string;
  name: string;
  description: string;
  threat_level: string;
  estimated_duration_minutes: number;
  objectives: string[];
}

export interface CampaignCreateRequest {
  threat_actor_id: string;
  target_instance_id: string;
  name?: string;
  speed_multiplier?: number;
  start_immediately?: boolean;
  objectives?: string[];
}
