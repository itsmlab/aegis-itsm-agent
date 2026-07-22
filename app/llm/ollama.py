"""
AEGIS SaaS — Ollama LLM Provider (dedicated implementation).
Connects to a local Ollama instance via its OpenAI-compatible API.
No monkey-patching needed — uses Ollama settings directly.
"""

import json
import time
from openai import OpenAI

from app.config import settings
from app.llm.base import LLMProvider


UNKNOWN_RESULT = {
    "id": "UNKNOWN",
    "name": "Pattern Not Recognized",
    "diagnosis": "No matching pattern found in knowledge base",
    "script": "Escalate to human team for manual analysis",
}


class OllamaProvider(LLMProvider):
    """
    Provider for local Ollama instances.

    Ollama exposes an OpenAI-compatible API at <OLLAMA_BASE_URL>/v1.
    This provider connects directly without modifying environment variables.

    Note: Some local models may not support `response_format={"type": "json_object"}`.
    This provider detects that and falls back to prompt-based JSON extraction.
    """

    def __init__(self):
        base_url = f"{settings.OLLAMA_BASE_URL}/v1"
        self.client = OpenAI(
            api_key="ollama",  # Ollama doesn't require a real API key
            base_url=base_url,
        )
        self.model = settings.OLLAMA_MODEL
        self._supports_json_mode: bool | None = None  # Lazy detection

    def get_provider_name(self) -> str:
        return "ollama"

    def _check_json_mode_support(self) -> bool:
        """
        Check if the configured Ollama model supports response_format JSON mode.
        Some local models (e.g., older llama3, phi3) may not support it.

        We test by sending a minimal request and checking for errors.
        Result is cached after first check.
        """
        if self._supports_json_mode is not None:
            return self._supports_json_mode

        try:
            test_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Say hello in JSON: {\"greeting\": \"hello\"}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=50,
            )
            content = test_response.choices[0].message.content
            json.loads(content)
            self._supports_json_mode = True
        except Exception:
            self._supports_json_mode = False

        return self._supports_json_mode

    def diagnose(self, alert: str, patterns_kb: str) -> dict:
        system_prompt = """You are Aegis, an autonomous incident triage agent.
Given a user alert and the AEGIS patterns knowledge base, identify the single closest matching pattern.

Rules:
- Compare symptoms, error codes, metrics, and context from the alert against each pattern.
- Pick the best match only if there is reasonable confidence; otherwise use UNKNOWN.
- Use the matched pattern's diagnosis and remediation script from the knowledge base.
- For "script", return the bash remediation commands from the matched pattern.
- Respond with valid JSON only, no markdown fences.

JSON schema:
{
  "id": "AEGIS-XXX or UNKNOWN",
  "name": "pattern name",
  "diagnosis": "root cause explanation tailored to the alert",
  "script": "remediation commands as a single string"
}"""

        user_prompt = f"""ALERT TITLE: {alert}
ALERT SOURCE: API
ALERT SEVERITY: not specified

ALERT DESCRIPTION:
{alert}

KNOWLEDGE BASE (AEGIS_PATTERNS.md):
{patterns_kb}

Find the closest matching pattern and return the JSON response."""

        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": settings.LLM_TEMPERATURE,
            }

            # Only use response_format if the model supports it
            if self._check_json_mode_support():
                kwargs["response_format"] = {"type": "json_object"}
            else:
                # For models without JSON mode, add explicit instruction in the prompt
                kwargs["messages"][0]["content"] += (
                    "\n\nIMPORTANT: Your response must be ONLY valid JSON. "
                    "No explanations, no markdown, no code fences. "
                    "Start with { and end with }."
                )

            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content

            # Try to extract JSON from the response (handles models that add extra text)
            result = self._extract_json(content)

        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            return dict(UNKNOWN_RESULT)
        except Exception as e:
            return {
                **UNKNOWN_RESULT,
                "diagnosis": f"Ollama API call failed: {str(e)}",
            }

        required_keys = ("id", "name", "diagnosis", "script")
        if not all(key in result for key in required_keys):
            return dict(UNKNOWN_RESULT)

        return {
            "id": str(result["id"]),
            "name": str(result["name"]),
            "diagnosis": str(result["diagnosis"]),
            "script": str(result["script"]),
        }

    def _extract_json(self, text: str) -> dict:
        """
        Extract JSON from model response, handling extra text that some
        local models may add before or after the JSON object.
        """
        text = text.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON between curly braces
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        # Try to find JSON between markdown code fences
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass

        raise json.JSONDecodeError("No valid JSON found in response", text, 0)
