# skelion_edge/waf_shield.py — Spryzen WAF & Tartarus Ingress Defense Engine
"""
Spryzen Ingress Security Engine ported for the Skelion / Helios DevProxy.
Implements:
1. Multi-vector WAF pattern inspection (SQLi, XSS, Path Traversal, RCE, SSTI).
2. Project Tartarus: Deception Honeypot for hostile scans (.env, .git, wp-admin).
3. Zero-allocation fast ASCII lookup table & signature matching.
"""

import json
import re
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List
from urllib.parse import unquote_plus

# Spryzen WAF Literals (Ported from spryzen_rust/src/waf.rs)
SPRYZEN_WAF_LITERALS = [
    # SQL Injection
    "union select", "union all", "select from", "insert into", "drop table",
    "update set", "delete from", "or 1=1", "and 1=1", "admin' --", "admin' #",
    # XSS (Cross-Site Scripting)
    "<script", "javascript:", "onerror=", "onload=", "onclick=", "alert(", "eval(", "document.cookie",
    # Path Traversal & LFI
    "/etc/passwd", "/etc/hosts", "/etc/shadow", "boot.ini", "..\\..\\", "../..", "/proc/self/environ",
    # Remote Code Execution (RCE)
    "/bin/bash", "/bin/sh", "curl ", "wget ", "netcat ", "nc -e", "cmd.exe", "powershell",
    # Server-Side Template Injection (SSTI)
    "{{7*7}}", "${7*7}", "#{7*7}",
    # Prototype Pollution
    "__proto__", "constructor.prototype",
    # Vulnerability Scanners & Recon
    "sqlmap", "nikto", "acunetix",
]

# Sensitive paths intercepted by Tartarus Mirror Dimension
TARTARUS_DECEPTION_PATHS = [
    "/.env", "/.git", "/wp-admin", "/actuator/health", "/phpinfo.php",
    "/config.json", "/aws/credentials", "/.aws", "/admin/db"
]

# Fast character lookup table for risky injection characters
RISKY_CHARS = set("'\"<>/\\-;{}$#`=(),*%+|&[]")


def normalize_payload(s: str) -> str:
    """Normalize input using Spryzen Normalization Engine:
    1. Decode URL percent-encoding (single and double encoded).
    2. Strip SQL/C-style inline comments (/* ... */).
    3. Collapse whitespace and lowercase.
    """
    if not s:
        return ""
    try:
        decoded = unquote_plus(s)
        if "%" in decoded:
            decoded = unquote_plus(decoded)
    except Exception:
        decoded = s

    # Strip inline comments: /*!50000union*/ or /*comment*/
    cleaned = re.sub(r"/\*.*?\*/", " ", decoded)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def scan_payload_for_threats(payload_str: str) -> Optional[Tuple[str, str, float]]:
    """Inspect payload string using Spryzen WAF heuristics.
    
    Returns (attack_type, matched_signature, threat_score) or None.
    """
    if not payload_str:
        return None

    # Quick pre-filter: if raw string has no risky characters or percent encoding, skip deep inspection
    if not any(c in RISKY_CHARS for c in payload_str):
        return None

    p_normalized = normalize_payload(payload_str)

    # 1. Spryzen Literal Signature Scan
    for literal in SPRYZEN_WAF_LITERALS:
        if literal in p_normalized:
            if any(k in literal for k in ["union", "select", "drop", "1=1", "--"]):
                return ("SQL_INJECTION", literal, 0.98)
            elif any(k in literal for k in ["script", "javascript", "alert", "cookie", "onerror"]):
                return ("XSS_ATTACK", literal, 0.95)
            elif any(k in literal for k in ["etc/passwd", "../..", "boot.ini"]):
                return ("PATH_TRAVERSAL", literal, 0.99)
            elif any(k in literal for k in ["bash", "wget", "curl", "powershell"]):
                return ("COMMAND_INJECTION_RCE", literal, 0.99)
            elif any(k in literal for k in ["7*7"]):
                return ("SSTI_INJECTION", literal, 0.92)
            elif "__proto__" in literal:
                return ("PROTOTYPE_POLLUTION", literal, 0.90)
            else:
                return ("MALICIOUS_SCANNER", literal, 0.85)

    # 2. Chunk-based heuristic: quote + comment or quote + boolean injection (simd_waf.rs)
    if ("'" in p_normalized or '"' in p_normalized) and ("--" in p_normalized or ";" in p_normalized or "#" in p_normalized or "or " in p_normalized or "and " in p_normalized):
        if re.search(r"('|\")\s*(\bor\b|\band\b|--|#|;)", p_normalized):
            return ("HEURISTIC_SQLI", "quote_boolean_comment_vector", 0.94)

    return None


