/**
 * Route references for the Faux Splunk Cloud plugin.
 */

import { createRouteRef, createSubRouteRef } from '@backstage/core-plugin-api';

/**
 * Root route for the plugin.
 */
export const rootRouteRef = createRouteRef({
  id: 'faux-splunk-cloud',
});

/**
 * Route for individual instance details.
 */
export const instanceRouteRef = createSubRouteRef({
  id: 'faux-splunk-cloud/instance',
  parent: rootRouteRef,
  path: '/instances/:instanceId',
});

/**
 * Route for workflow editor.
 */
export const workflowRouteRef = createSubRouteRef({
  id: 'faux-splunk-cloud/workflow',
  parent: rootRouteRef,
  path: '/workflows/:workflowId',
});

/**
 * Route for attack campaigns.
 */
export const campaignRouteRef = createSubRouteRef({
  id: 'faux-splunk-cloud/campaign',
  parent: rootRouteRef,
  path: '/campaigns/:campaignId',
});

/**
 * Route for ACS API explorer.
 */
export const acsExplorerRouteRef = createSubRouteRef({
  id: 'faux-splunk-cloud/acs',
  parent: rootRouteRef,
  path: '/acs/:stackId?',
});
