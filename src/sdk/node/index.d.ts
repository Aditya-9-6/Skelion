import { Request, Response, NextFunction } from 'express';

export interface SkelionOptions {
  /**
   * Skelion Scoped API Key (e.g. skl_live_...)
   */
  apiKey?: string;

  /**
   * Skelion Control Plane Endpoint (default: http://127.0.0.1:8003 or https://api.skelion.dev)
   */
  endpoint?: string;

  /**
   * Guarantee 0 downtime: returns buffered 200 OK on 5xx errors (default: true)
   */
  failOpen?: boolean;

  /**
   * Log telemetry operations to console (default: false)
   */
  debug?: boolean;

  /**
   * Logical service name (default: "node-service")
   */
  serviceName?: string;

  /**
   * Deployment environment: "production" | "staging" | "development"
   */
  environment?: string;
}

export function skelionMiddleware(options?: SkelionOptions): (
  err: any,
  req: Request,
  res: Response,
  next: NextFunction
) => void;

export default skelionMiddleware;
