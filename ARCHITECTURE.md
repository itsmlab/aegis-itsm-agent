# ITSMLab Architecture v3.1 — Full-Spectrum IT Incident Resolution

## Overview

ITSMLab is a full-spectrum autonomous AI agent that resolves IT incidents across all severity levels — from routine L1/L2 support tickets to critical Tier-3/Tier-4 outages — in seconds rather than hours.

The architecture is built around three core principles:
- **Modular** — each component has a single responsibility and can be deployed independently
- **API-first** — every component exposes a clean interface for integration with existing stacks
- **Incremental** — teams can adopt ITSMLab at any level without replacing existing tools

---

## Automation Pyramid

```
                    ▲
               ┌────┴────┐
               │   L4    │  20% automation
               │ Expert  │  Root cause + hotfix coordination
               ├─────────┤
               │   L3    │  50% automation
               │ Complex │  RAG diagnosis + remediation script
               ├─────────┤
               │   L2    │  70% automation
               │Recurring│  Pattern matching + suggested fix
               ├─────────┤
               │   L1    │  90% automation
               │ Simple  │  Hybrid classification + auto-resolve
               └─────────┘
```

---

## Deployment Models

ITSMLab supports two deployment models:

### On-Premise (Docker)

```
┌─────────────────────────────────────────────────────────┐
│                    Client (Browser/API)                  │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTPS (optional with Caddy)
                      ▼
┌─────────────────────────────────────────────────────────┐
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │
│  │  Caddy   │───▶│  ITSMLab │───▶│   PostgreSQL     │  │
│  │ (proxy)  │    │   App    │    │   (datos)        │  │
│  └──────────┘    └────┬─────┘    └──────────────────┘  │
│                       │                                 │
│              ┌────────┴────────┐                       │
│              ▼                  ▼                       │
│     ┌──────────────┐  ┌──────────────────┐             │
│     │   ChromaDB   │  │   LLM Provider   │             │
│     │   (RAG/KB)   │  │                  │             │
│     └──────────────┘  ├──────────────────┤             │
│                       │  Ollama (local)  │             │
│                       │  ─ o ─           │             │
│                       │  DeepSeek API    │             │
│                       │  ─ o ─           │             │
│                       │  OpenAI API      │             │
│                       │  ─ o ─           │             │
│                       │  Anthropic API   │             │
│                       └──────────────────┘             │
└─────────────────────────────────────────────────────────┘
```

**Deployment via:**
- `install.sh` (Linux/macOS) — one-command automated installer
- `install.ps1` (Windows) — one-command automated installer
- `docker-compose.yml` with profiles for Ollama and Caddy

### SaaS (Multi-Tenant Cloud)

