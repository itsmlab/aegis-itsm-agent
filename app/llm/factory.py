"""
ITSMLab — LLM Provider factory.
Returns the appropriate provider based on settings.LLM_PROVIDER.
"""

from app.config import settings
from app.llm.base import LLMProvider
from app.llm.deepseek import DeepSeekProvider
from app.llm.openai_compat import OpenAIProvider
from app.llm.ollama import OllamaProvider
from app.llm.anthropic import AnthropicProvider


def get_llm_provider() -> LLMProvider:
    """
    Factory function — returns the configured LLM provider.

    Providers:
      - "deepseek"  → DeepSeekProvider (default)
      - "openai"    → OpenAIProvider
      - "ollama"    → OllamaProvider (dedicated implementation)
      - "anthropic" → AnthropicProvider (Claude)

    Raises ValueError if the provider is unknown or misconfigured.
    """
    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name == "deepseek":
        return DeepSeekProvider()

    if provider_name == "openai":
        return OpenAIProvider()

    if provider_name == "ollama":
        return OllamaProvider()

    if provider_name == "anthropic":
        return AnthropicProvider()

    raise ValueError(
        f"Unknown LLM_PROVIDER: '{provider_name}'. "
        f"Expected one of: deepseek, openai, ollama, anthropic"
    )



