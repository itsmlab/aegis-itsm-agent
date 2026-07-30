#!/usr/bin/env bash
# ── ITSMLab — On-Premise Intelligent Installer ────────────────
# Automated installation script for deploying ITSMLab (ITSM-Agent) in a client environment.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/itsmlab/itsm-agent/main/install.sh | bash
#   # or locally:
#   chmod +x install.sh && ./install.sh
#
# Supports:
#   - Local LLM (Ollama) — no API key needed
#   - External API (DeepSeek, OpenAI, Anthropic) — requires API key
#
# Environment variables (optional):
#   LLM_PROVIDER     = "ollama" | "deepseek" | "openai" | "anthropic"  (default: ollama)
#   DEEPSEEK_API_KEY = your DeepSeek API key
#   OPENAI_API_KEY   = your OpenAI API key
#   ANTHROPIC_API_KEY = your Anthropic API key
#   OLLAMA_MODEL     = model name for Ollama (default: llama3)
#   ITSMLAB_DOMAIN   = domain for HTTPS (default: localhost)
#   LOG_LEVEL        = DEBUG | INFO | WARNING | ERROR (default: INFO)
#   SKIP_PRECHECKS   = set to "true" to skip prerequisite checks
#   SKIP_KB_INIT     = set to "true" to skip knowledge base initialization
# =============================================================

set -euo pipefail

# ── Colors ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "\n${CYAN}${BOLD}─── $1 ───${NC}\n"; }

# ── Trap handler: catch unexpected exits and print actionable message ──
trap_handler() {
    local exit_code=$?
    # Only print if we exited abnormally (not 0) and we're not in a sub-shell
    if [ "$exit_code" -ne 0 ] && [ "${BASH_SUBSHELL:-0}" -eq 0 ]; then
        echo ""
        log_error "Installation failed at step ${CURRENT_STEP:-"unknown"} (exit code: ${exit_code})."
        echo ""
        echo "  ${BOLD}Actionable recovery commands:${NC}"
        case "${CURRENT_STEP:-}" in
            "prerequisites")
                echo "    Fix the issues above and re-run: ./install.sh"
                ;;
            "docker_start")
                echo "    sudo systemctl start docker"
                echo "    sudo systemctl is-active docker  # verify it's running"
                echo "    Then re-run: ./install.sh"
                ;;
            "compose_pull")
                echo "    export \$(grep -v '^#' .env | xargs)"
                echo "    docker compose pull postgres chromadb app"
                echo "    Then re-run: ./install.sh"
                ;;
            "compose_up")
                echo "    export \$(grep -v '^#' .env | xargs)"
                echo "    docker compose up --build -d"
                echo "    Or re-run: ./install.sh"
                ;;
            "kb_init")
                echo "    docker compose exec app python scripts/init_knowledge_base.py"
                echo "    Or skip with: SKIP_KB_INIT=true ./install.sh"
                ;;
            *)
                echo "    export \$(grep -v '^#' .env | xargs)"
                echo "    docker compose up --build -d"
                echo "    Or re-run: ./install.sh"
                ;;
        esac
        echo ""
        echo "  ${BOLD}View logs:${NC}"
        echo "    docker compose logs app"
        echo "    docker compose logs postgres"
        echo ""
    fi
}
trap trap_handler EXIT

# ── Track current step for the trap handler ─────────────────
CURRENT_STEP=""

# ── Helper: check if a port is available ────────────────────
check_port() {
    local port=$1
    if command -v ss &> /dev/null; then
        if ss -tlnp "sport = :$port" 2>/dev/null | grep -q ":$port"; then
            return 1
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
            return 1
        fi
    fi
    return 0
}

# ── Helper: generate random password ────────────────────────
generate_password() {
    local length=${1:-16}
    if command -v openssl &> /dev/null; then
        openssl rand -base64 $((length * 3 / 4)) 2>/dev/null | tr -d '/+=' | cut -c1-"$length"
    elif command -v uuidgen &> /dev/null; then
        uuidgen | tr -d '-' | cut -c1-"$length"
    else
        echo "aegis_$(date +%s)_${RANDOM}"
    fi
}

