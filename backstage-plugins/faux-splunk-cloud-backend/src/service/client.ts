/**
 * HTTP client for communicating with the Faux Splunk Cloud FastAPI backend.
 */

import fetch from 'node-fetch';
import { Logger } from 'winston';

/**
 * Client for the Faux Splunk Cloud Python backend.
 */
export class FauxSplunkCloudClient {
  private baseUrl: string;
  private logger: Logger;

  constructor(baseUrl: string, logger: Logger) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.logger = logger;
  }

  /**
   * Make an HTTP request to the backend.
   */
  private async request<T>(
    method: string,
    path: string,
    body?: Record<string, unknown>,
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    this.logger.debug(`${method} ${url}`);

    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    if (!response.ok) {
      const errorBody = await response.text();
      this.logger.error(`Backend error: ${response.status} - ${errorBody}`);
      throw new Error(`Backend returned ${response.status}: ${errorBody}`);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }

  // ==========================================================================
  // Instance Management
  // ==========================================================================

  async listInstances(status?: string): Promise<unknown[]> {
    const path = status
      ? `/api/v1/instances?status=${encodeURIComponent(status)}`
      : '/api/v1/instances';
    const result = await this.request<{ instances: unknown[] }>('GET', path);
    return result.instances || [];
  }

  async createInstance(data: Record<string, unknown>): Promise<unknown> {
    return this.request('POST', '/api/v1/instances', data);
  }

  async getInstance(id: string): Promise<unknown> {
    try {
      return await this.request('GET', `/api/v1/instances/${id}`);
    } catch (error) {
      if ((error as Error).message.includes('404')) {
        return null;
      }
      throw error;
    }
  }

  async startInstance(id: string): Promise<unknown> {
    return this.request('POST', `/api/v1/instances/${id}/start`);
  }

  async stopInstance(id: string): Promise<unknown> {
    return this.request('POST', `/api/v1/instances/${id}/stop`);
  }

  async destroyInstance(id: string): Promise<void> {
    await this.request('DELETE', `/api/v1/instances/${id}`);
  }

  async extendTTL(id: string, hours: number): Promise<unknown> {
    return this.request('POST', `/api/v1/instances/${id}/extend`, { hours });
  }

  async getInstanceHealth(id: string): Promise<unknown> {
    return this.request('GET', `/api/v1/instances/${id}/health`);
  }

  async getInstanceLogs(id: string, tail: number): Promise<string> {
    const result = await this.request<{ logs: string }>(
      'GET',
      `/api/v1/instances/${id}/logs?tail=${tail}`,
    );
    return result.logs || '';
  }

  // ==========================================================================
  // Attack Simulation
  // ==========================================================================

  async listThreatActors(level?: string): Promise<unknown[]> {
    const path = level
      ? `/api/v1/attacks/actors?level=${encodeURIComponent(level)}`
      : '/api/v1/attacks/actors';
    const result = await this.request<{ actors: unknown[] }>('GET', path);
    return result.actors || [];
  }

  async getThreatActor(id: string): Promise<unknown> {
    try {
      return await this.request('GET', `/api/v1/attacks/actors/${id}`);
    } catch (error) {
      if ((error as Error).message.includes('404')) {
        return null;
      }
      throw error;
    }
  }

  async listCampaigns(instanceId?: string): Promise<unknown[]> {
    const path = instanceId
      ? `/api/v1/attacks/campaigns?instance_id=${encodeURIComponent(instanceId)}`
      : '/api/v1/attacks/campaigns';
    const result = await this.request<{ campaigns: unknown[] }>('GET', path);
    return result.campaigns || [];
  }

  async createCampaign(threatActorId: string, instanceId: string): Promise<unknown> {
    return this.request('POST', '/api/v1/attacks/campaigns', {
      threat_actor_id: threatActorId,
      target_instance_id: instanceId,
    });
  }

  async getCampaign(id: string): Promise<unknown> {
    try {
      return await this.request('GET', `/api/v1/attacks/campaigns/${id}`);
    } catch (error) {
      if ((error as Error).message.includes('404')) {
        return null;
      }
      throw error;
    }
  }

  async startCampaign(id: string): Promise<unknown> {
    return this.request('POST', `/api/v1/attacks/campaigns/${id}/start`);
  }

  async pauseCampaign(id: string): Promise<unknown> {
    return this.request('POST', `/api/v1/attacks/campaigns/${id}/pause`);
  }

  async listScenarios(): Promise<unknown[]> {
    const result = await this.request<{ scenarios: unknown[] }>('GET', '/api/v1/attacks/scenarios');
    return result.scenarios || [];
  }

  async executeScenario(scenarioId: string, instanceId: string): Promise<unknown> {
    return this.request('POST', `/api/v1/attacks/scenarios/${scenarioId}/execute`, {
      instance_id: instanceId,
    });
  }

  // ==========================================================================
  // Workflows
  // ==========================================================================

  async listWorkflows(): Promise<unknown[]> {
    const result = await this.request<{ workflows: unknown[] }>('GET', '/api/v1/workflows');
    return result.workflows || [];
  }

  async createWorkflow(name: string, description: string): Promise<unknown> {
    return this.request('POST', '/api/v1/workflows', { name, description });
  }

  async getWorkflow(id: string): Promise<unknown> {
    try {
      return await this.request('GET', `/api/v1/workflows/${id}`);
    } catch (error) {
      if ((error as Error).message.includes('404')) {
        return null;
      }
      throw error;
    }
  }

  async updateWorkflow(id: string, data: Record<string, unknown>): Promise<unknown> {
    return this.request('PUT', `/api/v1/workflows/${id}`, data);
  }

  async deleteWorkflow(id: string): Promise<void> {
    await this.request('DELETE', `/api/v1/workflows/${id}`);
  }

  async executeWorkflow(id: string): Promise<unknown> {
    return this.request('POST', `/api/v1/workflows/${id}/execute`);
  }

  async pauseWorkflow(id: string): Promise<unknown> {
    return this.request('POST', `/api/v1/workflows/${id}/pause`);
  }

  async listPrototypes(): Promise<unknown[]> {
    const result = await this.request<{ prototypes: unknown[] }>('GET', '/api/v1/workflows/prototypes');
    return result.prototypes || [];
  }

  // ==========================================================================
  // ACS Operations
  // ==========================================================================

  async executeAcsOperation(
    instanceId: string,
    method: string,
    path: string,
    body?: Record<string, unknown>,
  ): Promise<unknown> {
    return this.request('POST', `/api/v1/instances/${instanceId}/acs`, {
      method,
      path,
      body,
    });
  }
}
