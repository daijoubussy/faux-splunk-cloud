/**
 * Faux Splunk Cloud Backend Plugin
 *
 * Bridges Backstage to the Faux Splunk Cloud FastAPI backend.
 * Handles authentication, request proxying, and data transformation.
 */

export * from './service/router';
export { fauxSplunkCloudPlugin, fauxSplunkCloudPlugin as default } from './plugin';
