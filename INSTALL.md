# ITSMLab — On-Premise Installation Guide

> **Version:** 1.0.0  
> **Last updated:** July 2026  
> **Supported operating systems:** Linux (recommended), Windows, macOS

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Architecture](#2-architecture)
3. [Quick Installation (1 command)](#3-quick-installation-1-command)
4. [Manual Step-by-Step Installation](#4-manual-step-by-step-installation)
5. [AI Model Configuration](#5-ai-model-configuration)
   - [Option A: Local Model with Ollama](#option-a-local-model-with-ollama)
   - [Option B: External API (DeepSeek / OpenAI)](#option-b-external-api-deepseek--openai)
6. [Installation Verification](#6-installation-verification)
7. [Troubleshooting](#7-troubleshooting)
8. [Maintenance](#8-maintenance)
9. [Configuration Checklist](#9-configuration-checklist)

---

## 1. System Requirements

### Minimum (external API mode)

| Resource | Requirement |
|---------|-----------|
| CPU | 2 cores |
| RAM | 2 GB |
| Disk | 10 GB free |
| Docker | 24.0+ |
| Docker Compose | 2.20+ |
| OS | Linux (kernel 5.x+), Windows 10/11, macOS 12+ |

### Recommended (local mode with Ollama)

| Resource | Requirement |
|---------|-----------|
| CPU | 4 cores |
| RAM | 8 GB (16 GB for models >7B) |
| Disk | 20 GB free (for models) |
| GPU | NVIDIA with 4GB+ VRAM (optional, improves speed) |
| Docker | 24.0+ with NVIDIA Container Toolkit (if using GPU) |
| Docker Compose | 2.20+ |

### Required Software

- **Docker** and **Docker Compose** (included in Docker Desktop)
  - [Install Docker](https://docs.docker.com/get-docker/)
- **curl** (to verify the installation)
- **Git** (optional, to clone the repository)

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Client (Browser/API)                  │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTPS (optional with Caddy)
                      ▼
┌─────────────────────────────────────────────────────────┐
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │
│  │  Caddy   │───▶│  ITSMLab │───▶│   PostgreSQL     │  │
│  │ (proxy)  │    │   App    │    │   (data)         │  │
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
│                       └──────────────────┘             │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Description | Port |
|------------|-------------|--------|
| **ITSMLab App** | Main REST API (FastAPI) | `8000` |
| **PostgreSQL** | Relational database | `5432` |
| **ChromaDB** | Vector store for RAG | `8001` |
| **Ollama** (optional) | Local LLM service | `11434` |
| **Caddy** (optional) | Reverse proxy with automatic HTTPS | `80`, `443` |

---

## 3. Quick Installation (1 command)

### Linux / macOS

```bash
# Option 1: Local model with Ollama (recommended for testing)
curl -fsSL https://raw.githubusercontent.com/itsmlab/itsm-agent/main/install.sh | bash

# Option 2: With DeepSeek API
curl -fsSL https://raw.githubusercontent.com/itsmlab/itsm-agent/main/install.sh | \
  DEEPSEEK_API_KEY=sk-xxx LLM_PROVIDER=deepseek bash

# Option 3: With OpenAI API
curl -fsSL https://raw.githubusercontent.com/itsmlab/itsm-agent/main/install.sh | \
  OPENAI_API_KEY=sk-xxx LLM_PROVIDER=openai bash
```

### Windows (PowerShell)

```powershell
# Option 1: Local model with Ollama
.\install.ps1

# Option 2: With DeepSeek API
$env:LLM_PROVIDER="deepseek"; $env:DEEPSEEK_API_KEY="sk-xxx"; .\install.ps1

# Option 3: With OpenAI API
$env:LLM_PROVIDER="openai"; $env:OPENAI_API_KEY="sk-xxx"; .\install.ps1
```

> **Note:** The automatic installer verifies prerequisites, creates the `.env` file, downloads the Docker images, starts the containers, and initializes the RAG knowledge base.

---

## 4. Manual Step-by-Step Installation

### Step 1: Clone the repository

```bash
git clone https://github.com/itsmlab/itsm-agent.git
cd itsm-agent
```

### Step 2: Configure environment variables

Create a `.env` file in the project root:

```bash
# LLM provider: ollama | deepseek | openai
LLM_PROVIDER=ollama

# If using DeepSeek:
# DEEPSEEK_API_KEY=sk-your-api-key

# If using OpenAI:
# OPENAI_API_KEY=sk-your-api-key

# If using Ollama (optional):
# OLLAMA_BASE_URL=http://ollama:11434
# OLLAMA_MODEL=llama3

# Database (default values for single-node)
DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/itsmlab

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_USE_SERVER=true

# Security (false for initial testing)
AUTH_REQUIRED=false

# Logging
LOG_LEVEL=INFO
```

### Step 3: Start the services

```bash
# Core (app + postgres + chromadb)
docker compose --env-file .env up --build -d

# With local Ollama
docker compose --profile ollama --env-file .env up --build -d

# With HTTPS (requires configured domain)
docker compose --profile caddy --env-file .env up --build -d

# Everything complete
docker compose --profile ollama --profile caddy --env-file .env up --build -d
```

### Step 4: Initialize the knowledge base

```bash
docker compose exec app python scripts/init_knowledge_base.py
```

### Step 5: Verify

```bash
curl http://localhost:8000/v1/health
```

---

## 5. AI Model Configuration

### Option A: Local Model with Ollama

**What is Ollama?**  
Ollama is a local LLM engine that allows running models like Llama 3, Mistral, Phi-3, etc., directly on the client's infrastructure. It does not require internet connection for inference.

**Additional requirements:**

- 8 GB RAM minimum (16 GB recommended for 7B parameter models)
- NVIDIA GPU with 4GB+ VRAM (optional, but highly recommended)
- 10 GB disk space for the base model

**Recommended models:**

| Model | Size | Minimum RAM | Quality | Recommended use |
|--------|--------|------------|---------|-----------------|
| `llama3` (8B) | 4.7 GB | 8 GB | High | Production |
| `llama3:70b` | 40 GB | 48 GB | Very high | Production (GPU required) |
| `mistral` (7B) | 4.1 GB | 8 GB | High | Production |
| `phi3:mini` (3.8B) | 2.3 GB | 4 GB | Medium | Testing / limited resources |
| `qwen2:0.5b` | 352 MB | 2 GB | Low | Minimal testing |

**Ollama installation (if not using the Docker container):**

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows
# Download from https://ollama.com/download

# Download a model
ollama pull llama3

# Start server
ollama serve
```

**ITSMLab configuration:**

```bash
# .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434   # or http://ollama:11434 if using Docker
OLLAMA_MODEL=llama3
```

**Advantages:**
- No internet dependency
- No API usage costs
- Data 100% on client infrastructure
- Predictable latency (no network)

**Disadvantages:**
- Requires more powerful hardware
- Lower response quality than GPT-4/DeepSeek
- Slow first inference (model loading into memory)

---

### Option B: External API (DeepSeek / OpenAI)

**What is it?**  
The client uses their own API key from an external LLM provider. ITSMLab connects to the provider's API for inference.

**Requirements:**

- Valid API key from the chosen provider
- Internet connection from the ITSMLab server
- No additional hardware requirements

**Supported providers:**

| Provider | Environment variable | Estimated cost |
|-----------|-------------------|----------------|
| DeepSeek | `DEEPSEEK_API_KEY` | ~$0.14/1M tokens (input) |
| OpenAI (GPT-4o mini) | `OPENAI_API_KEY` | ~$0.15/1M tokens (input) |
| OpenAI (GPT-4o) | `OPENAI_API_KEY` | ~$2.50/1M tokens (input) |

**Configuration:**

```bash
# For DeepSeek
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-api-key-here

# For OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
```

**Advantages:**
- No specialized hardware requirements
- Better response quality (especially GPT-4o)
- No local resource consumption for inference

**Disadvantages:**
- Internet connection dependency
- Usage costs (can accumulate)
- Data sent to external servers
- Variable network latency

---

## 6. Installation Verification

### Health Check

```bash
curl http://localhost:8000/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "llm_provider": "ollama",
  "database": "connected",
  "chromadb": "connected"
}
```

### Test diagnosis

```bash
curl -X POST http://localhost:8000/v1/diagnose \
  -H "Content-Type: application/json" \
  -d '{"alert": "CPU usage at 95% on server web-01"}'
```

### Interactive documentation

Open in your browser: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 7. Troubleshooting

### Problem: The Ollama container does not start

```bash
# Check logs
docker compose logs ollama

# Check if GPU is available
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# Without GPU, it works on CPU (slower)
# Edit docker-compose.yml and remove the 'deploy.resources' section
```

### Problem: "LLM provider not configured"

```bash
# Verify that .env has the correct variables
cat .env | grep -E "LLM_PROVIDER|API_KEY"

# If using Ollama, make sure the service is running
curl http://localhost:11434/api/tags
```

### Problem: Knowledge base not initialized

```bash
# Initialize manually
docker compose exec app python scripts/init_knowledge_base.py

# Check status
docker compose exec app python -c "
from app.rag.knowledge_base import get_knowledge_base_stats
print(get_knowledge_base_stats())
"
```

### Problem: PostgreSQL connection error

```bash
# Verify that PostgreSQL is ready
docker compose logs postgres

# Check connectivity
docker compose exec app python -c "
from app.database import engine
engine.connect()
print('Database connected')
"
```

### Problem: Port 8000 already in use

```bash
# Change the port in docker-compose.yml
# Change "8000:8000" to "8080:8000"
# Then access at http://localhost:8080
```

---

## 8. Maintenance

### Update ITSMLab

```bash
# Download latest version
git pull

# Rebuild and restart
docker compose up --build -d

# Run database migrations (if any)
docker compose exec app alembic upgrade head
```

### View logs

```bash
# All services
docker compose logs -f

# App only
docker compose logs -f app

# Ollama only
docker compose logs -f ollama
```

### Backups

```bash
# Backup PostgreSQL database
docker compose exec postgres pg_dump -U postgres itsmlab > backup_$(date +%Y%m%d).sql

# Backup ChromaDB
tar -czf chromadb_backup_$(date +%Y%m%d).tar.gz chromadb_data/
```

### Stop services

```bash
# Stop everything
docker compose down

# Stop and remove volumes (caution: deletes data)
docker compose down -v
```

---

## 9. Configuration Checklist

### Pre-installation

- [ ] Verify that Docker 24.0+ is installed
- [ ] Verify that Docker Compose 2.20+ is installed
- [ ] Verify available RAM (minimum 2 GB, recommended 8 GB)
- [ ] Verify disk space (minimum 10 GB)
- [ ] Verify internet connectivity (if using external API)
- [ ] Verify GPU availability (optional, for Ollama)
- [ ] Decide LLM mode: local (Ollama) or external API
- [ ] Obtain API key (if applicable)

### Installation

- [ ] Clone repository or download files
- [ ] Create `.env` file with configuration
- [ ] Run `docker compose up -d`
- [ ] Verify that all containers are "running"
- [ ] Run `init_knowledge_base.py`
- [ ] Verify health endpoint: `curl localhost:8000/v1/health`
- [ ] Test diagnosis: `curl -X POST localhost:8000/v1/diagnose`

### Post-installation

- [ ] Configure HTTPS (Caddy or external proxy)
- [ ] Configure authentication (`AUTH_REQUIRED=true`)
- [ ] Configure automatic backups
- [ ] Configure monitoring (logs, metrics)
- [ ] Test with real alerts
- [ ] Document client-specific configuration

---

> **Problems?** Open an issue on [GitHub](https://github.com/itsmlab/itsm-agent/issues) or contact the support team.
