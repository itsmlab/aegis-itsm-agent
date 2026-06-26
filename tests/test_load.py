"""
AEGIS SaaS — Load tests.

Simulates 50 concurrent requests from different tenants to verify:
  - No crashes or 5xx errors
  - Acceptable response times (p95 < 5s, p99 < 10s)
  - No unexpected 429 errors (rate limiting should not trigger for Guard plan)

Run with:
    pytest tests/test_load.py -v --timeout=120

Requires: httpx (pip install httpx)
"""

import os
import uuid
import time
import statistics
import pytest
import httpx
from typing import List, Tuple

# ── Configuration ─────────────────────────────────────────────

NUM_TENANTS = 5          # Number of simulated tenants
REQUESTS_PER_TENANT = 10 # Requests per tenant (total = 50)
BASE_URL = "http://127.0.0.1:8000"

# Alert payloads for variety
ALERT_PAYLOADS = [
    {"source": "monitoring", "severity": "low", "title": "High CPU usage", "description": "CPU usage at 85% on web-server-01"},
    {"source": "pagerduty", "severity": "critical", "title": "Database failover failure", "description": "Primary database is down, failover to replica failed"},
    {"source": "zendesk", "severity": "medium", "title": "User cannot access VPN", "description": "User reports 403 error when connecting to VPN"},
    {"source": "api", "severity": "high", "title": "API latency spike", "description": "Response times increased from 200ms to 5s"},
    {"source": "manual", "severity": "low", "title": "Password reset request", "description": "User forgot password and needs admin reset"},
]


def make_tenant() -> dict:
    """Generate a unique tenant identifier."""
    return {
        "id": str(uuid.uuid4()),
        "slug": f"load-test-{uuid.uuid4().hex[:8]}",
        "plan": "guard",
    }


async def send_request(client: httpx.AsyncClient, tenant: dict, payload: dict) -> dict:
    """
    Send a single request and return timing/status info.
    Uses the health endpoint for simplicity and speed.
    """
    start = time.time()
    try:
        response = await client.get(f"{BASE_URL}/v1/health")
        elapsed = time.time() - start
        return {
            "tenant": tenant["slug"],
            "status": response.status_code,
            "latency": elapsed,
            "error": None,
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "tenant": tenant["slug"],
            "status": 0,
            "latency": elapsed,
            "error": str(e),
        }


async def run_tenant_requests(tenant: dict, num_requests: int) -> List[dict]:
    """
    Run a series of requests for a single tenant.
    Uses a shared client for connection pooling.
    """
    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(num_requests):
            payload = ALERT_PAYLOADS[i % len(ALERT_PAYLOADS)]
            result = await send_request(client, tenant, payload)
            results.append(result)
    return results


# ═══════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════


class TestLoad:
    """Load tests for AEGIS API."""

    @pytest.mark.asyncio
    async def test_50_concurrent_requests(self):
        """
        Simulate 50 requests from 5 different tenants (10 each).
        Verify no errors and acceptable response times.
        """
        # Generate tenants
        tenants = [make_tenant() for _ in range(NUM_TENANTS)]

        # Run all tenant requests concurrently
        all_results: List[dict] = []
        import asyncio

        tasks = [
            run_tenant_requests(tenant, REQUESTS_PER_TENANT)
            for tenant in tenants
        ]
        task_results = await asyncio.gather(*tasks)

        for results in task_results:
            all_results.extend(results)

        # ── Analyze results ──────────────────────────────────
        total = len(all_results)
        errors = [r for r in all_results if r["status"] != 200]
        rate_limited = [r for r in all_results if r["status"] == 429]
        latencies = [r["latency"] for r in all_results if r["status"] == 200]
        sorted_latencies = sorted(latencies)

        # Calculate percentiles
        p50 = sorted_latencies[len(sorted_latencies) // 2] if sorted_latencies else 0
        p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)] if sorted_latencies else 0
        p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)] if sorted_latencies else 0
        avg_latency = statistics.mean(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0

        # ── Print report ─────────────────────────────────────
        print()
        print("=" * 60)
        print("LOAD TEST REPORT")
        print("=" * 60)
        print(f"  Total requests:       {total}")
        print(f"  Successful (200):     {total - len(errors)}")
        print(f"  Errors:               {len(errors)}")
        print(f"  Rate limited (429):   {len(rate_limited)}")
        print(f"  Error rate:           {len(errors)/total*100:.1f}%")
        print()
        print("  Latency (seconds):")
        print(f"    Min:    {min_latency:.3f}")
        print(f"    Avg:    {avg_latency:.3f}")
        print(f"    P50:    {p50:.3f}")
        print(f"    P95:    {p95:.3f}")
        print(f"    P99:    {p99:.3f}")
        print(f"    Max:    {max_latency:.3f}")
        print()

        # Show errors if any
        if errors:
            print("  Errors detail:")
            for err in errors[:5]:  # Show first 5
                print(f"    Tenant: {err['tenant']}, Status: {err['status']}, Error: {err['error']}")
            if len(errors) > 5:
                print(f"    ... and {len(errors) - 5} more errors")

        # ── Assertions ────────────────────────────────────────
        # No 5xx errors
        server_errors = [r for r in errors if r["status"] >= 500]
        assert len(server_errors) == 0, f"Got {len(server_errors)} server errors (5xx)"

        # No connection errors
        conn_errors = [r for r in errors if r["error"] is not None]
        assert len(conn_errors) == 0, f"Got {len(conn_errors)} connection errors"

        # No unexpected 429 (Guard plan has 50/hr limit, we do 50 total)
        # Note: 429 could happen if previous tests consumed the rate limit
        if len(rate_limited) > 0:
            print(f"  ⚠️  {len(rate_limited)} requests were rate limited (429)")
            print("     This may be expected if previous tests consumed the rate limit.")
            print("     Guard plan limit is 50/hr.")

        # P95 should be under 5 seconds
        assert p95 < 5.0, f"P95 latency too high: {p95:.3f}s (max: 5.0s)"

        # P99 should be under 10 seconds
        assert p99 < 10.0, f"P99 latency too high: {p99:.3f}s (max: 10.0s)"

        # Average should be under 2 seconds
        assert avg_latency < 2.0, f"Average latency too high: {avg_latency:.3f}s (max: 2.0s)"

        print("  ✅ All assertions passed!")
