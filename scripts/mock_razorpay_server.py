# scripts/mock_razorpay_server.py
"""Standalone Mock Razorpay server providing WireMock/Razorpay compatible API.
Can run standalone or inside Docker/CI without external dependencies.
"""
import http.server
import json
import os
import sys
import uuid

PORT = int(os.getenv("MOCK_RAZORPAY_PORT", "8089"))

ORDERS = {}
PAYMENTS = {}


class MockRazorpayHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/__admin/health", "/health", "/v1/health"):
            return self._send_json(200, {"status": "healthy", "service": "mock-razorpay", "version": "1.0.0"})

        if self.path.startswith("/v1/orders/"):
            order_id = self.path.split("/")[-1]
            order = ORDERS.get(order_id)
            if order:
                return self._send_json(200, order)
            return self._send_json(200, {
                "id": order_id,
                "entity": "order",
                "amount": 399900,
                "amount_paid": 399900,
                "currency": "INR",
                "status": "paid",
            })

        self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b"{}"
        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            data = {}

        if self.path == "/v1/orders":
            amount = data.get("amount", 399900)
            currency = data.get("currency", "INR")
            receipt = data.get("receipt", f"rcpt_{uuid.uuid4().hex[:8]}")
            order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
            order = {
                "id": order_id,
                "entity": "order",
                "amount": amount,
                "amount_paid": 0,
                "amount_due": amount,
                "currency": currency,
                "receipt": receipt,
                "status": "created",
                "attempts": 0,
            }
            ORDERS[order_id] = order
            return self._send_json(200, order)

        if "/capture" in self.path:
            parts = self.path.split("/")
            payment_id = parts[3] if len(parts) > 3 else f"pay_mock_{uuid.uuid4().hex[:10]}"
            amount = data.get("amount", 399900)
            payment = {
                "id": payment_id,
                "entity": "payment",
                "amount": amount,
                "currency": "INR",
                "status": "captured",
            }
            PAYMENTS[payment_id] = payment
            return self._send_json(200, payment)

        self._send_json(404, {"error": "Not Found"})

    def log_message(self, format, *args):
        # Quiet logger for clean test output
        pass


def run(port: int = PORT):
    server_address = ("", port)
    httpd = http.server.ThreadingHTTPServer(server_address, MockRazorpayHandler)
    print(f"Mock Razorpay (WireMock-compatible) server running on port {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Mock Razorpay server...")
        httpd.server_close()


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run(p)
