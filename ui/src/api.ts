import axios from 'axios';
import type {
  Instance,
  InstanceCreate,
  ThreatActor,
  AttackCampaign,
  AttackStep,
  AttackScenario,
  CampaignCreateRequest,
  ACSIndex,
  ACSHECToken,
} from './types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Instance API
export const instancesApi = {
  list: async (): Promise<Instance[]> => {
    const { data } = await api.get('/v1/instances');
    return data.instances;
  },

  get: async (id: string): Promise<Instance> => {
    const { data } = await api.get(`/v1/instances/${id}`);
    return data;
  },

  create: async (request: InstanceCreate): Promise<Instance> => {
    const { data } = await api.post('/v1/instances', request);
    return data;
  },

  start: async (id: string): Promise<void> => {
    await api.post(`/v1/instances/${id}/start`);
  },

  stop: async (id: string): Promise<void> => {
    await api.post(`/v1/instances/${id}/stop`);
  },

  destroy: async (id: string): Promise<void> => {
    await api.delete(`/v1/instances/${id}`);
  },

  waitForReady: async (id: string): Promise<Instance> => {
    const { data } = await api.get(`/v1/instances/${id}/wait`);
    return data;
  },

  getHealth: async (id: string): Promise<{ status: string }> => {
    const { data } = await api.get(`/v1/instances/${id}/health`);
    return data;
  },

  getLogs: async (id: string, tail = 100): Promise<string> => {
    const { data } = await api.get(`/v1/instances/${id}/logs`, {
      params: { tail },
    });
    return data.logs;
  },

  extend: async (id: string, hours: number): Promise<Instance> => {
    const { data } = await api.post(`/v1/instances/${id}/extend`, { hours });
    return data;
  },
};

// Attack Simulation API
export const attacksApi = {
  listThreatActors: async (): Promise<ThreatActor[]> => {
    const { data } = await api.get('/v1/attacks/threat-actors');
    return data.threat_actors;
  },

  getThreatActor: async (id: string): Promise<ThreatActor> => {
    const { data } = await api.get(`/v1/attacks/threat-actors/${id}`);
    return data;
  },

  listCampaigns: async (instanceId?: string): Promise<AttackCampaign[]> => {
    const { data } = await api.get('/v1/attacks/campaigns', {
      params: instanceId ? { instance_id: instanceId } : {},
    });
    return data.campaigns;
  },

  getCampaign: async (id: string): Promise<AttackCampaign> => {
    const { data } = await api.get(`/v1/attacks/campaigns/${id}`);
    return data;
  },

  createCampaign: async (request: CampaignCreateRequest): Promise<AttackCampaign> => {
    const { data } = await api.post('/v1/attacks/campaigns', request);
    return data;
  },

  startCampaign: async (id: string): Promise<AttackCampaign> => {
    const { data } = await api.post(`/v1/attacks/campaigns/${id}/start`);
    return data;
  },

  pauseCampaign: async (id: string): Promise<AttackCampaign> => {
    const { data } = await api.post(`/v1/attacks/campaigns/${id}/pause`);
    return data;
  },

  getCampaignSteps: async (id: string): Promise<AttackStep[]> => {
    const { data } = await api.get(`/v1/attacks/campaigns/${id}/steps`);
    return data;
  },

  getCampaignLogs: async (id: string, limit = 1000): Promise<Record<string, unknown>[]> => {
    const { data } = await api.get(`/v1/attacks/campaigns/${id}/logs`, {
      params: { limit },
    });
    return data.logs;
  },

  listScenarios: async (): Promise<AttackScenario[]> => {
    const { data } = await api.get('/v1/attacks/scenarios');
    return data;
  },

  executeScenario: async (scenarioId: string, targetInstanceId: string): Promise<AttackCampaign> => {
    const { data } = await api.post(`/v1/attacks/scenarios/${scenarioId}/execute`, null, {
      params: { target_instance_id: targetInstanceId },
    });
    return data;
  },
};

// ACS API (for a specific instance)
export const createAcsApi = (stackId: string) => ({
  listIndexes: async (): Promise<ACSIndex[]> => {
    const { data } = await api.get(`/${stackId}/adminconfig/v2/indexes`);
    return data.indexes;
  },

  createIndex: async (name: string, datatype = 'event', searchableDays = 90): Promise<ACSIndex> => {
    const { data } = await api.post(`/${stackId}/adminconfig/v2/indexes`, {
      name,
      datatype,
      searchableDays,
    });
    return data;
  },

  deleteIndex: async (name: string): Promise<void> => {
    await api.delete(`/${stackId}/adminconfig/v2/indexes/${name}`);
  },

  listHecTokens: async (): Promise<ACSHECToken[]> => {
    const { data } = await api.get(`/${stackId}/adminconfig/v2/inputs/http-event-collectors`);
    return data['http-event-collectors'] || [];
  },

  createHecToken: async (name: string, defaultIndex = 'main'): Promise<ACSHECToken> => {
    const { data } = await api.post(`/${stackId}/adminconfig/v2/inputs/http-event-collectors`, {
      name,
      defaultIndex,
      indexes: [defaultIndex],
    });
    return data;
  },

  deleteHecToken: async (name: string): Promise<void> => {
    await api.delete(`/${stackId}/adminconfig/v2/inputs/http-event-collectors/${name}`);
  },
});

// Health check
export const healthApi = {
  check: async (): Promise<{ status: string }> => {
    const { data } = await api.get('/health');
    return data;
  },
};

export default api;
