# ── AEGIS — On-Premise Intelligent Installer (Windows) ────────
# Automated installation script for deploying AEGIS in a client environment.
#
# Usage:
#   .\install.ps1
#   # or with API key:
#   $env:LLM_PROVIDER="deepseek"; $env:DEEPSEEK_API_KEY="sk-xxx"; .\install.ps1
#
# Supports:
#   - Local LLM (Ollama) — no API key needed
#   - External API (DeepSeek, OpenAI, Anthropic) — requires API key
#
# Environment variables (optional):
#   LLM_PROVIDER      = "ollama" | "deepseek" | "openai" | "anthropic"  (default: ollama)
#   DEEPSEEK_API_KEY  = your DeepSeek API key
#   OPENAI_API_KEY    = your OpenAI API key
#   ANTHROPIC_API_KEY = your Anthropic API key
#   OLLAMA_MODEL      = model name for Ollama (default: llama3)
#   AEGIS_DOMAIN      = domain for HTTPS (default: localhost)
#   LOG_LEVEL         = DEBUG | INFO | WARNING | ERROR (default: INFO)
#   SKIP_PRECHECKS    = set to "true" to skip prerequisite checks
#   SKIP_KB_INIT      = set to "true" to skip knowledge base initialization
# =============================================================

$ErrorActionPreference = "Stop"

# ── Colors ──────────────────────────────────────────────────
$Host.UI.RawUI.ForegroundColor = "Cyan"
Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════╗"
Write-Host "  ║         AEGIS — On-Premise Installer      ║"
Write-Host "  ║   Autonomous Incident Triage Agent        ║"
Write-Host "  ║   v3.1.0 — Intelligent Installer          ║"
Write-Host "  ╚═══════════════════════════════════════════╝"
Write-Host ""
$Host.UI.RawUI.ForegroundColor = "White"

function Write-Info   { Write-Host "[INFO]  $args" -ForegroundColor Cyan }
function Write-Ok     { Write-Host "[OK]    $args" -ForegroundColor Green }
function Write-Warn   { Write-Host "[WARN]  $args" -ForegroundColor Yellow }
function Write-Error  { Write-Host "[ERROR] $args" -ForegroundColor Red }
function Write-Step   { Write-Host "`n─── $args ───`n" -ForegroundColor Magenta }

# ── Helper: generate random password ────────────────────────
function Generate-Password {
    param([int]$Length = 20)
    try {
        $bytes = [byte[]]::new($Length)
        [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
        return [Convert]::ToBase64String($bytes) -replace '[+/=]', '' -replace '[^a-zA-Z0-9]', '' | Select-Object -First 1
    } catch {
        return "aegis_$(Get-Date -Format 'yyyyMMddHHmmss')"
    }
}

# ── Helper: check if a port is available ────────────────────
function Test-PortAvailable {
    param([int]$Port)
    try {
        $connections = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
        return -not ($connections | Where-Object { $_.Port -eq $Port })
    } catch {
        return $true  # Assume available if we can't check
    }
}

# ════════════════════════════════════════════════════════════
# STEP 1: Prerequisite Verification
# ════════════════════════════════════════════════════════════
Write-Step "Step 1/6: Verifying prerequisites"

$FAILED_CHECKS = 0

# ── 1a. Docker ──────────────────────────────────────────────
Write-Info "Checking Docker..."
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed."
    Write-Host "  → Install Docker Desktop: https://docs.docker.com/get-docker/"
    $FAILED_CHECKS++
} else {
    # Verify Docker daemon is running
    try {
        $dockerInfo = docker info 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "Docker found: $(docker --version 2>&1)"
        } else {
            throw "Docker daemon not responding"
        }
    } catch {
        Write-Error "Docker is installed but the daemon is not running."
        Write-Host "  → Start Docker Desktop from the Start Menu or system tray."
        $FAILED_CHECKS++
    }
}

# ── 1b. Docker Compose ──────────────────────────────────────
Write-Info "Checking Docker Compose..."
try {
    $composeVersion = docker compose version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Docker Compose found: $composeVersion"
    } else {
        throw "Docker Compose not available"
    }
} catch {
    Write-Error "Docker Compose is not installed."
    Write-Host "  → Docker Desktop includes Docker Compose. Reinstall if needed."
    $FAILED_CHECKS++
}

# ── 1c. RAM check ───────────────────────────────────────────
Write-Info "Checking available RAM..."
try {
    $os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
    $totalRamGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
    if ($totalRamGB -lt 8) {
        Write-Warn "System has ${totalRamGB}GB RAM. 8GB+ recommended for Ollama + AEGIS."
        if ($totalRamGB -lt 4) {
            Write-Error "System has only ${totalRamGB}GB RAM. Minimum 4GB required."
            $FAILED_CHECKS++
        }
    } else {
        Write-Ok "RAM: ${totalRamGB}GB (sufficient)"
    }
} catch {
    Write-Warn "Cannot detect RAM. Skipping RAM check."
}

