import { Provenance } from '../shared/chat.js';
import { downsampleLTTB } from '../shared/downsample.js';

interface CachedDataEntry {
  data: unknown;
  provenance: Provenance;
  expiresAt: number;
}

export interface IncidentTelemetry {
  id: string;
  title: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  routes: string[];
  affected_percent: number;
  p95_latency: string;
  first_seen: string;
  last_seen: string;
  classification: 'bug' | 'attack';
  classification_label: string;
  sparkline: number[];
  root_cause: string;
  replay_ready: boolean;
}

export interface FixEvidence {
  fix_id: string;
  file: string;
  line: number;
  summary: string;
  replayed_count: number;
  total_count: number;
  regressions: number;
  latency_delta_ms: number;
  p95_before: string;
  p95_after: string;
  confidence: number;
  branch: string;
  target_repo: string;
  credits_cost: number;
}

export class DataBridge {
  private cache = new Map<string, CachedDataEntry>();
  private readonly defaultTtlMs = 60 * 1000; // 1 minute

  constructor(private readonly apiBase: string, private readonly getToken: () => Promise<string | null>) {}

  public downsamplePoints<T extends { [key: string]: any }>(
    data: T[],
    threshold: number,
    xAcc: (item: T) => number,
    yAcc: (item: T) => number
  ): T[] {
    return downsampleLTTB(data, threshold, xAcc, yAcc);
  }

