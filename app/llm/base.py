"""
ITSMLab — Abstract LLM Provider interface.
All LLM backends (DeepSeek, OpenAI, Ollama, etc.) implement this.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface for LLM-based incident diagnosis."""

    @abstractmethod
    def diagnose(self, alert: str, patterns_kb: str) -> dict:
        """
        Given an alert description and the patterns knowledge base,
        return a dict with keys: id, name, diagnosis, script.

        The patterns_kb is the full text of AEGIS_PATTERNS.md.
        """
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """Human-readable provider name, e.g. 'deepseek', 'openai', 'ollama'."""
        ...