def inspect_request_security(
    method: str,
    path: str,
    query_params: str = "",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Inspect incoming HTTP request with Spryzen WAF & Tartarus Deception.
    
    Returns:
      (is_blocked: bool, threat_details: dict or None, deception_response: dict or None)
    """
    # 1. Project Tartarus: Deception Mirror Dimension Check
    clean_path = path.lower()
    for trap in TARTARUS_DECEPTION_PATHS:
        if trap in clean_path:
            # Trap the attacker in Tartarus Honeypot with fake realistic response
            fake_content = (
                "DB_HOST=internal-db-prod-001.spryzen.local\n"
                "DB_USER=admin\n"
                "DB_PASS=SuperSecret123!\n"
                "API_KEY=sk_live_FakeTartarusHoneypotKey_91829\n"
            ) if ".env" in trap else json.dumps({
                "status": "ok",
                "hologram": "Tartarus Mirror Dimension Active",
                "deception_logged": True
            })
            return (
                True,
                {"type": "TARTARUS_DECEPTION", "path": path, "threat_score": 1.0},
                {
                    "status_code": 200,
                    "headers": {"Content-Type": "text/plain", "Server": "Apache/2.4.41 (Ubuntu)"},
                    "content": fake_content
                }
            )

    # 2. Inspect Path & Query String
    threat = scan_payload_for_threats(path) or scan_payload_for_threats(query_params)
    if threat:
        attack_type, signature, score = threat
        return (
            True,
            {
                "type": attack_type,
                "signature": signature,
                "threat_score": score,
                "source": "path_or_query",
                "path": path,
            },
            None
        )

    # 3. Inspect Body Payload
    # Exempt developer AI prompt streams and patch apply payloads so code discussions are not falsely blocked as injections
    if body and not path.startswith("/v1/chat") and not path.startswith("/v1/autofix/apply"):
        threat = scan_payload_for_threats(body)
        if threat:
            attack_type, signature, score = threat
            return (
                True,
                {
                    "type": attack_type,
                    "signature": signature,
                    "threat_score": score,
                    "source": "request_body",
                    "path": path,
                },
                None
            )

    return (False, None, None)


# ---------------------------------------------------------------------------
# Threat Telemetry & Event Ingestion
# ---------------------------------------------------------------------------

_THREAT_HISTORY: List[Dict[str, Any]] = []
_MAX_HISTORY = 200

_METRICS = {
    "total_inspections": 0,
    "blocked_sqli": 0,
    "blocked_xss": 0,
    "blocked_rce": 0,
    "blocked_path_traversal": 0,
    "blocked_other": 0,
    "tartarus_deceptions": 0,
}


def record_threat_event(threat: Dict[str, Any], client_ip: str = "unknown"):
    """Record a blocked threat event and increment metrics counters."""
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_ip": client_ip,
        **threat
    }
    _THREAT_HISTORY.insert(0, event)
    if len(_THREAT_HISTORY) > _MAX_HISTORY:
        _THREAT_HISTORY.pop()

    t_type = threat.get("type", "")
    if "SQL" in t_type:
        _METRICS["blocked_sqli"] += 1
    elif "XSS" in t_type:
        _METRICS["blocked_xss"] += 1
    elif "COMMAND" in t_type or "RCE" in t_type:
        _METRICS["blocked_rce"] += 1
    elif "PATH_TRAVERSAL" in t_type:
        _METRICS["blocked_path_traversal"] += 1
    elif "TARTARUS" in t_type:
        _METRICS["tartarus_deceptions"] += 1
    else:
        _METRICS["blocked_other"] += 1


def get_recent_threats(limit: int = 50) -> List[Dict[str, Any]]:
    """Return the most recent blocked security threats."""
    return _THREAT_HISTORY[:limit]


def get_waf_metrics() -> Dict[str, Any]:
    """Return overall WAF telemetry metrics."""
    return {
        "metrics": dict(_METRICS),
        "total_threats_blocked": sum(_METRICS[k] for k in _METRICS if k != "total_inspections"),
        "recent_events_count": len(_THREAT_HISTORY),
    }