```
┌─────────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  PagerDuty  │────▶│          │     │  L1/L2       │────▶│  Auto-resolve │
│  Slack Bot  │────▶│  ITSMLab │────▶│  (routine)   │     │  + runbook    │
│  API Call   │────▶│  Engine  │     │  L3/L4       │────▶│  Escalate to  │
│  Webhook    │────▶│          │     │  (critical)  │     │  senior eng.  │
└─────────────┘     └──────────┘     └──────────────┘     └──────────────┘
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    INTEGRATION MODULE v2                     │
│         (Universal adapter — ChromaDB + LLM Provider)      │
│                                                             │
│  Webhook  │  Slack  │  PagerDuty  │  Jira  │  ServiceNow  │
└─────────────────────────┬───────────────────────────────────┘
                          │ normalized input
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      ITSMLab CORE                            │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────────┐   │
│  │  TICKET CLASSIFIER   │  │  INCIDENT ORCHESTRATOR   │   │
│  │      (L1 / L2)       │  │       (L3 / L4)          │   │
│  │                      │  │                          │   │
│  │  77 historical tickets│  │  Technical alerts        │   │
│  │         ↓            │  │         ↓                │   │
│  │  SentenceTransformers │  │  RAG Pattern Retrieval  │   │
│  │  + Keyword Fallback  │  │  (top-3 chunks)          │   │
│  │         ↓            │  │         ↓                │   │
│  │  ChromaDB vector DB  │  │  LLM Provider + RAG      │   │
│  │  + weighted voting   │  │  (Ollama / DeepSeek /    │   │
│  │         ↓            │  │   OpenAI / Anthropic)    │   │
│  │  Category + fix      │  │         ↓                │   │
│  │  + confidence score  │  │  Diagnosis + script      │   │
│  │  + suggested resol.  │  │                          │   │
│  └──────────────────────┘  └──────────────────────────┘   │
│                                                             │
└─────────────────────────┬───────────────────────────────────┘
                          │ result
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    INTEGRATION MODULE                        │
│                                                             │
│  Returns result to source system:                           │
│  Slack message / PagerDuty note / Jira comment /           │
│  ServiceNow incident update                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    SCRIPT EXECUTOR                          │
│              (Phase 5 — with human approval)                │
│                                                             │
│  Sandbox environment → Human approves → Execute → Verify   │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Integration Module (v2.0)
Universal adapter that normalizes inputs from any source, routes to L1/L2 classifier or L3/L4 orchestrator, and returns results.

**Key improvements in v2.0:**
- L1/L2 now uses the real ChromaDB hybrid classifier instead of keyword matching
- New `/stats` endpoint for classifier diagnostics
- Category mapping for all 8 L1/L2 categories

| Phase | Sources | Destinations | Target |
|-------|---------|-------------|--------|
| 1 | Universal webhook (HTTP POST) | Slack, email | SaaS 50–500 employees |
| 2 | Slack bot, PagerDuty, Datadog | Slack thread, PagerDuty note | SaaS with monitoring stack |
| 3 | Jira, Opsgenie, Grafana | Jira comment, annotation | Mid-market 500–2,000 |
| 4 | ServiceNow, BMC Remedy | Incident record, CMDB | Enterprise 2,000+ |

### 2. Ticket Classifier (L1/L2) — Hybrid
RAG-based classifier that matches incoming tickets against historical resolutions using vector search + keyword fallback.

- **Input:** Ticket description (free text)
- **Process:** Semantic embedding → ChromaDB similarity search → weighted voting by distance → keyword fallback if confidence < 45%
- **Output:** Category + suggested resolution + confidence score + multi-category distribution + method used
- **Dataset:** 77 IT support tickets across 8 categories (loaded from `tickets_dataset.csv`)
- **Categories:** ACCESS, API, DATABASE, HOWTO, LICENSE, NETWORK, PERFORMANCE, SECURITY
- **Model:** `all-MiniLM-L6-v2` (SentenceTransformers)
- **Threshold:** 45% (returns UNKNOWN below this, reducing false positives)
- **Storage:** ChromaDB persistent local store (`tickets_db/`)
- **Cross-validation (5-fold):** 75.3% accuracy, 0.805 weighted F1-score

### 3. Incident Orchestrator (L3/L4)
LLM + RAG engine that diagnoses critical incidents against real postmortem patterns.

- **Input:** Alert text (metrics, logs, error messages)
- **Process:** RAG pattern retrieval → LLM Provider → structured JSON response
- **Output:** Pattern ID + root cause diagnosis + remediation script
- **LLM Provider:** Configurable via `LLM_PROVIDER` in `.env` (ollama, deepseek, openai, anthropic)
- **Temperature:** 0.1 (consistency over creativity for diagnosis)
- **Response format:** JSON object (enforced via `response_format` where supported)

#### LLM Provider Abstraction

The `app/llm/` layer provides a pluggable provider system:

```
┌─────────────────────────────────────────────────────────┐
│                    LLM Provider Factory                   │
│                    (app/llm/factory.py)                   │
│                                                          │
│  LLM_PROVIDER=ollama    →  OllamaProvider                │
│  LLM_PROVIDER=deepseek  →  DeepSeekProvider              │
│  LLM_PROVIDER=openai    →  OpenAIProvider                │
│  LLM_PROVIDER=anthropic →  AnthropicProvider             │
└─────────────────────────────────────────────────────────┘
```

All providers implement the `LLMProvider` interface (`app/llm/base.py`):
- `diagnose(alert_text, patterns)` → `DiagnosisResult`
- `get_provider_name()` → `str`

**Provider-specific features:**

| Provider | JSON Mode | API Key Required | SDK |
|----------|-----------|------------------|-----|
| Ollama | Auto-detected per model | No | OpenAI-compatible |
| DeepSeek | ✅ Yes | Yes | OpenAI-compatible |
| OpenAI | ✅ Yes | Yes | OpenAI SDK |
| Anthropic | ✅ Yes | Yes | Anthropic SDK |

#### RAG with Pattern Chunking

The orchestrator uses **Retrieval-Augmented Generation (RAG)** to reduce token usage and improve diagnosis speed:

```
Alert text
    │
    ▼
