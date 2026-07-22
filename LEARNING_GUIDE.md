# 📘 AEGIS — Learning Guide

> *Welcome to AEGIS. This guide is designed for anyone who wants to understand how the system works, whether you're a developer, DevOps engineer, PM, or just curious. Everything is explained in plain language with analogies and practical examples.*

> *"The knowledge to resolve any incident already exists. You just need to know where to find it."*

---

## Table of Contents

1. [🧠 Glossary of Technical Terms](#1--glossary-of-technical-terms)
2. [🏗️ The Architecture (The Incident Hospital)](#2--the-architecture-the-incident-hospital)
3. [🔄 The Journey of an Alert (Complete Flow)](#3--the-journey-of-an-alert-complete-flow)
4. [📂 Key Files Explained](#4--key-files-explained)
5. [🛠️ Useful Commands (Your Toolbox)](#5--useful-commands-your-toolbox)
6. [❓ Frequently Asked Questions](#6--frequently-asked-questions)

---

## 1. 🧠 Glossary of Technical Terms

Each term has a card with three parts:
- **What is it?** — Simple explanation, like for a teammate
- **What is it used for in AEGIS?** — Its purpose in the project
- **🔍 Found in:** — File(s) where it's used

---

### FastAPI

**What is it?** A modern Python framework for creating REST APIs. It's fast (as the name says), easy to use, and generates automatic documentation.

**What is it used for in AEGIS?** It's the heart of the backend. It defines all endpoints (`/v1/alert`, `/v1/health`, etc.), validates incoming and outgoing data, and generates interactive documentation at `/docs`.

**🔍 Found in:** `app/main.py`, `app/routers/alerts.py`, `app/routers/admin.py`

---

### Uvicorn

**What is it?** The "engine" that runs FastAPI. It's an ASGI server (the modern version of WSGI) that allows Python to handle many simultaneous connections.

**What is it used for in AEGIS?** When you run `python app/main.py` or `uvicorn app.main:app --reload`, Uvicorn starts the server and begins listening for requests at `http://localhost:8000`.

**🔍 Found in:** `app/main.py` (line 118: `uvicorn.run(...)`)

---

### Endpoint / Route

**What is it?** Each "URL address" exposed by the API. It's like a specific door in a building: each door leads to a different place.

**What is it used for in AEGIS?** Defines the system's entry points:
- `POST /v1/alert` → Send an alert for diagnosis
- `GET /v1/health` → Check if the system is alive
- `GET /v1/stats` → View usage statistics
- `POST /v1/admin/tenants` → Create a new client

**🔍 Found in:** `app/routers/alerts.py`, `app/routers/admin.py`

---

### Pydantic

**What is it?** A "quality control" for JSON data. It defines exactly what fields are expected, their types, and whether they are required or optional. If someone sends incorrect data, Pydantic rejects it before it reaches the program logic.

**What is it used for in AEGIS?** Defines data models: `AlertRequest` (incoming), `DiagnosisResponse` (outgoing), `CreateTenantRequest` (for creating clients). Also used for system configuration with `pydantic-settings`.

**🔍 Found in:** `app/config.py`, `app/routers/alerts.py`, `app/routers/admin.py`

---

### SQLAlchemy

**What is it?** A "translator" between Python and relational databases. It lets you work with databases using Python objects instead of writing SQL directly.

**What is it used for in AEGIS?** Manages all persistent information: tenants (clients), API keys, and usage records. Supports PostgreSQL in production and SQLite in development.

**🔍 Found in:** `app/database.py`, `app/models.py`

---

### ORM (Object-Relational Mapping)

**What is it?** The technique of representing database tables as Python classes. Each table row is an object, each column is an attribute.

**What is it used for in AEGIS?** The `Tenant`, `ApiKey`, and `UsageRecord` classes are ORM models. When you do `db.query(Tenant).first()`, SQLAlchemy translates that to SQL, queries the database, and returns a Python object.

**🔍 Found in:** `app/models.py`

---

### PostgreSQL

**What is it?** An open-source relational database, very powerful and reliable. It's the project's main database.

**What is it used for in AEGIS?** Stores operational data: client information (tenants), their API keys, and usage records for billing.

**🔍 Found in:** `app/config.py` (line 42: `DATABASE_URL`), `docker-compose.yml`

---

### SQLite

**What is it?** A database that doesn't need a server. Everything is stored in a single local file. Ideal for development and testing.

**What is it used for in AEGIS?** It's the automatic "Plan B". If you don't have PostgreSQL installed, the system creates an `aegis_dev.db` file and works the same way. This lets you develop without needing to install PostgreSQL.

**🔍 Found in:** `app/database.py` (`_create_sqlite_engine()` function)

---

### Alembic

**What is it?** A "version control" for the database. Just as Git saves changes to your code, Alembic saves changes to the database schema.

**What is it used for in AEGIS?** When you add a new field to a model or create a new table, Alembic generates a "migration" that can be applied to any database (development, testing, production).

**🔍 Found in:** `alembic/` (folder), `alembic.ini`

---

### ChromaDB

**What is it?** A special database that understands the *meaning* of texts, not just exact words. It's a "vector database" (Vector DB).

**What is it used for in AEGIS?** Stores the 77 historical tickets as vectors (embeddings). When a new ticket arrives, ChromaDB searches for the most similar historical tickets by meaning, not by exact words. Also stores the 20 incident pattern chunks for RAG retrieval.

**🔍 Found in:** `classifier.py` (line 137: `chromadb.PersistentClient`), `tickets_db/` (data folder), `app/rag/knowledge_base.py`

---

### Embedding

**What is it?** Imagine converting a sentence into a numeric code that captures its "essence" or "meaning". So "I forgot my password" and "I can't log in" end up with similar codes, even though they use different words.

**What is it used for in AEGIS?** The classifier converts each ticket to an embedding (a vector of 384 numbers) and searches for historical tickets with similar embeddings. It's like searching by "scent" instead of by labels.

**🔍 Found in:** `classifier.py` (line 133: `model.encode(description)`)

---

### SentenceTransformers

**What is it?** A Python library that generates embeddings from text. It takes a sentence and returns a numeric vector.

**What is it used for in AEGIS?** It's the tool the classifier uses to convert tickets to vectors. We use the `all-MiniLM-L6-v2` model because it's small, fast, and gives good results. Also used by the RAG knowledge base to embed pattern chunks.

**🔍 Found in:** `classifier.py` (line 12: `from sentence_transformers import SentenceTransformer`), `app/rag/knowledge_base.py`

---

### all-MiniLM-L6-v2

**What is it?** The specific embedding model we use. It's a small model (80 MB) that generates 384-dimensional vectors. "Mini" because it's lightweight, "LM" because it's a language model.

**What is it used for in AEGIS?** It's the brain of the classifier and the RAG knowledge base. It converts text into numeric vectors that ChromaDB can search.

**🔍 Found in:** `classifier.py` (line 34: `EMBEDDING_MODEL = "all-MiniLM-L6-v2"`), `app/rag/knowledge_base.py`

---

### Vector DB (Vector Database)

**What is it?** A database that searches by "semantic similarity" instead of exact match. It's like searching for "movies similar to this one" instead of "movies that have the word X in the title".

**What is it used for in AEGIS?** ChromaDB is our Vector DB. When classifying a ticket, we search for the most similar historical tickets by meaning, not by keywords. Also used for RAG pattern retrieval.

**🔍 Found in:** `classifier.py` (lines 307-310: `collection.query(query_embeddings=[...])`), `app/rag/knowledge_base.py`

---

### RAG (Retrieval-Augmented Generation)

**What is it?** A technique that combines two steps: first it **retrieves** relevant information from a knowledge base, then **generates** a response using an LLM with that information as context. It's like a student who first checks their notes and then answers the exam.

**What is it used for in AEGIS?** The L3/L4 orchestrator uses RAG in two ways:
1. **Legacy mode:** Loads `AEGIS_PATTERNS.md` (all 20 patterns) and sends them to the LLM
2. **RAG mode (improved):** Chunks each pattern individually, embeds them in ChromaDB, retrieves only the top-3 most relevant chunks, and sends those to the LLM — reducing token usage by ~80%

**🔍 Found in:** `orchestrator.py` (lines 89-95), `app/rag/knowledge_base.py`, `app/services/orchestrator_service.py`

---

### LLM (Large Language Model)

**What is it?** An artificial intelligence model trained on enormous amounts of text. It can understand language, answer questions, generate code, etc. Examples: GPT-4, DeepSeek, Llama.

**What is it used for in AEGIS?** It's the "brain" of L3/L4 diagnosis. It receives the alert and incident patterns, analyzes them, and generates a diagnosis and remediation script.

**🔍 Found in:** `app/llm/` (complete folder), `orchestrator.py`

---

### DeepSeek

**What is it?** An LLM created by DeepSeek (Chinese company). It's very economical ($0.14 per million tokens) and has good quality. It uses an OpenAI-compatible API.

**What is it used for in AEGIS?** It's the default LLM for L3/L4 diagnosis. Its low cost allows running many diagnoses without spending a fortune.

**🔍 Found in:** `app/llm/deepseek.py`, `app/config.py` (line 33: `DEEPSEEK_MODEL = "deepseek-chat"`)

---

### OpenAI-compatible API

**What is it?** A standard format for communicating with LLMs. If an AI provider says "has OpenAI-compatible API", it means you can use the same code you'd use with ChatGPT, just changing the URL and API key.

**What is it used for in AEGIS?** DeepSeek, OpenAI, and Ollama (local) all use the same API format. This allows switching providers by just changing a variable in `.env`.

**🔍 Found in:** `app/llm/openai_compat.py`, `app/llm/factory.py`

---

### Multi-tenancy

**What is it?** An architecture where a single system serves multiple clients (tenants), keeping their data isolated. Like an apartment building: same building, different apartments, each with its own key.

**What is it used for in AEGIS?** Allows multiple clients to use the same AEGIS instance, each with their own API key, their own plan (Shield/Guard/Fortress), and their own usage limits.

**🔍 Found in:** `app/models.py` (class `Tenant`), `app/dependencies.py` (`get_current_tenant()` function)

---

### Tenant

**What is it?** Each client in a multi-tenant system. It's an organization using the service.

**What is it used for in AEGIS?** Each tenant has:
- A unique `id` (UUID)
- An identifying `slug` (e.g., "acme-corp")
- A `plan` (shield, guard, fortress)
- One or more `ApiKey` for authentication
- Their own `UsageRecord` for billing

**🔍 Found in:** `app/models.py` (class `Tenant`)

---

### L1/L2

**What is it?** Support levels 1 and 2. These are routine and recurring tickets: access problems, how-to questions, licenses, simple configurations. They represent 60-70% of support volume.

**What is it used for in AEGIS?** The hybrid classifier (ChromaDB + keywords) is designed to automate these tickets. Examples:
- "I can't log in" → ACCESS
- "How do I configure my email signature?" → HOWTO
- "My Office license expired" → LICENSE

**🔍 Found in:** `classifier.py`, `app/services/classifier_service.py`

---

### L3/L4

**What is it?** Support levels 3 and 4. These are critical incidents: server crashes, database failures, network problems, outages. They require deep diagnosis and technical expertise.

**What is it used for in AEGIS?** The orchestrator with RAG + LLM is designed to diagnose these incidents. Examples:
- "Database server not responding, timeout on all connections" → AEGIS-005
- "p99 latency went from 50ms to 30s after deploy" → AEGIS-001

**🔍 Found in:** `orchestrator.py`, `app/services/orchestrator_service.py`

---

### Hybrid Classifier

**What is it?** A classifier that uses two methods instead of just one. It's like having a Plan B in case Plan A fails.

**What is it used for in AEGIS?** The classifier first tries vector search (semantic). If confidence is low (< 45%), it uses keywords as a fallback. This ensures we always have an answer, even for tickets with unusual vocabulary.

**🔍 Found in:** `classifier.py` (`classify_ticket()` function, lines 295-394)

---

### Keyword Fallback

**What is it?** The classifier's "Plan B". If vector search doesn't find similar tickets with enough confidence, a keyword system determines the category.

**What is it used for in AEGIS?** If someone writes a ticket with very specific words that don't appear in historical tickets, the vector system might not recognize it. Keywords act as a safety net.

**🔍 Found in:** `classifier.py` (`classify_by_keywords()` function, lines 253-293)

---

### Confidence Threshold

**What is it?** A minimum confidence limit. If the system isn't sure enough about its answer, it prefers to say "I don't know" rather than risk giving an incorrect answer.

**What is it used for in AEGIS?** The threshold is 45% (0.45). If the classifier's confidence is lower, it returns UNKNOWN. This reduces false positives: it's better for a ticket to go to human review than to be misclassified.

**🔍 Found in:** `classifier.py` (line 36: `CONFIDENCE_THRESHOLD = 0.45`)

---

### Postmortem

**What is it?** A detailed analysis after a serious incident. It documents what happened, why it happened, how it was detected, how it was resolved, and what will be done to prevent it from happening again.

**What is it used for in AEGIS?** The 20 patterns in `AEGIS_PATTERNS.md` are based on real postmortems from companies like AWS, Cloudflare, Google, GitHub, Netflix, and Azure. Each pattern captures the lessons learned from a real incident.

**🔍 Found in:** `AEGIS_PATTERNS.md` (each pattern has a "Source" section with the original postmortem)

---

### Pattern Knowledge Base

**What is it?** A library of documented incident patterns. Each pattern describes: symptoms, diagnosis, and solution.

**What is it used for in AEGIS?** It's the `AEGIS_PATTERNS.md` file with 20 patterns. The orchestrator uses it as context for the LLM. When an alert arrives, the LLM compares the symptoms against each pattern and chooses the most similar one.

**🔍 Found in:** `AEGIS_PATTERNS.md` (1142 lines, 20 patterns)

---

### Socket Mode (Slack)

**What is it?** A Slack connection mode that doesn't require exposing a public server. The bot connects to Slack through a "socket" (communication channel) initiated by the bot itself.

**What is it used for in AEGIS?** The Slack Bot (`slack_bot.py`) uses Socket Mode. This means you can run it on your local machine or a private server, without needing to configure public URLs or HTTPS.

**🔍 Found in:** `slack_bot.py` (line 29: `from slack_bolt.adapter.socket_mode import SocketModeHandler`)

---

### Webhook

**What is it?** A "doorbell" that rings when an event occurs. System A sends an HTTP request to System B when something important happens.

**What is it used for in AEGIS?** PagerDuty sends alerts to AEGIS via a webhook (`POST /pagerduty`). When an incident occurs in PagerDuty, it "rings the doorbell" of AEGIS with all the details.

**🔍 Found in:** `integration_module.py` (line 450: `@app.post("/pagerduty")`)

---

### X-API-Key

**What is it?** An "ID card" for accessing the API. It's a secret string that identifies who is making the request.

**What is it used for in AEGIS?** Each tenant has one or more API keys. When someone makes a request to `/v1/alert`, they must include the header `X-API-Key: aeg_live_...`. The system looks up the key in the database, identifies the tenant, and checks their plan and quota.

**🔍 Found in:** `app/dependencies.py` (`get_current_tenant()` function)

---

### Docker

**What is it?** A platform for running applications in "containers". A container is like a lightweight virtual machine that includes everything needed for the application to run.

**What is it used for in AEGIS?** The `docker-compose.yml` starts the core services: AEGIS app, PostgreSQL, and ChromaDB. With optional profiles for Ollama (local LLM) and Caddy (HTTPS proxy). AEGIS provides one-command installers:
- `install.sh` (Linux/macOS) — Automated installation with prerequisite checks
- `install.ps1` (Windows) — Automated installation with prerequisite checks

**🔍 Found in:** `Dockerfile`, `docker-compose.yml`, `install.sh`, `install.ps1`, `Caddyfile`

---

### Sandbox (Script Executor)

**What is it?** An isolated and secure environment for executing code without risk. It's like a "playground" where scripts can run without affecting the real system.

**What is it used for in AEGIS?** It's a planned feature (Phase 4 of the roadmap). The orchestrator generates remediation scripts, but before executing them in production, they go through a sandbox where a human reviews and approves them.

**🔍 Found in:** `ARCHITECTURE.md` (section "Script Executor (Phase 4)")

---

### Rate Limiting

**What is it?** A mechanism that controls how many requests a client can make in a given time period. Like a subway turnstile that only lets a certain number of people through per minute.

**What is it used for in AEGIS?** Each tenant has a rate limit based on their plan (Shield: 10 req/hour, Guard: 50 req/hour, Fortress: 200 req/hour). The `RateLimitService` uses an in-memory sliding window algorithm. When exceeded, the API returns HTTP 429 with rate limit headers.

**🔍 Found in:** `app/services/rate_limit_service.py`

---

### Graceful Degradation

**What is it?** The ability of a system to continue functioning (at a reduced capacity) when a component is unavailable. Like a car that can still drive on 3 cylinders if one fails.

**What is it used for in AEGIS?** If the LLM API key is not configured, AEGIS enters degraded mode:
- L1/L2 classification continues working normally
- L3/L4 diagnosis returns HTTP 503 with setup instructions
- The health endpoint shows `llm_available: false`

**🔍 Found in:** `app/services/orchestrator_service.py`, `app/routers/alerts.py`

---

## 2. 🏗️ The Architecture (The Incident Hospital)

Imagine AEGIS is a **hospital specialized in IT incidents**. Each area of the hospital has a specific function:

```
┌──────────────────────────────────────────────────────────────┐
│                     🏥 AEGIS HOSPITAL                        │
│                                                              │
│  🚪 RECEPTION                    📋 ADMINISTRATION          │
│  (app/main.py + routers/)        (app/routers/admin.py)     │
│  • Receives the patient          • Registers new clients     │
│  • Asks for ID                   • Generates credentials     │
│  • Verifies insurance            • Checks history            │
│                                                              │
│  🩺 TRIAGE                          💊 PHARMACY             │
│  (app/services/)                    (app/llm/)              │
│  • Is it simple? → Classifier       • DeepSeek (default)    │
│  • Is it critical? → Orchestrator   • OpenAI (alternative)  │
│                                      • Ollama (local)        │
│                                                              │
│  📋 MEDICAL RECORDS                 📚 MEDICAL LIBRARY      │
│  (app/database.py + models.py)      (AEGIS_PATTERNS.md)     │
│  • Patient data (tenants)           • 20 documented cases    │
│  • Visit history (usage)            • Symptoms + diagnosis   │
│                                      • Remediation scripts   │
│                                                              │
│  🧰 CONFIGURATION                                           │
│  (app/config.py)                                             │
│  • What medications do we have?                              │
│  • What are our hours?                                       │
│  • Who do we call in an emergency?                           │
└──────────────────────────────────────────────────────────────┘
```

---

### 🚪 Reception — API Layer (`app/main.py` + `app/routers/`)

**What does it do?** It's the entry door. Everything that enters or leaves AEGIS passes through here.

- Receives HTTP requests (alerts, health checks, administration)
- Validates that data is correct (Pydantic)
- Identifies the client (X-API-Key)
- Verifies they have coverage (plan and quota)
- Routes to the corresponding service

**Key files:**
- `app/main.py` — Entry point, configures the app, CORS, error handling
- `app/routers/alerts.py` — Alert endpoints: `POST /v1/alert`, `GET /v1/health`, `GET /v1/stats`
- `app/routers/admin.py` — Administration endpoints: create tenants, generate API keys

**To explore more:** Open `http://localhost:8000/docs` when the server is running. There you'll see all documented endpoints.

---

### 🩺 Triage — Service Layer (`app/services/`)

**What does it do?** It's the diagnosis area. Determines the severity of the incident and applies the appropriate treatment.

- **ClassifierService** — For simple tickets (L1/L2): searches history, classifies by category, suggests resolution
- **OrchestratorService** — For critical incidents (L3/L4): consults the pattern library, calls the LLM, generates diagnosis
- **BillingService** — Tracks how many incidents each client has used this month
- **RateLimitService** — Controls request rate per tenant (sliding window algorithm)

**Key files:**
- `app/services/classifier_service.py` — Multi-tenant classifier
- `app/services/orchestrator_service.py` — Orchestrator with LLM + graceful degradation
- `app/services/billing_service.py` — Usage tracking and billing
- `app/services/rate_limit_service.py` — Per-tenant rate limiting

**To explore more:** Check how `alerts.py` calls these services. The `process_alert()` function is the best starting point.

---

### 💊 Pharmacy — LLM Layer (`app/llm/`)

**What does it do?** This is where the "medications" (language models) are stored. Depending on what the hospital has configured, it uses one or another.

- **DeepSeek** — The default medication (economical and effective)
- **OpenAI** — Alternative (GPT-4o-mini, GPT-4o, etc.)
- **Ollama** — For running models locally (Llama 3, Mistral, Phi-3, etc.)
- **Anthropic** — Claude models (Opus, Sonnet, Haiku)

All medications follow the same interface (`LLMProvider`), so switching them is as simple as changing a variable in `.env`. The **factory** (`app/llm/factory.py`) is the "pharmacist" that selects the correct medication based on `LLM_PROVIDER`.

**Key files:**
- `app/llm/base.py` — The "prescription" (interface) that all medications must follow
- `app/llm/deepseek.py` — Implementation for DeepSeek
- `app/llm/openai_compat.py` — Implementation for OpenAI
- `app/llm/ollama.py` — Dedicated provider for Ollama (local models)
- `app/llm/anthropic.py` — Implementation for Anthropic/Claude (official SDK)
- `app/llm/factory.py` — The "pharmacist" that selects the correct medication

**Provider-specific features:**

| Provider | JSON Mode | API Key Required | SDK |
|----------|-----------|------------------|-----|
| Ollama | Auto-detected per model | No | OpenAI-compatible |
| DeepSeek | ✅ Yes | Yes | OpenAI-compatible |
| OpenAI | ✅ Yes | Yes | OpenAI SDK |
| Anthropic | ✅ Yes | Yes | Anthropic SDK |

**To explore more:** Look at `factory.py` to understand how the provider is selected based on `LLM_PROVIDER`.

---

### 📋 Medical Records — Database Layer (`app/database.py` + `app/models.py`)

**What does it do?** Stores all patient (client) information and their visit history.

- **Tenant** — Each client: name, plan, active status
- **ApiKey** — Each client's credentials (stored as hash for security)
- **UsageRecord** — Record of each diagnosis: when, which endpoint, how many tokens used

**Key files:**
- `app/database.py` — Database connection, with automatic PostgreSQL → SQLite fallback
- `app/models.py` — Classes representing the tables

**To explore more:** If you have PostgreSQL, connect and explore the `tenants`, `api_keys`, `usage_records` tables.

---

### 📚 Medical Library — Knowledge Base (`AEGIS_PATTERNS.md`)

**What does it do?** Stores knowledge from past incidents. These are 20 documented cases of real incidents at companies like AWS, Cloudflare, Google, GitHub, Netflix, and Azure.

Each case includes:
- **Symptoms** — What warning signs are visible?
- **Diagnosis** — What actually happened?
- **Remediation Script** — How was it fixed?

**Key file:**
- `AEGIS_PATTERNS.md` — 1142 lines, 20 patterns

**To explore more:** Open the file and read 2 or 3 patterns. You'll notice they all follow the same structure. That consistency is what allows the LLM to understand and use them.

---

### 🧰 Configuration — Settings Layer (`app/config.py`)

**What does it do?** Centralizes all system configuration in one place. It's like the hospital's control panel.

Here you define:
- File paths (where `AEGIS_PATTERNS.md`, `tickets_dataset.csv` are)
- Models (which embedding model, which LLM to use)
- Connections (PostgreSQL URL, ChromaDB host)
- Limits (how many incidents per month on Shield plan)
- Operation flags (debug, authentication required)

**Key file:**
- `app/config.py` — `Settings` class with pydantic-settings

**To explore more:** Review the variables in `app/config.py` and compare them with `.env.example`. You'll see how environment variables override default values.

---

## 3. 🔄 The Journey of an Alert (Complete Flow)

Let's follow two alerts from entry to diagnosis. Like a "day in the life of a ticket".

---

### Scenario 1: "I can't log in" (L1/L2)

**Step 1 — The patient arrives**

Someone sends an alert to reception:

```bash
curl -X POST http://localhost:8000/v1/alert \
  -H "Content-Type: application/json" \
  -d '{
    "source": "manual",
    "severity": "low",
    "title": "I can't log in",
    "description": "I get error 403 when trying to access the application"
  }'
```

**Step 2 — Identification**

Reception (endpoint `POST /v1/alert`) asks for ID. It reads the `X-API-Key` header. If there's none (development mode), it uses the "default" tenant. If there is one, it looks up the key in the database and gets the tenant.

**Step 3 — Insurance verification**

The system checks the tenant's plan. If it's "shield", it counts how many incidents they've used this month. If they've reached the limit (50), it responds with HTTP 429: "You've used all your queries this month, upgrade your plan."

**Step 4 — Triage: Is it serious?**

The `route_severity()` function analyzes:
- `severity = "low"` → Not critical
- The description doesn't contain words like "outage", "down", "500" → Not critical

Result: **L1/L2** → Goes to the classifier.

**Step 5 — L1/L2 Diagnosis**

The classifier (`classifier_service.classify()`) does the following:

1. **Converts text to embedding:** Takes "I can't log in, I get error 403" and converts it to a vector of 384 numbers representing its meaning.

2. **Searches ChromaDB:** Searches for the 5 most similar historical tickets by meaning. Finds tickets like:
   - "User cannot log in, error 403 forbidden" → ACCESS (distance: 0.15)
   - "Need access to Salesforce, account not provisioned" → ACCESS (distance: 0.32)
   - "Password reset requested" → ACCESS (distance: 0.41)

3. **Weighted voting:** Each ticket "votes" for its category, but closer ones have more weight. ACCESS wins with 88.4% confidence.

4. **Checks threshold:** 88.4% > 45% → High confidence, no keyword fallback needed.

5. **Prepares response:** Takes the resolution from the closest ticket: "Added user to correct AD group, cleared cache".

**Step 6 — Visit registration**

A `UsageRecord` is saved in the database: "Tenant X used endpoint /v1/alert on 20/06/2026".

**Step 7 — Response**

```json
{
  "timestamp": "2026-06-20T14:30:00.123456",
  "source": "manual",
  "severity": "low",
  "level": "L1/L2",
  "pattern_id": "L1-001",
  "pattern_name": "Access / Authentication Issue",
  "diagnosis": "User authentication or authorization failure detected. (classified via vector_weighted, confidence 88.4%)",
  "script": "Suggested resolution: Added user to correct AD group, cleared cache\n\n---\n\nStandard procedure:\n1. Verify user account is active\n2. Reset password if needed\n3. Check group/role assignments\n4. Clear browser cache and cookies",
  "confidence": "HIGH",
  "category_scores": {
    "ACCESS": 88.4,
    "HOWTO": 5.2,
    "SECURITY": 3.1
  }
}
```

**Total time: ~2 seconds.** The ticket is classified and has a suggested resolution.

---

### Scenario 2: "The database server went down" (L3/L4)

**Step 1 — The patient arrives**

PagerDuty sends a critical alert:

```bash
curl -X POST http://localhost:8000/v1/alert \
  -H "Content-Type: application/json" \
  -d '{
    "source": "pagerduty",
    "severity": "critical",
    "title": "Database connection timeout",
    "description": "Application returning 500 errors. Connection pool exhausted. Replication lag at 300 seconds."
  }'
```

**Steps 2 and 3 — Identification and insurance verification**

Same as the previous scenario.

**Step 4 — Triage: Is it serious?**

`route_severity()` detects:
- `severity = "critical"` → Red alert!
- The description contains "timeout", "500" → Confirmed

Result: **L3/L4** → Goes to the orchestrator.

**Step 5 — L3/L4 Diagnosis**

The orchestrator (`orchestrator_service.diagnose()`) does the following:

1. **Retrieves relevant patterns:** Uses RAG to find the top-3 most relevant pattern chunks from ChromaDB based on semantic similarity to the alert.

2. **Constructs the prompt:** Prepares a message for the LLM with:
   - **System prompt:** "You are Aegis, an autonomous triage agent. Compare the alert symptoms against the patterns. Respond ONLY with JSON."
   - **User prompt:** The user's alert + the 3 most relevant patterns.

3. **LLM analyzes:** DeepSeek receives the prompt, compares the alert symptoms ("500 errors", "connection pool exhausted", "replication lag 300s") against each pattern, and determines the most similar is **AEGIS-005 (Database Failover)**.

4. **Generates response:** DeepSeek returns a JSON with:
   - `id`: "AEGIS-005"
   - `name`: "Database Failover"
   - `diagnosis`: Explanation adapted to the specific alert
   - `script`: Bash remediation script from the pattern

**Step 6 — Visit registration**

A `UsageRecord` is saved in the database.

**Step 7 — Response**

```json
{
  "timestamp": "2026-06-20T14:31:00.654321",
  "source": "pagerduty",
  "severity": "critical",
  "level": "L3/L4",
  "pattern_id": "AEGIS-005",
  "pattern_name": "Database Failover",
  "diagnosis": "The primary database appears to have failed or become saturated, triggering an automatic failover. Connection pool exhaustion and replication lag of 300 seconds indicate the new primary is struggling to catch up. This matches the Database Failover pattern (AEGIS-005) from AWS RDS March 2023.",
  "script": "#!/bin/bash\n# AEGIS-005: Remediation for database failover\n\n# 1. Verify failover status\naws rds describe-db-instances ...\n\n# 2. Reconnect application (restart connection pools)\nkubectl rollout restart deployment/api\n\n# 3. Verify replica lag after failover\naws rds describe-db-instances ...\n\n# 4. Warm up cache\npsql -h new-primary -d my-db -c \"SELECT pg_prewarm('large_table');\"\n\n# 5. Alert DBA team\necho \"Failover detected on database.\" | mail -s \"DB Failover Alert\" dba@company.com",
  "confidence": null
}
```

**Total time: ~10-15 seconds.** The critical incident has a diagnosis and remediation script ready.

---

## 4. 📂 Key Files Explained

Each file is presented as a "character" of the project. Here we explain **what it does**, **how it's used**, and **what it contains**.

---

### 4.1 `classifier.py` — The Classifier

```
🎭 Personality: The receptionist expert in classifying tickets
```

**What does it do?**
Takes a ticket description and compares it against 77 historical tickets to determine the category and suggest a solution. Uses a hybrid system: first searches by meaning (vectors) and if not sure, uses keywords.

**How is it used?**
- **As a library:** Other files import `classify_ticket()` to classify tickets.
- **As a standalone program:** `python classifier.py` opens an interactive menu:
  - Option 1: Classify a new ticket
  - Option 2: Add a resolved ticket (to teach it)
  - Option 3: View database statistics
  - Option 4: Exit

**What does it contain?**
- **8 categories** with keywords: ACCESS, DATABASE, LICENSE, API, PERFORMANCE, NETWORK, SECURITY, HOWTO
- **Embedding model:** `all-MiniLM-L6-v2` (converts text to 384-number vectors)
- **ChromaDB:** Vector database with 77 historical tickets
- **Weighted voting system:** Most similar tickets have more weight in the decision
- **Keyword fallback:** Plan B if vector search doesn't give good confidence

**🔍 File:** `classifier.py` (529 lines)

---

### 4.2 `orchestrator.py` — The Diagnostician

```
🎭 Personality: The specialist doctor for critical incidents
```

**What does it do?**
Takes a critical alert description, compares it against 20 real incident patterns, and generates a diagnosis + remediation script using an LLM (DeepSeek).

**How is it used?**
- **As a library:** Other files import `diagnose()` to diagnose incidents.
- **As a standalone program:** `python orchestrator.py` opens an interactive loop where you write the alert and it diagnoses it.

**What does it contain?**
- **Knowledge base loader:** Reads `AEGIS_PATTERNS.md` completely
- **DeepSeek client:** Connects to the DeepSeek API (OpenAI-compatible)
- **Prompt system:** Clear instructions for the LLM to return valid JSON
- **Response parser:** Extracts `id`, `name`, `diagnosis`, and `script` from JSON
- **Error handling:** If the API fails or JSON is invalid, returns UNKNOWN

**🔍 File:** `orchestrator.py` (176 lines)

---

### 4.3 `slack_bot.py` — The Slack Bot

```
🎭 Personality: The assistant that lives in Slack
```

**What does it do?**
Listens to messages in Slack and responds with AEGIS diagnoses. Can be @mentioned in channels, receive direct messages, or use the `/aegis` command.

**How is it used?**
```bash
python slack_bot.py
```
Then in Slack:
- `@AEGIS I can't log in` → Responds with diagnosis
- Direct message to the bot: "The server is giving error 500" → Diagnoses
- `/aegis diagnose Database went down` → Diagnoses

**What does it contain?**
- **Socket Mode connection:** Connects to Slack without needing a public server
- **Dual-mode:** Uses SaaS services (`app/services/`) if available, or legacy modules if not
- **Severity routing:** Decides if the query is L1/L2 or L3/L4 based on keywords
- **Response formatting:** Uses emojis and Slack formatting for clear responses

**🔍 File:** `slack_bot.py` (262 lines)

---

### 4.4 `AEGIS_PATTERNS.md` — The Pattern Library

```
🎭 Personality: The book of clinical cases
```

**What does it contain?**
20 real incident patterns that occurred at companies like AWS, Cloudflare, Google, GitHub, Netflix, and Azure. Each pattern documents:

- **Symptoms:** What warning signs are visible? (presented in a table)
- **Diagnosis:** What actually happened? (detailed explanation)
- **Remediation Script:** How was it fixed? (bash code ready to execute)

**How is it used in the system?**
The orchestrator reads it and passes it to the LLM as context. With RAG chunking, only the top-3 most relevant patterns are retrieved based on semantic similarity.

**Example of a pattern (AEGIS-001):**
- **Source:** AWS Kinesis Event - November 2020
- **Symptoms:** API 503, latency increases, throttling, Kinesis exceptions
- **Diagnosis:** Cascade dependency saturation (domino effect from non-resilient dependency)
- **Script:** Bash that identifies the slow dependency, activates circuit breaker, scales, and restarts

**🔍 File:** `AEGIS_PATTERNS.md` (1142 lines, 20 patterns)

---

### 4.5 `integration_module.py` — The Universal Webhook (Legacy)

```
🎭 Personality: The previous version of the receptionist
```

**What does it do?**
It's the standalone version of the webhook that received alerts before the SaaS (`app/`) existed. It's still functional and useful as a reference.

**Endpoints:**
- `POST /alert` — Receives alerts and diagnoses them (same as `/v1/alert` in SaaS)
- `GET /health` — Checks system status
- `POST /pagerduty` — Webhook for PagerDuty (parses v2 and v3 payloads)
- `GET /stats` — Classifier statistics

**Why does it exist if the SaaS is already there?**
The integration module was the first version. When multi-tenancy, billing, and authentication were added, the `app/` folder was created. But `integration_module.py` is still useful for:
- Understanding the project's evolution
- Having a simple reference point
- Running quick tests without the full SaaS infrastructure

**🔍 File:** `integration_module.py` (520 lines)

---

### 4.6 `app/rag/knowledge_base.py` — The RAG Knowledge Base

```
🎭 Personality: The librarian who finds the right book instantly
```

**What does it do?**
Implements Retrieval-Augmented Generation (RAG) for the L3/L4 orchestrator. Instead of sending all 20 patterns to the LLM on every request, it chunks each pattern individually, embeds them in ChromaDB, and retrieves only the most relevant ones.

**How does it work?**
1. **Chunking:** Splits `AEGIS_PATTERNS.md` into 20 chunks (one per pattern) using regex on `## Pattern AEGIS-XXX` headers
2. **Embedding:** Converts each chunk to a vector using `all-MiniLM-L6-v2`
3. **Storage:** Stores chunks in a dedicated ChromaDB collection (`patterns_chunks`)
4. **Retrieval:** On diagnosis, embeds the alert text and finds the top-3 most similar chunks by cosine distance
5. **Generation:** Sends only those 3 chunks to the LLM as context

**Benefits:**
- Reduces token usage by ~80%
- Improves diagnosis speed
- Keeps the LLM focused on the most relevant patterns

**Initialization:**
```bash
python scripts/init_knowledge_base.py
```

**🔍 File:** `app/rag/knowledge_base.py` (261 lines)

---

### 4.7 `app/services/rate_limit_service.py` — The Rate Limiter

```
🎭 Personality: The bouncer at the club door
```

**What does it do?**
Controls how many requests each tenant can make per hour. Uses an in-memory sliding window algorithm with thread-safe counters.

**Rate limits by plan:**
| Plan | Requests per hour |
|------|-------------------|
| Shield | 10 |
| Guard | 50 |
| Fortress | 200 |

**Response headers:**
- `X-RateLimit-Limit` — Maximum requests per hour
- `X-RateLimit-Remaining` — Requests remaining in current window
- `X-RateLimit-Reset` — Unix timestamp when the window resets
- `Retry-After` — Seconds to wait (only on 429 responses)

**🔍 File:** `app/services/rate_limit_service.py` (142 lines)

---

### 4.8 `app/services/orchestrator_service.py` — The Orchestrator (SaaS)

```
🎭 Personality: The specialist doctor, now with 24/7 backup
```

**What does it do?**
The SaaS version of the orchestrator. Diagnoses L3/L4 incidents using RAG + LLM, with graceful degradation when the LLM is unavailable.

**Key features:**
- **RAG pattern retrieval:** Uses `knowledge_base.py` to find relevant patterns
- **Graceful degradation:** If no API key is configured, returns a clear 503 response
- **Multi-tenant:** Works with tenant-specific configurations
- **Health reporting:** Exposes `is_degraded` and `get_provider_name()` for the health endpoint

**Degraded mode behavior:**
| Component | Normal | Degraded |
|-----------|--------|----------|
| L1/L2 Classifier | Works | Works (no LLM needed) |
| L3/L4 Orchestrator | LLM diagnosis | 503 + setup instructions |
| Health endpoint | `llm_available: true` | `llm_available: false` |

**🔍 File:** `app/services/orchestrator_service.py`

---

## 5. 🛠️ Useful Commands (Your Toolbox)

Commands grouped by mission, so you can quickly find what you need.

---

### 🚀 To start the project

```bash
# 1. Clone (if you haven't already)
git clone https://github.com/laral5173/aegis-itsm-agent.git
cd aegis-itsm-agent

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API key (create .env file)
# echo DEEPSEEK_API_KEY=your-key >> .env

# 5. Initialize RAG knowledge base (optional, for improved L3/L4)
python scripts/init_knowledge_base.py

# 6. Run!
python app/main.py

# 7. Open interactive documentation:
#    http://localhost:8000/docs
```

---

### 🧪 To test individual components

```bash
# L1/L2 Classifier (interactive menu)
python classifier.py

# L3/L4 Orchestrator (describe an alert)
python orchestrator.py

# Slack Bot (requires tokens in .env)
python slack_bot.py
```

---

### 📊 To evaluate the model

```bash
# Accuracy tests (22 test tickets)
python test_classifier.py

# 5-fold cross-validation
python cross_validation.py
```

---

### 🐳 To use Docker

```bash
# One-command install (Linux/macOS) — checks prerequisites, creates .env, starts services
curl -fsSL https://raw.githubusercontent.com/laral5173/aegis-itsm-agent/main/install.sh | bash

# One-command install (Windows PowerShell)
.\install.ps1

# Or manually with Docker Compose:
# Core services only (app + PostgreSQL + ChromaDB)
docker compose --env-file .env up -d

# With Ollama (local LLM)
docker compose --profile ollama --env-file .env up -d

# With HTTPS (requires domain)
docker compose --profile caddy --env-file .env up -d

# Everything
docker compose --profile ollama --profile caddy --env-file .env up -d
```

---

### 📬 To test the API

```bash
# Simple ticket (L1/L2) — Windows CMD
curl -X POST http://localhost:8000/v1/alert ^
  -H "Content-Type: application/json" ^
  -d "{\"source\":\"manual\",\"severity\":\"low\",\"title\":\"I can't log in\",\"description\":\"Error 403 when logging in\"}"

# Simple ticket (L1/L2) — PowerShell
curl -X POST http://localhost:8000/v1/alert `
  -H "Content-Type: application/json" `
  -d '{"source":"manual","severity":"low","title":"I can'\''t log in","description":"Error 403 when logging in"}'

# Critical incident (L3/L4)
curl -X POST http://localhost:8000/v1/alert ^
  -H "Content-Type: application/json" ^
  -d "{\"source\":\"pagerduty\",\"severity\":\"critical\",\"title\":\"DB down\",\"description\":\"Database connection timeout\"}"

# Check system status
curl http://localhost:8000/v1/health

# View usage statistics
curl http://localhost:8000/v1/stats
```

---

### 🔧 For administration

```bash
# Create a new tenant (client)
curl -X POST http://localhost:8000/v1/admin/tenants ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"My Company\",\"slug\":\"my-company\",\"plan\":\"shield\"}"

# List all tenants
curl http://localhost:8000/v1/admin/tenants

# View usage for a specific tenant
curl http://localhost:8000/v1/admin/usage/{tenant_id}
```

---

## 6. ❓ Frequently Asked Questions

---

### 1. "I don't have a DeepSeek API key, can I still try the project?"

**Yes.** The L1/L2 classifier works completely without an API key. Only the L3/L4 orchestrator (which uses the LLM) needs it. You can try:
- `python classifier.py` — Interactive classifier menu
- `POST /v1/alert` with severity "low" or "medium" — Will use the classifier
- `GET /v1/health` — You'll see the system responds

If you try an L3/L4 diagnosis without an API key, the system returns HTTP 503 with a clear message explaining how to configure it.

---

### 2. "Can I use ChatGPT instead of DeepSeek?"

**Yes.** In your `.env` file, change:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini
```
You can also use Ollama (local models):
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3
```
The system uses a common interface (OpenAI-compatible), so switching providers is just a configuration change.

---

### 3. "How do I teach the classifier a new ticket?"

Two ways:

**Option A — From the interactive menu:**
```bash
python classifier.py
# Option 2: "Add a resolved ticket"
# It will ask for: description, resolution, and category
```

**Option B — Editing the CSV:**
Open `tickets_dataset.csv` and add a new row:
```csv
id,description,resolution,category
T078,User cannot access VPN from home,Added user to VPN group and updated firewall rules,ACCESS
```
The classifier loads the CSV automatically on startup.

---

### 4. "What does it mean when the response is UNKNOWN?"

It means the classifier didn't find any historical ticket similar enough. The confidence didn't reach the 45% threshold. This can happen for two reasons:

1. **The ticket is a new type** that doesn't exist in the 77 historical tickets.
2. **The ticket is poorly written** or uses very different vocabulary.

**What to do?** Review the ticket manually and, once resolved, add it to the database so the classifier learns.

---

### 5. "Do I need PostgreSQL?"

**No.** The system has automatic fallback to SQLite. If you don't have PostgreSQL installed:
1. The system detects it on startup
2. Creates an `aegis_dev.db` file in the project root
3. Everything works the same

For local development, SQLite is perfect. For production, PostgreSQL is recommended.

---

### 6. "How do I create a new client (tenant)?"

Use the administration endpoint:

```bash
curl -X POST http://localhost:8000/v1/admin/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "slug": "acme-corp", "plan": "shield"}'
```

The response includes the new tenant's API key. **Save it**, it's only shown once.

Available plans:
- **shield:** Up to 50 incidents/month (10 requests/hour)
- **guard:** Unlimited incidents (50 requests/hour)
- **fortress:** Unlimited incidents + enterprise features (200 requests/hour)

---

### 7. "How do I add a new incident pattern?"

Edit `AEGIS_PATTERNS.md` and add a new block at the end following the existing format:

```markdown
## Pattern AEGIS-021
**Name:** Your pattern name
**Source:** Incident source

### Symptoms (automatically detectable)

| Symptom | Where to see | Typical format |
|---------|--------------|----------------|
| Symptom 1 | Where to see it | Typical format |

### Diagnosis (root cause)

Explanation of what actually happened.

### Remediation Script

```bash
#!/bin/bash
# Remediation commands
```
```

The orchestrator will load it automatically on the next diagnosis. If using RAG mode, re-run `python scripts/init_knowledge_base.py` to re-chunk the knowledge base.

---

### 8. "The Slack Bot doesn't work, what should I check?"

Follow this checklist:

1. **Are the tokens in `.env`?**
   ```
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_APP_TOKEN=xapp-...
   ```

2. **Does the Slack app have Socket Mode enabled?**
   Go to your app at [api.slack.com/apps](https://api.slack.com/apps) → Socket Mode → Enabled

3. **Does it have the correct scopes?**
   - `chat:write` — To send messages
   - `commands` — For the `/aegis` command
   - `app_mentions:read` — To detect @mentions

4. **Is the Slash Command configured?**
   `/aegis` with empty Request URL (Socket Mode doesn't need URL)

5. **Is the bot in the channel?**
   Invite the bot to the channel where you want to use it.

---

### 9. "Where are the ChromaDB embeddings stored?"

In the `tickets_db/` folder at the project root. This folder is created automatically the first time you run the classifier.

If you want to start from scratch (e.g., with a new dataset), just delete the `tickets_db/` folder and the classifier will recreate it.

The RAG pattern chunks are stored in `patterns_db/` (created by `scripts/init_knowledge_base.py`).

---

### 10. "How do I contribute to the project?"

1. Check [`CONTRIBUTING.md`](./CONTRIBUTING.md) for contribution guidelines.
2. The project follows a [Code of Conduct](./CODE_OF_CONDUCT.md).
3. Contributions can be:
   - **New patterns** in `AEGIS_PATTERNS.md`
   - **Classifier improvements** (more tickets, better accuracy)
   - **New integrations** (Jira, ServiceNow, Datadog)
   - **Bug fixes** and code improvements
   - **Documentation** like this guide

---

### 11. "What do the confidence levels HIGH / MEDIUM / LOW mean?"

These are labels to make it easier to interpret the classifier's confidence:

| Label | Range | Meaning |
|-------|-------|---------|
| **HIGH** | ≥ 75% | The classifier is very confident. The category is reliable. |
| **MEDIUM** | 50% – 74% | Moderate confidence. Review manually before acting. |
| **LOW** | < 50% | Low confidence. Likely requires human review. |

---

### 12. "How do I run tests to verify everything works?"

```bash
# Classifier tests (22 test tickets)
python test_classifier.py

# Cross-validation (5-fold, measures real accuracy)
python cross_validation.py

# Verify the server responds
curl http://localhost:8000/v1/health

# Verify imports work
python test_integration.py
```

---

### 13. "What is the Script Executor and how is it used?"

The **Script Executor** is a planned feature (Phase 4 of the roadmap). Currently, the orchestrator generates remediation scripts, but **does not execute them automatically**. Instead:

1. The orchestrator returns the script in the JSON response
2. A human reviews the script
3. If safe, they execute it manually

In the future (Phase 4), scripts will be executed in an isolated sandbox with human approval.

---

### 14. "Can I run the classifier without starting the server?"

**Yes.** The classifier and orchestrator can be run as standalone programs:

```bash
# Classifier with interactive menu
python classifier.py

# Orchestrator with interactive loop
python orchestrator.py
```

This is useful for:
- Testing the classifier with custom tickets
- Adding tickets to the database
- Viewing statistics without needing the web server

---

### 15. "What if I see an error 'DEEPSEEK_API_KEY not configured'?"

It means the L3/L4 orchestrator can't find the DeepSeek API key. Solution:

1. Create a `.env` file in the project root (you can copy `.env.example`)
2. Add: `DEEPSEEK_API_KEY=your-api-key`
3. Get a free key at [platform.deepseek.com](https://platform.deepseek.com)

If you only want to test the L1/L2 classifier, this error won't affect you. The system will gracefully degrade and return a clear 503 message for L3/L4 requests.

---

### 16. "What is rate limiting and how does it affect me?"

Rate limiting controls how many requests your tenant can make per hour. It's like a subway turnstile that only lets a certain number of people through per minute.

| Plan | Requests per hour |
|------|-------------------|
| Shield | 10 |
| Guard | 50 |
| Fortress | 200 |

If you exceed your limit, you'll receive HTTP 429 with headers telling you when to retry. The limit resets automatically after one hour.

---

### 17. "What happens if the LLM is not available?"

AEGIS handles this gracefully:
- **L1/L2 classification** continues working normally (no LLM needed)
- **L3/L4 diagnosis** returns HTTP 503 with a clear message explaining how to configure the API key
- The **health endpoint** shows `llm_available: false`
- The system logs a warning at startup

This allows you to evaluate the system, test L1/L2 classification, and explore the API without needing an LLM API key.

---

> **Found something to improve in this guide?**  
> Contributions are welcome. Check [`CONTRIBUTING.md`](./CONTRIBUTING.md) to learn how to help.
