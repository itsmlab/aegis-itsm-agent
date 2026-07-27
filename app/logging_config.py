"""
ITSMLab — Structured JSON logging configuration.

Provides:
  - JSON-formatted log output for production (machine-parseable)
  - Human-readable console output for development
  - Automatic injection of tenant_id, request_id, endpoint into log records
  - A MetricsCollector for business metrics (response times, accuracy, errors)

Usage:
    from app.logging_config import get_logger, metrics_collector

    logger = get_logger(__name__)
    logger.info("Ticket classified", extra={
        "tenant_id": tenant_id,
        "category": category,
        "confidence": confidence,
    })
"""

import json
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional


# ── JSON Formatter ─────────────────────────────────────────────


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter that outputs structured log records.

    Each log line is a single JSON object with fields:
      timestamp, level, logger, message, and any extra fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add any extra fields passed via extra={...}
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "module", "msecs", "message", "msg",
                "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName",
            ):
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


# ── Logger factory ─────────────────────────────────────────────


def get_logger(name: str) -> logging.Logger:
    """
    Get a structured logger for the given module name.

    In production (DEBUG=False), outputs JSON to stdout.
    In development (DEBUG=True), outputs human-readable text.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Determine format based on DEBUG setting
    # We import settings lazily to avoid circular imports
    from app.config import settings

    if settings.DEBUG:
        # Human-readable format for development
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    else:
        # JSON format for production
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())

    logger.addHandler(handler)
    return logger


# ── Metrics Collector ──────────────────────────────────────────


class MetricsCollector:
    """
    Collects business metrics for the /metrics endpoint.

    Thread-safe. Stores:
      - Request counts and latencies per endpoint
      - Error counts per endpoint
      - Classification results per tenant
      - LLM usage (tokens, response times)
    """

    def __init__(self):
        self._lock = Lock()

        # Request metrics
        self._request_count: dict[str, int] = defaultdict(int)
        self._error_count: dict[str, int] = defaultdict(int)
        self._latency_sum: dict[str, float] = defaultdict(float)
        self._latency_count: dict[str, int] = defaultdict(int)

        # Classification metrics
        self._classification_count: dict[str, int] = defaultdict(int)  # category -> count
        self._classification_confidence_sum: dict[str, float] = defaultdict(float)
        self._classification_confidence_count: dict[str, int] = defaultdict(int)

        # LLM metrics
        self._llm_calls: int = 0
        self._llm_tokens: int = 0
        self._llm_latency_sum: float = 0.0

        # Per-tenant metrics
        self._tenant_request_count: dict[str, int] = defaultdict(int)
        self._tenant_error_count: dict[str, int] = defaultdict(int)

        # Uptime tracking
        self._start_time = time.time()

    # ── Request tracking ───────────────────────────────────────

    def record_request(self, endpoint: str, tenant_id: str, latency: float, status_code: int):
        """Record a request with its latency and status."""
        with self._lock:
            self._request_count[endpoint] += 1
            self._latency_sum[endpoint] += latency
            self._latency_count[endpoint] += 1
            self._tenant_request_count[tenant_id] += 1

            if status_code >= 400:
                self._error_count[endpoint] += 1
                self._tenant_error_count[tenant_id] += 1

    # ── Classification tracking ────────────────────────────────

    def record_classification(self, category: str, confidence: float):
        """Record a classification result."""
        with self._lock:
            self._classification_count[category] += 1
            self._classification_confidence_sum[category] += confidence
            self._classification_confidence_count[category] += 1

    # ── LLM tracking ───────────────────────────────────────────

    def record_llm_call(self, tokens_used: int, latency: float):
        """Record an LLM API call."""
        with self._lock:
            self._llm_calls += 1
            self._llm_tokens += tokens_used
            self._llm_latency_sum += latency

    # ── Snapshot ───────────────────────────────────────────────

    def snapshot(self) -> dict:
        """
        Return a snapshot of all metrics for the /metrics endpoint.
        Thread-safe: acquires the lock and copies data.
        """
        with self._lock:
            uptime_seconds = time.time() - self._start_time

            # Build endpoint metrics
            endpoints = {}
            for ep in set(list(self._request_count.keys()) + list(self._error_count.keys())):
                req_count = self._request_count.get(ep, 0)
                err_count = self._error_count.get(ep, 0)
                lat_sum = self._latency_sum.get(ep, 0.0)
                lat_count = self._latency_count.get(ep, 0)
                endpoints[ep] = {
                    "requests": req_count,
                    "errors": err_count,
                    "error_rate": round(err_count / req_count, 4) if req_count > 0 else 0.0,
                    "avg_latency_ms": round((lat_sum / lat_count) * 1000, 2) if lat_count > 0 else 0.0,
                }

            # Build classification metrics
            categories = {}
            for cat in self._classification_count:
                count = self._classification_count[cat]
                conf_sum = self._classification_confidence_sum[cat]
                conf_count = self._classification_confidence_count[cat]
                categories[cat] = {
                    "count": count,
                    "avg_confidence": round(conf_sum / conf_count, 4) if conf_count > 0 else 0.0,
                }

            # Build per-tenant metrics
            all_tenant_ids = set(
                list(self._tenant_request_count.keys())
                + list(self._tenant_error_count.keys())
            )
            tenants = {}
            for tid in all_tenant_ids:
                tenants[tid] = {
                    "requests": self._tenant_request_count.get(tid, 0),
                    "errors": self._tenant_error_count.get(tid, 0),
                }

            return {
                "uptime_seconds": uptime_seconds,
                "uptime_human": self._format_uptime(uptime_seconds),
                "total_requests": sum(self._request_count.values()),
                "total_errors": sum(self._error_count.values()),
                "endpoints": endpoints,
                "classification": {
                    "total": sum(self._classification_count.values()),
                    "categories": categories,
                },
                "llm": {
                    "total_calls": self._llm_calls,
                    "total_tokens": self._llm_tokens,
                    "avg_latency_ms": round((self._llm_latency_sum / self._llm_calls) * 1000, 2)
                    if self._llm_calls > 0 else 0.0,
                },
                "tenants": tenants,
                "timestamp": datetime.utcnow().isoformat(),
            }

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime as human-readable string."""
        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)


# ── Singleton instances ────────────────────────────────────────

metrics_collector = MetricsCollector()

# Initialize the root logger
logger = get_logger("itsmlab")
