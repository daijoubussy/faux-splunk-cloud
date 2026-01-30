/**
 * Faux Splunk Cloud API client for Backstage.
 *
 * This API provides access to:
 * - Instance management (create, list, start, stop, destroy)
 * - Attack simulation (campaigns, threat actors, scenarios)
 * - Workflow management (MineMeld-style pipelines)
 * - ACS API operations (indexes, HEC tokens)
 */

import { createApiRef, DiscoveryApi, FetchApi } from '@backstage/core-plugin-api';
import type {
  Instance,
  InstanceCreate,
  ThreatActor,
  AttackCampaign,
  CampaignCreate,
  AttackScenario,
  Workflow,
  WorkflowCreate,
  ACSIndex,
  ACSHECToken,
} from './types';

/**
 * API reference for the Faux Splunk Cloud plugin.
 */
export const fauxSplunkCloudApiRef = createApiRef<FauxSplunkCloudApi>({
  id: 'plugin.faux-splunk-cloud.service',
});

/**
 * Interface for the Faux Splunk Cloud API.
 */
export interface FauxSplunkCloudApi {
  // Instance Management
  listInstances(): Promise<Instance[]>;
  getInstance(id: string): Promise<Instance>;
  createInstance(request: InstanceCreate): Promise<Instance>;
  startInstance(id: string): Promise<void>;
  stopInstance(id: string): Promise<void>;
  destroyInstance(id: string): Promise<void>;
  getInstanceLogs(id: string, tail?: number): Promise<string>;
  extendInstanceTTL(id: string, hours: number): Promise<Instance>;

  // Attack Simulation
  listThreatActors(): Promise<ThreatActor[]>;
  getThreatActor(id: string): Promise<ThreatActor>;
  listCampaigns(instanceId?: string): Promise<AttackCampaign[]>;
  getCampaign(id: string): Promise<AttackCampaign>;
  createCampaign(request: CampaignCreate): Promise<AttackCampaign>;
  startCampaign(id: string): Promise<AttackCampaign>;
  pauseCampaign(id: string): Promise<AttackCampaign>;
  listScenarios(): Promise<AttackScenario[]>;
  executeScenario(scenarioId: string, instanceId: string): Promise<AttackCampaign>;

  // Workflow Management (MineMeld successor)
  listWorkflows(): Promise<Workflow[]>;
  getWorkflow(id: string): Promise<Workflow>;
  createWorkflow(request: WorkflowCreate): Promise<Workflow>;
  updateWorkflow(id: string, request: Partial<WorkflowCreate>): Promise<Workflow>;
  deleteWorkflow(id: string): Promise<void>;
  executeWorkflow(id: string): Promise<void>;
  pauseWorkflow(id: string): Promise<void>;

  // ACS API
  listIndexes(stackId: string): Promise<ACSIndex[]>;
  createIndex(stackId: string, name: string, datatype?: string): Promise<ACSIndex>;
  deleteIndex(stackId: string, name: string): Promise<void>;
  listHECTokens(stackId: string): Promise<ACSHECToken[]>;
  createHECToken(stackId: string, name: string, defaultIndex?: string): Promise<ACSHECToken>;
  deleteHECToken(stackId: string, name: string): Promise<void>;
}

/**
 * Options for creating the API client.
 */
export interface FauxSplunkCloudApiClientOptions {
  discoveryApi: DiscoveryApi;
  fetchApi: FetchApi;
}

/**
 * Implementation of the Faux Splunk Cloud API client.
 */
export class FauxSplunkCloudApiClient implements FauxSplunkCloudApi {
  private readonly discoveryApi: DiscoveryApi;
  private readonly fetchApi: FetchApi;

  constructor(options: FauxSplunkCloudApiClientOptions) {
    this.discoveryApi = options.discoveryApi;
    this.fetchApi = options.fetchApi;
  }

  private async getBaseUrl(): Promise<string> {
    return await this.discoveryApi.getBaseUrl('faux-splunk-cloud');
  }