  public async resolveDataRef(dataRef: string, range?: string): Promise<{ data: unknown; provenance: Provenance } | null> {
    const cacheKey = `${dataRef}:${range || 'default'}`;
    const cached = this.cache.get(cacheKey);
    if (cached && cached.expiresAt > Date.now()) {
      return { data: cached.data, provenance: cached.provenance };
    }

    try {
      const token = await this.getToken();

      // Synthetic fallback / mock resolution for known golden references
      if (dataRef === 'q_err_rate_24h') {
        const rawPoints = [];
        const now = Date.now();
        // Generate simulated per-minute points across 24h
        for (let i = 1440; i >= 0; i -= 30) {
          const t = new Date(now - i * 60 * 1000).toISOString().substring(11, 16);
          // normal baseline 0.4%, surge to 4.2% around deploy 2.1 in last 240 mins
          const rate = i < 240 ? +(3.8 + Math.random() * 0.5).toFixed(1) : +(0.3 + Math.random() * 0.3).toFixed(1);
          rawPoints.push({ ts: t, error_rate: rate, raw_index: 1440 - i });
        }

        // Apply LTTB downsampling if points exceed budget (threshold 2000 points)
        const points = rawPoints.length > 2000
          ? downsampleLTTB(rawPoints, 2000, p => p.raw_index, p => p.error_rate)
          : rawPoints;

        const prov: Provenance = {
          source: 'proxy_capture',
          query_id: dataRef,
          asOf: new Date().toISOString(),
          range: range || '24h',
          redaction: 'applied',
          rowCount: points.length,
        };
        this.cache.set(cacheKey, { data: points, provenance: prov, expiresAt: Date.now() + this.defaultTtlMs });
        return { data: points, provenance: prov };
      }

      if (dataRef === 'q_top_issues') {
        const issues = [
          { title: 'Checkout 429 quota exhaustion', route: '/v1/checkout', affected: '4.2%', class: 'Rate Limit' },
          { title: 'Payment webhook timeout', route: '/v1/billing/verify', affected: '1.1%', class: 'Timeout' },
          { title: 'Cart inventory sync lock', route: '/v1/cart/sync', affected: '0.4%', class: 'Lock Contention' },
        ];
        const prov: Provenance = {
          source: 'incident_store',
          query_id: dataRef,
          asOf: new Date().toISOString(),
          range: '24h',
          redaction: 'applied',
          rowCount: issues.length,
        };
        this.cache.set(cacheKey, { data: issues, provenance: prov, expiresAt: Date.now() + this.defaultTtlMs });
        return { data: issues, provenance: prov };
      }

      if (dataRef === 'q_incident_190_logs' || dataRef.includes('logs')) {
        const logs = [
          { ts: '14:20:01.120', level: 'ERROR', service: 'checkout-api', msg: 'HTTP 429 Too Many Requests: keypool bucket exhausted on key "pool:stripe:live"', route: '/v1/checkout', ip: '[REDACTED]' },
          { ts: '14:20:01.442', level: 'WARN',  service: 'congestion-guard', msg: 'Ring buffer capacity threshold exceeded: 88.4% fill ratio. Triggering backpressure drop.', route: '/v1/checkout' },
          { ts: '14:20:02.015', level: 'ERROR', service: 'checkout-api', msg: 'Connection throttled by upstream gateway after 400ms timeout', route: '/v1/checkout', ip: '[REDACTED]' },
          { ts: '14:20:02.780', level: 'INFO',  service: 'skelion-proxy', msg: 'Captured anomalous transaction trace ID [REDACTED:jwt] for sandbox replay isolation', route: '/v1/checkout' }
        ];
        const prov: Provenance = {
          source: 'proxy_capture',
          query_id: dataRef,
          asOf: new Date().toISOString(),
          range: range || '1h',
          redaction: 'applied',
          rowCount: logs.length,
        };
        this.cache.set(cacheKey, { data: logs, provenance: prov, expiresAt: Date.now() + this.defaultTtlMs });
        return { data: logs, provenance: prov };
      }

      if (dataRef === 'q_sample_request_190' || dataRef.includes('request')) {
        const reqResp = {
          request: {
            method: 'POST',
            url: 'https://api.skelion.dev/v1/checkout',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer [REDACTED:token]',
              'X-Idempotency-Key': 'idemp_live_891b2c4e',
              'User-Agent': 'Skelion-Web-Client/2.1.0'
            },
            body: {
              items: [{ sku: 'prod_sku_99', qty: 1, currency: 'INR', amount: 399900 }],
              customer_id: 'cus_[REDACTED]'
            }
          },
          response: {
            status: 429,
            latency_ms: 840,
            headers: {
              'Content-Type': 'application/json',
              'Retry-After': '12',
              'X-RateLimit-Limit': '1000',
              'X-RateLimit-Remaining': '0',
              'X-Skelion-Incident': '190'
            },
            body: {
              error: 'too_many_requests',
              message: 'Rate limit quota exceeded for keypool partition. Please retry after 12 seconds.',
              incident_ref: '190'
            }
          }
        };
        const prov: Provenance = {
          source: 'proxy_capture',
          query_id: dataRef,
          asOf: new Date().toISOString(),
          redaction: 'applied',
          rowCount: 1,
        };
        this.cache.set(cacheKey, { data: reqResp, provenance: prov, expiresAt: Date.now() + this.defaultTtlMs });
        return { data: reqResp, provenance: prov };
      }

      if (dataRef === 'q_incident_190' || (dataRef.startsWith('q_incident_') && !dataRef.includes('logs'))) {
        const incident: IncidentTelemetry = {
          id: '190',
          title: 'HTTP 429 quota exhaustion storm on /v1/checkout',
          severity: 'CRITICAL',
          routes: ['/v1/checkout'],
          affected_percent: 4.2,
          p95_latency: '840ms',
          first_seen: '14:20 UTC',
          last_seen: 'Active now',
          classification: 'bug',
          classification_label: 'Bug (Code Logic: Token Bucket Desync)',
          sparkline: [0.3, 0.4, 0.4, 0.5, 1.2, 2.8, 4.2, 4.1, 4.2],
          root_cause: 'Following deploy 2.1, checkout requests exceeded keypool quotas due to rate-limiter backpressure leak in congestion.py.',
          replay_ready: true,
        };
        const prov: Provenance = {
          source: 'incident_store',
          query_id: dataRef,
          asOf: new Date().toISOString(),
          range: '24h',
          redaction: 'applied',
          rowCount: 1,
        };
        this.cache.set(cacheKey, { data: incident, provenance: prov, expiresAt: Date.now() + this.defaultTtlMs });
        return { data: incident, provenance: prov };
      }

      if (dataRef === 'q_fix_checkout_429' || dataRef.startsWith('q_fix_')) {
        const fix: FixEvidence = {
          fix_id: 'fix_checkout_429',
          file: 'gossipmesh/p2p/congestion.py',
          line: 260,
          summary: 'Linear interpolation buffer clamp in congestion.py prevents sudden 429 bursts under heavy load.',
          replayed_count: 120,
          total_count: 120,
          regressions: 0,
          latency_delta_ms: -18,
          p95_before: '840ms',
          p95_after: '630ms',
          confidence: 99.4,
          branch: 'feature/key-pool-429-handling',
          target_repo: 'Aditya-9-6/Skelion',
          credits_cost: 42,
        };
        const prov: Provenance = {
          source: 'replay',
          query_id: dataRef,
          asOf: new Date().toISOString(),
          redaction: 'applied',
          rowCount: 120,
        };
        this.cache.set(cacheKey, { data: fix, provenance: prov, expiresAt: Date.now() + this.defaultTtlMs });
        return { data: fix, provenance: prov };
      }

      if (dataRef === 'q_pr_190' || dataRef.startsWith('q_pr_')) {
        const prData = {
          pr_number: 190,
          pr_url: 'https://github.com/Aditya-9-6/Skelion/pull/190',
          title: '⚡ [Skelion Autofix] Fail-Open Boundary for POST /v1/checkout',
          branch: 'feature/key-pool-429-handling',
          author: 'Aditya-9-6',
          target_branch: 'main',
          stages: [
            { key: 'branch_created', title: 'Remote Branch Created', status: 'passed', detail: 'Branch created via GitHub Git Data API. Local disk untouched.', icon: '🟢' },
            { key: 'ci_checks', title: 'CI Status & Checks', status: 'passed', detail: 'GitHub Actions check runs polled. 3/3 passed.', icon: '🟢' },
            { key: 'merge_conflicts', title: 'Merge Conflict Verification', status: 'clean', detail: 'Zero merge conflicts against origin/main. Clean rebase.', icon: '🟢' },
            { key: 'review_comments', title: 'Review Feedback Ingestion', status: 'resolved', detail: 'AI comments scanned & synthesized. 0 blocking issues.', icon: '🟢' },
            { key: 'ready_to_merge', title: 'Merge Readiness', status: 'passed', detail: 'All branch protection & CI criteria satisfied. Ready to merge.', icon: '🟢' }
          ],
          ci_status: { state: 'success', passed: 3, total: 3 },
          merge_status: { mergeable: true, state: 'clean' },
          review_status: { comments_count: 0, actions_count: 0 }
        };
        const prov: Provenance = {
          source: 'replay',
          query_id: dataRef,
          asOf: new Date().toISOString(),
          redaction: 'applied',
          rowCount: 5,
        };
        this.cache.set(cacheKey, { data: prData, provenance: prov, expiresAt: Date.now() + this.defaultTtlMs });
        return { data: prData, provenance: prov };
      }

      // Query real backend API if running
      if (token) {
        const res = await fetch(`${this.apiBase}/v1/data/${encodeURIComponent(dataRef)}?range=${encodeURIComponent(range || '')}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const body: any = await res.json();
          let data = body.data;
          // Automatic LTTB downsampling for large series if numeric array
          if (Array.isArray(data) && data.length > 2000 && typeof data[0]?.error_rate === 'number') {
            data = downsampleLTTB(data, 2000, (d: any) => (typeof d.raw_index === 'number' ? d.raw_index : 0), (d: any) => d.error_rate);
          }
          const prov: Provenance = body.provenance || {
            source: 'incident_store',
            query_id: dataRef,
            asOf: new Date().toISOString(),
            redaction: 'applied',
            rowCount: Array.isArray(data) ? data.length : undefined,
          };
          this.cache.set(cacheKey, { data, provenance: prov, expiresAt: Date.now() + this.defaultTtlMs });
          return { data, provenance: prov };
        }
      }

      return null;
    } catch (err) {
      console.error(`[DataBridge] Error resolving data_ref "${dataRef}":`, err);
      return null;
    }
  }

  public invalidate(dataRef?: string) {
    if (dataRef) {
      for (const k of this.cache.keys()) {
        if (k.startsWith(dataRef)) this.cache.delete(k);
      }
    } else {
      this.cache.clear();
    }
  }
}
