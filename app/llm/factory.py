"""
AEGIS SaaS — LLM Provider factory.
Returns the appropriate provider based on settings.LLM_PROVIDER.
"""

from app.config import settings
from app.llm.base import LLMProvider
from app.llm.deepseek import DeepSeekProvider
from app.llm.openai_compat import OpenAIProvider


def get_llm_provider() -> LLMProvider:
    """
    Factory function — returns the configured LLM provider.

    Providers:
      - "deepseek" → DeepSeekProvider (default)
      - "openai"   → OpenAIProvider
      - "ollama"   → OpenAIProvider (Ollama uses OpenAI-compatible API)

    Raises ValueError if the provider is unknown or misconfigured.
    """
    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name == "deepseek":
        return DeepSeekProvider()

    if provider_name == "openai":
        return OpenAIProvider()

    if provider_name == "ollama":
        # Ollama exposes an OpenAI-compatible API at OLLAMA_BASE_URL/v1
        from app.llm.openai_compat import OpenAIProvider as OllamaProvider

        # Monkey-patch settings for Ollama
        import os
        original_key = os.environ.get("OPENAI_API_KEY")
        original_url = os.environ.get("OPENAI_BASE_URL")
        original_model = os.environ.get("OPENAI_MODEL")
        os.environ["OPENAI_API_KEY"] = "ollama"
        os.environ["OPENAI_BASE_URL"] = f"{settings.OLLAMA_BASE_URL}/v1"
        os.environ["OPENAI_MODEL"] = settings.OLLAMA_MODEL

        # Reload settings to pick up overrides
        from app.config import Settings
        ollama_settings = Settings()

        provider = OllamaProvider()
        provider.client.base_url = f"{settings.OLLAMA_BASE_URL}/v1"
        provider.model = settings.OLLAMA_MODEL

        # Restore original env vars
        if original_key is not None:
            os.environ["OPENAI_API_KEY"] = original_key
        else:
            os.environ.pop("OPENAI_API_KEY", None)
        if original_url is not None:
            os.environ["OPENAI_BASE_URL"] = original_url
        else:
            os.environ.pop("OPENAI_BASE_URL", None)
        if original_model is not None:
            os.environ["OPENAI_MODEL"] = original_model
        else:
            os.environ.pop("OPENAI_MODEL", None)

        return provider

    raise ValueError(
        f"Unknown LLM_PROVIDER: '{provider_name}'. "
        f"Expected one of: deepseek, openai, ollama"
    )
