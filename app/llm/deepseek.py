"""
ITSMLab — DeepSeek LLM Provider implementation.
Uses the OpenAI-compatible DeepSeek API.
"""

import json
from openai import OpenAI

from app.config import settings
from app.llm.base import LLMProvider


UNKNOWN_RESULT = {
    "id": "UNKNOWN",
    "name": "Pattern Not Recognized",
    "diagnosis": "No matching pattern found in knowledge base",
    "script": "Escalate to human team for manual analysis",
}


class DeepSeekProvider(LLMProvider):
    """Provider for DeepSeek API (deepseek-chat model)."""

    def __init__(self):
        api_key = settings.DEEPSEEK_API_KEY
        if not api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY is not configured. "
                "Set it in your .env file or environment variables."
            )
        self.client = OpenAI(api_key=api_key, base_url=settings.DEEPSEEK_BASE_URL)
        self.model = settings.DEEPSEEK_MODEL

    def get_provider_name(self) -> str:
        return "deepseek"

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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=settings.LLM_TEMPERATURE,
            )
            content = response.choices[0].message.content
            result = json.loads(content)
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            return dict(UNKNOWN_RESULT)
        except Exception as e:
            return {
                **UNKNOWN_RESULT,
                "diagnosis": f"DeepSeek API call failed: {str(e)}",
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