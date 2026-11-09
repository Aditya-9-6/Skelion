import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    burst_load: {
      executor: 'ramping-arrival-rate',
      startRate: 50,
      timeUnit: '1s',
      preAllocatedVUs: 100,
      maxVUs: 500,
      stages: [
        { duration: '10s', target: 200 },
        { duration: '20s', target: 500 }, // 500 RPS burst
        { duration: '10s', target: 100 },
      ],
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<200', 'avg<150'], // <= 200ms avg latency
    http_req_failed: ['rate<0.01'],             // <= 1% error rate
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8002';

export default function () {
  // 1. Health & status endpoint
  const resLimits = http.get(`${BASE_URL}/v1/limits/status`);
  check(resLimits, {
    'limits status 200': (r) => r.status === 200,
  });

  // 2. Billing plan status
  const resPlan = http.get(`${BASE_URL}/v1/billing/plan`);
  check(resPlan, {
    'billing plan 200': (r) => r.status === 200,
  });

  sleep(0.05);
}