# ── Helper: safely run docker compose with env-file fallback ─
# Tries --env-file first (v2 syntax), falls back to export method
docker_compose_run() {
    local compose_args=("$@")

    # Attempt 1: use --env-file (native v2 syntax)
    if [ -n "${ENV_FILE:-}" ]; then
        if docker compose --env-file "$ENV_FILE" "${compose_args[@]}" 2>/dev/null; then
            return 0
        fi
        log_warn "docker compose --env-file failed. Falling back to export method..."
    fi

    # Attempt 2: export env vars into shell, then run without --env-file
    if [ -n "${ENV_FILE:-}" ] && [ -f "$ENV_FILE" ]; then
        set +a  # automatically export all variables
        . "$ENV_FILE"
        set -a
    fi
    docker compose "${compose_args[@]}"
}

# ── Helper: calculate estimated download size for images ────
calculate_estimated_download() {
    local total_mb=0
    # Base images
    total_mb=$((total_mb + 200))   # postgres:16-alpine ~200MB
    total_mb=$((total_mb + 800))   # chromadb/chroma:latest ~800MB
    total_mb=$((total_mb + 300))   # app build context ~300MB

    if [ "${LLM_PROVIDER:-ollama}" = "ollama" ]; then
        total_mb=$((total_mb + 4500))  # ollama/ollama:latest + llama3 model ~4.5GB
    fi

    if [ -n "${ITSMLAB_DOMAIN:-}" ]; then
        total_mb=$((total_mb + 50))  # caddy:2-alpine ~50MB
    fi

    echo "$total_mb"
}

# ════════════════════════════════════════════════════════════
# PRE-FLIGHT: Previous installation detection
# ════════════════════════════════════════════════════════════
if [ -f .env ] || [ -f .env.aegis ]; then
    # Check if docker compose already created resources (containers or volumes)
    if command -v docker &> /dev/null && docker compose ps --format json 2>/dev/null | grep -q .; then
        echo ""
        echo "  ╔══════════════════════════════════════════════════════════════╗"
        echo "  ║     ⚠️  PREVIOUS INSTALLATION DETECTED                      ║"
        echo "  ║                                                              ║"
        echo "  ║  It looks like ITSMLab was already installed or partially     ║"
        echo "  ║  set up on this system.                                      ║"
        echo "  ║                                                              ║"
        echo "  ║  To continue where you left off, just run:                   ║"
        echo "  ║                                                              ║"
        echo "  ║    docker compose up -d                                      ║"
        echo "  ║                                                              ║"
        echo "  ║  To restart the full installer, clean up first:              ║"
        echo "  ║    docker compose down --volumes                             ║"
        echo "  ║    rm -f .env .env.aegis docker-compose.override.yml        ║"
        echo "  ║    ./install.sh                                              ║"
        echo "  ╚══════════════════════════════════════════════════════════════╝"
        echo ""
        # Don't exit — let the user decide to continue or not
        log_info "Continuing with installer in 5 seconds (Ctrl+C to abort)..."
        sleep 5
    fi
fi

# ── Banner ──────────────────────────────────────────────────
echo ""
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║      ITSMLab — On-Premise Installer       ║"
echo "  ║   Autonomous Incident Triage Agent        ║"
echo "  ║   v3.2.0 — Intelligent Installer          ║"
echo "  ╚═══════════════════════════════════════════╝"
echo ""

# ════════════════════════════════════════════════════════════
# STEP 1: Prerequisite Verification
# ════════════════════════════════════════════════════════════
CURRENT_STEP="prerequisites"
log_step "Step 1/6: Verifying prerequisites"

FAILED_CHECKS=0

# ── 1a. Docker ──────────────────────────────────────────────
log_info "Checking Docker..."
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed."
    echo "  → Install Docker: https://docs.docker.com/get-docker/"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
    # Verify Docker daemon is running
    if docker info &> /dev/null; then
        log_ok "Docker found: $(docker --version 2>/dev/null)"
    else
        log_warn "Docker is installed but the daemon is not running."
        echo "  → Attempting to start Docker daemon..."
        CURRENT_STEP="docker_start"
        if sudo systemctl start docker 2>/dev/null; then
            # Wait a moment for the daemon to initialize
            sleep 2
            if systemctl is-active docker &>/dev/null; then
                log_ok "Docker daemon started successfully."
            else
                log_error "Docker daemon failed to start after 'systemctl start docker'."
                echo "  → Check: sudo journalctl -u docker --no-pager | tail -20"
                echo "  → Or start manually: sudo dockerd &"
                FAILED_CHECKS=$((FAILED_CHECKS + 1))
            fi
        else
            log_error "Could not start Docker daemon with 'sudo systemctl start docker'."
            echo "  → Try: sudo systemctl start docker"
            echo "  → Check: sudo journalctl -u docker --no-pager | tail -20"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
        fi
        CURRENT_STEP="prerequisites"
    fi