[Embedding Model]  →  all-MiniLM-L6-v2 (384-dim vector)
    │
    ▼
[ChromaDB Collection]  →  "patterns_chunks"
    │  (20 chunks, one per pattern)
    ▼
[Top-3 most relevant chunks]  →  by cosine distance
    │
    ▼
[LLM Prompt]  →  alert + 3 relevant patterns
    │
    ▼
[Diagnosis + Script]
```

**Chunking strategy:**
- Each pattern in `ITSMLab_PATTERNS.md` is split into its own chunk using the `## Pattern ITSMLab-XXX` header as delimiter
- Chunks are embedded with `all-MiniLM-L6-v2` and stored in a dedicated ChromaDB collection (`patterns_chunks`)
- On diagnosis, only the **top-3 most relevant chunks** are retrieved based on semantic similarity to the alert
- This reduces token usage by **~80%** compared to sending the full knowledge base
- Falls back to the full knowledge base if RAG is not initialized

**Initialization:**
```bash
python scripts/init_knowledge_base.py
```

#### Graceful Degradation

If the LLM is not configured or unavailable, the orchestrator enters **degraded mode**:

- Detected at startup via `_check_api_key()` in `OrchestratorService`
- The `is_degraded` property signals the state to the API layer
- `diagnose()` returns a provider-specific diagnostic message instead of raising an exception
- `get_provider_name()` returns `"unconfigured"` instead of crashing
- The health endpoint exposes `llm_available: false`

**Behavior by component:**

| Component | Normal Mode | Degraded Mode |
|-----------|-------------|---------------|
| L1/L2 Classifier | Works normally | Works normally (no LLM needed) |
| L3/L4 Orchestrator | LLM diagnosis | Returns 503 with provider-specific setup instructions |
| Health endpoint | `llm_available: true` | `llm_available: false` |
| Logging | Normal operation | Warning at startup + per-request |

**Degraded mode messages are dynamic per provider:**
- `deepseek` → "Please set DEEPSEEK_API_KEY in your .env file"
- `openai` → "Please set OPENAI_API_KEY in your .env file"
- `anthropic` → "Please set ANTHROPIC_API_KEY in your .env file"
- `ollama` → "Ollama is not running or not reachable"

### 4. Knowledge Base
20 real incident patterns extracted from public postmortems.

| ID | Pattern | Source |
|----|---------|--------|
| ITSMLab-001 | Cascade dependency saturation | AWS Kinesis 2020 |
| ITSMLab-002 | Human error during deploy | AWS S3 2017 |
| ITSMLab-003 | Rate limiting / throttling spike | AWS DynamoDB 2021 |
| ITSMLab-004 | Cold starts and concurrency | AWS Lambda 2022 |
| ITSMLab-005 | Database failover failure | AWS RDS 2023 |
| ITSMLab-006 | DNS / Anycast routing loop | Cloudflare 2022 |
| ITSMLab-007 | Distributed cluster partition | Google Bigtable 2016 |
| ITSMLab-008 | MySQL metadata lock cascade | GitHub 2021 |
| ITSMLab-009 | Cassandra saturation post-chaos | Netflix 2018 |
| ITSMLab-010 | BGP route leak | Cloudflare 2024 |
| ITSMLab-011 | Retry amplification cascade | Azure OpenAI 2026 |
| ITSMLab-012 | Control plane / managed identity failure | Azure VMs 2026 |
| ITSMLab-013 | DDoS mitigation misconfiguration | Azure Front Door 2024 |
| ITSMLab-014 | DNS resolution failure | Azure Front Door 2025 |
| ITSMLab-015 | Regional multi-service disruption | Azure West Europe 2025 |
| ITSMLab-016 | Entra ID / auth failures | Azure AD 2022 |
| ITSMLab-017 | Firewall network connectivity loss | Azure Firewall 2022 |
| ITSMLab-018 | WAN / network routing failure | Azure WAN 2023 |
| ITSMLab-019 | AKS node pool / control plane failure | Azure AKS 2024 |
| ITSMLab-020 | SQL connection pool exhaustion | Azure SQL 2025 |

### 5. Rate Limiting

