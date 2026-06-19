"""
AEGIS SaaS — Orchestrator service for L3/L4 incident diagnosis.
Uses the configured LLMProvider to diagnose critical incidents.
"""

from pathlib import Path

from app.config import settings
from app.llm.factory import get_llm_provider
from app.llm.base import LLMProvider


class OrchestratorService:
    """
    Wraps the L3/L4 diagnosis logic using the configured LLM provider.
    Loads the patterns knowledge base from AEGIS_PATTERNS.md.
    """

    def __init__(self):
        self._patterns_kb: str | None = None
        self._llm_provider: LLMProvider | None = None

    def _load_patterns_kb(self) -> str:
        """Load the full patterns knowledge base from disk."""
        patterns_file = Path(settings.PATTERNS_FILE)
        if not patterns_file.exists():
            raise FileNotFoundError(
                f"AEGIS_PATTERNS.md not found at {settings.PATTERNS_FILE}"
            )
        return patterns_file.read_text(encoding="utf-8")

    def _get_llm(self) -> LLMProvider:
        """Get or create the LLM provider singleton."""
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
        return self._llm_provider

    def diagnose(self, alert_text: str) -> dict:
        """
        Diagnose a critical incident using the LLM provider.

        Returns dict with keys: id, name, diagnosis, script.
        """
        if self._patterns_kb is None:
            self._patterns_kb = self._load_patterns_kb()

        llm = self._get_llm()
        return llm.diagnose(alert_text, self._patterns_kb)

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