fi

# ── 1b. Docker Compose (modern check) ───────────────────────
log_info "Checking Docker Compose..."
COMPOSE_CMD=""
# Priority 1: modern 'docker compose' (plugin, v20.10+)
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
    log_ok "Docker Compose (plugin) found: $(docker compose version 2>/dev/null)"
# Priority 2: legacy standalone 'docker-compose' binary
elif command -v docker-compose &> /dev/null && docker-compose --version &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    log_warn "Using legacy 'docker-compose' binary. Consider installing the official Docker Compose plugin."
    log_info "  → Install plugin: sudo apt-get install docker-compose-plugin"
else
    log_error "Docker Compose is not installed."
    echo "  → Install the official Docker Compose plugin:"
    echo "    sudo apt-get update && sudo apt-get install -y docker-compose-plugin"
    echo "  → Or install standalone: https://docs.docker.com/compose/install/"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# ── 1c. RAM check (fixed for Ubuntu 24.04) ──────────────────
log_info "Checking available RAM..."
if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Read MemTotal from /proc/meminfo, extract the numeric value in kB
        total_ram_kb=$(grep -E '^MemTotal:' /proc/meminfo | awk '{print $2}')
        # Validate we got a numeric value
        if ! [[ "$total_ram_kb" =~ ^[0-9]+$ ]]; then
            log_warn "Could not parse MemTotal from /proc/meminfo (got: '${total_ram_kb}'). Skipping RAM check."
            total_ram_gb=0
        else
            # Calculate GB using awk for floating-point precision, then round
            total_ram_gb=$(awk "BEGIN {printf \"%d\", $total_ram_kb / 1024 / 1024}")
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        total_ram_bytes=$(sysctl -n hw.memsize 2>/dev/null)
        if [[ "$total_ram_bytes" =~ ^[0-9]+$ ]]; then
            total_ram_gb=$((total_ram_bytes / 1024 / 1024 / 1024))
        else
            log_warn "Could not detect RAM on macOS. Skipping RAM check."
            total_ram_gb=0
        fi
    fi

    if [ "$total_ram_gb" -gt 0 ]; then
        if [ "$total_ram_gb" -lt 4 ]; then
            log_error "System has only ${total_ram_gb}GB RAM. Minimum 4GB required for Ollama + ITSMLab."
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
        elif [ "$total_ram_gb" -lt 8 ]; then
            log_warn "System has ${total_ram_gb}GB RAM. 8GB+ recommended for Ollama + ITSMLab."
            log_warn "Installation will proceed, but performance may be degraded."
        else
            log_ok "RAM: ${total_ram_gb}GB (sufficient)"
        fi
    fi
else
    log_warn "Cannot detect RAM on this OS. Skipping RAM check."
fi

# ── 1d. Disk space check (with estimated download size) ─────
log_info "Checking available disk space..."
if command -v df &> /dev/null; then
    available_kb=$(df -k . | tail -1 | awk '{print $4}')
    available_gb=$((available_kb / 1024 / 1024))

    # Calculate estimated download size
    estimated_mb=$(calculate_estimated_download)
    estimated_gb=$(( (estimated_mb / 1024) + 1 ))  # round up

    # We need: estimated download + 2GB buffer for runtime data
    required_gb=$((estimated_gb + 2))

    if [ "$available_gb" -lt "$required_gb" ]; then
        log_warn "Only ${available_gb}GB available. ${required_gb}GB+ recommended (${estimated_gb}GB for images + 2GB buffer)."
        log_warn "The download may fail partway through due to insufficient disk space."
    else
        log_ok "Disk space: ${available_gb}GB available (${required_gb}GB needed — sufficient)"
    fi
