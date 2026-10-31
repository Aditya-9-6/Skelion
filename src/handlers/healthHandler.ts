/**
 * Health‑check handler – returns a minimal JSON payload.
 * Exposed publicly; used by load‑balancers & monitoring.
 */
import { Request, Response } from 'express';

export const healthHandler = (_req: Request, res: Response): void => {
  // No PII, no heavy processing – safe for fail‑open proxies.
  res.status(200).json({ status: 'ok' });
};
