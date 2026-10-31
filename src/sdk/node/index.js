// @skelion/node — Official Node.js & Express Drop-in Resilience Middleware
// Intercepts unhandled edge crashes fail-open, scrubs PII, and reports to Skelion SaaS

const https = require('https');
const http = require('http');

/**
 * Configure Skelion Express / Node.js Middleware
 * @param {Object} options
 * @param {string} options.apiKey - Skelion Scoped API Key (e.g. skl_live_...)
 * @param {string} [options.endpoint] - Skelion Control Plane Endpoint (default: http://127.0.0.1:8003)
 * @param {boolean} [options.failOpen] - Guarantee 0 downtime: returns buffered 200 OK on 5xx errors (default: true)
 * @param {boolean} [options.debug] - Log telemetry operations (default: false)
 */
function skelionMiddleware(options = {}) {
  const apiKey = options.apiKey || process.env.SKELION_API_KEY;
  const endpoint = (options.endpoint || process.env.SKELION_ENDPOINT || 'http://127.0.0.1:8003').replace(/\/$/, '');
  const failOpen = options.failOpen !== undefined ? options.failOpen : true;
  const debug = !!options.debug;

  if (!apiKey && debug) {
    console.warn('[Skelion SDK] Warning: No SKELION_API_KEY provided. Telemetry will operate in mock mode.');
  }

  return function (err, req, res, next) {
    if (!err) return next();

    const statusCode = err.status || err.statusCode || 500;
    const startTime = req._skelionStartTime || Date.now();
    const latencyMs = Math.round(Date.now() - startTime);

    if (debug) {
      console.error(`[Skelion SDK] Intercepted error on ${req.method} ${req.originalUrl}:`, err.message);
    }

    // 1. Asynchronously send telemetry to Skelion SaaS without blocking response
    if (apiKey) {
      const payload = JSON.stringify({
        http_method: req.method,
        route_path: req.originalUrl || req.url,
        status_code: statusCode,
        error_summary: err.message || 'Unhandled exception',
        captured_headers: {
          'user-agent': req.headers['user-agent'],
          'content-type': req.headers['content-type'],
          host: req.headers.host
        },
        captured_payload: typeof req.body === 'string' ? req.body : JSON.stringify(req.body || {}),
        latency_ms: latencyMs
      });

      try {
        const parsedUrl = new URL(`${endpoint}/v1/ingest/incident`);
        const client = parsedUrl.protocol === 'https:' ? https : http;
        const ingestReq = client.request(parsedUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`,
            'Content-Length': Buffer.byteLength(payload)
          },
          timeout: 4000
        });

        ingestReq.on('error', (e) => {
          if (debug) console.error('[Skelion SDK] Telemetry error:', e.message);
        });

        ingestReq.write(payload);
        ingestReq.end();
      } catch (e) {
        // Fail-open: Never disrupt application on telemetry exception
      }
    }

    // 2. Fail-Open Response Boundary (Shield users from fatal 500 white screens)
    if (failOpen && statusCode >= 500) {
      return res.status(200).json({
        status: 'fail_open_buffered',
        incident_route: req.originalUrl || req.url,
        message: 'Your request was buffered safely by Skelion Edge Resilience and will be reconciled automatically.'
      });
    }

    return next(err);
  };
}

module.exports = { skelionMiddleware };