else
    log_warn "Cannot detect disk space. Skipping disk check."
fi

# ── 1e. Port availability ───────────────────────────────────
log_info "Checking port availability..."
PORTS_TO_CHECK=(8000 5432 11434)
for port in "${PORTS_TO_CHECK[@]}"; do
    if check_port "$port"; then
        log_ok "Port $port is available"
    else
        log_warn "Port $port is already in use. ITSMLab may conflict with existing services."
    fi
done

# ── 1f. GPU detection (optional) ────────────────────────────
log_info "Checking for GPU..."
GPU_AVAILABLE=false
if command -v nvidia-smi &> /dev/null; then
    gpu_info=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)
    if [ -n "$gpu_info" ]; then
        log_ok "NVIDIA GPU detected: ${gpu_info}"
        GPU_AVAILABLE=true
    else
        log_warn "nvidia-smi found but no GPU detected."
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # Check for Apple Silicon (MPS)
    if sysctl -n machdep.cpu.brand_string 2>/dev/null | grep -qi "Apple"; then
        log_ok "Apple Silicon detected (MPS acceleration available)"
        GPU_AVAILABLE=true
    fi
else
    log_warn "No GPU detected. Ollama will run on CPU (slower but functional)."
fi

# ── Abort if critical checks failed ─────────────────────────
if [ "$FAILED_CHECKS" -gt 0 ] && [ "${SKIP_PRECHECKS:-}" != "true" ]; then
    log_error "${FAILED_CHECKS} critical check(s) failed. Aborting installation."
    echo "  → Fix the issues above and re-run the installer."
    echo "  → To bypass checks: SKIP_PRECHECKS=true ./install.sh"
    exit 1
fi

# ════════════════════════════════════════════════════════════
# STEP 2: LLM Provider Configuration
# ════════════════════════════════════════════════════════════
CURRENT_STEP="llm_config"
log_step "Step 2/6: Configuring LLM provider"

LLM_PROVIDER="${LLM_PROVIDER:-ollama}"

case "$LLM_PROVIDER" in
    ollama)
        log_info "Using local Ollama (no API key needed)"
        OLLAMA_MODEL="${OLLAMA_MODEL:-llama3}"
        log_info "  Model: ${OLLAMA_MODEL}"
        if [ "$GPU_AVAILABLE" = true ]; then
            log_ok "GPU available — Ollama will use GPU acceleration"
        else
            log_warn "No GPU — Ollama will run on CPU. Consider using a smaller model (e.g., llama3.2:1b)."
        fi
        ;;
    deepseek)
        if [ -z "${DEEPSEEK_API_KEY:-}" ]; then
            log_error "DEEPSEEK_API_KEY is not set."
            echo "  Usage: DEEPSEEK_API_KEY=sk-xxx ./install.sh"
            echo "  Or:    export DEEPSEEK_API_KEY=sk-xxx && ./install.sh"
            exit 1
        fi
        log_ok "DeepSeek API key configured"
        ;;
    openai)
        if [ -z "${OPENAI_API_KEY:-}" ]; then
            log_error "OPENAI_API_KEY is not set."
            echo "  Usage: OPENAI_API_KEY=sk-xxx ./install.sh"
            echo "  Or:    export OPENAI_API_KEY=sk-xxx && ./install.sh"
            exit 1
        fi
        log_ok "OpenAI API key configured"
        ;;
    anthropic)
        if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
            log_error "ANTHROPIC_API_KEY is not set."
            echo "  Usage: ANTHROPIC_API_KEY=sk-ant-xxx ./install.sh"
            echo "  Or:    export ANTHROPIC_API_KEY=sk-ant-xxx && ./install.sh"
            exit 1
        fi
        log_ok "Anthropic API key configured"
        ;;
    *)
        log_error "Unknown LLM_PROVIDER: ${LLM_PROVIDER}"
        echo "  Valid options: ollama, deepseek, openai, anthropic"
        exit 1
        ;;
esac

# ════════════════════════════════════════════════════════════
# STEP 3: Generate .env Configuration
# ════════════════════════════════════════════════════════════
CURRENT_STEP="env_config"
log_step "Step 3/6: Generating .env configuration"