# ── 1d. Disk space check ────────────────────────────────────
Write-Info "Checking available disk space..."
try {
    $drive = Get-PSDrive -Name (Get-Location).Drive.Name -ErrorAction Stop
    $availableGB = [math]::Round($drive.Free / 1GB, 1)
    if ($availableGB -lt 10) {
        Write-Warn "Only ${availableGB}GB available. 10GB+ recommended for Docker images + data."
    } else {
        Write-Ok "Disk space: ${availableGB}GB available (sufficient)"
    }
} catch {
    Write-Warn "Cannot detect disk space. Skipping disk check."
}

# ── 1e. Port availability ───────────────────────────────────
Write-Info "Checking port availability..."
$PORTS_TO_CHECK = @(8000, 5432, 11434)
foreach ($port in $PORTS_TO_CHECK) {
    if (Test-PortAvailable -Port $port) {
        Write-Ok "Port $port is available"
    } else {
        Write-Warn "Port $port is already in use. AEGIS may conflict with existing services."
    }
}

# ── 1f. GPU detection (optional) ────────────────────────────
Write-Info "Checking for GPU..."
$GPU_AVAILABLE = $false
try {
    $gpu = Get-CimInstance -ClassName Win32_VideoController -ErrorAction Stop | Where-Object {
        $_.Name -match "NVIDIA|AMD|Radeon"
    }
    if ($gpu) {
        Write-Ok "GPU detected: $($gpu.Name)"
        $GPU_AVAILABLE = $true
    } else {
        Write-Warn "No dedicated GPU detected. Ollama will run on CPU (slower but functional)."
    }
} catch {
    Write-Warn "Cannot detect GPU. Skipping GPU check."
}

# ── Abort if critical checks failed ─────────────────────────
if ($FAILED_CHECKS -gt 0 -and $env:SKIP_PRECHECKS -ne "true") {
    Write-Error "${FAILED_CHECKS} critical check(s) failed. Aborting installation."
    Write-Host "  → Fix the issues above and re-run the installer."
    Write-Host "  → To bypass checks: `$env:SKIP_PRECHECKS='true'; .\install.ps1"
    exit 1
}

# ════════════════════════════════════════════════════════════
# STEP 2: LLM Provider Configuration
# ════════════════════════════════════════════════════════════
Write-Step "Step 2/6: Configuring LLM provider"

$LLM_PROVIDER = if ($env:LLM_PROVIDER) { $env:LLM_PROVIDER } else { "ollama" }

switch ($LLM_PROVIDER) {
    "ollama" {
        Write-Info "Using local Ollama (no API key needed)"
        $OLLAMA_MODEL = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "llama3" }
        Write-Info "  Model: $OLLAMA_MODEL"
        if ($GPU_AVAILABLE) {
            Write-Ok "GPU available — Ollama will use GPU acceleration"
        } else {
            Write-Warn "No GPU — Ollama will run on CPU. Consider using a smaller model (e.g., llama3.2:1b)."
        }
    }
    "deepseek" {
        if (-not $env:DEEPSEEK_API_KEY) {
            Write-Error "DEEPSEEK_API_KEY is not set."
            Write-Host "  Usage: `$env:DEEPSEEK_API_KEY='sk-xxx'; .\install.ps1"
            exit 1
        }
        Write-Ok "DeepSeek API key configured"
    }
    "openai" {
        if (-not $env:OPENAI_API_KEY) {
            Write-Error "OPENAI_API_KEY is not set."
            Write-Host "  Usage: `$env:OPENAI_API_KEY='sk-xxx'; .\install.ps1"
            exit 1
        }
        Write-Ok "OpenAI API key configured"
    }
    "anthropic" {
        if (-not $env:ANTHROPIC_API_KEY) {
            Write-Error "ANTHROPIC_API_KEY is not set."
            Write-Host "  Usage: `$env:ANTHROPIC_API_KEY='sk-ant-xxx'; .\install.ps1"
            exit 1
        }
        Write-Ok "Anthropic API key configured"
    }
    default {
        Write-Error "Unknown LLM_PROVIDER: $LLM_PROVIDER"
        Write-Host "  Valid options: ollama, deepseek, openai, anthropic"
        exit 1
    }
}

# ════════════════════════════════════════════════════════════
# STEP 3: Generate .env Configuration
# ════════════════════════════════════════════════════════════
Write-Step "Step 3/6: Generating .env configuration"

# Generate random PostgreSQL password
$POSTGRES_PASSWORD = Generate-Password -Length 20
Write-Info "Generated random PostgreSQL password"

$ENV_FILE = if (Test-Path .env) { ".env.aegis" } else { ".env" }

