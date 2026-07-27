# ⚡ ITSMLab — Autonomous AI Agent for IT Incident Resolution

> *"The knowledge to resolve any incident already exists — from repetitive L1 tickets to critical Tier-4 outages. It lives in postmortems, runbooks, and the experience of engineers who already solved your problem. ITSMLab puts it to work for your team in real time."*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-operational-green?logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-RAG-green?logo=chainlink&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-VectorDB-orange)
![LLM](https://img.shields.io/badge/LLM-Multi--Provider-purple)
![Status](https://img.shields.io/badge/Status-v3.1.0--On--Premise-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## The Problem

When an IT incident occurs — whether a routine L1 ticket or a full Tier-4 production outage:

| Reality | Impact |
|--------|--------|
| L1/L2 tickets consume **60-70%** of support team time | Despite having known resolutions |
| Tier-3/4 incidents take **4+ hours** to diagnose | Costing thousands to millions in downtime |
| The fix already exists in postmortems and runbooks | But is not accessible in real time |
| Knowledge lives in Slack threads and people's heads | Lost when engineers leave |

## The Solution

ITSMLab is a full-spectrum autonomous AI agent that resolves IT incidents across all severity levels:

1. **Receives** an alert or ticket via universal webhook (any HTTP POST)
2. **Classifies** L1/L2 tickets and suggests resolutions instantly (hybrid vector + keyword classifier)
3. **Diagnoses** L3/L4 root causes in **< 15 seconds** using RAG over 20 real incident patterns
4. **Delivers** a production-ready remediation script — human approves or auto-executes

### Deployment Options

ITSMLab supports **two deployment models**:

| Option | Description | Best for |
|--------|-------------|----------|
| **🏠 On-Premise** | Install in your own infrastructure via Docker | Privacy, air-gapped environments, data sovereignty |
| **☁️ SaaS** | Multi-tenant cloud service with billing | Teams that want a managed solution |

### LLM Provider Options

ITSMLab is **LLM-agnostic** — you choose the AI model:

| Provider | Type | Setup |
|----------|------|-------|
| **Ollama** (local) | Runs on your hardware | No API key needed, just Docker |
| **DeepSeek** | External API | `DEEPSEEK_API_KEY` in `.env` |
| **OpenAI** (GPT-4o, GPT-4o-mini) | External API | `OPENAI_API_KEY` in `.env` |
| **Anthropic** (Claude) | External API | `ANTHROPIC_API_KEY` in `.env` |

---

## How It Works

```
Alert / Ticket
      │
      ▼
[Integration Module]  ← universal webhook (POST /alert)
      │
 ┌────┴────┐
 │         │
 ▼         ▼
Classifier  Orchestrator
(L1/L2)    (L3/L4)
ChromaDB   LLM Provider
+ RAG      (Ollama / DeepSeek /
            OpenAI / Anthropic)
 │         │
 └────┬────┘
      │
      ▼
Diagnosis + Script
(ready in < 15s)
      │
      ▼
[Integration Module]  ← returns JSON response
Slack / PagerDuty / Jira / ServiceNow
```

### Timing breakdown

| Time | Action |
|------|--------|
| t = 0s | Alert or ticket enters ITSMLab via POST /alert |
| t = 2s | Integration Module normalizes and routes input |
| t = 5s | RAG engine searches pattern knowledge base |
| t = 10s | LLM generates tailored diagnosis |
| t = 15s | Remediation script ready for approval or auto-execution |

---

## Quick Start

### Option A: On-Premise Installation (recommended)

```bash
# One-command install — Linux / macOS
curl -fsSL https://raw.githubusercontent.com/itsmlab/itsm-agent/main/install.sh | bash

# One-command install — Windows (PowerShell)
# Download install.ps1 and run:
.\install.ps1
```

The installer will:
1. ✅ Check prerequisites (Docker, RAM, disk space)
2. ✅ Create `.env` with your chosen LLM provider
3. ✅ Start all services (app, PostgreSQL, ChromaDB)
4. ✅ Initialize the RAG knowledge base
5. ✅ Verify everything is running

> 📖 See [`INSTALL.md`](./INSTALL.md) for the complete installation guide.

### Option B: Manual Setup (for development)

```bash
git clone https://github.com/itsmlab/itsm-agent.git
cd itsm-agent

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### Configure LLM Provider

Create a `.env` file in the root:

```bash
# For local model (Ollama) — no API key needed
LLM_PROVIDER=ollama

# For external API — choose one:
# LLM_PROVIDER=deepseek
# DEEPSEEK_API_KEY=your-deepseek-api-key-here
#
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-openai-api-key
#
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key
```

> **Note:** If you don't configure an LLM, ITSMLab still works for L1/L2 classification. L3/L4 diagnosis will return a clear message explaining how to configure it. See [Graceful Degradation](#graceful-degradation).

### Run the server

```bash
python app/main.py
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** for the interactive API documentation.

### Send an alert

```bash
curl -X POST http://localhost:8000/v1/alert \
  -H "Content-Type: application/json" \
  -d '{
    "source": "manual",
    "severity": "low",
    "title": "User cannot log in",
    "description": "User gets 403 error when accessing the application"
  }'
```

### Run individual components (CLI mode)

```bash
# L3/L4 incident diagnostician
python orchestrator.py

# L1/L2 ticket classifier
python classifier.py

# Slack bot (Socket Mode)
python slack_bot.py

# Run accuracy tests
python test_classifier.py

# Run cross-validation
python cross_validation.py
```

---

## Architecture

| Layer | Component | Technology | Status |
|-------|-----------|-----------|--------|
| Integration | Integration Module v2 | FastAPI + webhooks + ChromaDB | ✅ Operational |
| L1/L2 Classification | Ticket Classifier | ChromaDB + SentenceTransformers + Keyword Fallback | ✅ Operational |
| L3/L4 Diagnosis | Incident Orchestrator | LLM Provider (Ollama / DeepSeek / OpenAI / Anthropic) + RAG | ✅ Operational |
| LLM Abstraction | Provider Factory | `app/llm/` — pluggable providers | ✅ 4 providers |
| Knowledge | Pattern Knowledge Base | 20 real incident patterns in markdown | ✅ 20 patterns |
| Execution | Script Executor | Sandbox + approval flow | 🔜 Phase 4 |

### L1/L2 Classifier Details

| Feature | Description |
|---------|-------------|
| **Dataset** | 77 IT support tickets across 8 categories |
| **Categories** | ACCESS, API, DATABASE, HOWTO, LICENSE, NETWORK, PERFORMANCE, SECURITY |
| **Method** | Hybrid: vector search + weighted voting + keyword fallback |
| **Confidence threshold** | 45% (returns UNKNOWN below threshold, reducing false positives) |
| **Multi-category** | Category distribution percentage shown for ambiguous tickets |
| **Suggested resolution** | Resolution from the most similar historical ticket |
| **Model** | all-MiniLM-L6-v2 (SentenceTransformers) |
| **Vector DB** | ChromaDB persistent local store (`tickets_db/`) |

#### Cross-Validation Results (5-fold stratified)

```
Accuracy:            75.3%
Weighted F1-Score:   0.805
Weighted Precision:  0.894
Weighted Recall:     0.753
Avg Confidence:      67.0%
```

| Category | Precision | Recall | F1-Score |
|----------|-----------|--------|----------|
| ACCESS   | 0.900     | 0.692  | 0.783    |
| API      | 1.000     | 0.714  | 0.833    |
| DATABASE | 0.909     | 0.909  | 0.909    |
| HOWTO    | 0.875     | 0.875  | 0.875    |
| LICENSE  | 0.857     | 0.857  | 0.857    |
| NETWORK  | 0.875     | 0.636  | 0.737    |
| PERF.    | 0.750     | 0.900  | 0.818    |
| SECURITY | 1.000     | 0.500  | 0.667    |

---

## Knowledge Base — 20 Real Incident Patterns

Extracted from public postmortems of companies that operate at scale:

| ID | Pattern | Source | Priority |
|----|---------|--------|----------|
| **AWS Patterns** | | | |
| ITSMLab-001 | Cascade dependency saturation | AWS Kinesis 2020 | 🔴 HIGH |
| ITSMLab-002 | Human error during deploy | AWS S3 2017 | 🔴 HIGH |
| ITSMLab-003 | Rate limiting / throttling spike | AWS DynamoDB 2021 | 🟡 MEDIUM |
| ITSMLab-004 | Cold starts and concurrency | AWS Lambda 2022 | 🟡 MEDIUM |
| ITSMLab-005 | Database failover failure | AWS RDS 2023 | 🔴 HIGH |
| **Other Cloud Patterns** | | | |
| ITSMLab-006 | DNS / Anycast routing loop | Cloudflare 2022 | 🔴 HIGH |
| ITSMLab-007 | Distributed cluster partition | Google Bigtable 2016 | 🔴 HIGH |
| ITSMLab-008 | MySQL metadata lock cascade | GitHub 2021 | 🔴 HIGH |
| ITSMLab-009 | Cassandra saturation post-chaos | Netflix 2018 | 🟡 MEDIUM |
| ITSMLab-010 | BGP route leak | Cloudflare 2024 | 🔴 HIGH |
| **Azure Patterns** | | | |
| ITSMLab-011 | Retry amplification cascade | Azure OpenAI 2026 | 🔴 HIGH |
| ITSMLab-012 | Control plane / managed identity failure | Azure VMs 2026 | 🔴 HIGH |
| ITSMLab-013 | DDoS mitigation misconfiguration | Azure Front Door 2024 | 🔴 HIGH |
| ITSMLab-014 | DNS resolution failure | Azure Front Door 2025 | 🔴 HIGH |
| ITSMLab-015 | Regional multi-service disruption | Azure West Europe 2025 | 🔴 HIGH |
| ITSMLab-016 | Entra ID / auth failures | Azure AD 2022 | 🔴 HIGH |
| ITSMLab-017 | Firewall network connectivity loss | Azure Firewall 2022 | 🔴 HIGH |
| ITSMLab-018 | WAN / network routing failure | Azure WAN 2023 | 🔴 HIGH |
| ITSMLab-019 | AKS node pool / control plane failure | Azure AKS 2024 | 🔴 HIGH |
| ITSMLab-020 | SQL connection pool exhaustion | Azure SQL 2025 | 🔴 HIGH |

Each pattern includes: symptoms, root cause diagnosis, and a production-ready remediation script.

---

## Recent Improvements

### v3.1.0 — On-Premise Ready (July 2026)

- **Multi-provider LLM abstraction** — Ollama, DeepSeek, OpenAI, Anthropic via pluggable factory
- **One-command installer** — `install.sh` (Linux/macOS) and `install.ps1` (Windows)
- **Docker Compose profiles** — Optional Ollama and Caddy (HTTPS) services
- **Dynamic degraded mode** — Provider-specific messages when LLM is unavailable
- **Installation guide** — [`INSTALL.md`](./INSTALL.md) with architecture diagram, requirements, troubleshooting
- **Anthropic/Claude support** — New provider using official SDK

### RAG with Pattern Chunking

The L3/L4 orchestrator now uses **Retrieval-Augmented Generation (RAG)** to select only the most relevant patterns from the knowledge base, instead of sending the full `ITSMLab_PATTERNS.md` to the LLM on every request.

- Each pattern is **chunked individually** and stored as a vector embedding in ChromaDB
- On diagnosis, only the **top-3 most relevant chunks** are retrieved based on semantic similarity
- This reduces **token usage by ~80%** and improves diagnosis speed
- Falls back to the full knowledge base if RAG is not initialized

Run the initialization script:
```bash
python scripts/init_knowledge_base.py
```

### Rate Limiting

ITSMLab enforces per-tenant rate limits based on plan:

| Plan | Requests per hour |
|------|-------------------|
| Shield | 10 |
| Guard | 50 |
| Fortress | 200 |

Rate limit information is returned in response headers:
- `X-RateLimit-Limit` — Maximum requests per hour
- `X-RateLimit-Remaining` — Requests remaining in the current window
- `X-RateLimit-Reset` — Unix timestamp when the window resets

When exceeded, the API returns **HTTP 429** with a clear error message.

### Graceful Degradation

If the LLM is not configured or unavailable, ITSMLab enters **degraded mode**:

- **L1/L2 classification** continues to work normally (no LLM needed)
- **L3/L4 diagnosis** returns **HTTP 503** with a provider-specific message explaining how to configure it
- The **health endpoint** (`GET /v1/health`) includes `llm_available: false` to signal the degraded state
- The orchestrator logs a warning at startup: `"LLM provider not configured"`

This allows you to evaluate the system, test L1/L2 classification, and explore the API without needing an LLM API key.

---

## API Reference

### POST /v1/alert

Receives any alert or ticket and returns diagnosis + remediation script.

**Request:**
```json
{
  "source": "manual",
  "severity": "low",
  "title": "User cannot log in",
  "description": "User gets 403 error when accessing the application"
}
```

**Response (L1/L2 example):**
```json
{
  "timestamp": "2026-06-16T01:21:36.238013",
  "source": "manual",
  "severity": "low",
  "level": "L1/L2",
  "pattern_id": "L1-001",
  "pattern_name": "Access / Authentication Issue",
  "diagnosis": "User authentication or authorization failure detected. (classified via vector_weighted, confidence 88.4%)",
  "script": "Suggested resolution: Verified user role permissions in application and granted access\n\n---\n\nStandard procedure:\n1. Verify user account is active...",
  "confidence": "HIGH"
}
```

**Response (L3/L4 example):**
```json
{
  "timestamp": "2026-06-16T01:21:36.238013",
  "source": "pagerduty",
  "severity": "critical",
  "level": "L3/L4",
  "pattern_id": "ITSMLab-005",
  "pattern_name": "Database Failover",
  "diagnosis": "Root cause explanation tailored to the alert...",
  "script": "#!/bin/bash\n# Remediation commands...",
  "confidence": null
}
```

### GET /v1/health

Returns system status — patterns file, classifier state, LLM provider, LLM availability, timestamp.

### GET /v1/stats

Returns classifier and usage statistics.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Integration | FastAPI + Uvicorn | Universal webhook — any system can send alerts via HTTP POST |
| L1/L2 Classification | ChromaDB + SentenceTransformers | Hybrid vector + keyword classifier with 77 tickets |
| L3/L4 Diagnosis | LLM Provider + RAG | Pluggable: Ollama, DeepSeek, OpenAI, Anthropic |
| Vector DB | ChromaDB (local) | Semantic search over incident patterns |
| LLM | Multiple providers | Choose local (Ollama) or external API (DeepSeek/OpenAI/Anthropic) |
| Runtime | Python 3.11+ | Fast prototyping, rich ML ecosystem |

---

## Repository Structure

```
aegis-itsm-agent/
│
├── app/                           # SaaS multi-tenant backend
│   ├── config.py                  # Centralized settings (pydantic-settings)
│   ├── database.py                # PostgreSQL + SQLite fallback
│   ├── models.py                  # Tenant, ApiKey, UsageRecord
│   ├── dependencies.py            # Auth middleware (X-API-Key)
│   ├── main.py                    # FastAPI entry point
│   ├── llm/                       # LLM provider abstraction
│   │   ├── base.py                # Abstract LLMProvider interface
│   │   ├── deepseek.py            # DeepSeek implementation
│   │   ├── openai_compat.py       # OpenAI-compatible (OpenAI, Ollama)
│   │   ├── ollama.py              # Ollama dedicated provider
│   │   ├── anthropic.py           # Anthropic/Claude provider
│   │   └── factory.py             # Provider factory
│   ├── services/                  # Business logic services
│   │   ├── classifier_service.py  # Multi-tenant classifier
│   │   ├── orchestrator_service.py# Multi-tenant orchestrator
│   │   ├── billing_service.py     # Usage tracking + quota enforcement
│   │   └── rate_limit_service.py  # Per-tenant rate limiting
│   ├── rag/                       # RAG knowledge base
│   │   └── knowledge_base.py      # Pattern chunking + retrieval
│   ├── templates/                 # HTML templates
│   │   └── dashboard.html         # Web dashboard (dark mode)
│   └── routers/                   # API endpoints
│       ├── alerts.py              # POST /v1/alert, GET /v1/health, GET /v1/stats
│       ├── admin.py               # POST /v1/admin/tenants, /api-keys
│       ├── dashboard.py           # GET /dashboard (web UI)
│       └── metrics.py             # GET /metrics (system metrics)
│
├── scripts/                       # Utility scripts
│   ├── init_knowledge_base.py     # Initialize RAG knowledge base
│   ├── evaluate_real_data.py      # Cross-validation with real data
│   └── import_real_data.py        # Import tickets from CSV to ChromaDB
│
├── alembic/                       # Database migrations
├── Dockerfile                     # Multi-stage Docker build
├── docker-compose.yml             # app + PostgreSQL + ChromaDB + Ollama (profile) + Caddy (profile)
├── Caddyfile                      # HTTPS reverse proxy config
├── install.sh                     # One-command installer (Linux/macOS)
├── install.ps1                    # One-command installer (Windows)
│
├── classifier.py              # L1/L2 hybrid classifier (vector + keyword fallback)
├── integration_module.py      # API webhook v2.0 (ChromaDB + DeepSeek + PagerDuty)
├── orchestrator.py            # L3/L4 incident diagnostician
├── slack_bot.py               # Slack bot (Socket Mode)
├── tickets_dataset.csv        # 77 IT support tickets in 8 categories
├── test_classifier.py         # Accuracy tests (22 tickets)
├── cross_validation.py        # 5-fold cross-validation with metrics
├── test_integration.py        # Import verification for integration module
├── ITSMLab_PATTERNS.md          # 20 real incident patterns (L3/L4 knowledge base)
├── ARCHITECTURE.md            # Technical architecture and design decisions
├── INSTALL.md                 # On-premise installation guide
├── CLIENT_INTEGRATION_GUIDE.md# Client integration guide
├── CONTRIBUTING.md            # Guide for contributors
├── CODE_OF_CONDUCT.md         # Community guidelines
├── CONSULTING_PROJECT.md      # Consulting proposal / case study
├── README.md                  # This file
├── LICENSE                    # MIT License
├── requirements.txt           # Python dependencies
├── .env.example               # Copy this to .env and fill in your keys
├── .gitignore                 # Excludes venv, .env, tickets_db, __pycache__
└── docs/                      # Business documentation
```

---

## Roadmap

| Phase | Timeline | Deliverable | Status |
|-------|---------|-------------|--------|
| 1 — Core | Weeks 1–2 | Integration Module, end-to-end demo | ✅ Complete |
| 2 — Beta | Weeks 3–6 | Slack bot, PagerDuty connector, 3 beta customers | ✅ Complete |
| A — SaaS Base | Weeks 7–8 | Multi-tenant FastAPI, PostgreSQL, LLM abstraction, Docker, billing | ✅ Complete |
| 1 — RAG Chunking | Week 9 | Pattern chunking, vector retrieval, reduced token usage | ✅ Complete |
| 2 — Rate Limiting | Week 10 | Per-tenant rate limits, response headers, 429 handling | ✅ Complete |
| 3 — Graceful Degradation | Week 11 | LLM-unavailable mode, 503 responses, health check indicators | ✅ Complete |
| 4 — On-Premise | Week 12 | Multi-provider LLM, install scripts, HTTPS, installation guide | ✅ Complete |
| 5 — Agent | Weeks 13–16 | Script auto-execution, feedback loop | 📅 Planned |
| 6 — Launch | Weeks 17–22 | Landing page, pricing live, 10 paying customers | 📅 Planned |
| 7 — Scale | Month 6+ | Jira/Opsgenie, 20+ patterns, enterprise pilots | 📅 Future |

---

## Consulting

I offer consulting services to help teams implement ITSMLab and automate their incident response:

- **Assessment** — Analyze your current incident management workflow and identify automation opportunities
- **Implementation** — Deploy ITSMLab in your environment (on-premise, cloud, or hybrid)
- **Customization** — Train the classifier on your historical tickets, add your runbooks to the knowledge base
- **Integration** — Connect ITSMLab to your existing tools (Slack, PagerDuty, Jira, ServiceNow, Datadog)
- **Training** — Teach your team how to maintain and extend ITSMLab

See [`CONSULTING_PROJECT.md`](./CONSULTING_PROJECT.md) for a detailed case study and proposal.

---

## Contributing

Contributions are welcome! Please see [`CONTRIBUTING.md`](./CONTRIBUTING.md) for guidelines.

This project follows a [Code of Conduct](./CODE_OF_CONDUCT.md) — be excellent to each other.

---

## About

Built by **Leopoldo Lara** — AI Solutions Engineer and M.Sc. in Artificial Intelligence (GPA 9.78/10) with 15+ years of enterprise experience at Blue Yonder and Epicor Software. Currently serving as Tier-4 Escalation Authority for mission-critical SaaS environments globally.

ITSMLab was born from firsthand exposure to hundreds of real incidents across 23 enterprise Azure deployments — and the conviction that the knowledge to resolve them should be available to every team, not just the ones with 10-year veterans on call at 3am.

- **GitHub**: [github.com/itsmlab](https://github.com/itsmlab)
- **LinkedIn**: [linkedin.com/in/leopoldo-lara](https://linkedin.com/in/leopoldo-lara)

---

## License

This project is licensed under the **MIT License**.  
See the [`LICENSE`](./LICENSE) file for details.

---

*See [`ITSMLab_PATTERNS.md`](./ITSMLab_PATTERNS.md) for the complete knowledge base, [`ARCHITECTURE.md`](./ARCHITECTURE.md) for technical design decisions, and [`INSTALL.md`](./INSTALL.md) for on-premise installation.*
