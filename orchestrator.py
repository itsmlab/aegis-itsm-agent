# Copyright (c) 2025 Leopoldo Lara. All rights reserved.
# Licensed under the Apache License, Version 2.0.
#
"""
Aegis - Incident Diagnostic Orchestrator
Uses Deepseek API to match alerts against AEGIS_PATTERNS.md
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Load API key from .env file
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")

PATTERNS_FILE = Path(__file__).parent / "AEGIS_PATTERNS.md"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

UNKNOWN_RESULT = {
    "id": "UNKNOWN",
    "name": "Pattern Not Recognized",
    "diagnosis": "No matching pattern found in knowledge base",
    "script": "Escalate to human team for manual analysis",
}

print("🛡️ Aegis v0.1 - Initializing...")
print("=" * 50)

# ============================================
# Knowledge base
# ============================================

def load_patterns_kb():
    """Load the full patterns knowledge base from disk."""
    return PATTERNS_FILE.read_text(encoding="utf-8")

def count_patterns(kb_text):
    """Count documented patterns in the knowledge base."""
    return kb_text.count("## Pattern AEGIS-")

# ============================================
# Diagnostic function
# ============================================

def diagnose(alert, patterns_kb=None):
    """Match alert against AEGIS_PATTERNS.md using the Deepseek API."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return {
            **UNKNOWN_RESULT,
            "diagnosis": "DEEPSEEK_API_KEY not configured. Set it in your environment or .env file.",
        }

    if patterns_kb is None:
        patterns_kb = load_patterns_kb()

    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    system_prompt = """You are Aegis, an autonomous incident triage agent.
Given a user alert and the AEGIS patterns knowledge base, identify the single closest matching pattern.

Rules:
- Compare symptoms, error codes, metrics, and context from the alert against each pattern.
- Pick the best match only if there is reasonable confidence; otherwise use UNKNOWN.
- Use the matched pattern's diagnosis and remediation script from the knowledge base.
- For "script", return the bash remediation commands from the matched pattern (without the shebang line if present).
- Respond with valid JSON only, no markdown fences.

JSON schema:
{
  "id": "AEGIS-XXX or UNKNOWN",
  "name": "pattern name",
  "diagnosis": "root cause explanation tailored to the alert",
  "script": "remediation commands as a single string"
}"""

    user_prompt = f"""ALERT:
{alert}

KNOWLEDGE BASE (AEGIS_PATTERNS.md):
{patterns_kb}

Find the closest matching pattern and return the JSON response."""

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = response.choices[0].message.content
        result = json.loads(content)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return UNKNOWN_RESULT
    except Exception:
        return {
            **UNKNOWN_RESULT,
            "diagnosis": "Deepseek API call failed. Check your API key and network connection.",
        }

    required_keys = ("id", "name", "diagnosis", "script")
    if not all(key in result for key in required_keys):
        return UNKNOWN_RESULT

    return {
        "id": str(result["id"]),
        "name": str(result["name"]),
        "diagnosis": str(result["diagnosis"]),
        "script": str(result["script"]),
    }

# ============================================
# Main loop
# ============================================

patterns_kb = load_patterns_kb()
pattern_count = count_patterns(patterns_kb)

print("\nKnowledge base loaded: " + str(pattern_count) + " patterns ready")
print("LLM: Deepseek (" + DEEPSEEK_MODEL + ")")
print("\nAegis ready to diagnose")
print("=" * 50)
print("\nDescribe an incident alert (symptoms, errors, metrics)")
print("=" * 50)

while True:
    print("\nWaiting for alert...")
    print("(Type an alert or 'exit' to quit)")
    
    alert = input("Alert: ").strip()
    
    if alert.lower() == "exit":
        print("\nShutting down Aegis...")
        break
    
    if not alert:
        continue
    
    print("\nDiagnosing...")
    result = diagnose(alert, patterns_kb)
    
    print("\n" + "=" * 50)
    print("Pattern: " + result["id"] + " - " + result["name"])
    print("Diagnosis: " + result["diagnosis"])
    print("\nRemediation script:")
    print("-" * 30)
    print(result["script"])
    print("-" * 30)
    print("=" * 50)
    
    print("\nExecute script? (y/n)")
    execute = input("> ").strip().lower()
    
    if execute == "y":
        print("Simulation mode: Script NOT actually executed")
        print("In production, the command would run here")
    else:
        print("Manual execution suggested")

print("\nGoodbye from Aegis!")