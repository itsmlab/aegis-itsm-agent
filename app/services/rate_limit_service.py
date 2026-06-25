"""
AEGIS SaaS — Rate limiting service per tenant.

Stores request counters per tenant and hour window in memory.
Provides:
  - check_rate_limit(tenant_id, plan) -> tuple[bool, dict]
    Returns (allowed, headers) where headers contains X-RateLimit-* fields.

Rate limits by plan (per hour):
  - shield:   10 requests/hour
  - guard:    50 requests/hour
  - fortress: 200 requests/hour
"""

import time
import threading
from collections import defaultdict
from typing import Optional

from app.logging_config import get_logger

logger = get_logger(__name__)

# ── Rate limit configuration ──────────────────────────────────

RATE_LIMITS = {
    "shield": 10,
    "guard": 50,
    "fortress": 200,
}

DEFAULT_RATE_LIMIT = 10  # fallback for unknown plans

WINDOW_SECONDS = 3600  # 1 hour window


class RateLimitService:
    """
    In-memory rate limiter using sliding windows per tenant.

    Thread-safe: uses a lock to protect the counters dict.
    Counters are automatically cleaned up after expiry.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # _counters[tenant_id] = list of timestamps (epoch seconds)
        self._counters: dict[str, list[float]] = defaultdict(list)

    def _get_limit(self, plan: str) -> int:
        """Get the rate limit for a given plan."""
        return RATE_LIMITS.get(plan.lower(), DEFAULT_RATE_LIMIT)

    def _cleanup(self, tenant_id: str):
        """Remove timestamps older than the window."""
        now = time.time()
        cutoff = now - WINDOW_SECONDS
        timestamps = self._counters.get(tenant_id, [])
        # Keep only timestamps within the window
        self._counters[tenant_id] = [t for t in timestamps if t > cutoff]

    def check_rate_limit(self, tenant_id: str, plan: str) -> tuple[bool, dict]:
        """
        Check if the tenant can make a request.

        Args:
            tenant_id: The tenant's UUID.
            plan: The tenant's plan (shield, guard, fortress).

        Returns:
            Tuple of (allowed, headers).
            allowed is True if the request is within the rate limit.
            headers is a dict with X-RateLimit-* fields.
        """
        limit = self._get_limit(plan)

        with self._lock:
            self._cleanup(tenant_id)
            timestamps = self._counters.get(tenant_id, [])
            current_count = len(timestamps)

            if current_count >= limit:
                # Rate limit exceeded
                reset_time = int(time.time()) + WINDOW_SECONDS
                headers = {
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(WINDOW_SECONDS),
                }
                logger.warning("Rate limit exceeded", extra={
                    "tenant_id": tenant_id,
                    "plan": plan,
                    "limit": limit,
                    "current_count": current_count,
                })
                return False, headers

            # Record this request
            self._counters[tenant_id].append(time.time())
            remaining = limit - (current_count + 1)
            reset_time = int(time.time()) + WINDOW_SECONDS

            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time),
            }

            return True, headers

    def get_usage(self, tenant_id: str, plan: str) -> dict:
        """
        Get current rate limit usage for a tenant (without recording a request).

        Useful for the /v1/stats endpoint.
        """
        limit = self._get_limit(plan)

        with self._lock:
            self._cleanup(tenant_id)
            timestamps = self._counters.get(tenant_id, [])
            current_count = len(timestamps)

        return {
            "limit_per_hour": limit,
            "current_count": current_count,
            "remaining": max(0, limit - current_count),
            "window_seconds": WINDOW_SECONDS,
        }

    def reset_tenant(self, tenant_id: str):
        """Reset rate limit counters for a tenant (admin use)."""
        with self._lock:
            self._counters.pop(tenant_id, None)
        logger.info("Rate limit reset for tenant", extra={
            "tenant_id": tenant_id,
        })


# Singleton
rate_limit_service = RateLimitService()