# Generate random PostgreSQL password
POSTGRES_PASSWORD=$(generate_password 20)
log_info "Generated random PostgreSQL password"

if [ -f .env ]; then
    log_warn ".env file already exists. Creating .env.aegis instead."
    ENV_FILE=".env.aegis"
else
    ENV_FILE=".env"
fi

cat > "$ENV_FILE" <<EOF
# ── ITSMLab Configuration ────────────────────────────────────
# Generated by install.sh on $(date)
# LLM Provider: ${LLM_PROVIDER}

# ── LLM Provider ─────────────────────────────────────────────
LLM_PROVIDER=${LLM_PROVIDER}

EOF

if [ "$LLM_PROVIDER" = "deepseek" ]; then
    echo "DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}" >> "$ENV_FILE"
elif [ "$LLM_PROVIDER" = "openai" ]; then
    echo "OPENAI_API_KEY=${OPENAI_API_KEY}" >> "$ENV_FILE"
elif [ "$LLM_PROVIDER" = "anthropic" ]; then
    echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" >> "$ENV_FILE"
elif [ "$LLM_PROVIDER" = "ollama" ]; then
    cat >> "$ENV_FILE" <<EOF
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=${OLLAMA_MODEL}
EOF
fi

cat >> "$ENV_FILE" <<EOF

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
LOG_LEVEL=${LOG_LEVEL:-INFO}
EOF

log_ok "Configuration written to ${ENV_FILE}"

# ════════════════════════════════════════════════════════════
# STEP 4: Update docker-compose.yml with generated password
# ════════════════════════════════════════════════════════════
CURRENT_STEP="docker_override"
log_step "Step 4/6: Configuring Docker services"

# Create a docker-compose override for the generated password
cat > docker-compose.override.yml <<EOF
# ── ITSMLab Docker Override ──────────────────────────────────
# Auto-generated by install.sh on $(date)
# Overrides default PostgreSQL credentials with secure random values
version: "3.9"
services:
  postgres:
    environment:
      POSTGRES_USER: aegis
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: aegis
EOF

log_ok "Docker override created with secure credentials"

# ════════════════════════════════════════════════════════════
# STEP 5: Pull Docker Images
# ════════════════════════════════════════════════════════════
CURRENT_STEP="compose_pull"
log_step "Step 5/6: Pulling Docker images"

log_info "Pulling core images (postgres, chromadb, app)..."
docker_compose_run pull postgres chromadb app 2>&1 | tail -5
log_ok "Core images pulled"

if [ "$LLM_PROVIDER" = "ollama" ]; then
    log_info "Pulling Ollama image..."
    docker_compose_run --profile ollama pull ollama 2>&1 | tail -3
    log_ok "Ollama image pulled"
fi

# ════════════════════════════════════════════════════════════
# STEP 6: Start ITSMLab
# ════════════════════════════════════════════════════════════
CURRENT_STEP="compose_up"
log_step "Step 6/6: Starting ITSMLab"

COMPOSE_FLAGS=""

if [ "$LLM_PROVIDER" = "ollama" ]; then
    COMPOSE_FLAGS="${COMPOSE_FLAGS} --profile ollama"
fi

if [ -n "${ITSMLAB_DOMAIN:-}" ]; then
    COMPOSE_FLAGS="${COMPOSE_FLAGS} --profile caddy"
    export CADDY_DOMAIN="${ITSMLAB_DOMAIN}"
fi

log_info "Starting containers (this may take a minute)..."
docker_compose_run ${COMPOSE_FLAGS} up --build -d 2>&1 | tail -5

# ── Post-Installation Validation ────────────────────────────
CURRENT_STEP="validation"
log_step "Post-Installation: Validating services"

# Wait for all services to be healthy (up to 120 seconds)
log_info "Waiting for all services to be healthy..."
MAX_RETRIES=60
SLEEP_SECONDS=2

