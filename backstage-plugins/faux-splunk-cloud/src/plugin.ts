/**
 * Faux Splunk Cloud Backstage Plugin
 *
 * This plugin provides:
 * - Ephemeral Splunk instance management
 * - Attack simulation for security testing
 * - Threat intelligence workflow editor (MineMeld successor)
 * - ACS API exploration
 */

import {
  createPlugin,
  createRoutableExtension,
  createComponentExtension,
  createApiFactory,
  discoveryApiRef,
  fetchApiRef,
} from '@backstage/core-plugin-api';

import { rootRouteRef, instanceRouteRef, workflowRouteRef } from './routes';
import { fauxSplunkCloudApiRef, FauxSplunkCloudApiClient } from './api';

/**
 * The Faux Splunk Cloud plugin instance.
 */
export const fauxSplunkCloudPlugin = createPlugin({
  id: 'faux-splunk-cloud',
  routes: {
    root: rootRouteRef,
    instance: instanceRouteRef,
    workflow: workflowRouteRef,
  },
  apis: [
    createApiFactory({
      api: fauxSplunkCloudApiRef,
      deps: { discoveryApi: discoveryApiRef, fetchApi: fetchApiRef },
      factory: ({ discoveryApi, fetchApi }) =>
        new FauxSplunkCloudApiClient({ discoveryApi, fetchApi }),
    }),
  ],
});

/**
 * Main page component for Faux Splunk Cloud.
 *
 * Provides the full management interface including:
 * - Dashboard overview
 * - Instance management
 * - Attack simulation
 * - Workflow editor
 */
export const FauxSplunkCloudPage = fauxSplunkCloudPlugin.provide(
  createRoutableExtension({
    name: 'FauxSplunkCloudPage',
    component: () =>
      import('./components/FauxSplunkCloudPage').then(m => m.FauxSplunkCloudPage),
    mountPoint: rootRouteRef,
  }),
);

/**
 * Card component for embedding in entity pages.
 *
 * Shows instance status and quick actions for a catalog entity.
 */
export const EntityFauxSplunkCloudCard = fauxSplunkCloudPlugin.provide(
  createComponentExtension({
    name: 'EntityFauxSplunkCloudCard',
    component: {
      lazy: () =>
        import('./components/EntityFauxSplunkCloudCard').then(
          m => m.EntityFauxSplunkCloudCard,
        ),
    },
  }),
);

/**
 * Workflow editor component for threat intelligence pipelines.
 *
 * WYSIWYG editor for creating MineMeld-style workflows.
 */
export const WorkflowEditorPage = fauxSplunkCloudPlugin.provide(
  createRoutableExtension({
    name: 'WorkflowEditorPage',
    component: () =>
      import('./components/WorkflowEditor').then(m => m.WorkflowEditorPage),
    mountPoint: workflowRouteRef,
  }),
);
