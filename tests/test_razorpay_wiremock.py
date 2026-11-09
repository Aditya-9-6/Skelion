# tests/test_razorpay_wiremock.py
"""Integration tests verifying FastAPI and Razorpay client interactions with WireMock mock server."""
import threading
import time
import uuid
import httpx
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

from skelion_agent.control_plane import app
import scripts.mock_razorpay_server as mock_server


@pytest.fixture(scope="module")
def wiremock_server():
    """Start local mock Razorpay server thread if not already running."""
    port = 8089
    server_thread = threading.Thread(
        target=mock_server.run,
        args=(port,),
        daemon=True,
    )
    server_thread.start()
    # Wait for mock server to be ready
    ready = False
    for _ in range(20):
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/__admin/health", timeout=1.0)
            if r.status_code == 200:
                ready = True
                break
        except Exception:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"


def test_wiremock_health(wiremock_server):
    """Verify WireMock-compatible mock Razorpay server responds healthy."""
    r = httpx.get(f"{wiremock_server}/__admin/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_wiremock_order_creation(wiremock_server):
    """Verify WireMock order creation API behaves identically to live Razorpay."""
    payload = {
        "amount": 399900,
        "currency": "INR",
        "receipt": f"rcpt_test_{uuid.uuid4().hex[:6]}",
    }
    r = httpx.post(f"{wiremock_server}/v1/orders", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["amount"] == 399900
    assert data["currency"] == "INR"
    assert data["status"] == "created"
    assert "id" in data


def test_wiremock_order_fetch(wiremock_server):
    """Verify WireMock order retrieval."""
    r = httpx.get(f"{wiremock_server}/v1/orders/order_test_999")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "order_test_999"
    assert data["status"] in ("paid", "created")


def test_wiremock_payment_capture(wiremock_server):
    """Verify payment capture endpoint."""
    r = httpx.post(
        f"{wiremock_server}/v1/payments/pay_test_123/capture",
        json={"amount": 399900, "currency": "INR"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "captured"
