/**
 * Faux Splunk Cloud Backend Plugin definition.
 *
 * Uses the new Backstage backend system API.
 */

import {
  coreServices,
  createBackendPlugin,
} from '@backstage/backend-plugin-api';
import { createRouter } from './service/router';

/**
 * The Faux Splunk Cloud backend plugin.
 */
export const fauxSplunkCloudPlugin = createBackendPlugin({
  pluginId: 'faux-splunk-cloud',
  register(env) {
    env.registerInit({
      deps: {
        httpRouter: coreServices.httpRouter,
        logger: coreServices.logger,
        config: coreServices.rootConfig,
      },
      async init({ httpRouter, logger, config }) {
        httpRouter.use(
          await createRouter({
            logger,
            config,
          }),
        );
        httpRouter.addAuthPolicy({
          path: '/health',
          allow: 'unauthenticated',
        });
      },
    });
  },
});
