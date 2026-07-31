# 🔧 INSTALLER_FIXES.md — Correcciones del Instalador ITSMLab

> **Fecha:** 30 de julio de 2026
> **Entorno de prueba:** Ubuntu 24.04 LTS, Docker 29.1.3, Docker Compose 1.29.2
> **Proyecto:** ITSMLab (AEGIS) — Autonomous Incident Triage Agent

---

## Resumen

Durante la instalación de ITSMLab en una VM con Ubuntu 24.04, se identificaron **8 problemas críticos** que impedían una instalación exitosa. Este documento detalla cada problema, su causa raíz, y la solución implementada.

---

## Problemas y Soluciones

### 1. Detección de RAM incorrecta (0GB / 1GB)

**Problema:** El script detectaba 0GB o 1GB de RAM en lugar de la RAM real de la VM.

**Causa raíz:** El parsing de `/proc/meminfo` fallaba en Ubuntu 24.04, devolviendo un valor no numérico que se interpretaba como 0.

**Solución implementada:**
- Método principal: `grep -E '^MemTotal:' /proc/meminfo | awk '{print $2}'` con validación numérica.
- Método de respaldo: `free -h` si el primer método falla.
- Validación de que el valor sea numérico antes de usarlo.

**Archivo:** `install.sh` (sección 1c)

```bash
# Método 1: /proc/meminfo
total_ram_kb=$(grep -E '^MemTotal:' /proc/meminfo 2>/dev/null | awk '{print $2}')
# Método 2 (fallback): free -h
total_ram_gb=$(free -h 2>/dev/null | awk '/^Mem:/ {print $2}' | sed 's/[^0-9.]//g' | awk '{printf "%d", $1}')
```

---

### 2. Detección de espacio en disco incorrecta

**Problema:** El script no detectaba correctamente el espacio disponible en disco.

**Causa raíz:** Se usaba `df -k .` que depende del directorio actual, el cual puede apuntar a un mount point diferente al de la partición raíz.

**Solución implementada:**
- Cambiado a `df -k /` para obtener el espacio real de la partición raíz.
- Validación numérica del resultado.
- Cálculo del espacio requerido basado en el tamaño estimado de las imágenes.

**Archivo:** `install.sh` (sección 1d)

```bash
available_kb=$(df -k / 2>/dev/null | tail -1 | awk '{print $4}')
```

---

### 3. Docker daemon no corriendo

**Problema:** El script no verificaba si Docker estaba activo antes de continuar.

**Causa raíz:** No se verificaba el estado del daemon de Docker, solo se intentaba iniciar sin confirmar.

**Solución implementada:**
- Agregado `sudo systemctl status docker` para diagnóstico.
- Agregado `sudo systemctl start docker` para iniciar.
- Verificación con `systemctl is-active docker` para confirmar que quedó activo.
- Mensajes de error accionables con comandos de diagnóstico.

**Archivo:** `install.sh` (sección 1a)

```bash
sudo systemctl status docker --no-pager 2>&1 | head -10 || true
sudo systemctl start docker
systemctl is-active docker
```

---

### 4. Flag `--env-file` no soportado

**Problema:** El instalador usaba `--env-file` con `docker run`, pero no es soportado en todas las versiones de Docker Compose.

**Causa raíz:** Docker Compose v1 (legacy) no soporta `--env-file` de la misma forma que v2.

**Solución implementada:**
- Nueva función `docker_compose_run()` que intenta `--env-file` primero (v2) y cae al método de exportación si falla.
- Método de exportación: `set -a; . "$ENV_FILE"; set +a` para exportar variables al shell.
- Usa el comando detectado (`$COMPOSE_CMD`) en lugar de hardcodear `docker compose`.

**Archivo:** `install.sh` (función `docker_compose_run`)

```bash
# Método 1: --env-file (v2)
$COMPOSE_CMD --env-file "$ENV_FILE" "${compose_args[@]}"
# Método 2 (fallback): exportar variables
set +a; . "$ENV_FILE"; set -a
$COMPOSE_CMD "${compose_args[@]}"
```

