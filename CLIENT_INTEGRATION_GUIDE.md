# ITSMLab — Client Integration Guide

> **Version 3.1.0** · *Autonomous IT Incident Resolution*

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Prerequisites](#2-prerequisites)
3. [Step 1: Initial Setup](#3-step-1-initial-setup)
4. [Step 2: API Integration](#4-step-2-api-integration)
5. [Step 3: PagerDuty Integration](#5-step-3-pagerduty-integration)
6. [Step 4: Slack Integration](#6-step-4-slack-integration)
7. [Step 5: Dashboard & Monitoring](#7-step-5-dashboard--monitoring)
8. [Plans & Billing](#8-plans--billing)
9. [FAQ](#9-faq)
10. [Support](#10-support)

---

## 1. Introduction

### What is ITSMLab?

ITSMLab is an **autonomous IT incident resolution system** that acts as your first line of defense. When your monitoring tools (PagerDuty, Slack, or custom scripts) detect an issue, ITSMLab automatically:

1. **Classifies** the incident by category (Access, Database, Network, Security, etc.)
2. **Diagnoses** the root cause using a vector-based knowledge base
3. **Resolves** L1/L2 incidents automatically with runbook scripts
4. **Escalates** critical L3/L4 incidents to your senior engineers with full context

Think of ITSMLab as a **tireless L1 engineer** that works 24/7, resolves routine issues in seconds, and gives your team more time to focus on complex problems.

### How it works

```
┌─────────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  PagerDuty  │────▶│          │     │  L1/L2       │────▶│  Auto-resolve │
│  Slack Bot  │────▶│  ITSMLab │────▶│  (routine)   │     │  + runbook    │
│  API Call   │────▶│  Engine  │     │  L3/L4       │────▶│  Escalate to  │
│  Webhook    │────▶│          │     │  (critical)  │     │  senior eng.  │
└─────────────┘     └──────────┘     └──────────────┘     └──────────────┘
```

---

## 2. Prerequisites

Before integrating with ITSMLab, ensure you have:

| Requirement | Details |
|-------------|---------|
| **ITSMLab tenant** | Your organization's account (see [Step 1](#3-step-1-initial-setup)) |
| **API key** | A valid `itsmlab_live_*` key for authentication |
| **Network access** | Ability to reach the ITSMLab API endpoint (HTTPS) |
| **Monitoring tools** | PagerDuty account (optional), Slack workspace (optional) |
| **HTTP client** | `curl`, Postman, or any HTTP library for API calls |

### Supported integrations

| Integration | Status | Documentation |
|-------------|--------|---------------|
| REST API | ✅ Active | See [Step 2](#4-step-2-api-integration) |
| PagerDuty Webhook | ✅ Active | See [Step 3](#5-step-3-pagerduty-integration) |
| Slack Bot | ✅ Active | See [Step 4](#6-step-4-slack-integration) |
| Email (SMTP) | 🔜 Coming soon | — |
| ServiceNow | 🔜 Coming soon | — |
| Jira | 🔜 Coming soon | — |

---

## 3. Step 1: Initial Setup

### 3.1 Get your tenant

Contact the ITSMLab admin team to create your tenant. You will receive:

- **Tenant ID** — a UUID that identifies your organization (e.g., `f01f8222-aa0a-4e7f-bda5-10582cbb2e50`)
- **Tenant slug** — a human-readable identifier (e.g., `acme-corp`)
- **Plan** — your subscription tier (`shield`, `guard`, or `fortress`)
- **API key** — a secret key starting with `itsmlab_live_`

> ⚠️ **Important:** Your API key is shown only once. Store it securely in a password manager or secrets vault. If you lose it, you'll need to generate a new one.

### 3.2 Verify connectivity

Once you have your API key, verify that you can reach the ITSMLab API:

```bash
curl -s https://your-itsmlab-instance.com/v1/health \
  -H "X-API-Key: itsmlab_live_your_key_here"
```

Expected response:

```json
{
  "status": "healthy",
  "tenant": "acme-corp",
  "plan": "guard",
  "classifier_tickets": 77,
  "patterns_file": "found",
  "llm_provider": "deepseek",
  "version": "3.0.0",
  "timestamp": "2026-06-25T22:00:00"
}
```

### 3.3 Check your stats

```bash
curl -s https://your-itsmlab-instance.com/v1/stats \
  -H "X-API-Key: itsmlab_live_your_key_here"
```

This returns your current usage, classifier status, and plan information.

---

## 4. Step 2: API Integration

### 4.1 Sending an alert

The primary endpoint for submitting incidents is `POST /v1/alert`.

**Endpoint:** `POST https://your-itsmlab-instance.com/v1/alert`

**Headers:**
| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | ✅ |
| `X-API-Key` | `itsmlab_live_your_key_here` | ✅ |

**Request body:**

```json
{
  "source": "pagerduty",
  "severity": "low",
  "title": "User cannot log in",
  "description": "User gets 403 error when accessing the application",
  "metadata": {
    "user_id": "john.doe@acme.com",
    "region": "us-east-1"
  }
}
```

**Example with curl:**

```bash
curl -s -X POST https://your-itsmlab-instance.com/v1/alert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: itsmlab_live_your_key_here" \
  -d '{
    "source": "pagerduty",
    "severity": "low",
    "title": "User cannot log in",
    "description": "User gets 403 error when accessing the application"
  }'
```

### 4.2 Understanding the response

```json
{
  "timestamp": "2026-06-25T22:00:00.000000",
  "source": "pagerduty",
  "severity": "low",
  "level": "L1/L2",
  "pattern_id": "L1-001",
  "pattern_name": "Access / Authentication Issue",
  "diagnosis": "User authentication or authorization failure detected. (classified via vector_weighted, confidence 53.2%)",
  "script": "1. Verify user account is active\n2. Reset password if needed\n3. Check group/role assignments\n4. Clear browser cache and cookies",
  "confidence": "53.2%",
  "similar_tickets": [
    {
      "title": "Login failure after password reset",
      "category": "ACCESS",
      "resolution": "Reset password and clear browser cache"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `level` | `L1/L2` (routine) or `L3/L4` (critical) |
| `pattern_id` | The matched pattern identifier |
| `pattern_name` | Human-readable pattern name |
| `diagnosis` | Root cause analysis with confidence score |
| `script` | Step-by-step resolution runbook |
| `confidence` | Classification confidence (L1/L2 only) |
| `similar_tickets` | Historical tickets with similar patterns |

### 4.3 Severity routing

ITSMLab automatically routes incidents based on severity and keywords:

| Severity | Route | Description |
|----------|-------|-------------|
| `low` | L1/L2 | Routine issues (password reset, access requests) |
| `medium` | L1/L2 | Non-critical issues (slow performance, configuration) |
| `high` | L3/L4 | Critical issues (service degradation) |
| `critical` | L3/L4 | Emergency (outage, data loss, security breach) |

If no severity is provided, ITSMLab analyzes the description for critical keywords like `outage`, `down`, `failover`, `crash`, `500`, `503`, etc.

### 4.4 L1/L2 response (routine)

For routine incidents, ITSMLab returns:
- A **diagnosis** with the predicted category and confidence score
- A **resolution script** with step-by-step instructions
- **Similar tickets** from the knowledge base

### 4.5 L3/L4 response (critical)

For critical incidents, ITSMLab returns:
- A **diagnosis** generated by the LLM (DeepSeek or OpenAI)
- A **resolution plan** with escalation steps
- The incident is flagged for immediate human attention

**Example critical alert:**

```bash
curl -s -X POST https://your-itsmlab-instance.com/v1/alert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: itsmlab_live_your_key_here" \
  -d '{
    "source": "pagerduty",
    "severity": "critical",
    "title": "Database failover failure",
    "description": "Primary database is down, failover to replica failed. Error 500 on all write operations."
  }'
```

### 4.6 Error handling

| Status Code | Meaning | What to do |
|-------------|---------|------------|
| `200` | Success | Process the diagnosis response |
| `400` | Bad request | Check your payload structure |
| `401` | Unauthorized | Verify your API key |
| `422` | Validation error | Check required fields (title, description) |
| `429` | Rate limit exceeded | Wait and retry (plan-dependent) |
| `500` | Server error | Contact ITSMLab support |

### 4.7 Code examples

**Python:**

```python
import requests

API_URL = "https://your-itsmlab-instance.com"
API_KEY = "itsmlab_live_your_key_here"

alert = {
    "source": "monitoring",
    "severity": "low",
    "title": "High CPU usage on web server",
    "description": "CPU usage at 92% on web-01 for 5 minutes",
}

response = requests.post(
    f"{API_URL}/v1/alert",
    json=alert,
    headers={"X-API-Key": API_KEY},
)

if response.status_code == 200:
    result = response.json()
    print(f"Level: {result['level']}")
    print(f"Diagnosis: {result['diagnosis']}")
    print(f"Resolution: {result['script']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

**Node.js:**

```javascript
const API_URL = 'https://your-itsmlab-instance.com';
const API_KEY = 'itsmlab_live_your_key_here';

const alert = {
  source: 'monitoring',
  severity: 'low',
  title: 'High CPU usage on web server',
  description: 'CPU usage at 92% on web-01 for 5 minutes',
};

const response = await fetch(`${API_URL}/v1/alert`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  },
  body: JSON.stringify(alert),
});

const result = await response.json();
console.log(`Level: ${result.level}`);
console.log(`Diagnosis: ${result.diagnosis}`);
```

**Bash (script):**

```bash
#!/bin/bash
# send_alert.sh — Send an alert to ITSMLab

API_URL="https://your-itsmlab-instance.com"
API_KEY="itsmlab_live_your_key_here"

curl -s -X POST "${API_URL}/v1/alert" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "source": "monitoring",
    "severity": "low",
    "title": "'"$1"'",
    "description": "'"$2"'"
  }' | jq .
```

Usage: `./send_alert.sh "High memory usage" "Memory at 95% on db-01"`

---

## 5. Step 3: PagerDuty Integration

### 5.1 Configure the PagerDuty webhook

1. Log in to your **PagerDuty** account
2. Go to **Integrations → Generic Webhooks (v3)**
3. Click **"Add Webhook"**
4. Configure:

| Field | Value |
|-------|-------|
| **Webhook URL** | `https://your-itsmlab-instance.com/v1/alert` |
| **Secret** | Leave blank (ITSMLab uses API key header) |
| **Scope** | Select the services you want ITSMLab to monitor |
| **Events** | `incident.triggered` |

5. Add a custom header:
   - **Name:** `X-API-Key`
   - **Value:** `itsmlab_live_your_key_here`

6. Click **"Add Webhook"** to save

### 5.2 How it works

When PagerDuty triggers an incident:

1. PagerDuty sends a webhook to ITSMLab with the incident details
2. ITSMLab classifies the incident and runs a diagnosis
3. For L1/L2 incidents, ITSMLab returns a resolution script
4. For L3/L4 incidents, ITSMLab provides escalation context
5. The response can be used to auto-resolve or update the PagerDuty incident

### 5.3 Testing the integration

Trigger a test alert from PagerDuty:

```bash
# Simulate a PagerDuty webhook
curl -s -X POST https://your-itsmlab-instance.com/v1/alert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: itsmlab_live_your_key_here" \
  -d '{
    "source": "pagerduty",
    "severity": "low",
    "title": "Test alert from PagerDuty",
    "description": "This is a test incident for integration validation"
  }'
```

---

## 6. Step 4: Slack Integration

### 6.1 Configure the Slack bot

1. Go to your Slack **Apps** page
2. Click **"Add Apps"** and search for your ITSMLab bot
3. Click **"Add to Slack"**
4. The bot will join the configured channel (e.g., `#itsmlab-alerts`)

### 6.2 Using the Slack bot

Once the bot is in your channel, you can interact with it:

**Send an alert via DM or channel:**

```
/itsmlab diagnose User cannot log in after password reset
```

**Check system status:**

```
/itsmlab status
```

**Get usage statistics:**

```
/itsmlab stats
```

### 6.3 Slack webhook integration

You can also configure Slack to forward messages to ITSMLab:

1. In Slack, go to **Settings → Workflows**
2. Create a new workflow triggered by **"When a message is posted in a channel"**
3. Add a step: **"Send a webhook"**
4. Set the webhook URL to `https://your-itsmlab-instance.com/v1/alert`
5. Add header `X-API-Key: itsmlab_live_your_key_here`
6. Map the message content to the `title` and `description` fields

---

## 7. Step 5: Dashboard & Monitoring

### 7.1 Access the dashboard

Open your browser and navigate to:

```
https://your-itsmlab-instance.com/dashboard
```

The dashboard shows:

| Section | Description |
|---------|-------------|
| **Summary Cards** | Total diagnoses, monthly usage, tokens consumed, knowledge base size |
| **System Health** | API status, classifier status, LLM provider, version |
| **Category Distribution** | Bar chart of incidents by category |
| **Recent Activity** | Table of recent diagnoses with timestamps, endpoints, and status |

### 7.2 Metrics API

For programmatic monitoring, use the `GET /metrics` endpoint:

```bash
curl -s https://your-itsmlab-instance.com/metrics \
  -H "X-API-Key: itsmlab_live_your_key_here"
```

Response:

```json
{
  "uptime_seconds": 86400,
  "total_requests": 1523,
  "total_errors": 12,
  "endpoints": {
    "GET /v1/health": {"count": 450, "errors": 0, "avg_latency_ms": 15.2},
    "POST /v1/alert": {"count": 1023, "errors": 10, "avg_latency_ms": 850.0},
    "GET /v1/stats": {"count": 50, "errors": 2, "avg_latency_ms": 20.1}
  },
  "classification": {
    "total": 1023,
    "categories": {
      "ACCESS": 320,
      "DATABASE": 210,
      "NETWORK": 180,
      "PERFORMANCE": 150,
      "SECURITY": 100,
      "API": 40,
      "LICENSE": 23
    }
  },
  "llm": {
    "total_calls": 150,
    "total_tokens": 45000,
    "avg_latency_ms": 3200.0
  },
  "tenants": {
    "acme-corp": {"requests": 1023, "errors": 10}
  },
  "timestamp": "2026-06-25T22:00:00"
}
```

### 7.3 API documentation

Interactive API documentation is available at:

```
https://your-itsmlab-instance.com/docs
```

This provides a Swagger UI where you can explore and test all endpoints.

---

## 8. Plans & Billing

### Available plans

| Feature | Shield | Guard | Fortress |
|---------|--------|-------|----------|
| **Monthly incidents** | 50 | Unlimited | Unlimited |
| **L1/L2 auto-resolution** | ✅ | ✅ | ✅ |
| **L3/L4 LLM diagnosis** | ✅ | ✅ | ✅ |
| **PagerDuty integration** | ✅ | ✅ | ✅ |
| **Slack integration** | ✅ | ✅ | ✅ |
| **Dashboard** | ✅ | ✅ | ✅ |
| **API access** | ✅ | ✅ | ✅ |
| **Custom patterns** | ❌ | ❌ | ✅ |
| **Dedicated support** | ❌ | ✅ | ✅ |
| **SLA guarantee** | ❌ | ❌ | 99.9% |

### Usage tracking

You can check your current usage at any time:

```bash
curl -s https://your-itsmlab-instance.com/v1/stats \
  -H "X-API-Key: itsmlab_live_your_key_here"
```

The response includes:
- `total_incidents` — all-time incident count
- `monthly_incidents` — incidents this billing period
- `total_tokens_used` — LLM tokens consumed

### Rate limits

ITSMLab enforces per-tenant rate limits using a sliding window algorithm. Limits are based on your plan:

| Plan | Requests per hour | Window |
|------|-------------------|--------|
| Shield | 10 | 1 hour sliding |
| Guard | 50 | 1 hour sliding |
| Fortress | 200 | 1 hour sliding |

**Response headers:**

Every API response includes rate limit information in the response headers:

| Header | Description | Example |
|--------|-------------|---------|
| `X-RateLimit-Limit` | Maximum requests per hour | `10` |
| `X-RateLimit-Remaining` | Requests remaining in current window | `7` |
| `X-RateLimit-Reset` | Unix timestamp when the window resets | `1719360000` |

**When you exceed the limit:**

If you exceed your plan's rate limit, you'll receive a `429 Too Many Requests` response with additional information:

```json
{
  "detail": "Rate limit exceeded. Try again in 3600 seconds."
}
```

The response also includes a `Retry-After` header with the number of seconds to wait.

**Best practices:**
- Monitor the `X-RateLimit-Remaining` header to track your usage
- Implement exponential backoff when receiving 429 responses
- Upgrade your plan if you consistently hit the limit

### Graceful degradation

ITSMLab is designed to work even when the LLM (AI) provider is not configured. This is called **graceful degradation**.

**What happens if no API key is configured?**

| Feature | Behavior |
|---------|----------|
| **L1/L2 classification** | ✅ Works normally (no LLM needed) |
| **L3/L4 diagnosis** | ❌ Returns degraded response with setup instructions |
| **Health endpoint** | Shows `llm_available: false` |

**L3/L4 degraded response example (DeepSeek):**

```json
{
  "error": "Service Unavailable",
  "message": "LLM provider 'deepseek' not configured. Please set DEEPSEEK_API_KEY in your .env file.",
  "level": "L3/L4",
  "pattern_id": "LLM-UNAVAILABLE",
  "pattern_name": "LLM Provider Not Configured",
  "diagnosis": "LLM provider 'deepseek' not configured. Please set DEEPSEEK_API_KEY in your .env file.",
  "script": "1. Open the .env file in the project root\n2. Add DEEPSEEK_API_KEY=your_deepseek_api_key_here\n3. Restart the ITSMLab service\n4. Verify with GET /v1/health",
  "confidence": null
}
```

**L3/L4 degraded response example (Ollama):**

```json
{
  "error": "Service Unavailable",
  "message": "Ollama is not running or not reachable. Please ensure Ollama is installed and running.",
  "level": "L3/L4",
  "pattern_id": "LLM-UNAVAILABLE",
  "pattern_name": "Ollama Not Reachable",
  "diagnosis": "Ollama is not running or not reachable. Please ensure Ollama is installed and running.",
  "script": "1. Install Ollama from https://ollama.com\n2. Run: ollama pull llama3\n3. Run: ollama serve\n4. Verify: curl http://localhost:11434/api/tags\n5. Restart the ITSMLab service",
  "confidence": null
}
```

**How to check LLM status:**

```bash
curl -s https://your-itsmlab-instance.com/v1/health \
  -H "X-API-Key: itsmlab_live_your_key_here"
```

Look for these fields in the response:
- `llm_provider`: `"deepseek"`, `"openai"`, `"ollama"`, or `"unconfigured"`
- `llm_available`: `true` or `false`

**To configure the LLM:**

1. Set `LLM_PROVIDER=deepseek` (or `openai` or `ollama`) in your `.env` file
2. Set the corresponding API key (`DEEPSEEK_API_KEY` or `OPENAI_API_KEY`) if using external API
3. For Ollama, ensure the Ollama service is running
4. Restart the ITSMLab service
5. Verify with `GET /v1/health` — `llm_available` should be `true`

---

## 9. FAQ


### General

**Q: What happens if ITSMLab can't classify an incident?**

A: If the confidence score is below the threshold (45%), ITSMLab marks the incident as "UNKNOWN" and routes it to a human agent with all available context.

**Q: Does ITSMLab modify my systems?**

A: No. ITSMLab is a read-only diagnostic system. It provides resolution scripts, but does not execute them automatically unless explicitly configured to do so.

**Q: How is my data protected?**

A: All API communications use HTTPS. API keys are stored as SHA-256 hashes. Each tenant's data is isolated in a multi-tenant architecture.

**Q: Can I run ITSMLab on-premises?**

A: Yes. ITSMLab is designed for on-premise deployment. You can install it on your own infrastructure using Docker with a single command:

```bash
# Linux/macOS
curl -fsSL https://raw.githubusercontent.com/itsmlab/itsm-agent/main/install.sh | bash

# Windows (PowerShell)
.\install.ps1
```

See the [Installation Guide](./INSTALL.md) for complete instructions, including:
- Hardware requirements (RAM, disk, GPU)
- LLM provider configuration (Ollama local or external API)
- Docker Compose profiles for Ollama and HTTPS
- Troubleshooting common issues
- Architecture diagram

### Technical

**Q: What is the maximum payload size?**

A: The `title` field supports up to 500 characters, and `description` supports up to 10,000 characters.

**Q: What happens if I send too many requests?**

A: If you exceed your plan's rate limit, you'll receive a `429 Too Many Requests` response. Retry after the specified time.

**Q: How long are diagnosis results stored?**

A: Diagnosis results are stored for 90 days for Shield plans, and 365 days for Guard and Fortress plans.

**Q: Can I integrate ITSMLab with my own monitoring tool?**

A: Yes. Any tool that can send HTTP requests can integrate with ITSMLab via the REST API. See [Step 2](#4-step-2-api-integration) for details.

### Troubleshooting

**Q: I'm getting a 401 error. What should I do?**

A: Verify that:
1. Your API key starts with `itsmlab_live_`
2. The key is correctly copied (no extra spaces)
3. The key hasn't been revoked
4. You're sending it in the `X-API-Key` header

**Q: The diagnosis seems incorrect. How can I improve it?**

A: Provide more context in the `title` and `description` fields. Include error messages, affected components, and any recent changes. The more detail you provide, the better the classification.

**Q: How do I reset my API key?**

A: Contact your ITSMLab admin to generate a new key. The old key will be revoked immediately.

---

## 10. Support

### Contact channels

| Channel | Details |
|---------|---------|
| **Email** | support@itsmlab.com |
| **Slack** | Join our community: itsmlab.slack.com |
| **Documentation** | [docs.itsmlab.com](https://docs.itsmlab.com) |
| **Status page** | [status.itsmlab.com](https://status.itsmlab.com) |

### Response times

| Plan | Response Time | Support Hours |
|------|---------------|---------------|
| Shield | 24 hours | Business hours (Mon-Fri) |
| Guard | 4 hours | 24/7 |
| Fortress | 1 hour | 24/7 with dedicated engineer |

### Reporting issues

When reporting an issue, please include:

1. Your **tenant slug** (e.g., `acme-corp`)
2. The **timestamp** of the incident
3. The **request ID** from the error response (e.g., `b2c74afb-8ff6-47f2-b890-3444018ed24d`)
4. The **full request and response** (with API key masked)

---

> 🛡️ **ITSMLab** — Autonomous IT Incident Resolution · v3.1.0
>
> *"Your first line of defense, working 24/7."*
