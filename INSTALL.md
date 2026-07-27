# ITSMLab — Guía de Instalación On-Premise

> **Versión:** 1.0.0  
> **Última actualización:** Julio 2026  
> **Sistema operativo soportado:** Linux (recomendado), Windows, macOS

---

## Tabla de Contenidos

1. [Requisitos del Sistema](#1-requisitos-del-sistema)
2. [Arquitectura](#2-arquitectura)
3. [Instalación Rápida (1 comando)](#3-instalación-rápida-1-comando)
4. [Instalación Manual Paso a Paso](#4-instalación-manual-paso-a-paso)
5. [Configuración del Modelo de IA](#5-configuración-del-modelo-de-ia)
   - [Opción A: Modelo Local con Ollama](#opción-a-modelo-local-con-ollama)
   - [Opción B: API Externa (DeepSeek / OpenAI)](#opción-b-api-externa-deepseek--openai)
6. [Verificación de la Instalación](#6-verificación-de-la-instalación)
7. [Solución de Problemas](#7-solución-de-problemas)
8. [Mantenimiento](#8-mantenimiento)
9. [Checklist de Configuración](#9-checklist-de-configuración)

---

## 1. Requisitos del Sistema

### Mínimos (modo API externa)

| Recurso | Requisito |
|---------|-----------|
| CPU | 2 cores |
| RAM | 2 GB |
| Disco | 10 GB libres |
| Docker | 24.0+ |
| Docker Compose | 2.20+ |
| SO | Linux (kernel 5.x+), Windows 10/11, macOS 12+ |

### Recomendados (modo local con Ollama)

| Recurso | Requisito |
|---------|-----------|
| CPU | 4 cores |
| RAM | 8 GB (16 GB para modelos >7B) |
| Disco | 20 GB libres (para modelos) |
| GPU | NVIDIA con 4GB+ VRAM (opcional, mejora velocidad) |
| Docker | 24.0+ con NVIDIA Container Toolkit (si usa GPU) |
| Docker Compose | 2.20+ |

### Software Requerido

- **Docker** y **Docker Compose** (incluido en Docker Desktop)
  - [Instalar Docker](https://docs.docker.com/get-docker/)
- **curl** (para verificar la instalación)
- **Git** (opcional, para clonar el repositorio)

---

## 2. Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    Cliente (Browser/API)                  │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTPS (opcional con Caddy)
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
│                       └──────────────────┘             │
└─────────────────────────────────────────────────────────┘
```

### Componentes

| Componente | Descripción | Puerto |
|------------|-------------|--------|
| **ITSMLab App** | API REST principal (FastAPI) | `8000` |
| **PostgreSQL** | Base de datos relacional | `5432` |
| **ChromaDB** | Vector store para RAG | `8001` |
| **Ollama** (opcional) | Servicio de LLM local | `11434` |
| **Caddy** (opcional) | Proxy reverso con HTTPS automático | `80`, `443` |

---

## 3. Instalación Rápida (1 comando)

### Linux / macOS

```bash
# Opción 1: Modelo local con Ollama (recomendado para pruebas)
curl -fsSL https://raw.githubusercontent.com/laral5173/aegis-itsm-agent/main/install.sh | bash

# Opción 2: Con API de DeepSeek
curl -fsSL https://raw.githubusercontent.com/laral5173/aegis-itsm-agent/main/install.sh | \
  DEEPSEEK_API_KEY=sk-xxx LLM_PROVIDER=deepseek bash

# Opción 3: Con API de OpenAI
curl -fsSL https://raw.githubusercontent.com/laral5173/aegis-itsm-agent/main/install.sh | \
  OPENAI_API_KEY=sk-xxx LLM_PROVIDER=openai bash
```

### Windows (PowerShell)

```powershell
# Opción 1: Modelo local con Ollama
.\install.ps1

# Opción 2: Con API de DeepSeek
$env:LLM_PROVIDER="deepseek"; $env:DEEPSEEK_API_KEY="sk-xxx"; .\install.ps1

# Opción 3: Con API de OpenAI
$env:LLM_PROVIDER="openai"; $env:OPENAI_API_KEY="sk-xxx"; .\install.ps1
```

> **Nota:** El instalador automático verifica prerequisitos, crea el archivo `.env`, descarga las imágenes Docker, inicia los contenedores e inicializa la base de conocimiento RAG.

---

## 4. Instalación Manual Paso a Paso

### Paso 1: Clonar el repositorio

```bash
git clone https://github.com/laral5173/aegis-itsm-agent.git
cd aegis-itsm-agent
```

### Paso 2: Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```bash
# Proveedor de LLM: ollama | deepseek | openai
LLM_PROVIDER=ollama

# Si usas DeepSeek:
# DEEPSEEK_API_KEY=sk-tu-api-key

# Si usas OpenAI:
# OPENAI_API_KEY=sk-tu-api-key

# Si usas Ollama (opcional):
# OLLAMA_BASE_URL=http://ollama:11434
# OLLAMA_MODEL=llama3

# Base de datos (valores por defecto para single-node)
DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/itsmlab

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_USE_SERVER=true

# Seguridad (false para pruebas iniciales)
AUTH_REQUIRED=false

# Logging
LOG_LEVEL=INFO
```

### Paso 3: Iniciar los servicios

```bash
# Core (app + postgres + chromadb)
docker compose --env-file .env up --build -d

# Con Ollama local
docker compose --profile ollama --env-file .env up --build -d

# Con HTTPS (requiere dominio configurado)
docker compose --profile caddy --env-file .env up --build -d

# Todo completo
docker compose --profile ollama --profile caddy --env-file .env up --build -d
```

### Paso 4: Inicializar la base de conocimiento

```bash
docker compose exec app python scripts/init_knowledge_base.py
```

### Paso 5: Verificar

```bash
curl http://localhost:8000/v1/health
```

---

## 5. Configuración del Modelo de IA

### Opción A: Modelo Local con Ollama

**¿Qué es Ollama?**  
Ollama es un motor de LLM local que permite correr modelos como Llama 3, Mistral, Phi-3, etc., directamente en la infraestructura del cliente. No requiere conexión a internet para inferencia.

**Requisitos adicionales:**

- 8 GB de RAM mínimo (16 GB recomendado para modelos de 7B parámetros)
- GPU NVIDIA con 4GB+ VRAM (opcional, pero muy recomendado)
- 10 GB de espacio en disco para el modelo base

**Modelos recomendados:**

| Modelo | Tamaño | RAM mínima | Calidad | Uso recomendado |
|--------|--------|------------|---------|-----------------|
| `llama3` (8B) | 4.7 GB | 8 GB | Alta | Producción |
| `llama3:70b` | 40 GB | 48 GB | Muy alta | Producción (GPU necesaria) |
| `mistral` (7B) | 4.1 GB | 8 GB | Alta | Producción |
| `phi3:mini` (3.8B) | 2.3 GB | 4 GB | Media | Pruebas / recursos limitados |
| `qwen2:0.5b` | 352 MB | 2 GB | Baja | Pruebas mínimas |

**Instalación de Ollama (si no se usa el contenedor Docker):**

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows
# Descargar de https://ollama.com/download

# Descargar un modelo
ollama pull llama3

# Iniciar servidor
ollama serve
```

**Configuración en ITSMLab:**

```bash
# .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434   # o http://ollama:11434 si usas Docker
OLLAMA_MODEL=llama3
```

**Ventajas:**
- Sin dependencia de internet
- Sin costos de API por uso
- Datos 100% en infraestructura del cliente
- Latencia predecible (sin red)

**Desventajas:**
- Requiere hardware más potente
- Calidad de respuesta menor que GPT-4/DeepSeek
- Primera inferencia lenta (carga del modelo en memoria)

---

### Opción B: API Externa (DeepSeek / OpenAI)

**¿Qué es?**  
El cliente usa su propia API key de un proveedor de LLM externo. ITSMLab se conecta a la API del proveedor para hacer inferencia.

**Requisitos:**

- API key válida del proveedor elegido
- Conexión a internet desde el servidor de ITSMLab
- Sin requisitos adicionales de hardware

**Proveedores soportados:**

| Proveedor | Variable de entorno | Costo estimado |
|-----------|-------------------|----------------|
| DeepSeek | `DEEPSEEK_API_KEY` | ~$0.14/1M tokens (entrada) |
| OpenAI (GPT-4o mini) | `OPENAI_API_KEY` | ~$0.15/1M tokens (entrada) |
| OpenAI (GPT-4o) | `OPENAI_API_KEY` | ~$2.50/1M tokens (entrada) |

**Configuración:**

```bash
# Para DeepSeek
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-tu-api-key-aqui

# Para OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-tu-api-key-aqui
```

**Ventajas:**
- Sin requisitos de hardware especializado
- Mejor calidad de respuesta (especialmente GPT-4o)
- Sin consumo de recursos locales para inferencia

**Desventajas:**
- Dependencia de conexión a internet
- Costos por uso (pueden acumularse)
- Datos enviados a servidores externos
- Latencia de red variable

---

## 6. Verificación de la Instalación

### Health Check

```bash
curl http://localhost:8000/v1/health
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "llm_provider": "ollama",
  "database": "connected",
  "chromadb": "connected"
}
```

### Diagnóstico de prueba

```bash
curl -X POST http://localhost:8000/v1/diagnose \
  -H "Content-Type: application/json" \
  -d '{"alert": "CPU usage at 95% on server web-01"}'
```

### Documentación interactiva

Abre en tu navegador: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 7. Solución de Problemas

### Problema: El contenedor de Ollama no inicia

```bash
# Verificar logs
docker compose logs ollama

# Verificar si hay GPU disponible
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# Sin GPU, funciona en CPU (más lento)
# Editar docker-compose.yml y quitar la sección 'deploy.resources'
```

### Problema: "LLM provider not configured"

```bash
# Verificar que el .env tiene las variables correctas
cat .env | grep -E "LLM_PROVIDER|API_KEY"

# Si usas Ollama, asegúrate de que el servicio esté corriendo
curl http://localhost:11434/api/tags
```

### Problema: Base de conocimiento no inicializada

```bash
# Inicializar manualmente
docker compose exec app python scripts/init_knowledge_base.py

# Verificar estado
docker compose exec app python -c "
from app.rag.knowledge_base import get_knowledge_base_stats
print(get_knowledge_base_stats())
"
```

### Problema: Error de conexión a PostgreSQL

```bash
# Verificar que PostgreSQL está listo
docker compose logs postgres

# Verificar conectividad
docker compose exec app python -c "
from app.database import engine
engine.connect()
print('Database connected')
"
```

### Problema: Puerto 8000 ya en uso

```bash
# Cambiar el puerto en docker-compose.yml
# Cambiar "8000:8000" a "8080:8000"
# Luego acceder en http://localhost:8080
```

---

## 8. Mantenimiento

### Actualizar ITSMLab

```bash
# Descargar última versión
git pull

# Reconstruir y reiniciar
docker compose up --build -d

# Ejecutar migraciones de base de datos (si las hay)
docker compose exec app alembic upgrade head
```

### Ver logs

```bash
# Todos los servicios
docker compose logs -f

# Solo la app
docker compose logs -f app

# Solo Ollama
docker compose logs -f ollama
```

### Respaldos

```bash
# Respaldar base de datos PostgreSQL
docker compose exec postgres pg_dump -U postgres itsmlab > backup_$(date +%Y%m%d).sql

# Respaldar ChromaDB
tar -czf chromadb_backup_$(date +%Y%m%d).tar.gz chromadb_data/
```

### Detener servicios

```bash
# Detener todo
docker compose down

# Detener y eliminar volúmenes (cuidado: borra datos)
docker compose down -v
```

---

## 9. Checklist de Configuración

### Pre-instalación

- [ ] Verificar que Docker 24.0+ está instalado
- [ ] Verificar que Docker Compose 2.20+ está instalado
- [ ] Verificar RAM disponible (mínimo 2 GB, recomendado 8 GB)
- [ ] Verificar espacio en disco (mínimo 10 GB)
- [ ] Verificar conectividad a internet (si usa API externa)
- [ ] Verificar GPU disponible (opcional, para Ollama)
- [ ] Decidir modo de LLM: local (Ollama) o API externa
- [ ] Obtener API key (si aplica)

### Instalación

- [ ] Clonar repositorio o descargar archivos
- [ ] Crear archivo `.env` con configuración
- [ ] Ejecutar `docker compose up -d`
- [ ] Verificar que todos los contenedores están "running"
- [ ] Ejecutar `init_knowledge_base.py`
- [ ] Verificar health endpoint: `curl localhost:8000/v1/health`
- [ ] Probar diagnóstico: `curl -X POST localhost:8000/v1/diagnose`

### Post-instalación

- [ ] Configurar HTTPS (Caddy o proxy externo)
- [ ] Configurar autenticación (`AUTH_REQUIRED=true`)
- [ ] Configurar respaldos automáticos
- [ ] Configurar monitoreo (logs, métricas)
- [ ] Probar con alertas reales
- [ ] Documentar configuración específica del cliente

---

> **¿Problemas?** Abre un issue en [GitHub](https://github.com/laral5173/aegis-itsm-agent/issues) o contacta al equipo de soporte.