---

### 5. `docker compose` vs `docker-compose`

**Problema:** El script no detectaba qué comando de Compose estaba disponible.

**Causa raíz:** Docker v20.10+ usa `docker compose` (plugin), mientras que versiones anteriores usan `docker-compose` (binario legacy).

**Solución implementada:**
- Detección automática con prioridad:
  1. `docker compose version` (plugin moderno)
  2. `docker-compose --version` (binario legacy)
- La variable `COMPOSE_CMD` se usa en todas las llamadas a Compose.
- Instrucciones para instalar el plugin oficial si ninguno está disponible.

**Archivo:** `install.sh` (sección 1b)

```bash
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
fi
```

---

### 6. Flag incorrecto en Dockerfile

**Problema:** `--no-cache-deps` no existe en pip.

**Causa raíz:** Error tipográfico — la opción correcta de pip es `--no-cache-dir`.

**Solución implementada:**
- Cambiado `--no-cache-deps` a `--no-cache-dir` en el `Dockerfile`.

**Archivo:** `Dockerfile`

```dockerfile
# Antes (incorrecto):
RUN pip install --user --no-cache-deps -r requirements.txt
# Después (correcto):
RUN pip install --user --no-cache-dir -r requirements.txt
```

---

### 7. Permiso denegado (grupo docker)

**Problema:** El usuario no estaba en el grupo `docker`, causando errores de permiso.

**Causa raíz:** Docker requiere que el usuario esté en el grupo `docker` para acceder al socket del daemon sin sudo.

**Solución implementada:**
- Verificación de que el usuario esté en el grupo `docker`.
- Sugerencia de `sudo usermod -aG docker $USER`.
- Alternativa de ejecutar con `sudo ./install.sh`.

**Archivo:** `install.sh` (sección 1a-2)

```bash
if ! id -nG | grep -qw docker; then
    echo "  → Fix: sudo usermod -aG docker \$USER"
    echo "  → Then log out and back in (or run: newgrp docker)"
fi
```

---

### 8. Espacio en disco insuficiente

**Problema:** No se verificaba el espacio mínimo antes de comenzar la instalación.

**Causa raíz:** El script solo advertía si había <10GB, pero no abortaba si el espacio era críticamente bajo.

**Solución implementada:**
- Mínimo absoluto: **5GB** (Ollama + llama3 solo requieren ~4.5GB).
- Si el espacio es <5GB → **ERROR** y aborta.
- Si el espacio es <requerido (estimado + 2GB buffer) → **ADVERTENCIA**.
- Cálculo automático del tamaño estimado de descarga.

**Archivo:** `install.sh` (sección 1d)

```bash
MIN_DISK_GB=5
if [ "$available_gb" -lt "$MIN_DISK_GB" ]; then
    log_error "Only ${available_gb}GB available. Minimum ${MIN_DISK_GB}GB required."
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
```

---

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `install.sh` | Detección de RAM, espacio, Docker, grupo docker, comandos Compose |
| `Dockerfile` | `--no-cache-deps` → `--no-cache-dir` |
| `docker-compose.yml` | Variables de entorno con defaults (`${VAR:-default}`) |
| `README.md` | Sección "Solución de Problemas (Troubleshooting)" |
| `INSTALLER_FIXES.md` | Este documento |

---

## Verificación

Para verificar que las correcciones funcionan:

```bash
# 1. Verificar RAM
grep MemTotal /proc/meminfo
free -h

# 2. Verificar espacio
df -h /

# 3. Verificar Docker
sudo systemctl status docker
docker info

# 4. Verificar Compose
docker compose version || docker-compose --version

# 5. Verificar grupo docker
id -nG | grep docker

# 6. Ejecutar el instalador
./install.sh
```

---

## Notas Adicionales

- El instalador ahora usa `set -euo pipefail` para detenerse en errores críticos.
- Se agregó un trap handler que imprime comandos de recuperación accionables.
- Se agregó detección de instalación previa para permitir continuar con `docker compose up -d`.
- El instalador detecta automáticamente si usar `docker compose` o `docker-compose`.
