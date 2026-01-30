/**
 * Faux Splunk Cloud - Backstage Frontend Plugin
 *
 * Provides ephemeral Splunk Victoria instances for development and testing,
 * with integrated threat intelligence workflow management (MineMeld successor).
 */

export {
  fauxSplunkCloudPlugin,
  FauxSplunkCloudPage,
  EntityFauxSplunkCloudCard,
  WorkflowEditorPage,
} from './plugin';

export { FauxSplunkCloudApi, fauxSplunkCloudApiRef } from './api';

export type {
  Instance,
  InstanceCreate,
  InstanceConfig,
  InstanceEndpoints,
  InstanceCredentials,
  InstanceStatus,
  InstanceTopology,
  ThreatActor,
  AttackCampaign,
  AttackStep,
  AttackScenario,
  Workflow,
  WorkflowNode,
  WorkflowEdge,
  WorkflowPrototype,
  Indicator,
} from './types';

// Re-export route refs for external use
export { rootRouteRef, instanceRouteRef, workflowRouteRef } from './routes';
