import { Router } from 'express';
import { healthHandler } from '../handlers/healthHandler';

export const healthRouter = Router();

/**
 * GET /healthz – public health endpoint.
 * Rate‑limited upstream by Spryzen WAF (5 rps per IP).
 */
healthRouter.get('/healthz', healthHandler);