@"
# ── AEGIS Configuration ──────────────────────────────────────
# Generated by install.ps1 on $(Get-Date)
# LLM Provider: ${LLM_PROVIDER}

# ── LLM Provider ─────────────────────────────────────────────
LLM_PROVIDER=${LLM_PROVIDER}

"@ | Out-File -FilePath $ENV_FILE -Encoding UTF8

if ($LLM_PROVIDER -eq "deepseek") {
    Add-Content $ENV_FILE "DEEPSEEK_API_KEY=$env:DEEPSEEK_API_KEY"
} elseif ($LLM_PROVIDER -eq "openai") {
    Add-Content $ENV_FILE "OPENAI_API_KEY=$env:OPENAI_API_KEY"
} elseif ($LLM_PROVIDER -eq "anthropic") {
    Add-Content $ENV_FILE "ANTHROPIC_API_KEY=$env:ANTHROPIC_API_KEY"
} elseif ($LLM_PROVIDER -eq "ollama") {
    Add-Content $ENV_FILE @"
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=${OLLAMA_MODEL}
"@
}

Add-Content $ENV_FILE @"

# ── Database ─────────────────────────────────────────────────
DATABASE_URL=postgresql+psycopg2://aegis:${POSTGRES_PASSWORD}@postgres:5432/aegis
POSTGRES_USER=aegis
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=aegis

# ── ChromaDB (RAG vector store) ──────────────────────────────
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_USE_SERVER=true

# ── Security ─────────────────────────────────────────────────
AUTH_REQUIRED=false

# ── Logging ──────────────────────────────────────────────────
LOG_LEVEL=$(if ($env:LOG_LEVEL) { $env:LOG_LEVEL } else { "INFO" })
"@

Write-Ok "Configuration written to $ENV_FILE"

# ════════════════════════════════════════════════════════════
# STEP 4: Update docker-compose.yml with generated password
# ════════════════════════════════════════════════════════════
Write-Step "Step 4/6: Configuring Docker services"

# Create a docker-compose override for the generated password
@"
# ── AEGIS Docker Override ────────────────────────────────────
# Auto-generated by install.ps1 on $(Get-Date)
# Overrides default PostgreSQL credentials with secure random values
version: "3.9"
services:
  postgres:
    environment:
      POSTGRES_USER: aegis
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: aegis
"@ | Out-File -FilePath "docker-compose.override.yml" -Encoding UTF8

Write-Ok "Docker override created with secure credentials"

# ════════════════════════════════════════════════════════════
# STEP 5: Pull Docker Images
# ════════════════════════════════════════════════════════════
Write-Step "Step 5/6: Pulling Docker images"

Write-Info "Pulling core images (postgres, chromadb, app)..."
docker compose --env-file "$ENV_FILE" pull postgres chromadb app 2>&1 | Select-Object -Last 5
Write-Ok "Core images pulled"

if ($LLM_PROVIDER -eq "ollama") {
    Write-Info "Pulling Ollama image..."
    docker compose --profile ollama --env-file "$ENV_FILE" pull ollama 2>&1 | Select-Object -Last 3
    Write-Ok "Ollama image pulled"
}

# ════════════════════════════════════════════════════════════
# STEP 6: Start AEGIS
# ════════════════════════════════════════════════════════════
Write-Step "Step 6/6: Starting AEGIS"

$COMPOSE_FLAGS = "--env-file $ENV_FILE"

if ($LLM_PROVIDER -eq "ollama") {
    $COMPOSE_FLAGS = "$COMPOSE_FLAGS --profile ollama"
}

if ($env:AEGIS_DOMAIN) {
    $COMPOSE_FLAGS = "$COMPOSE_FLAGS --profile caddy"
    $env:CADDY_DOMAIN = $env:AEGIS_DOMAIN
}

Write-Info "Starting containers (this may take a minute)..."
docker compose $COMPOSE_FLAGS up --build -d 2>&1 | Select-Object -Last 5

# ── Post-Installation Validation ────────────────────────────
Write-Step "Post-Installation: Validating services"

# Wait for all services to be healthy (up to 120 seconds)
Write-Info "Waiting for all services to be healthy..."
$MAX_RETRIES = 60
$SLEEP_SECONDS = 2