for i in $(seq 1 $MAX_RETRIES); do
    ALL_HEALTHY=true

    # Check PostgreSQL health
    POSTGRES_HEALTHY=$(docker compose ps postgres --format json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health',''))" 2>/dev/null || echo "")
    if [ "$POSTGRES_HEALTHY" != "healthy" ]; then
        ALL_HEALTHY=false
    fi

    # Check App health via HTTP
    if curl -s http://localhost:8000/v1/health > /dev/null 2>&1; then
        APP_HEALTHY=true
    else
        APP_HEALTHY=false
        ALL_HEALTHY=false
    fi

    if [ "$ALL_HEALTHY" = true ]; then
        log_ok "All services are healthy!"
        break
    fi

    if [ "$i" -eq "$MAX_RETRIES" ]; then
        log_warn "Timed out waiting for all services. Checking individual status..."
        log_info "  Run 'docker compose ps' to see container status"
        log_info "  Run 'docker compose logs app' to see app logs"
    fi

    # Show progress every 10 seconds
    if [ $((i % 5)) -eq 0 ]; then
        log_info "  Still waiting... (${i}s elapsed)"
    fi

    sleep $SLEEP_SECONDS
done

# ── Detailed service status ─────────────────────────────────
log_info "Service status:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true

# ── Initialize Knowledge Base (RAG) ─────────────────────────
CURRENT_STEP="kb_init"
if [ "${SKIP_KB_INIT:-}" != "true" ]; then
    log_info "Initializing knowledge base..."
    if docker compose exec -T app python scripts/init_knowledge_base.py 2>&1; then
        log_ok "Knowledge base initialized"
    else
        log_warn "Knowledge base initialization failed (non-critical). You can run it later:"
        echo "  docker compose exec app python scripts/init_knowledge_base.py"
    fi
else
    log_info "Skipping knowledge base initialization (SKIP_KB_INIT=true)"
fi

# ── Final Health Check ──────────────────────────────────────
log_info "Running final health check..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/v1/health 2>/dev/null || echo "{}")
if echo "$HEALTH_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null | grep -q "ok"; then
    log_ok "Health endpoint: OK"
else
    log_warn "Health endpoint returned unexpected response: ${HEALTH_RESPONSE}"
fi

# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
CURRENT_STEP=""
log_step "Installation Complete"

echo ""
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║      ITSMLab Installation Complete!       ║"
echo "  ╚═══════════════════════════════════════════╝"
echo ""
echo "  ── Access URLs ──────────────────────────────"
echo "    API:          http://localhost:8000"
echo "    Health:       http://localhost:8000/v1/health"
echo "    Docs:         http://localhost:8000/docs"
echo ""

if [ -n "${ITSMLAB_DOMAIN:-}" ]; then
    echo "    HTTPS:        https://${ITSMLAB_DOMAIN}"
    echo ""
fi

echo "  ── Configuration ────────────────────────────"
echo "    LLM Provider: ${LLM_PROVIDER}"
if [ "$LLM_PROVIDER" = "ollama" ]; then
    echo "    Model:        ${OLLAMA_MODEL}"
fi
echo "    Config file:  ${ENV_FILE}"
echo ""

echo "  ── Database ─────────────────────────────────"
echo "    User:         aegis"
echo "    Password:     ${POSTGRES_PASSWORD}"
echo "    Database:     aegis"
echo "    ⚠️  Save this password! It won't be shown again."
echo ""

echo "  ── Useful Commands ──────────────────────────"
echo "    View logs:    docker compose logs -f app"
echo "    Stop:         docker compose down"
echo "    Restart:      docker compose up -d"
echo "    Update:       docker compose pull && docker compose up -d"
echo "    Shell:        docker compose exec app bash"
echo ""

if [ "$LLM_PROVIDER" = "ollama" ]; then
    echo "  ── Ollama Notes ────────────────────────────"
    echo "    The first LLM request may be slow while Ollama"
    echo "    loads the model into memory."
    if [ "$GPU_AVAILABLE" = false ]; then
        echo ""
        echo "    ⚠️  Running on CPU. For better performance:"
        echo "      • Use a smaller model: OLLAMA_MODEL=llama3.2:1b"
        echo "      • Or install NVIDIA drivers + nvidia-container-toolkit"
    fi
    echo ""
fi

echo "  ── Troubleshooting ──────────────────────────"
echo "    If services fail to start:"
echo "      1. docker compose logs app     # Check app errors"
echo "      2. docker compose logs postgres # Check DB errors"
echo "      3. docker compose ps           # Check container status"
echo "      4. docker compose restart app  # Restart the app"
echo ""
