# Copyright (c) 2025 Leopoldo Lara. All rights reserved.
# Licensed under the Apache License, Version 2.0.
#
"""
AEGIS Slack Bot — receives alerts via Slack and returns AEGIS diagnosis.

Usage:
  1. Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN in .env
  2. Run: python slack_bot.py
  3. Message the bot or use /aegis diagnose <description>

Requires a Slack app with:
  - Socket Mode enabled
  - Events: message.im, app_mention
  - Bot Token Scopes: chat:write, commands, app_mentions:read
  - Slash Command: /aegis
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Load environment
load_dotenv()

# ── Import AEGIS modules ───────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import io
_old_stdout = sys.stdout
sys.stdout = io.StringIO()

from classifier import (
    load_dataset_from_csv, create_collection, load_tickets_to_db,
    classify_ticket, get_statistics, DATASET_PATH, SAMPLE_TICKETS
)
from orchestrator import diagnose, load_patterns_kb, count_patterns

sys.stdout = _old_stdout

# ── Initialize ChromaDB ────────────────────────────────────────
print("🤖 AEGIS Slack Bot - Initializing...")
dataset = load_dataset_from_csv(DATASET_PATH)
if not dataset:
    dataset = SAMPLE_TICKETS

collection = create_collection()
load_tickets_to_db(dataset, collection)
stats = get_statistics(collection)

# Load L3/L4 knowledge base
patterns_kb = load_patterns_kb()
pattern_count = count_patterns(patterns_kb)

print(f"📊 Classifier: {stats['total']} tickets, {len(stats['categories'])} categories")
print(f"📚 Patterns: {pattern_count} L3/L4 patterns")

# ── Category mapping (same as integration_module) ──────────────
CATEGORY_MAP = {
    "ACCESS":     {"id": "L1-001", "name": "Access / Authentication Issue",
                   "diagnosis": "User authentication or authorization failure detected.",
                   "script": "1. Verify user account is active\n2. Reset password if needed\n3. Check group/role assignments"},
    "DATABASE":   {"id": "L1-005", "name": "Database Issue",
                   "diagnosis": "Database connection, query, or performance issue detected.",
                   "script": "1. Check database connection pool\n2. Review slow query log\n3. Verify replication status"},
    "LICENSE":    {"id": "L1-003", "name": "License / Quota Issue",
                   "diagnosis": "License expiration or quota exceeded detected.",
                   "script": "1. Check license expiration\n2. Renew or extend license\n3. Review quota usage"},
    "API":        {"id": "L1-006", "name": "API / Integration Issue",
                   "diagnosis": "API endpoint or webhook failure detected.",
                   "script": "1. Check API endpoint availability\n2. Verify auth tokens\n3. Review rate limits"},
    "PERFORMANCE":{"id": "L1-002", "name": "Performance Degradation",
                   "diagnosis": "Application performance issue detected.",
                   "script": "1. Check CPU and memory usage\n2. Review active queries\n3. Verify CDN and cache status"},
    "NETWORK":    {"id": "L1-007", "name": "Network / Connectivity Issue",
                   "diagnosis": "Network connectivity or DNS resolution issue detected.",
                   "script": "1. Test connectivity with ping/traceroute\n2. Check DNS resolution\n3. Verify firewall rules"},
    "SECURITY":   {"id": "L1-008", "name": "Security / Certificate Issue",
                   "diagnosis": "Security vulnerability, certificate expiry, or threat detected.",
                   "script": "1. Verify SSL/TLS certificate validity\n2. Run security scan\n3. Apply patches"},
    "HOWTO":      {"id": "L1-004", "name": "How-To / Configuration Request",
                   "diagnosis": "User needs guidance on setup or configuration.",
                   "script": "1. Direct user to documentation portal\n2. Share relevant KB article\n3. Schedule session if needed"},
    "UNKNOWN":    {"id": "L1-UNKNOWN", "name": "Unclassified Ticket",
                   "diagnosis": "No matching L1/L2 pattern found. Routing to human agent.",
                   "script": "1. Review ticket manually\n2. Assign to appropriate team\n3. Update knowledge base"},
}

# ── Route severity ─────────────────────────────────────────────
def route_severity(description: str) -> str:
    critical_keywords = [
        "outage", "down", "unavailable", "timeout", "cascad",
        "failover", "crash", "error 5", "500", "503", "504",
        "latency spike", "memory", "cpu", "disk full", "replication"
    ]
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in critical_keywords):
        return "L3/L4"
    return "L1/L2"

# ── Slack Bolt App ─────────────────────────────────────────────
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    print("⚠️  SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in .env")
    print("   Run with: python slack_bot.py")
    sys.exit(1)

app = App(token=SLACK_BOT_TOKEN)
client = WebClient(token=SLACK_BOT_TOKEN)

# ── Diagnosis function ─────────────────────────────────────────
def diagnose_alert(alert_text: str) -> str:
    """Run AEGIS diagnosis on an alert text and return a formatted response."""
    level = route_severity(alert_text)

    if level == "L1/L2":
        result = classify_ticket(alert_text, collection)
        category = result["category"]
        confidence = result["confidence"]
        method = result.get("method", "unknown")
        suggested = result.get("suggested_resolution", "")
        pattern = CATEGORY_MAP.get(category, CATEGORY_MAP["UNKNOWN"])

        lines = [
            f"🔹 *Level:* L1/L2",
            f"🔹 *Pattern:* {pattern['name']} ({pattern['id']})",
            f"🔹 *Confidence:* {confidence:.1%} ({method})",
            f"🔹 *Diagnosis:* {pattern['diagnosis']}",
        ]
        if suggested:
            lines.append(f"🔹 *Suggested Resolution:* {suggested}")
        lines.append(f"\n📋 *Procedure:*\n```\n{pattern['script']}\n```")
        return "\n".join(lines)
    else:
        result = diagnose(alert_text, patterns_kb)
        lines = [
            f"🔴 *Level:* L3/L4",
            f"🔴 *Pattern:* {result['name']} ({result['id']})",
            f"🔴 *Diagnosis:* {result['diagnosis']}",
            f"\n📋 *Remediation Script:*\n```\n{result['script']}\n```",
        ]
        return "\n".join(lines)

# ── Events ─────────────────────────────────────────────────────

@app.event("app_mention")
def handle_mention(event, say):
    """Respond when the bot is @mentioned."""
    text = event.get("text", "")
    user = event.get("user", "unknown")
    # Remove bot user ID from text
    import re
    text = re.sub(r"<@\w+>", "", text).strip()

    if not text:
        say("Hi! Tell me about an incident and I'll diagnose it. "
            "Example: `@AEGIS User cannot log in, gets 403 error`")
        return

    say(f"⏳ Diagnosing incident reported by <@{user}>...")
    response = diagnose_alert(text)
    say(response)

@app.event("message")
def handle_message(event, say):
    """Handle direct messages to the bot."""
    # Only respond in DMs (channel type "im")
    channel_type = event.get("channel_type", "")
    if channel_type != "im":
        return

    text = event.get("text", "")
    if not text or text.startswith("/"):
        return

    say(f"⏳ Diagnosing...")
    response = diagnose_alert(text)
    say(response)

# ── Slash command ──────────────────────────────────────────────

@app.command("/aegis")
def handle_slash_command(ack, respond, command):
    """Handle /aegis diagnose <description>"""
    ack()
    text = command.get("text", "").strip()

    if not text:
        respond("Usage: `/aegis diagnose <incident description>`\n"
                "Example: `/aegis diagnose User cannot log in, gets 403 error`")
        return

    if text.lower().startswith("diagnose "):
        text = text[9:].strip()

    respond(f"⏳ Diagnosing...")
    response = diagnose_alert(text)
    respond(response)

# ── Run ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🤖 AEGIS Slack Bot")
    print("=" * 50)
    print(f"ChromaDB classifier: {stats['total']} tickets in {len(stats['categories'])} categories")
    print(f"L3/L4 patterns: {pattern_count} patterns")
    print("Starting Socket Mode handler...")
    print("=" * 50)

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