for ($i = 0; $i -lt $MAX_RETRIES; $i++) {
    $ALL_HEALTHY = $true

    # Check PostgreSQL health via docker ps
    try {
        $postgresStatus = docker compose ps postgres --format json 2>&1 | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($postgresStatus -and $postgresStatus.Health -ne "healthy") {
            $ALL_HEALTHY = $false
        }
    } catch {
        $ALL_HEALTHY = $false
    }

    # Check App health via HTTP
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/v1/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -ne 200) {
            $ALL_HEALTHY = $false
        }
    } catch {
        $ALL_HEALTHY = $false
    }

    if ($ALL_HEALTHY) {
        Write-Ok "All services are healthy!"
        break
    }

    if ($i -eq ($MAX_RETRIES - 1)) {
        Write-Warn "Timed out waiting for all services. Checking individual status..."
        Write-Info "  Run 'docker compose ps' to see container status"
        Write-Info "  Run 'docker compose logs app' to see app logs"
    }

    # Show progress every 10 seconds
    if ($i % 5 -eq 0 -and $i -gt 0) {
        Write-Info "  Still waiting... ($($i * $SLEEP_SECONDS)s elapsed)"
    }

    Start-Sleep -Seconds $SLEEP_SECONDS
}

# ── Detailed service status ─────────────────────────────────
Write-Info "Service status:"
docker compose ps --format "table {{.Name}}`t{{.Status}}`t{{.Ports}}" 2>&1 | ForEach-Object { Write-Host "  $_" }

# ── Initialize Knowledge Base (RAG) ─────────────────────────
if ($env:SKIP_KB_INIT -ne "true") {
    Write-Info "Initializing knowledge base..."
    try {
        docker compose $COMPOSE_FLAGS exec -T app python scripts/init_knowledge_base.py 2>&1 | Out-Null
        Write-Ok "Knowledge base initialized"
    } catch {
        Write-Warn "Knowledge base initialization failed (non-critical). You can run it later:"
        Write-Host "  docker compose exec app python scripts/init_knowledge_base.py"
    }
} else {
    Write-Info "Skipping knowledge base initialization (SKIP_KB_INIT=true)"
}

# ── Final Health Check ──────────────────────────────────────
Write-Info "Running final health check..."
try {
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:8000/v1/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    $healthJson = $healthResponse.Content | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($healthJson.status -eq "ok") {
        Write-Ok "Health endpoint: OK"
    } else {
        Write-Warn "Health endpoint returned: $($healthResponse.Content)"
    }
} catch {
    Write-Warn "Health endpoint not responding: $_"
}

# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
Write-Step "Installation Complete"

$Host.UI.RawUI.ForegroundColor = "Cyan"
Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════╗"
Write-Host "  ║         AEGIS Installation Complete!      ║"
Write-Host "  ╚═══════════════════════════════════════════╝"
Write-Host ""
$Host.UI.RawUI.ForegroundColor = "White"

Write-Host "  ── Access URLs ──────────────────────────────"
Write-Host "    API:          http://localhost:8000"
Write-Host "    Health:       http://localhost:8000/v1/health"
Write-Host "    Docs:         http://localhost:8000/docs"
Write-Host ""

if ($env:AEGIS_DOMAIN) {
    Write-Host "    HTTPS:        https://$env:AEGIS_DOMAIN"
    Write-Host ""
}

Write-Host "  ── Configuration ────────────────────────────"
Write-Host "    LLM Provider: $LLM_PROVIDER"
if ($LLM_PROVIDER -eq "ollama") {
    Write-Host "    Model:        $OLLAMA_MODEL"
}
Write-Host "    Config file:  $ENV_FILE"
Write-Host ""

Write-Host "  ── Database ─────────────────────────────────"
Write-Host "    User:         aegis"
Write-Host "    Password:     $POSTGRES_PASSWORD"
Write-Host "    Database:     aegis"
Write-Host "    ⚠️  Save this password! It won't be shown again."
Write-Host ""

Write-Host "  ── Useful Commands ──────────────────────────"
Write-Host "    View logs:    docker compose logs -f app"
Write-Host "    Stop:         docker compose down"
Write-Host "    Restart:      docker compose up -d"
Write-Host "    Update:       docker compose pull `&`& docker compose up -d"
Write-Host "    Shell:        docker compose exec app powershell"
Write-Host ""

if ($LLM_PROVIDER -eq "ollama") {
    Write-Host "  ── Ollama Notes ────────────────────────────"
    Write-Host "    The first LLM request may be slow while Ollama"
    Write-Host "    loads the model into memory."
    if (-not $GPU_AVAILABLE) {
        Write-Host ""
        Write-Host "    ⚠️  Running on CPU. For better performance:"
        Write-Host "      • Use a smaller model: `$env:OLLAMA_MODEL='llama3.2:1b'"
        Write-Host "      • Or install NVIDIA drivers + nvidia-container-toolkit"
    }
    Write-Host ""
}

Write-Host "  ── Troubleshooting ──────────────────────────"
Write-Host "    If services fail to start:"
Write-Host "      1. docker compose logs app     # Check app errors"
Write-Host "      2. docker compose logs postgres # Check DB errors"
Write-Host "      3. docker compose ps           # Check container status"
Write-Host "      4. docker compose restart app  # Restart the app"
Write-Host ""
