# 🔧 INSTALLER_FIXES.md — ITSMLab Installer Fixes

> **Date:** July 30, 2026
> **Test environment:** Ubuntu 24.04 LTS, Docker 29.1.3, Docker Compose 1.29.2
> **Project:** ITSMLab (AEGIS) — Autonomous Incident Triage Agent

---

## Summary

During the installation of ITSMLab on a VM with Ubuntu 24.04, **8 critical issues** were identified that prevented a successful installation. This document details each issue, its root cause, and the implemented solution.

---

## Issues and Solutions

### 1. Incorrect RAM detection (0GB / 1GB)

**Issue:** The script detected 0GB or 1GB of RAM instead of the VM's actual RAM.

**Root cause:** The parsing of `/proc/meminfo` failed on Ubuntu 24.04, returning a non-numeric value that was interpreted as 0.

**Implemented solution:**
- Primary method: `grep -E '^MemTotal:' /proc/meminfo | awk '{print $2}'` with numeric validation.
- Fallback method: `free -h` if the first method fails.
- Validation that the value is numeric before using it.

**File:** `install.sh` (section 1c)

```bash
# Method 1: /proc/meminfo
total_ram_kb=$(grep -E '^MemTotal:' /proc/meminfo 2>/dev/null | awk '{print $2}')
# Method 2 (fallback): free -h
total_ram_gb=$(free -h 2>/dev/null | awk '/^Mem:/ {print $2}' | sed 's/[^0-9.]//g' | awk '{printf "%d", $1}')
```

---

### 2. Incorrect disk space detection

**Issue:** The script did not correctly detect the available disk space.

**Root cause:** It used `df -k .` which depends on the current directory, which may point to a different mount point than the root partition.

**Implemented solution:**
- Changed to `df -k /` to get the actual space of the root partition.
- Numeric validation of the result.
- Calculation of required space based on the estimated size of the images.

**File:** `install.sh` (section 1d)

```bash
available_kb=$(df -k / 2>/dev/null | tail -1 | awk '{print $4}')
```

---

### 3. Docker daemon not running

**Issue:** The script did not verify whether Docker was active before continuing.

**Root cause:** The Docker daemon status was not checked; it only attempted to start without confirming.

**Implemented solution:**
- Added `sudo systemctl status docker` for diagnostics.
- Added `sudo systemctl start docker` to start it.
- Verification with `systemctl is-active docker` to confirm it became active.
- Actionable error messages with diagnostic commands.

**File:** `install.sh` (section 1a)

```bash
sudo systemctl status docker --no-pager 2>&1 | head -10 || true
sudo systemctl start docker
systemctl is-active docker
```

---

### 4. Unsupported `--env-file` flag

**Issue:** The installer used `--env-file` with `docker run`, but it is not supported in all versions of Docker Compose.

**Root cause:** Docker Compose v1 (legacy) does not support `--env-file` the same way as v2.

**Implemented solution:**
- New `docker_compose_run()` function that tries `--env-file` first (v2) and falls back to the export method if it fails.
- Export method: `set -a; . "$ENV_FILE"; set +a` to export variables to the shell.
- Uses the detected command (`$COMPOSE_CMD`) instead of hardcoding `docker compose`.

**File:** `install.sh` (function `docker_compose_run`)

```bash
# Method 1: --env-file (v2)
$COMPOSE_CMD --env-file "$ENV_FILE" "${compose_args[@]}"
# Method 2 (fallback): export variables
set +a; . "$ENV_FILE"; set -a
$COMPOSE_CMD "${compose_args[@]}"
```

---

### 5. `docker compose` vs `docker-compose`

**Issue:** The script did not detect which Compose command was available.

**Root cause:** Docker v20.10+ uses `docker compose` (plugin), while older versions use `docker-compose` (legacy binary).

**Implemented solution:**
- Automatic detection with priority:
  1. `docker compose version` (modern plugin)
  2. `docker-compose --version` (legacy binary)
- The `COMPOSE_CMD` variable is used in all Compose calls.
- Instructions to install the official plugin if neither is available.

**File:** `install.sh` (section 1b)

```bash
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
fi
```

---

### 6. Incorrect flag in Dockerfile

**Issue:** `--no-cache-deps` does not exist in pip.

**Root cause:** Typo — the correct pip option is `--no-cache-dir`.

**Implemented solution:**
- Changed `--no-cache-deps` to `--no-cache-dir` in the `Dockerfile`.

**File:** `Dockerfile`

```dockerfile
# Before (incorrect):
RUN pip install --user --no-cache-deps -r requirements.txt
# After (correct):
RUN pip install --user --no-cache-dir -r requirements.txt
```

---

### 7. Permission denied (docker group)

**Issue:** The user was not in the `docker` group, causing permission errors.

**Root cause:** Docker requires the user to be in the `docker` group to access the daemon socket without sudo.

**Implemented solution:**
- Verification that the user is in the `docker` group.
- Suggestion of `sudo usermod -aG docker $USER`.
- Alternative of running with `sudo ./install.sh`.

**File:** `install.sh` (section 1a-2)

```bash
if ! id -nG | grep -qw docker; then
    echo "  → Fix: sudo usermod -aG docker \$USER"
    echo "  → Then log out and back in (or run: newgrp docker)"
fi
```

---

### 8. Insufficient disk space

**Issue:** The minimum space was not verified before starting the installation.

**Root cause:** The script only warned if there was <10GB, but did not abort if the space was critically low.

**Implemented solution:**
- Absolute minimum: **5GB** (Ollama + llama3 only require ~4.5GB).
- If space is <5GB → **ERROR** and abort.
- If space is <required (estimated + 2GB buffer) → **WARNING**.
- Automatic calculation of the estimated download size.

**File:** `install.sh` (section 1d)

```bash
MIN_DISK_GB=5
if [ "$available_gb" -lt "$MIN_DISK_GB" ]; then
    log_error "Only ${available_gb}GB available. Minimum ${MIN_DISK_GB}GB required."
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
```

---

## Modified Files

| File | Change |
|---------|--------|
| `install.sh` | RAM detection, disk space, Docker, docker group, Compose commands |
| `Dockerfile` | `--no-cache-deps` → `--no-cache-dir` |
| `docker-compose.yml` | Environment variables with defaults (`${VAR:-default}`) |
| `README.md` | "Troubleshooting" section |
| `INSTALLER_FIXES.md` | This document |

---

## Verification

To verify that the fixes work:

```bash
# 1. Verify RAM
grep MemTotal /proc/meminfo
free -h

# 2. Verify disk space
df -h /

# 3. Verify Docker
sudo systemctl status docker
docker info

# 4. Verify Compose
docker compose version || docker-compose --version

# 5. Verify docker group
id -nG | grep docker

# 6. Run the installer
./install.sh
```

---

## Additional Notes

- The installer now uses `set -euo pipefail` to stop on critical errors.
- A trap handler was added that prints actionable recovery commands.
- Previous installation detection was added to allow continuing with `docker compose up -d`.
- The installer automatically detects whether to use `docker compose` or `docker-compose`.
