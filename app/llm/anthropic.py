"""
AEGIS SaaS — Anthropic (Claude) LLM Provider.
Connects to Anthropic's API using the official Anthropic Python SDK.
"""

import json
from anthropic import Anthropic

from app.config import settings
from app.llm.base import LLMProvider


UNKNOWN_RESULT = {
    "id": "UNKNOWN",
    "name": "Pattern Not Recognized",
    "diagnosis": "No matching pattern found in knowledge base",
    "script": "Escalate to human team for manual analysis",
}


class AnthropicProvider(LLMProvider):
    """
    Provider for Anthropic's Claude models.

    Uses the official Anthropic SDK. Requires ANTHROPIC_API_KEY to be set.
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL

    def get_provider_name(self) -> str:
        return "anthropic"

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
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=settings.LLM_TEMPERATURE,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
            )

            content = response.content[0].text

            # Try to extract JSON from the response
            result = self._extract_json(content)

        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            return dict(UNKNOWN_RESULT)
        except Exception as e:
            return {
                **UNKNOWN_RESULT,
                "diagnosis": f"Anthropic API call failed: {str(e)}",
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
        models may add before or after the JSON object.
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
