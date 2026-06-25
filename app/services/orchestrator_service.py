"""
AEGIS SaaS — Orchestrator service for L3/L4 incident diagnosis.
Uses the configured LLMProvider to diagnose critical incidents.

Now uses RAG (Retrieval-Augmented Generation) to select only the most
relevant patterns from the knowledge base, instead of sending the full
AEGIS_PATTERNS.md to the LLM on every request.
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

    Uses RAG retrieval to select only the most relevant patterns from
    the knowledge base, reducing token usage and improving diagnosis speed.

    Falls back to the full knowledge base if RAG is not initialized.
    """

    def __init__(self):
        self._patterns_kb: str | None = None
        self._llm_provider: LLMProvider | None = None
        self._rag_available: bool | None = None
        logger.info("Orchestrator service initialized", extra={
            "llm_provider": settings.LLM_PROVIDER,
            "patterns_file": str(settings.PATTERNS_FILE),
        })

    def _check_rag_available(self) -> bool:
        """Check if the RAG knowledge base is initialized."""
        if self._rag_available is not None:
            return self._rag_available

        try:
            from app.rag.knowledge_base import get_knowledge_base_stats
            stats = get_knowledge_base_stats()
            self._rag_available = stats["initialized"]
            if self._rag_available:
                logger.info("RAG knowledge base available", extra={
                    "chunk_count": stats["chunk_count"],
                })
            else:
                logger.warning("RAG knowledge base not initialized, using full file fallback")
            return self._rag_available
        except Exception as e:
            self._rag_available = False
            logger.warning("RAG check failed, using full file fallback", extra={
                "error": str(e),
            })
            return False

    def _retrieve_relevant_patterns(self, alert_text: str) -> str:
        """
        Retrieve the most relevant pattern chunks for the given alert.

        Returns a formatted string with the top-k patterns, or the full
        knowledge base if RAG is not available.
        """
        if not self._check_rag_available():
            return self._load_full_kb()

        try:
            from app.rag.knowledge_base import retrieve_similar_chunks

            chunks = retrieve_similar_chunks(alert_text, top_k=3)

            if not chunks:
                logger.warning("RAG returned no chunks, falling back to full KB")
                return self._load_full_kb()

            # Format the retrieved chunks into a compact knowledge base string
            parts = ["# RELEVANT PATTERNS (retrieved from knowledge base)\n"]
            for chunk in chunks:
                parts.append(f"## {chunk['pattern_id']} — {chunk['title']}")
                parts.append(f"(Relevance distance: {chunk['distance']})\n")
                parts.append(chunk["content"])
                parts.append("")

            result = "\n".join(parts)
            logger.info("Using RAG-retrieved patterns", extra={
                "chunks_used": len(chunks),
                "result_length": len(result),
                "top_pattern": chunks[0]["pattern_id"] if chunks else "none",
            })
            return result

        except Exception as e:
            logger.warning("RAG retrieval failed, falling back to full KB", extra={
                "error": str(e),
            })
            return self._load_full_kb()

    def _load_full_kb(self) -> str:
        """Load the full patterns knowledge base from disk (fallback)."""
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
        logger.info("Using full knowledge base (fallback)", extra={
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

        Uses RAG to select only the most relevant patterns, reducing
        token usage and improving diagnosis speed.

        Returns dict with keys: id, name, diagnosis, script.
        """
        start = time.time()

        # Retrieve relevant patterns (RAG) or full KB as fallback
        patterns_kb = self._retrieve_relevant_patterns(alert_text)

        llm = self._get_llm()
        result = llm.diagnose(alert_text, patterns_kb)

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
            "kb_source": "rag" if self._rag_available else "full_file",
        })

        return result

    def get_pattern_count(self) -> int:
        """Count documented patterns in the knowledge base."""
        if self._patterns_kb is None:
            self._patterns_kb = self._load_full_kb()
        return self._patterns_kb.count("## Pattern AEGIS-")

    def get_provider_name(self) -> str:
        """Get the name of the configured LLM provider."""
        return self._get_llm().get_provider_name()


# Singleton
orchestrator_service = OrchestratorService()
