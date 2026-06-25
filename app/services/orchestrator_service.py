"""
AEGIS SaaS — Orchestrator service for L3/L4 incident diagnosis.
Uses the configured LLMProvider to diagnose critical incidents.
"""

import time
from pathlib import Path

from app.config import settings
from app.llm.factory import get_llm_provider
from app.llm.base import LLMProvider
from app.logging_config import get_logger, metrics_collector

logger = get_logger(__name__)


class OrchestratorService:
    """
    Wraps the L3/L4 diagnosis logic using the configured LLM provider.
    Loads the patterns knowledge base from AEGIS_PATTERNS.md.
    """

    def __init__(self):
        self._patterns_kb: str | None = None
        self._llm_provider: LLMProvider | None = None
        logger.info("Orchestrator service initialized", extra={
            "llm_provider": settings.LLM_PROVIDER,
            "patterns_file": str(settings.PATTERNS_FILE),
        })

    def _load_patterns_kb(self) -> str:
        """Load the full patterns knowledge base from disk."""
        patterns_file = Path(settings.PATTERNS_FILE)
        if not patterns_file.exists():
            logger.error("Patterns file not found", extra={
                "path": str(settings.PATTERNS_FILE),
            })
            raise FileNotFoundError(
                f"AEGIS_PATTERNS.md not found at {settings.PATTERNS_FILE}"
            )
        kb = patterns_file.read_text(encoding="utf-8")
        pattern_count = kb.count("## Pattern AEGIS-")
        logger.info("Patterns knowledge base loaded", extra={
            "pattern_count": pattern_count,
            "file_size_bytes": len(kb),
        })
        return kb

    def _get_llm(self) -> LLMProvider:
        """Get or create the LLM provider singleton."""
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
            logger.info("LLM provider initialized", extra={
                "provider": self._llm_provider.get_provider_name(),
            })
        return self._llm_provider

    def diagnose(self, alert_text: str) -> dict:
        """
        Diagnose a critical incident using the LLM provider.

        Returns dict with keys: id, name, diagnosis, script.
        """
        start = time.time()

        if self._patterns_kb is None:
            self._patterns_kb = self._load_patterns_kb()

        llm = self._get_llm()
        result = llm.diagnose(alert_text, self._patterns_kb)

        latency = time.time() - start
        pattern_id = str(result.get("id", "UNKNOWN"))
        tokens_used = result.get("tokens_used", 0)

        # Record LLM metrics
        metrics_collector.record_llm_call(tokens_used=tokens_used, latency=latency)

        logger.info("Incident diagnosed", extra={
            "pattern_id": pattern_id,
            "pattern_name": str(result.get("name", "Unknown")),
            "latency_ms": round(latency * 1000, 2),
            "tokens_used": tokens_used,
            "input_length": len(alert_text),
        })

        return result

    def get_pattern_count(self) -> int:
        """Count documented patterns in the knowledge base."""
        if self._patterns_kb is None:
            self._patterns_kb = self._load_patterns_kb()
        return self._patterns_kb.count("## Pattern AEGIS-")

    def get_provider_name(self) -> str:
        """Get the name of the configured LLM provider."""
        return self._get_llm().get_provider_name()


# Singleton
orchestrator_service = OrchestratorService()
