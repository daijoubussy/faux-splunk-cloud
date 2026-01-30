/**
 * Express router for Faux Splunk Cloud backend plugin.
 *
 * Proxies requests to the FastAPI backend and handles authentication.
 */

import { errorHandler } from '@backstage/backend-common';
import express, { Router, Request, Response, NextFunction } from 'express';
import { Logger } from 'winston';
import { Config } from '@backstage/config';
import { FauxSplunkCloudClient } from './client';

export interface RouterOptions {
  logger: Logger;
  config: Config;
}

/**
 * Creates the Express router for the Faux Splunk Cloud backend.
 */
export async function createRouter(options: RouterOptions): Promise<Router> {
  const { logger, config } = options;

  const baseUrl = config.getOptionalString('fauxSplunkCloud.baseUrl') ?? 'http://localhost:8000';
  const client = new FauxSplunkCloudClient(baseUrl, logger);

  const router = Router();
  router.use(express.json());

  // Health check endpoint
  router.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok' });
  });

  // ==========================================================================
  // Instance Management
  // ==========================================================================

  // List instances
  router.get('/instances', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const status = req.query.status as string | undefined;
      const instances = await client.listInstances(status);
      res.json({ instances });
    } catch (error) {
      next(error);
    }
  });

  // Create instance
  router.post('/instances', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const instance = await client.createInstance(req.body);
      res.status(201).json(instance);
    } catch (error) {
      next(error);
    }
  });

  // Get instance
  router.get('/instances/:id', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const instance = await client.getInstance(req.params.id);
      if (!instance) {
        res.status(404).json({ error: 'Instance not found' });
        return;
      }
      res.json(instance);
    } catch (error) {
      next(error);
    }
  });

  // Start instance
  router.post('/instances/:id/start', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const instance = await client.startInstance(req.params.id);
      res.json(instance);
    } catch (error) {
      next(error);
    }
  });

  // Stop instance
  router.post('/instances/:id/stop', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const instance = await client.stopInstance(req.params.id);
      res.json(instance);
    } catch (error) {
      next(error);
    }
  });

  // Delete instance
  router.delete('/instances/:id', async (req: Request, res: Response, next: NextFunction) => {
    try {
      await client.destroyInstance(req.params.id);
      res.status(204).send();
    } catch (error) {
      next(error);
    }
  });

  // Extend instance TTL
  router.post('/instances/:id/extend', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { hours } = req.body;
      const instance = await client.extendTTL(req.params.id, hours);
      res.json(instance);
    } catch (error) {
      next(error);
    }
  });

  // Get instance health
  router.get('/instances/:id/health', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const health = await client.getInstanceHealth(req.params.id);
      res.json(health);
    } catch (error) {
      next(error);
    }
  });

  // Get instance logs
  router.get('/instances/:id/logs', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const tail = parseInt(req.query.tail as string) || 100;
      const logs = await client.getInstanceLogs(req.params.id, tail);
      res.json({ logs });
    } catch (error) {
      next(error);
    }
  });

  // ==========================================================================
  // Attack Simulation
  // ==========================================================================

  // List threat actors
  router.get('/attacks/actors', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const level = req.query.level as string | undefined;
      const actors = await client.listThreatActors(level);
      res.json({ actors });
    } catch (error) {
      next(error);
    }
  });

  // Get threat actor
  router.get('/attacks/actors/:id', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const actor = await client.getThreatActor(req.params.id);
      if (!actor) {
        res.status(404).json({ error: 'Threat actor not found' });
        return;
      }
      res.json(actor);
    } catch (error) {
      next(error);
    }
  });

  // List campaigns
  router.get('/attacks/campaigns', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const instanceId = req.query.instanceId as string | undefined;
      const campaigns = await client.listCampaigns(instanceId);
      res.json({ campaigns });
    } catch (error) {
      next(error);
    }
  });

  // Create campaign
  router.post('/attacks/campaigns', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { threatActorId, instanceId } = req.body;
      const campaign = await client.createCampaign(threatActorId, instanceId);
      res.status(201).json(campaign);
    } catch (error) {
      next(error);
    }
  });

  // Get campaign
  router.get('/attacks/campaigns/:id', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const campaign = await client.getCampaign(req.params.id);
      if (!campaign) {
        res.status(404).json({ error: 'Campaign not found' });
        return;
      }
      res.json(campaign);
    } catch (error) {
      next(error);
    }
  });

  // Start campaign
  router.post('/attacks/campaigns/:id/start', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const campaign = await client.startCampaign(req.params.id);
      res.json(campaign);
    } catch (error) {
      next(error);
    }
  });

  // Pause campaign
  router.post('/attacks/campaigns/:id/pause', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const campaign = await client.pauseCampaign(req.params.id);
      res.json(campaign);
    } catch (error) {
      next(error);
    }
  });

  // List scenarios
  router.get('/attacks/scenarios', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const scenarios = await client.listScenarios();
      res.json({ scenarios });
    } catch (error) {
      next(error);
    }
  });

  // Execute scenario
  router.post('/attacks/scenarios/:id/execute', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { instanceId } = req.body;
      const campaign = await client.executeScenario(req.params.id, instanceId);
      res.status(201).json(campaign);
    } catch (error) {
      next(error);
    }
  });

  // ==========================================================================
  // Workflows (MineMeld)
  // ==========================================================================

  // List workflows
  router.get('/workflows', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const workflows = await client.listWorkflows();
      res.json({ workflows });
    } catch (error) {
      next(error);
    }
  });

  // Create workflow
  router.post('/workflows', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { name, description } = req.body;
      const workflow = await client.createWorkflow(name, description);
      res.status(201).json(workflow);
    } catch (error) {
      next(error);
    }
  });

  // Get workflow
  router.get('/workflows/:id', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const workflow = await client.getWorkflow(req.params.id);
      if (!workflow) {
        res.status(404).json({ error: 'Workflow not found' });
        return;
      }
      res.json(workflow);
    } catch (error) {
      next(error);
    }
  });

  // Update workflow
  router.put('/workflows/:id', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const workflow = await client.updateWorkflow(req.params.id, req.body);
      res.json(workflow);
    } catch (error) {
      next(error);
    }
  });

  // Delete workflow
  router.delete('/workflows/:id', async (req: Request, res: Response, next: NextFunction) => {
    try {
      await client.deleteWorkflow(req.params.id);
      res.status(204).send();
    } catch (error) {
      next(error);
    }
  });

  // Execute workflow
  router.post('/workflows/:id/execute', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const workflow = await client.executeWorkflow(req.params.id);
      res.json(workflow);
    } catch (error) {
      next(error);
    }
  });

  // Pause workflow
  router.post('/workflows/:id/pause', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const workflow = await client.pauseWorkflow(req.params.id);
      res.json(workflow);
    } catch (error) {
      next(error);
    }
  });

  // List prototypes
  router.get('/workflows/prototypes', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const prototypes = await client.listPrototypes();
      res.json({ prototypes });
    } catch (error) {
      next(error);
    }
  });

  // ==========================================================================
  // ACS Operations
  // ==========================================================================

  // Execute ACS operation
  router.post('/acs/:instanceId', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { method, path, body } = req.body;
      const result = await client.executeAcsOperation(
        req.params.instanceId,
        method,
        path,
        body,
      );
      res.json(result);
    } catch (error) {
      next(error);
    }
  });

  // Error handler
  router.use(errorHandler());

  logger.info('Faux Splunk Cloud backend router initialized');
  return router;
}