ITSMLab enforces per-tenant rate limits using an in-memory sliding window algorithm.

**Architecture:**

```
Request arrives
    │
    ▼
[RateLimitService.check_rate_limit(tenant_id, plan)]
    │
    ├── Cleanup expired timestamps (> 1 hour old)
    ├── Count requests in current window
    ├── If count >= limit → return False + 429 headers
    └── If count < limit → record timestamp → return True + headers
```

**Rate limits by plan:**

| Plan | Requests per hour | Window |
|------|-------------------|--------|
| Shield | 10 | 1 hour sliding |
| Guard | 50 | 1 hour sliding |
| Fortress | 200 | 1 hour sliding |

**Response headers:**

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests per hour |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset` | Unix timestamp when the window resets |
| `Retry-After` | Seconds to wait (only on 429 responses) |

**Implementation details:**
- Thread-safe: uses a `threading.Lock` to protect the counters dictionary
- In-memory: counters are not persisted across restarts
- Auto-cleanup: expired timestamps are removed on each check
- Singleton: `rate_limit_service` is shared across all endpoints

### 6. Script Executor (Phase 5)
Sandboxed execution environment with human approval flow.

- Receives script from Orchestrator
- Runs in isolated sandbox (no direct production access)
- Requires human approval before execution
- Logs result and feeds back to knowledge base

---

## Technology Stack

| Layer | Component | Technology | Status |
|-------|-----------|-----------|--------|
| Integration | Integration Module v2 | FastAPI + webhooks + ChromaDB | ✅ Operational |
| L1/L2 Classification | Ticket Classifier | ChromaDB + SentenceTransformers + Keyword Fallback | ✅ Operational |
| L3/L4 Diagnosis | Incident Orchestrator | LLM Provider (Ollama / DeepSeek / OpenAI / Anthropic) + RAG | ✅ Operational |
| LLM Abstraction | Provider Factory | `app/llm/` — pluggable providers | ✅ 4 providers |
| Knowledge | Pattern Knowledge Base | 20 real incident patterns in markdown | ✅ 20 patterns |
| RAG Retrieval | Pattern Chunking | ChromaDB + SentenceTransformers | ✅ Operational |
| Rate Limiting | Per-tenant sliding window | In-memory + threading.Lock | ✅ Operational |
| Graceful Degradation | LLM-unavailable mode | OrchestratorService degraded state | ✅ Operational |
| On-Premise Install | Installer scripts | `install.sh` (Linux/macOS), `install.ps1` (Windows) | ✅ v3.1.0 |
| HTTPS Proxy | Caddy | Automatic Let's Encrypt, Docker profile | ✅ v3.1.0 |
| Execution | Script Executor | Sandbox + approval flow | 🔜 Phase 5 |
| Infrastructure | Hosting | Railway / Fly.io | 🔜 Phase 6 |

---

## Learning Loop

```
Ticket/Alert created
        ↓
ITSMLab classifies or diagnoses
        ↓
Human reviews and resolves
        ↓
Resolution fed back to knowledge base
        ↓
