# ⚡ AEGIS — Autonomous AI Agent for IT Incident Resolution

> *"The knowledge to resolve any incident already exists — from repetitive L1 tickets to critical Tier-4 outages. It lives in postmortems, runbooks, and the experience of engineers who already solved your problem. AEGIS puts it to work for your team in real time."*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-operational-green?logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-RAG-green?logo=chainlink&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-VectorDB-orange)
![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-purple)
![Status](https://img.shields.io/badge/Status-Phase%20A%20Complete-brightgreen)
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

AEGIS is a full-spectrum autonomous AI agent that resolves IT incidents across all severity levels:

1. **Receives** an alert or ticket via universal webhook (any HTTP POST)
2. **Classifies** L1/L2 tickets and suggests resolutions instantly (hybrid vector + keyword classifier)
3. **Diagnoses** L3/L4 root causes in **< 15 seconds** using RAG over 20 real incident patterns
4. **Delivers** a production-ready remediation script — human approves or auto-executes

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
ChromaDB   DeepSeek API
+ RAG      + RAG
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
| t = 0s | Alert or ticket enters AEGIS via POST /alert |
| t = 2s | Integration Module normalizes and routes input |
| t = 5s | RAG engine searches pattern knowledge base |
| t = 10s | LLM generates tailored diagnosis |
| t = 15s | Remediation script ready for approval or auto-execution |

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/laral5173/aegis-itsm-agent.git
cd aegis-itsm-agent

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 2. Configure API key

Create a `.env` file in the root:

```
DEEPSEEK_API_KEY=your-deepseek-api-key-here
```

Get your API key at [platform.deepseek.com](https://platform.deepseek.com)

### 3. Run the server

```bash
python app/main.py
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** for the interactive API documentation.

### 4. Send an alert

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

### 5. Run individual components (CLI mode)

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
| L3/L4 Diagnosis | Incident Orchestrator | DeepSeek API + RAG | ✅ Operational |
| Knowledge | Pattern Knowledge Base | 20 real incident patterns in markdown | ✅ 20 patterns |
| Execution | Script Executor | Sandbox + approval flow | 🔜 Phase 3 |

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
| AEGIS-001 | Cascade dependency saturation | AWS Kinesis 2020 | 🔴 HIGH |
| AEGIS-002 | Human error during deploy | AWS S3 2017 | 🔴 HIGH |
| AEGIS-003 | Rate limiting / throttling spike | AWS DynamoDB 2021 | 🟡 MEDIUM |
| AEGIS-004 | Cold starts and concurrency | AWS Lambda 2022 | 🟡 MEDIUM |
| AEGIS-005 | Database failover failure | AWS RDS 2023 | 🔴 HIGH |
| **Other Cloud Patterns** | | | |
| AEGIS-006 | DNS / Anycast routing loop | Cloudflare 2022 | 🔴 HIGH |
| AEGIS-007 | Distributed cluster partition | Google Bigtable 2016 | 🔴 HIGH |
| AEGIS-008 | MySQL metadata lock cascade | GitHub 2021 | 🔴 HIGH |
| AEGIS-009 | Cassandra saturation post-chaos | Netflix 2018 | 🟡 MEDIUM |
| AEGIS-010 | BGP route leak | Cloudflare 2024 | 🔴 HIGH |
| **Azure Patterns** | | | |
| AEGIS-011 | Retry amplification cascade | Azure OpenAI 2026 | 🔴 HIGH |
| AEGIS-012 | Control plane / managed identity failure | Azure VMs 2026 | 🔴 HIGH |
| AEGIS-013 | DDoS mitigation misconfiguration | Azure Front Door 2024 | 🔴 HIGH |
| AEGIS-014 | DNS resolution failure | Azure Front Door 2025 | 🔴 HIGH |
| AEGIS-015 | Regional multi-service disruption | Azure West Europe 2025 | 🔴 HIGH |
| AEGIS-016 | Entra ID / auth failures | Azure AD 2022 | 🔴 HIGH |
| AEGIS-017 | Firewall network connectivity loss | Azure Firewall 2022 | 🔴 HIGH |
| AEGIS-018 | WAN / network routing failure | Azure WAN 2023 | 🔴 HIGH |
| AEGIS-019 | AKS node pool / control plane failure | Azure AKS 2024 | 🔴 HIGH |
| AEGIS-020 | SQL connection pool exhaustion | Azure SQL 2025 | 🔴 HIGH |

Each pattern includes: symptoms, root cause diagnosis, and a production-ready remediation script.

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
  "pattern_id": "AEGIS-005",
  "pattern_name": "Database Failover",
  "diagnosis": "Root cause explanation tailored to the alert...",
  "script": "#!/bin/bash\n# Remediation commands...",
  "confidence": null
}
```

### GET /v1/health

Returns system status — patterns file, classifier state, LLM provider, timestamp.

### GET /v1/stats

Returns classifier and usage statistics.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Integration | FastAPI + Uvicorn | Universal webhook — any system can send alerts via HTTP POST |
| L1/L2 Classification | ChromaDB + SentenceTransformers | Hybrid vector + keyword classifier with 77 tickets |
| L3/L4 Diagnosis | DeepSeek API + RAG | Cost-effective, high-quality diagnosis ($0.14/1M tokens) |
| Vector DB | ChromaDB (local) | Semantic search over incident patterns |
| LLM | DeepSeek API | Cost-effective, high-quality diagnosis ($0.14/1M tokens) |
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
│   │   └── factory.py             # Provider factory
│   ├── services/                  # Business logic services
│   │   ├── classifier_service.py  # Multi-tenant classifier
│   │   ├── orchestrator_service.py# Multi-tenant orchestrator
│   │   └── billing_service.py     # Usage tracking + quota enforcement
│   ├── templates/                 # HTML templates
│   │   └── dashboard.html         # Web dashboard (dark mode)
│   └── routers/                   # API endpoints
│       ├── alerts.py              # POST /v1/alert, GET /v1/health, GET /v1/stats
│       ├── admin.py               # POST /v1/admin/tenants, /api-keys
│       └── dashboard.py           # GET /dashboard (web UI)
│
├── scripts/                       # Utility scripts
│   ├── evaluate_real_data.py      # Cross-validation with real data
│   └── import_real_data.py        # Import tickets from CSV to ChromaDB
│
├── alembic/                       # Database migrations
├── Dockerfile                     # Multi-stage Docker build
├── docker-compose.yml             # app + PostgreSQL + ChromaDB
│
├── classifier.py              # L1/L2 hybrid classifier (vector + keyword fallback)
├── integration_module.py      # API webhook v2.0 (ChromaDB + DeepSeek + PagerDuty)
├── orchestrator.py            # L3/L4 incident diagnostician
├── slack_bot.py               # Slack bot (Socket Mode)
├── tickets_dataset.csv        # 77 IT support tickets in 8 categories
├── test_classifier.py         # Accuracy tests (22 tickets)
├── cross_validation.py        # 5-fold cross-validation with metrics
├── test_integration.py        # Import verification for integration module
├── AEGIS_PATTERNS.md          # 20 real incident patterns (L3/L4 knowledge base)
├── ARCHITECTURE.md            # Technical architecture and design decisions
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
| 3 — Agent | Weeks 9–12 | Script auto-execution, feedback loop | 📅 Planned |
| 4 — Launch | Weeks 13–18 | Landing page, pricing live, 10 paying customers | 📅 Planned |
| 5 — Scale | Month 6+ | Jira/Opsgenie, 20+ patterns, enterprise pilots | 📅 Future |

---

## Consulting

I offer consulting services to help teams implement AEGIS and automate their incident response:

- **Assessment** — Analyze your current incident management workflow and identify automation opportunities
- **Implementation** — Deploy AEGIS in your environment (on-premise, cloud, or hybrid)
- **Customization** — Train the classifier on your historical tickets, add your runbooks to the knowledge base
- **Integration** — Connect AEGIS to your existing tools (Slack, PagerDuty, Jira, ServiceNow, Datadog)
- **Training** — Teach your team how to maintain and extend AEGIS

See [`CONSULTING_PROJECT.md`](./CONSULTING_PROJECT.md) for a detailed case study and proposal.

---

## Contributing

Contributions are welcome! Please see [`CONTRIBUTING.md`](./CONTRIBUTING.md) for guidelines.

This project follows a [Code of Conduct](./CODE_OF_CONDUCT.md) — be excellent to each other.

---

## About

Built by **Leopoldo Lara** — AI Solutions Engineer and M.Sc. in Artificial Intelligence (GPA 9.78/10) with 15+ years of enterprise experience at Blue Yonder and Epicor Software. Currently serving as Tier-4 Escalation Authority for mission-critical SaaS environments globally.

AEGIS was born from firsthand exposure to hundreds of real incidents across 23 enterprise Azure deployments — and the conviction that the knowledge to resolve them should be available to every team, not just the ones with 10-year veterans on call at 3am.

- **GitHub**: [github.com/laral5173](https://github.com/laral5173)
- **LinkedIn**: [linkedin.com/in/leopoldo-lara](https://linkedin.com/in/leopoldo-lara)

---

## License

This project is licensed under the **MIT License**.  
See the [`LICENSE`](./LICENSE) file for details.

---

*See [`AEGIS_PATTERNS.md`](./AEGIS_PATTERNS.md) for the complete knowledge base and [`ARCHITECTURE.md`](./ARCHITECTURE.md) for technical design decisions.*
