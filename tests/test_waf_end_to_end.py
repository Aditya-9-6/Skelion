# tests/test_waf_end_to_end.py — Full Integration & Verification Test Suite for Spryzen WAF in Skelion
import unittest
import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://127.0.0.1:8003"


def send_http(path, method="GET", body=None, headers=None):
    url = f"{BASE_URL}{path}"
    data = None
    h = headers or {}
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
            h["Content-Type"] = "application/json"
        elif isinstance(body, str):
            data = body.encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            return resp.status, content, resp.headers
    except urllib.error.HTTPError as err:
        content = err.read().decode("utf-8", errors="ignore")
        return err.code, content, err.headers
    except Exception as exc:
        return 0, str(exc), {}


class TestSpryzenWAFIntegration(unittest.TestCase):

    def setUp(self):
        # Warmup and ensure server is reachable
        for _ in range(5):
            status, _, _ = send_http("/v1/waf/metrics")
            if status == 200:
                break
            time.sleep(0.5)
        self.assertEqual(status, 200, "Skelion Control Plane must be reachable on port 8003")

    def test_01_tartarus_honeypot_deception(self):
        """Verify Project Tartarus intercepts scanner probes with realistic fake payloads."""
        status, body, headers = send_http("/.env")
        self.assertEqual(status, 200)
        self.assertIn("internal-db-prod-001.spryzen.local", body)
        self.assertIn("sk_live_FakeTartarusHoneypotKey", body)

        # Other deception path
        status, body, _ = send_http("/wp-admin")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertTrue(data.get("deception_logged"))

    def test_02_sqli_query_blocking(self):
        """Verify SQL injection payloads in query params are blocked with 403."""
        status, body, _ = send_http("/v1/auth/me?q=admin%27%20or%201=1--")
        self.assertEqual(status, 403)
        data = json.loads(body)
        self.assertEqual(data.get("error"), "Forbidden")
        self.assertIn("SQL_INJECTION", data.get("threat", {}).get("type"))

    def test_03_sqli_union_select_blocking(self):
        """Verify SQLi UNION SELECT is blocked."""
        status, body, _ = send_http("/v1/auth/me?id=1%20UNION%20SELECT%20null,null--")
        self.assertEqual(status, 403)
        data = json.loads(body)
        self.assertEqual(data.get("threat", {}).get("type"), "SQL_INJECTION")

    def test_04_xss_in_body_blocking(self):
        """Verify Cross-Site Scripting (XSS) in request bodies is blocked with 403."""
        status, body, _ = send_http("/v1/waf/test-payload", method="POST", body={"payload": "<script>alert('xss')</script>"})
        self.assertEqual(status, 403)
        data = json.loads(body)
        self.assertEqual(data.get("threat", {}).get("type"), "XSS_ATTACK")

    def test_05_path_traversal_lfi_blocking(self):
        """Verify Local File Inclusion (LFI) and path traversal are blocked."""
        status, body, _ = send_http("/v1/auth/me?file=../../../../etc/passwd")
        self.assertEqual(status, 403)
        data = json.loads(body)
        self.assertEqual(data.get("threat", {}).get("type"), "PATH_TRAVERSAL")

    def test_06_rce_command_injection_blocking(self):
        """Verify Command Injection & RCE probes are blocked."""
        status, body, _ = send_http("/v1/auth/me?cmd=;%20/bin/bash%20-i")
        self.assertEqual(status, 403)
        data = json.loads(body)
        self.assertIn("COMMAND_INJECTION_RCE", data.get("threat", {}).get("type"))

    def test_07_ssti_injection_blocking(self):
        """Verify Server-Side Template Injection is blocked."""
        status, body, _ = send_http("/v1/auth/me?template={{7*7}}")
        self.assertEqual(status, 403)
        data = json.loads(body)
        self.assertEqual(data.get("threat", {}).get("type"), "SSTI_INJECTION")

    def test_08_prototype_pollution_blocking(self):
        """Verify Prototype Pollution payloads are blocked."""
        status, body, _ = send_http("/v1/auth/me?__proto__[polluted]=true")
        self.assertEqual(status, 403)
        data = json.loads(body)
        self.assertEqual(data.get("threat", {}).get("type"), "PROTOTYPE_POLLUTION")

    def test_09_clean_request_zero_false_positives(self):
        """Verify normal application requests pass through with 200 OK."""
        status, body, _ = send_http("/v1/auth/me")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("org_default", data.get("id"))

    def test_10_waf_telemetry_and_events(self):
        """Verify WAF metrics and threat events log update accurately."""
        status, body, _ = send_http("/v1/waf/metrics")
        self.assertEqual(status, 200)
        metrics_data = json.loads(body)
        self.assertGreater(metrics_data.get("total_threats_blocked", 0), 0)

        status, body, _ = send_http("/v1/waf/events?limit=10")
        self.assertEqual(status, 200)
        events_data = json.loads(body)
        self.assertEqual(events_data.get("status"), "ok")
        self.assertIsInstance(events_data.get("events"), list)
        self.assertGreater(len(events_data.get("events")), 0)

    def test_11_incident_feed_isolation(self):
        """Verify WAF cyberattacks do NOT pollute the developer application incident feed."""
        # Query incidents using dev token
        status, body, _ = send_http("/v1/incidents", headers={"Authorization": "Bearer dev"})
        self.assertEqual(status, 200)
        inc_data = json.loads(body)
        incidents = inc_data.get("incidents", [])

        # Ensure no WAF 403 block was misclassified as an application crash incident
        for inc in incidents:
            title = inc.get("title", "")
            self.assertNotIn("Spryzen WAF Shield", title)


if __name__ == "__main__":
    unittest.main(verbosity=2)
