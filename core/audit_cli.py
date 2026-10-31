# core/audit_cli.py — Skelion Production Health Audit CLI (Sales Magnet)
# Open-source core module (Apache-2.0). 100% Offline execution, Zero Egress.

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.redact import redact_text, normalize_route_path

# ---------------------------------------------------------------------------
# Log Parsers (Nginx combined, Nginx JSON, and Application JSONL)
# ---------------------------------------------------------------------------

RE_NGINX_COMBINED = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>[A-Z]+)\s+(?P<path>\S+)\s+[^\"]*"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<referer>[^\"]*)"\s+"(?P<user_agent>[^\"]*)"(?:\s+(?P<latency>[\d\.]+))?'
)


def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse an individual log entry from Nginx or JSONL."""
    line = line.strip()
    if not line:
        return None

    # 1. Try JSONL
    if line.startswith("{") and line.endswith("}"):
        try:
            data = json.loads(line)
            status = int(
                data.get("status")
                or data.get("status_code")
                or data.get("http_status")
                or 200
            )
            method = str(data.get("method") or "GET").upper()
            raw_path = str(
                data.get("path") or data.get("url") or data.get("route") or "/"
            )
            latency = float(
                data.get("latency_ms")
                or data.get("duration_ms")
                or data.get("response_time")
                or 0.0
            )
            body = str(
                data.get("body")
                or data.get("response_body")
                or data.get("error")
                or data.get("message")
                or ""
            )
            timestamp = (
                data.get("timestamp")
                or data.get("time")
                or datetime.now(timezone.utc).isoformat()
            )
            return {
                "method": method,
                "raw_path": raw_path,
                "route": normalize_route_path(raw_path.split("?")[0]),
                "status": status,
                "latency_ms": latency,
                "body": redact_text(body),
                "timestamp": timestamp,
            }
        except Exception:
            pass

    # 2. Try Nginx Combined format
    m = RE_NGINX_COMBINED.match(line)
    if m:
        d = m.groupdict()
        status = int(d["status"])
        method = d["method"]
        raw_path = d["path"]
        latency = float(d["latency"]) * 1000.0 if d.get("latency") else 12.0
        return {
            "method": method,
            "raw_path": raw_path,
            "route": normalize_route_path(raw_path.split("?")[0]),
            "status": status,
            "latency_ms": latency,
            "body": "",
            "timestamp": d["time"],
        }

    return None


# ---------------------------------------------------------------------------
# Diagnostic Analyzers
# ---------------------------------------------------------------------------


def analyze_logs(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Inspect normalized logs and detect production anomalies:
    1. Silent failures (HTTP 200 with error signatures).
    2. 5xx Server Errors & 4xx spikes.
    3. Latency regressions (p95 latency outliers).
    4. Upstream / LLM rate limit storms (429 or provider timeouts).
    """
    total_requests = len(records)
    if total_requests == 0:
        return {"total_requests": 0, "issues": [], "health_score": 100}

    route_stats = {}
    silent_failures = []
    upstream_429_errors = []
    server_5xx_errors = []

    SILENT_ERROR_PATTERNS = re.compile(
        r"(?i)\b(?:error|exception|failed|failure|traceback|undefined|unhandled|panic|timeout)\b"
    )

    for r in records:
        route = r["route"]
        status = r["status"]
        latency = r["latency_ms"]
        body = r["body"]

        if route not in route_stats:
            route_stats[route] = {"total": 0, "errors": 0, "latencies": []}

        route_stats[route]["total"] += 1
        route_stats[route]["latencies"].append(latency)

        # A. Upstream / LLM 429 Rate Limits
        if status == 429:
            route_stats[route]["errors"] += 1
            upstream_429_errors.append(r)

        # B. 5xx Server Outages
        elif status >= 500:
            route_stats[route]["errors"] += 1
            server_5xx_errors.append(r)

        # C. Silent Failures (HTTP 200 but error in response body)
        elif status == 200 and body and len(body) > 4:
            if (
                SILENT_ERROR_PATTERNS.search(body)
                or '"error":' in body
                or '"success":false' in body
            ):
                silent_failures.append(r)
                route_stats[route]["errors"] += 1

    # Formulate Ranked Issues
    issues = []

    # 1. Silent 200 Failures (Highest priority & stealth risk)
    if silent_failures:
        affected = len(silent_failures)
        pct = round((affected / total_requests) * 100, 1)
        sample = silent_failures[0]
        issues.append(
            {
                "id": "iss_silent_200",
                "title": f"Silent Business Failures: HTTP 200 with Error Payloads ({affected} requests)",
                "severity": "CRITICAL",
                "category": "silent_failure",
                "confidence": 95,
                "affected_requests": affected,
                "affected_pct": pct,
                "route": sample["route"],
                "summary": "Endpoints returning HTTP 200 OK while payload contains unhandled exception or business failure payload. Monitoring systems miss these completely.",
                "evidence": sample["body"][:250]
                if sample["body"]
                else "Response contains error JSON object",
                "recommended_fix": "Add error boundary middleware and emit non-200 status codes with structured RFC 7807 problem details.",
            }
        )

    # 2. 5xx Crashes
    if server_5xx_errors:
        affected = len(server_5xx_errors)
        pct = round((affected / total_requests) * 100, 1)
        sample = server_5xx_errors[0]
        issues.append(
            {
                "id": "iss_server_500",
                "title": f"Unhandled Production Crashes & 5xx Spikes ({affected} requests)",
                "severity": "HIGH",
                "category": "server_crash",
                "confidence": 98,
                "affected_requests": affected,
                "affected_pct": pct,
                "route": sample["route"],
                "summary": f"Server errors detected on {sample['route']}. Users are receiving 500/502/503 responses.",
                "evidence": f"HTTP {sample['status']} on {sample['method']} {sample['route']}",
                "recommended_fix": "Synthesize regression replay test and wrap route in fail-safe fallback handler.",
            }
        )

    # 3. LLM / Upstream 429 Storms
    if upstream_429_errors:
        affected = len(upstream_429_errors)
        pct = round((affected / total_requests) * 100, 1)
        sample = upstream_429_errors[0]
        issues.append(
            {
                "id": "iss_upstream_429",
                "title": f"Upstream API / LLM Rate Limit Storms ({affected} requests blocked)",
                "severity": "MEDIUM",
                "category": "rate_limit_storm",
                "confidence": 90,
                "affected_requests": affected,
                "affected_pct": pct,
                "route": sample["route"],
                "summary": "Upstream services or LLM providers are returning HTTP 429 Too Many Requests, stalling user sessions.",
                "evidence": f"HTTP 429 on {sample['route']}",
                "recommended_fix": "Enable GossipMesh multi-key rotation and exponential backoff retry jitter.",
            }
        )

    # 4. Latency Regressions (p95 > 500ms)
    for route, st in route_stats.items():
        if st["latencies"]:
            l_sorted = sorted(st["latencies"])
            p95 = l_sorted[int(len(l_sorted) * 0.95)]
            if p95 > 500.0 and st["total"] >= 5:
                issues.append(
                    {
                        "id": f"iss_latency_{abs(hash(route)) % 10000}",
                        "title": f"Latency Regression on {route} (p95: {int(p95)}ms)",
                        "severity": "MEDIUM",
                        "category": "latency_regression",
                        "confidence": 85,
                        "affected_requests": st["total"],
                        "affected_pct": round((st["total"] / total_requests) * 100, 1),
                        "route": route,
                        "summary": f"Route {route} exhibits elevated p95 latency ({int(p95)}ms), degrading user conversion and responsiveness.",
                        "evidence": f"p95 latency = {int(p95)}ms across {st['total']} sample requests",
                        "recommended_fix": "Inspect database queries and cache repetitive read operations.",
                    }
                )

    # Sort issues by severity and affected request count
    sev_weight = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    issues.sort(
        key=lambda x: (sev_weight.get(x["severity"], 0), x["affected_requests"]),
        reverse=True,
    )

    # Compute Overall Health Score (0 - 100)
    total_errors = sum(st["errors"] for st in route_stats.values())
    error_rate = (total_errors / total_requests) if total_requests > 0 else 0
    health_score = max(0, int(100 - (error_rate * 250) - (len(issues) * 10)))

    return {
        "total_requests": total_requests,
        "unique_routes": len(route_stats),
        "total_anomalies": total_errors,
        "health_score": health_score,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# HTML Report Generator (Self-Contained & Printable)
# ---------------------------------------------------------------------------


def render_html_report(project_name: str, metrics: Dict[str, Any], output_path: str):
    """Generate self-contained, publication-grade 1-page HTML health report."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    health = metrics["health_score"]
    health_color = (
        "#10b981" if health >= 85 else ("#f59e0b" if health >= 65 else "#ef4444")
    )

    issues_html = ""
    for i, iss in enumerate(metrics["issues"][:5], 1):
        badge_color = (
            "#ef4444"
            if iss["severity"] == "CRITICAL"
            else ("#f59e0b" if iss["severity"] == "HIGH" else "#3b82f6")
        )
        issues_html += f"""
        <div style="background:#111624; border:1px solid #1c2438; border-radius:10px; padding:1.2rem; margin-bottom:1rem;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
            <b style="font-size:1.05rem; color:#fff;">#{i}. {iss['title']}</b>
            <span style="background:rgba(255,255,255,0.08); color:{badge_color}; border:1px solid {badge_color}; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold;">
              {iss['severity']} &bull; {iss['confidence']}% Confidence
            </span>
          </div>
          <div style="font-size:0.85rem; color:#8b9bb4; margin-bottom:0.6rem;">{iss['summary']}</div>
          <div style="background:rgba(0,0,0,0.4); border-left:3px solid {badge_color}; padding:0.6rem 0.8rem; border-radius:4px; font-family:monospace; font-size:11.5px; color:#cfd9e8; margin-bottom:0.6rem;">
            <b>Evidence:</b> {iss['evidence']}
          </div>
          <div style="font-size:0.82rem; color:#7c5cff;">
            <b>Proposed Fix:</b> {iss['recommended_fix']}
          </div>
        </div>
        """

    if not metrics["issues"]:
        issues_html = "<div style='padding:2rem; text-align:center; color:#10b981; font-weight:bold;'>✨ Zero anomalies detected! All routes are healthy and resilient.</div>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Skelion Production Health Audit — {project_name}</title>
  <style>
    body {{ background:#090c13; color:#f0f3fa; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin:0; padding:2.5rem; }}
    .container {{ max-width:900px; margin:0 auto; }}
    .header {{ display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #1c2438; padding-bottom:1.5rem; margin-bottom:2rem; }}
    .brand {{ font-size:1.3rem; font-weight:800; background:linear-gradient(90deg, #7c5cff, #ff5caa); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
    .kpi-row {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:1rem; margin-bottom:2rem; }}
    .kpi-card {{ background:#111624; border:1px solid #1c2438; border-radius:10px; padding:1.2rem; text-align:center; }}
    .kpi-val {{ font-size:1.8rem; font-weight:800; margin-top:4px; }}
    .kpi-lbl {{ font-size:0.75rem; color:#8b9bb4; text-transform:uppercase; letter-spacing:0.05em; }}
    .footer {{ margin-top:2.5rem; border-top:1px solid #1c2438; padding-top:1.2rem; font-size:0.8rem; color:#8b9bb4; display:flex; justify-content:space-between; }}
    @media print {{ body {{ background:#fff; color:#000; }} .kpi-card {{ border:1px solid #ddd; }} }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <div class="brand">SKELION PRODUCTION HEALTH AUDIT</div>
        <div style="font-size:0.85rem; color:#8b9bb4; margin-top:4px;">Target Service: <b>{project_name}</b> &bull; Generated: {now_str}</div>
      </div>
      <div style="text-align:right;">
        <span style="font-size:11px; background:rgba(16,185,129,0.15); color:#10b981; border:1px solid #10b981; padding:4px 8px; border-radius:6px; font-weight:bold;">
          100% Local &bull; Zero Egress
        </span>
      </div>
    </div>

    <!-- KPI Row -->
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-lbl">Health Score</div>
        <div class="kpi-val" style="color:{health_color};">{health}/100</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-lbl">Requests Analyzed</div>
        <div class="kpi-val">{metrics['total_requests']:,}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-lbl">Unique Routes</div>
        <div class="kpi-val">{metrics['unique_routes']}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-lbl">Issues Found</div>
        <div class="kpi-val" style="color:#ef4444;">{len(metrics['issues'])}</div>
      </div>
    </div>

    <h3 style="margin-bottom:1rem; font-size:1.15rem;">Top Prioritized Production Issues</h3>
    {issues_html}

    <!-- Next Steps / CTA -->
    <div style="background:rgba(124,92,255,0.08); border:1px solid #7c5cff; border-radius:10px; padding:1.2rem; margin-top:2rem;">
      <b style="color:#7c5cff; font-size:0.95rem;">🚀 Recommended Next Steps</b>
      <div style="font-size:0.85rem; color:#cbd5e1; margin-top:6px; line-height:1.5;">
        1. Review the proposed patches in the Skelion VS Code extension.<br>
        2. Run continuous shadow replay verification with <code>skelion proxy --shadow</code>.<br>
        3. Activate automated PR bot healing on GitHub to resolve silent failures before users notice.
      </div>
    </div>

    <div class="footer">
      <div>Generated locally on host machine. Zero logs or customer PII were uploaded.</div>
      <div>Skelion Autonomous Production Resilience</div>
    </div>
  </div>
</body>
</html>
"""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


# ---------------------------------------------------------------------------
# CLI Command Entrypoint
# ---------------------------------------------------------------------------


def run_audit(
    log_file: str,
    project_name: str = "Production Service",
    output_dir: str = "./skelion-report",
) -> Dict[str, Any]:
    """Execute end-to-end local production health audit."""
    if not os.path.exists(log_file):
        raise FileNotFoundError(f"Log source file not found: {log_file}")

    records = []
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            rec = parse_log_line(line)
            if rec:
                records.append(rec)

    metrics = analyze_logs(records)

    # Export findings.json
    os.makedirs(output_dir, exist_ok=True)
    findings_path = os.path.join(output_dir, "findings.json")
    with open(findings_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Export report.html
    html_path = os.path.join(output_dir, "report.html")
    render_html_report(project_name, metrics, html_path)

    return {
        "status": "success",
        "requests_analyzed": len(records),
        "issues_count": len(metrics["issues"]),
        "health_score": metrics["health_score"],
        "html_report": os.path.abspath(html_path),
        "findings_json": os.path.abspath(findings_path),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Skelion Production Health Audit CLI (100% Local)"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to input log file (Nginx, JSONL, access log)",
    )
    parser.add_argument(
        "--project", default="Production Service", help="Project or service name"
    )
    parser.add_argument(
        "--out", default="./skelion-report", help="Output directory for reports"
    )
    args = parser.parse_args()

    print(f"[*] Starting Skelion Production Health Audit on {args.source}...")
    try:
        res = run_audit(args.source, args.project, args.out)
        print("[+] Audit Complete!")
        print(f"    - Requests Analyzed: {res['requests_analyzed']:,}")
        print(f"    - Health Score: {res['health_score']}/100")
        print(f"    - Issues Found: {res['issues_count']}")
        print(f"    - Standalone HTML Report: {res['html_report']}")
        print(f"    - Findings JSON: {res['findings_json']}")
    except Exception as e:
        print(f"[-] Audit Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