  private async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const baseUrl = await this.getBaseUrl();
    const response = await this.fetchApi.fetch(`${baseUrl}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(error.message || `API request failed: ${response.status}`);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // Instance Management
  async listInstances(): Promise<Instance[]> {
    const result = await this.fetch<{ instances: Instance[] }>('/api/v1/instances');
    return result.instances;
  }

  async getInstance(id: string): Promise<Instance> {
    return this.fetch<Instance>(`/api/v1/instances/${id}`);
  }

  async createInstance(request: InstanceCreate): Promise<Instance> {
    return this.fetch<Instance>('/api/v1/instances', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async startInstance(id: string): Promise<void> {
    await this.fetch(`/api/v1/instances/${id}/start`, { method: 'POST' });
  }

  async stopInstance(id: string): Promise<void> {
    await this.fetch(`/api/v1/instances/${id}/stop`, { method: 'POST' });
  }

  async destroyInstance(id: string): Promise<void> {
    await this.fetch(`/api/v1/instances/${id}`, { method: 'DELETE' });
  }

  async getInstanceLogs(id: string, tail = 100): Promise<string> {
    const result = await this.fetch<{ logs: string }>(`/api/v1/instances/${id}/logs?tail=${tail}`);
    return result.logs;
  }

  async extendInstanceTTL(id: string, hours: number): Promise<Instance> {
    return this.fetch<Instance>(`/api/v1/instances/${id}/extend`, {
      method: 'POST',
      body: JSON.stringify({ hours }),
    });
  }

  // Attack Simulation
  async listThreatActors(): Promise<ThreatActor[]> {
    const result = await this.fetch<{ threat_actors: ThreatActor[] }>('/api/v1/attacks/threat-actors');
    return result.threat_actors;
  }

  async getThreatActor(id: string): Promise<ThreatActor> {
    return this.fetch<ThreatActor>(`/api/v1/attacks/threat-actors/${id}`);
  }

  async listCampaigns(instanceId?: string): Promise<AttackCampaign[]> {
    const query = instanceId ? `?instance_id=${instanceId}` : '';
    const result = await this.fetch<{ campaigns: AttackCampaign[] }>(`/api/v1/attacks/campaigns${query}`);
    return result.campaigns;
  }

  async getCampaign(id: string): Promise<AttackCampaign> {
    return this.fetch<AttackCampaign>(`/api/v1/attacks/campaigns/${id}`);
  }

  async createCampaign(request: CampaignCreate): Promise<AttackCampaign> {
    return this.fetch<AttackCampaign>('/api/v1/attacks/campaigns', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async startCampaign(id: string): Promise<AttackCampaign> {
    return this.fetch<AttackCampaign>(`/api/v1/attacks/campaigns/${id}/start`, { method: 'POST' });
  }

  async pauseCampaign(id: string): Promise<AttackCampaign> {
    return this.fetch<AttackCampaign>(`/api/v1/attacks/campaigns/${id}/pause`, { method: 'POST' });
  }

  async listScenarios(): Promise<AttackScenario[]> {
    return this.fetch<AttackScenario[]>('/api/v1/attacks/scenarios');
  }

  async executeScenario(scenarioId: string, instanceId: string): Promise<AttackCampaign> {
    return this.fetch<AttackCampaign>(`/api/v1/attacks/scenarios/${scenarioId}/execute?target_instance_id=${instanceId}`, {
      method: 'POST',
    });
  }

  // Workflow Management
  async listWorkflows(): Promise<Workflow[]> {
    const result = await this.fetch<{ workflows: Workflow[] }>('/api/v1/workflows');
    return result.workflows;
  }

  async getWorkflow(id: string): Promise<Workflow> {
    return this.fetch<Workflow>(`/api/v1/workflows/${id}`);
  }

  async createWorkflow(request: WorkflowCreate): Promise<Workflow> {
    return this.fetch<Workflow>('/api/v1/workflows', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async updateWorkflow(id: string, request: Partial<WorkflowCreate>): Promise<Workflow> {
    return this.fetch<Workflow>(`/api/v1/workflows/${id}`, {
      method: 'PUT',
      body: JSON.stringify(request),
    });
  }

  async deleteWorkflow(id: string): Promise<void> {
    await this.fetch(`/api/v1/workflows/${id}`, { method: 'DELETE' });
  }

  async executeWorkflow(id: string): Promise<void> {
    await this.fetch(`/api/v1/workflows/${id}/execute`, { method: 'POST' });
  }

  async pauseWorkflow(id: string): Promise<void> {
    await this.fetch(`/api/v1/workflows/${id}/pause`, { method: 'POST' });
  }

  // ACS API
  async listIndexes(stackId: string): Promise<ACSIndex[]> {
    const result = await this.fetch<{ indexes: ACSIndex[] }>(`/${stackId}/adminconfig/v2/indexes`);
    return result.indexes;
  }

  async createIndex(stackId: string, name: string, datatype = 'event'): Promise<ACSIndex> {
    return this.fetch<ACSIndex>(`/${stackId}/adminconfig/v2/indexes`, {
      method: 'POST',
      body: JSON.stringify({ name, datatype }),
    });
  }

  async deleteIndex(stackId: string, name: string): Promise<void> {
    await this.fetch(`/${stackId}/adminconfig/v2/indexes/${name}`, { method: 'DELETE' });
  }

  async listHECTokens(stackId: string): Promise<ACSHECToken[]> {
    const result = await this.fetch<{ 'http-event-collectors': ACSHECToken[] }>(
      `/${stackId}/adminconfig/v2/inputs/http-event-collectors`
    );
    return result['http-event-collectors'] || [];
  }

  async createHECToken(stackId: string, name: string, defaultIndex = 'main'): Promise<ACSHECToken> {
    return this.fetch<ACSHECToken>(`/${stackId}/adminconfig/v2/inputs/http-event-collectors`, {
      method: 'POST',
      body: JSON.stringify({ name, defaultIndex }),
    });
  }

  async deleteHECToken(stackId: string, name: string): Promise<void> {
    await this.fetch(`/${stackId}/adminconfig/v2/inputs/http-event-collectors/${name}`, { method: 'DELETE' });
  }
}