ITSMLab improves for next similar incident
```

---

## File Structure

```
aegis-itsm-agent/
├── README.md                 # Project overview and quick start
├── ARCHITECTURE.md           # This file
├── INSTALL.md                # On-premise installation guide
├── ITSMLab_PATTERNS.md       # 20 incident patterns (L3-L4 knowledge base)
├── classifier.py             # L1-L2 hybrid classifier (vector + keyword fallback)
├── integration_module.py     # API webhook v2.0 (ChromaDB + DeepSeek)
├── orchestrator.py           # L3-L4 incident diagnostician
├── slack_bot.py              # Slack bot (Socket Mode)
├── tickets_dataset.csv       # 77 IT support tickets in 8 categories
├── test_classifier.py        # Accuracy tests (22 tickets)
├── test_integration.py       # Import verification for integration module
├── cross_validation.py       # 5-fold cross-validation with metrics
├── requirements.txt          # Python dependencies
├── .env                      # API keys (not in repo)
├── .gitignore                # Excludes venv, .env, tickets_db
├── Dockerfile                # Multi-stage Docker build
├── docker-compose.yml        # app + PostgreSQL + ChromaDB + Ollama (profile) + Caddy (profile)
├── Caddyfile                 # HTTPS reverse proxy config
├── install.sh                # One-command installer (Linux/macOS)
├── install.ps1               # One-command installer (Windows)
├── app/                      # SaaS multi-tenant backend
│   ├── config.py             # Centralized settings (pydantic-settings)
│   ├── database.py           # PostgreSQL + SQLite fallback
│   ├── models.py             # Tenant, ApiKey, UsageRecord
│   ├── dependencies.py       # Auth middleware (X-API-Key)
│   ├── main.py               # FastAPI entry point
│   ├── llm/                  # LLM provider abstraction
│   │   ├── base.py           # Abstract LLMProvider interface
│   │   ├── deepseek.py       # DeepSeek implementation
│   │   ├── openai_compat.py  # OpenAI-compatible (OpenAI, Ollama)
│   │   ├── ollama.py         # Ollama dedicated provider
│   │   ├── anthropic.py      # Anthropic/Claude provider
│   │   └── factory.py        # Provider factory
│   ├── services/
│   │   ├── classifier_service.py   # Multi-tenant classifier
│   │   ├── orchestrator_service.py # Orchestrator with graceful degradation
│   │   ├── billing_service.py      # Usage tracking + quota enforcement
│   │   └── rate_limit_service.py   # Per-tenant rate limiting
│   ├── rag/
│   │   └── knowledge_base.py       # Pattern chunking + retrieval
│   ├── templates/
│   │   └── dashboard.html          # Web dashboard (dark mode)
│   └── routers/
│       ├── alerts.py         # POST /v1/alert, GET /v1/health, GET /v1/stats
│       ├── admin.py          # POST /v1/admin/tenants, /api-keys
│       ├── dashboard.py      # GET /dashboard (web UI)
│       └── metrics.py        # GET /metrics (system metrics)
├── scripts/
│   ├── init_knowledge_base.py      # RAG knowledge base initialization
│   ├── evaluate_real_data.py       # Cross-validation with real data
│   └── import_real_data.py         # Import tickets from CSV to ChromaDB
├── docs/                     # Business documentation
│   ├── ITSMLab_Business_Document.docx
│   ├── ITSMLab_Executive_Summary.docx
│   ├── ITSMLab_Lean_Canvas_EN.docx
│   └── ITSMLab_Pitch_Deck.pptx
└── tickets_db/               # ChromaDB vector store (created at runtime)
```

---

## Roadmap

| Phase | Timeline | Focus | Status |
|-------|---------|-------|--------|
| 1 — Patterns | Completed | 20 incident patterns, hybrid classifier, orchestrator, v2 integration | ✅ Done |
| 2 — Beta | Weeks 3–6 | Slack bot, PagerDuty, 3 beta customers | ✅ Done |
| A — SaaS Base | Weeks 7–8 | Multi-tenant FastAPI, PostgreSQL, LLM abstraction, Docker, billing | ✅ Done |
| 1 — RAG Chunking | Week 9 | Pattern chunking, vector retrieval, reduced token usage | ✅ Done |
| 2 — Rate Limiting | Week 10 | Per-tenant rate limits, response headers, 429 handling | ✅ Done |
| 3 — Graceful Degradation | Week 11 | LLM-unavailable mode, 503 responses, health check indicators | ✅ Done |
| 4 — On-Premise | Week 12 | Multi-provider LLM, install scripts, HTTPS, installation guide | ✅ Done |
| 5 — Agent | Weeks 13–16 | Script auto-execution sandbox, feedback loop | 📅 Planned |
| 6 — Launch | Weeks 17–22 | Landing page, pricing live, 10 paying customers | 📅 Planned |
| 7 — Scale | Month 6+ | Jira, Opsgenie, 20+ patterns, enterprise pilots | 📅 Future |

---

## Pricing Tiers

| | ITSMLab Shield | ITSMLab Guard | ITSMLab Fortress |
|-|----------------|---------------|------------------|
| **Price** | $499/month | $1,499/month | Custom |
| **Incidents** | Up to 50/month | Unlimited | Unlimited |
| **Rate limit** | 10 req/hour | 50 req/hour | 200 req/hour |
| **Integration** | Webhook + Slack | + PagerDuty + Datadog | + ServiceNow + Jira |
| **Execution** | Manual approval | Sandbox auto-exec | Full autonomous |

---

*Last updated: July 2026 — ITSMLab v3.1 (On-Premise Ready)*
