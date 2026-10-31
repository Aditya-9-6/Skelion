# skelion-node

> Official Drop-in Fail-Open Resilience & Telemetry Middleware for Express & Node.js

Intercepts unhandled edge crashes fail-open, scrubs PII, and streams sanitized telemetry to **Skelion SaaS** for autonomous AST patch generation and replay verification.

## Installation

```bash
npm install skelion-node
```

## Quickstart

Add 2 lines to your Express application after your API routes:

```javascript
const express = require('express');
const { skelionMiddleware } = require('skelion-node');

const app = express();
app.use(express.json());

// Your normal application routes
app.post('/api/orders/checkout', (req, res) => {
  // If an unhandled exception or third-party outage occurs here:
  throw new Error('Payment gateway timeout');
});

// Mount Skelion Error Boundary Middleware
app.use(skelionMiddleware({
  apiKey: process.env.SKELION_API_KEY, // skl_live_...
  failOpen: true                       // Returns buffered 200 OK so end-users never see 500 downtime
}));

app.listen(3000, () => console.log('Server running on port 3000'));
```

## Features

- **Guaranteed Fail-Open:** Never crashes or blocks user traffic. Buffers failed requests with synthetic fallbacks.
- **Zero-PII Scrubbing:** Authorization headers, cookies, passwords, and credit card patterns are masked client-side before dispatch.
- **Deterministic Error Fingerprinting:** Crash groups are deduplicated automatically in the Skelion dashboard.
- **Autonomous Patch Synthesis:** Integrates with Skelion GitHub bot to open 0-regression pull requests for verified fixes.

## Configuration Options

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `apiKey` | `string` | `process.env.SKELION_API_KEY` | Scoped API key (`skl_live_...`) |
| `endpoint` | `string` | `http://127.0.0.1:8003` | Skelion SaaS Ingress URL |
| `failOpen` | `boolean` | `true` | Return buffered 200 instead of unhandled 500 |
| `debug` | `boolean` | `false` | Enable console telemetry logging |

## License

Apache-2.0
