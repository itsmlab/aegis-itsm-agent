# 📘 AEGIS — Guía de Aprendizaje (Learning Guide)

> *Bienvenido a AEGIS. Esta guía está diseñada para cualquier persona que quiera entender cómo funciona el sistema, sin importar si eres desarrollador, DevOps, PM o simplemente tienes curiosidad. Todo está explicado en lenguaje sencillo, con analogías y ejemplos prácticos.*

> *"El conocimiento para resolver cualquier incidente ya existe. Solo hay que saber dónde buscarlo."*

---

## Índice

1. [🧠 Glosario de Términos Técnicos](#1--glosario-de-términos-técnicos)
2. [🏗️ La Arquitectura (El Hospital de Incidentes)](#2--la-arquitectura-el-hospital-de-incidentes)
3. [🔄 El Viaje de una Alerta (Flujo Completo)](#3--el-viaje-de-una-alerta-flujo-completo)
4. [📂 Conociendo los Archivos Clave](#4--conociendo-los-archivos-clave)
5. [🛠️ Comandos Útiles (Tu Caja de Herramientas)](#5--comandos-útiles-tu-caja-de-herramientas)
6. [❓ Preguntas Frecuentes](#6--preguntas-frecuentes)

---

## 1. 🧠 Glosario de Términos Técnicos

Cada término tiene una ficha con tres partes:
- **¿Qué es?** — Explicación simple, como para un compañero
- **¿Para qué sirve en AEGIS?** — Su propósito en el proyecto
- **🔍 Lo encuentras en:** — Archivo(s) donde se usa

---

### FastAPI

**¿Qué es?** Un framework moderno de Python para crear APIs REST. Es rápido (como su nombre dice), fácil de usar y genera documentación automática.

**¿Para qué sirve en AEGIS?** Es el corazón del backend. Define todos los endpoints (`/v1/alert`, `/v1/health`, etc.), valida los datos que entran y salen, y genera la documentación interactiva en `/docs`.

**🔍 Lo encuentras en:** `app/main.py`, `app/routers/alerts.py`, `app/routers/admin.py`

---

### Uvicorn

**¿Qué es?** El "motor" que hace correr FastAPI. Es un servidor ASGI (la versión moderna de WSGI) que permite que Python maneje muchas conexiones simultáneas.

**¿Para qué sirve en AEGIS?** Cuando ejecutas `python app/main.py` o `uvicorn app.main:app --reload`, Uvicorn es quien levanta el servidor y empieza a escuchar peticiones en `http://localhost:8000`.

**🔍 Lo encuentras en:** `app/main.py` (línea 118: `uvicorn.run(...)`)

---

### Endpoint / Ruta

**¿Qué es?** Cada "dirección URL" que expone la API. Es como una puerta específica en un edificio: cada puerta lleva a un lugar diferente.

**¿Para qué sirve en AEGIS?** Define los puntos de entrada del sistema:
- `POST /v1/alert` → Enviar una alerta para diagnóstico
- `GET /v1/health` → Verificar que el sistema está vivo
- `GET /v1/stats` → Ver estadísticas de uso
- `POST /v1/admin/tenants` → Crear un nuevo cliente

**🔍 Lo encuentras en:** `app/routers/alerts.py`, `app/routers/admin.py`

---

### Pydantic

**¿Qué es?** Un "control de calidad" para datos JSON. Define exactamente qué campos se esperan, de qué tipo, y si son obligatorios u opcionales. Si alguien envía datos incorrectos, Pydantic los rechaza antes de que lleguen a la lógica del programa.

**¿Para qué sirve en AEGIS?** Define los modelos de datos: `AlertRequest` (lo que entra), `DiagnosisResponse` (lo que sale), `CreateTenantRequest` (para crear clientes). También se usa para la configuración del sistema con `pydantic-settings`.

**🔍 Lo encuentras en:** `app/config.py`, `app/routers/alerts.py`, `app/routers/admin.py`

---

### SQLAlchemy

**¿Qué es?** Un "traductor" entre Python y las bases de datos relacionales. Te permite trabajar con bases de datos usando objetos de Python en lugar de escribir SQL directamente.

**¿Para qué sirve en AEGIS?** Gestiona toda la información persistente: tenants (clientes), API keys, y registros de uso. Soporta PostgreSQL en producción y SQLite en desarrollo.

**🔍 Lo encuentras en:** `app/database.py`, `app/models.py`

---

### ORM (Object-Relational Mapping)

**¿Qué es?** La técnica de representar tablas de bases de datos como clases de Python. Cada fila de la tabla es un objeto, cada columna es un atributo.

**¿Para qué sirve en AEGIS?** Las clases `Tenant`, `ApiKey` y `UsageRecord` son modelos ORM. Cuando haces `db.query(Tenant).first()`, SQLAlchemy traduce eso a SQL, consulta la BD, y te devuelve un objeto Python.

**🔍 Lo encuentras en:** `app/models.py`

---

### PostgreSQL

**¿Qué es?** Una base de datos relacional de código abierto, muy potente y confiable. Es la base de datos principal del proyecto.

**¿Para qué sirve en AEGIS?** Almacena los datos operativos: información de los clientes (tenants), sus API keys, y el registro de uso para facturación.

**🔍 Lo encuentras en:** `app/config.py` (línea 42: `DATABASE_URL`), `docker-compose.yml`

---

### SQLite

**¿Qué es?** Una base de datos que no necesita servidor. Todo se guarda en un solo archivo local. Es ideal para desarrollo y pruebas.

**¿Para qué sirve en AEGIS?** Es el "plan B" automático. Si no tienes PostgreSQL instalado, el sistema crea un archivo `aegis_dev.db` y funciona igual. Así puedes desarrollar sin necesidad de instalar PostgreSQL.

**🔍 Lo encuentras en:** `app/database.py` (función `_create_sqlite_engine()`)

---

### Alembic

**¿Qué es?** Un "control de versiones" para la base de datos. Así como Git guarda cambios en tu código, Alembic guarda cambios en el esquema de la BD.

**¿Para qué sirve en AEGIS?** Cuando agregues un campo nuevo a un modelo o crees una tabla nueva, Alembic genera una "migración" que puede aplicarse a cualquier base de datos (desarrollo, pruebas, producción).

**🔍 Lo encuentras en:** `alembic/` (carpeta), `alembic.ini`

---

### ChromaDB

**¿Qué es?** Una base de datos especial que entiende el *significado* de los textos, no solo las palabras exactas. Es una "base de datos vectorial" (Vector DB).

**¿Para qué sirve en AEGIS?** Almacena los 77 tickets históricos como vectores (embeddings). Cuando llega un ticket nuevo, ChromaDB busca los tickets históricos más parecidos por significado, no por palabras exactas.

**🔍 Lo encuentras en:** `classifier.py` (línea 137: `chromadb.PersistentClient`), `tickets_db/` (carpeta de datos)

---

### Embedding

**¿Qué es?** Imagina que conviertes una frase en un código numérico que captura su "esencia" o "significado". Así, "olvidé mi contraseña" y "no puedo iniciar sesión" terminan con códigos parecidos, aunque usen palabras distintas.

**¿Para qué sirve en AEGIS?** El clasificador convierte cada ticket a un embedding (un vector de 384 números) y busca tickets históricos con embeddings similares. Es como buscar por "olor" en lugar de por etiquetas.

**🔍 Lo encuentras en:** `classifier.py` (línea 133: `model.encode(description)`)

---

### SentenceTransformers

**¿Qué es?** Una librería de Python que genera embeddings a partir de texto. Toma una frase y devuelve un vector numérico.

**¿Para qué sirve en AEGIS?** Es la herramienta que usa el clasificador para convertir tickets a vectores. Usamos el modelo `all-MiniLM-L6-v2` porque es pequeño, rápido y da buenos resultados.

**🔍 Lo encuentras en:** `classifier.py` (línea 12: `from sentence_transformers import SentenceTransformer`)

---

### all-MiniLM-L6-v2

**¿Qué es?** El modelo concreto de embeddings que usamos. Es un modelo pequeño (80 MB) que genera vectores de 384 dimensiones. "Mini" porque es ligero, "LM" porque es un modelo de lenguaje.

**¿Para qué sirve en AEGIS?** Es el cerebro del clasificador. Convierte texto en vectores numéricos que ChromaDB puede buscar.

**🔍 Lo encuentras en:** `classifier.py` (línea 34: `EMBEDDING_MODEL = "all-MiniLM-L6-v2"`)

---

### Vector DB (Base de Datos Vectorial)

**¿Qué es?** Una base de datos que busca por "parecido semántico" en lugar de por coincidencia exacta. Es como buscar "películas parecidas a esta" en lugar de "películas que tengan la palabra X en el título".

**¿Para qué sirve en AEGIS?** ChromaDB es nuestra Vector DB. Cuando clasificamos un ticket, buscamos los tickets históricos más parecidos por significado, no por palabras clave.

**🔍 Lo encuentras en:** `classifier.py` (líneas 307-310: `collection.query(query_embeddings=[...])`)

---

### RAG (Retrieval-Augmented Generation)

**¿Qué es?** Una técnica que combina dos pasos: primero **busca** información relevante en una base de conocimiento, y luego **genera** una respuesta usando un LLM con esa información como contexto. Es como un estudiante que primero consulta sus apuntes y luego responde el examen.

**¿Para qué sirve en AEGIS?** El orquestador L3/L4 funciona con RAG:
1. **Busca:** Carga `AEGIS_PATTERNS.md` (los 20 patrones de incidentes)
2. **Genera:** Envía la alerta + los patrones al LLM (DeepSeek)
3. **Responde:** El LLM identifica el patrón más parecido y genera un diagnóstico personalizado

**🔍 Lo encuentras en:** `orchestrator.py` (líneas 89-95: el prompt incluye la alerta + la knowledge base)

---

### LLM (Large Language Model)

**¿Qué es?** Un modelo de inteligencia artificial entrenado con enormes cantidades de texto. Puede entender lenguaje, responder preguntas, generar código, etc. Ejemplos: GPT-4, DeepSeek, Llama.

**¿Para qué sirve en AEGIS?** Es el "cerebro" del diagnóstico L3/L4. Recibe la alerta y los patrones de incidentes, los analiza, y genera un diagnóstico y un script de remediación.

**🔍 Lo encuentras en:** `app/llm/` (carpeta completa), `orchestrator.py`

---

### DeepSeek

**¿Qué es?** Un LLM creado por DeepSeek (empresa china). Es muy económico ($0.14 por millón de tokens) y tiene buena calidad. Usa una API compatible con OpenAI.

**¿Para qué sirve en AEGIS?** Es el LLM que usamos por defecto para el diagnóstico L3/L4. Su bajo costo permite ejecutar muchos diagnósticos sin gastar una fortuna.

**🔍 Lo encuentras en:** `app/llm/deepseek.py`, `app/config.py` (línea 33: `DEEPSEEK_MODEL = "deepseek-chat"`)

---

### OpenAI-compatible API

**¿Qué es?** Un formato estándar de comunicación con LLMs. Si un proveedor de IA dice "tiene API compatible con OpenAI", significa que puedes usar el mismo código que usarías con ChatGPT, solo cambiando la URL y la API key.

**¿Para qué sirve en AEGIS?** DeepSeek, OpenAI y Ollama (local) usan el mismo formato de API. Esto permite cambiar de proveedor solo cambiando una variable en `.env`.

**🔍 Lo encuentras en:** `app/llm/openai_compat.py`, `app/llm/factory.py`

---

### Multi-tenancy

**¿Qué es?** Una arquitectura donde un solo sistema sirve a múltiples clientes (tenants), manteniendo sus datos aislados. Como un edificio de departamentos: mismo edificio, diferentes departamentos, cada uno con su propia llave.

**¿Para qué sirve en AEGIS?** Permite que varios clientes usen la misma instancia de AEGIS, cada uno con su propia API key, su propio plan (Shield/Guard/Fortress), y sus propios límites de uso.

**🔍 Lo encuentras en:** `app/models.py` (clase `Tenant`), `app/dependencies.py` (función `get_current_tenant()`)

---

### Tenant

**¿Qué es?** Cada cliente en un sistema multi-tenant. Es una organización que usa el servicio.

**¿Para qué sirve en AEGIS?** Cada tenant tiene:
- Un `id` único (UUID)
- Un `slug` identificador (ej: "acme-corp")
- Un `plan` (shield, guard, fortress)
- Una o más `ApiKey` para autenticarse
- Sus propios `UsageRecord` para facturación

**🔍 Lo encuentras en:** `app/models.py` (clase `Tenant`)

---

### L1/L2

**¿Qué es?** Los niveles 1 y 2 de soporte técnico. Son tickets rutinarios y recurrentes: problemas de acceso, cómo hacer algo, licencias, configuraciones simples. Representan el 60-70% del volumen de soporte.

**¿Para qué sirve en AEGIS?** El clasificador híbrido (ChromaDB + keywords) está diseñado para automatizar estos tickets. Ejemplos:
- "No puedo iniciar sesión" → ACCESS
- "¿Cómo configuro mi firma de correo?" → HOWTO
- "Mi licencia de Office expiró" → LICENSE

**🔍 Lo encuentras en:** `classifier.py`, `app/services/classifier_service.py`

---

### L3/L4

**¿Qué es?** Los niveles 3 y 4 de soporte técnico. Son incidentes críticos: caídas de servidor, fallos de base de datos, problemas de red, outages. Requieren diagnóstico profundo y experiencia técnica.

**¿Para qué sirve en AEGIS?** El orquestador con RAG + LLM está diseñado para diagnosticar estos incidentes. Ejemplos:
- "El servidor de BD no responde, timeout en todas las conexiones" → AEGIS-005
- "Latencia de p99 subió de 50ms a 30s después del deploy" → AEGIS-001

**🔍 Lo encuentras en:** `orchestrator.py`, `app/services/orchestrator_service.py`

---

### Hybrid Classifier

**¿Qué es?** Un clasificador que usa dos métodos en lugar de uno solo. Es como tener un plan B por si el plan A falla.

**¿Para qué sirve en AEGIS?** El clasificador primero intenta con búsqueda vectorial (semántica). Si la confianza es baja (< 45%), usa palabras clave como respaldo. Esto asegura que siempre tengamos una respuesta, incluso para tickets con vocabulario inusual.

**🔍 Lo encuentras en:** `classifier.py` (función `classify_ticket()`, líneas 295-394)

---

### Keyword Fallback

**¿Qué es?** El "plan B" del clasificador. Si la búsqueda vectorial no encuentra tickets parecidos con suficiente confianza, se usa un sistema de palabras clave para determinar la categoría.

**¿Para qué sirve en AEGIS?** Si alguien escribe un ticket con palabras muy específicas que no aparecen en los tickets históricos, el sistema de vectores puede no reconocerlo. Las palabras clave actúan como red de seguridad.

**🔍 Lo encuentras en:** `classifier.py` (función `classify_by_keywords()`, líneas 253-293)

---

### Confidence Threshold

**¿Qué es?** Un límite mínimo de confianza. Si el sistema no está lo suficientemente seguro de su respuesta, prefiere decir "no sé" antes de arriesgarse a dar una respuesta incorrecta.

**¿Para qué sirve en AEGIS?** El umbral está en 45% (0.45). Si la confianza del clasificador es menor, devuelve UNKNOWN. Esto reduce los falsos positivos: es mejor que un ticket vaya a revisión humana a que se clasifique mal.

**🔍 Lo encuentras en:** `classifier.py` (línea 36: `CONFIDENCE_THRESHOLD = 0.45`)

---

### Postmortem

**¿Qué es?** Un análisis detallado después de un incidente grave. Documenta qué ocurrió, por qué ocurrió, cómo se detectó, cómo se resolvió, y qué se hará para que no vuelva a pasar.

**¿Para qué sirve en AEGIS?** Los 20 patrones de `AEGIS_PATTERNS.md` están basados en postmortems reales de empresas como AWS, Cloudflare, Google, GitHub, Netflix y Azure. Cada patrón captura las lecciones aprendidas de un incidente real.

**🔍 Lo encuentras en:** `AEGIS_PATTERNS.md` (cada patrón tiene sección "Source" con el postmortem original)

---

### Pattern Knowledge Base

**¿Qué es?** Una biblioteca de patrones de incidentes documentados. Cada patrón describe: síntomas, diagnóstico y solución.

**¿Para qué sirve en AEGIS?** Es el archivo `AEGIS_PATTERNS.md` con 20 patrones. El orquestador lo usa como contexto para el LLM. Cuando llega una alerta, el LLM compara los síntomas contra cada patrón y elige el más parecido.

**🔍 Lo encuentras en:** `AEGIS_PATTERNS.md` (1142 líneas, 20 patrones)

---

### Socket Mode (Slack)

**¿Qué es?** Un modo de conexión de Slack que no requiere exponer un servidor público. El bot se conecta a Slack a través de un "socket" (canal de comunicación) iniciado desde el propio bot.

**¿Para qué sirve en AEGIS?** El Slack Bot (`slack_bot.py`) usa Socket Mode. Esto significa que puedes ejecutarlo en tu máquina local o en un servidor privado, sin necesidad de configurar URLs públicas ni HTTPS.

**🔍 Lo encuentras en:** `slack_bot.py` (línea 29: `from slack_bolt.adapter.socket_mode import SocketModeHandler`)

---

### Webhook

**¿Qué es?** Un "timbre" que suena cuando ocurre un evento. Un sistema A envía una petición HTTP a un sistema B cuando algo importante sucede.

**¿Para qué sirve en AEGIS?** PagerDuty envía alertas a AEGIS mediante un webhook (`POST /pagerduty`). Cuando ocurre un incidente en PagerDuty, este "toca el timbre" de AEGIS con todos los detalles.

**🔍 Lo encuentras en:** `integration_module.py` (línea 450: `@app.post("/pagerduty")`)

---

### X-API-Key

**¿Qué es?** Una "cédula de identidad" para acceder a la API. Es una cadena secreta que identifica a quien hace la petición.

**¿Para qué sirve en AEGIS?** Cada tenant tiene una o más API keys. Cuando alguien hace una petición a `/v1/alert`, debe incluir el header `X-API-Key: aeg_live_...`. El sistema busca la key en la base de datos, identifica al tenant, y verifica su plan y cuota.

**🔍 Lo encuentras en:** `app/dependencies.py` (función `get_current_tenant()`)

---

### Docker

**¿Qué es?** Una plataforma para ejecutar aplicaciones en "contenedores". Un contenedor es como una máquina virtual liviana que incluye todo lo necesario para que la aplicación funcione.

**¿Para qué sirve en AEGIS?** El `docker-compose.yml` levanta tres contenedores: la app de AEGIS, PostgreSQL y ChromaDB. Con un solo comando (`docker-compose up`) tienes todo el sistema funcionando.

**🔍 Lo encuentras en:** `Dockerfile`, `docker-compose.yml`

---

### Sandbox (Script Executor)

**¿Qué es?** Un entorno aislado y seguro para ejecutar código sin riesgo. Es como un "patio de juegos" donde los scripts pueden correr sin afectar el sistema real.

**¿Para qué sirve en AEGIS?** Es una funcionalidad planeada (Phase 3 del roadmap). El orquestador genera scripts de remediación, pero antes de ejecutarlos en producción, pasan por un sandbox donde un humano los revisa y aprueba.

**🔍 Lo encuentras en:** `ARCHITECTURE.md` (sección "Script Executor (Phase 3)")

---

## 2. 🏗️ La Arquitectura (El Hospital de Incidentes)

Imagina que AEGIS es un **hospital especializado en incidentes IT**. Cada área del hospital tiene una función específica:

```
┌──────────────────────────────────────────────────────────────┐
│                     🏥 AEGIS HOSPITAL                        │
│                                                              │
│  🚪 RECEPCIÓN                    📋 ADMINISTRACIÓN          │
│  (app/main.py + routers/)        (app/routers/admin.py)     │
│  • Recibe al paciente            • Registra nuevos clientes  │
│  • Pide identificación           • Genera credenciales       │
│  • Verifica seguro               • Consulta historial        │
│                                                              │
│  🩺 TRIAGE                          💊 FARMACIA             │
│  (app/services/)                    (app/llm/)              │
│  • ¿Es simple? → Clasificador       • DeepSeek (default)    │
│  • ¿Es grave? → Orquestador         • OpenAI (alternativo)  │
│                                      • Ollama (local)        │
│                                                              │
│  📋 EXPEDIENTES                     📚 BIBLIOTECA MÉDICA    │
│  (app/database.py + models.py)      (AEGIS_PATTERNS.md)     │
│  • Datos de pacientes (tenants)     • 20 casos documentados  │
│  • Historial de visitas (usage)     • Síntomas + diagnóstico │
│                                      • Scripts de remediación│
│                                                              │
│  🧰 CONFIGURACIÓN                                            │
│  (app/config.py)                                             │
│  • ¿Qué medicamentos tenemos?                                │
│  • ¿Cuál es nuestro horario?                                 │
│  • ¿A quién llamamos en caso de emergencia?                  │
└──────────────────────────────────────────────────────────────┘
```

---

### 🚪 Recepción — Capa de API (`app/main.py` + `app/routers/`)

**¿Qué hace?** Es la puerta de entrada. Todo lo que entra o sale de AEGIS pasa por aquí.

- Recibe peticiones HTTP (alertas, consultas de salud, administración)
- Valida que los datos sean correctos (Pydantic)
- Identifica al cliente (X-API-Key)
- Verifica que tenga cobertura (plan y cuota)
- Enruta al servicio correspondiente

**Archivos clave:**
- `app/main.py` — Punto de entrada, configura la app, CORS, manejo de errores
- `app/routers/alerts.py` — Endpoints de alertas: `POST /v1/alert`, `GET /v1/health`, `GET /v1/stats`
- `app/routers/admin.py` — Endpoints de administración: crear tenants, generar API keys

**Para explorar más:** Abre `http://localhost:8000/docs` cuando el servidor esté corriendo. Ahí ves todos los endpoints documentados.

---

### 🩺 Triage — Capa de Servicios (`app/services/`)

**¿Qué hace?** Es el área de diagnóstico. Determina la gravedad del incidente y aplica el tratamiento adecuado.

- **ClassifierService** — Para tickets simples (L1/L2): busca en el historial, clasifica por categoría, sugiere resolución
- **OrchestratorService** — Para incidentes críticos (L3/L4): consulta la biblioteca de patrones, llama al LLM, genera diagnóstico
- **BillingService** — Controla cuántos incidentes ha usado cada cliente este mes

**Archivos clave:**
- `app/services/classifier_service.py` — Clasificador multi-tenant
- `app/services/orchestrator_service.py` — Orquestador con LLM
- `app/services/billing_service.py` — Control de uso y facturación

**Para explorar más:** Revisa cómo `alerts.py` llama a estos servicios. La función `process_alert()` es el mejor punto de partida.

---

### 💊 Farmacia — Capa de LLM (`app/llm/`)

**¿Qué hace?** Es donde se guardan los "medicamentos" (modelos de lenguaje). Dependiendo de lo que tenga configurado el hospital, usa uno u otro.

- **DeepSeek** — El medicamento por defecto (económico y efectivo)
- **OpenAI** — Alternativa (GPT-4o-mini, etc.)
- **Ollama** — Para ejecutar modelos localmente (Llama 3, etc.)

Todos los medicamentos vienen en el mismo formato (OpenAI-compatible), así que cambiarlos es tan simple como cambiar una variable en `.env`.

**Archivos clave:**
- `app/llm/base.py` — La "receta" (interfaz) que todos los medicamentos deben seguir
- `app/llm/deepseek.py` — Implementación para DeepSeek
- `app/llm/openai_compat.py` — Implementación para OpenAI y Ollama
- `app/llm/factory.py` — El "farmacéutico" que elige el medicamento correcto

**Para explorar más:** Mira `factory.py` para entender cómo se selecciona el proveedor según `LLM_PROVIDER`.

---

### 📋 Expedientes — Capa de Base de Datos (`app/database.py` + `app/models.py`)

**¿Qué hace?** Guarda toda la información de los pacientes (clientes) y su historial de visitas.

- **Tenant** — Cada cliente: su nombre, plan, si está activo
- **ApiKey** — Las credenciales de cada cliente (guardadas como hash por seguridad)
- **UsageRecord** — Registro de cada diagnóstico: cuándo, qué endpoint, cuántos tokens usó

**Archivos clave:**
- `app/database.py` — Conexión a la BD, con fallback automático PostgreSQL → SQLite
- `app/models.py` — Las clases que representan las tablas

**Para explorar más:** Si tienes PostgreSQL, conéctate y explora las tablas `tenants`, `api_keys`, `usage_records`.

---

### 📚 Biblioteca Médica — Knowledge Base (`AEGIS_PATTERNS.md`)

**¿Qué hace?** Almacena el conocimiento de incidentes pasados. Son 20 casos documentados de incidentes reales en empresas como AWS, Cloudflare, Google, GitHub, Netflix y Azure.

Cada caso incluye:
- **Síntomas** — ¿Qué señales de alerta se ven?
- **Diagnóstico** — ¿Qué ocurrió realmente?
- **Script de remediación** — ¿Cómo se solucionó?

**Archivo clave:**
- `AEGIS_PATTERNS.md` — 1142 líneas, 20 patrones

**Para explorar más:** Abre el archivo y lee 2 o 3 patrones. Notarás que todos siguen la misma estructura. Esa consistencia es lo que permite al LLM entenderlos y usarlos.

---

### 🧰 Configuración — Capa de Settings (`app/config.py`)

**¿Qué hace?** Centraliza toda la configuración del sistema en un solo lugar. Es como el cuadro de mandos del hospital.

Aquí se define:
- Rutas de archivos (dónde está `AEGIS_PATTERNS.md`, `tickets_dataset.csv`)
- Modelos (qué embedding model, qué LLM usar)
- Conexiones (URL de PostgreSQL, host de ChromaDB)
- Límites (cuántos incidentes por mes en plan Shield)
- Flags de operación (debug, autenticación requerida)

**Archivo clave:**
- `app/config.py` — Clase `Settings` con pydantic-settings

**Para explorar más:** Revisa las variables en `app/config.py` y compáralas con `.env.example`. Verás cómo las variables de entorno sobreescriben los valores por defecto.

---

## 3. 🔄 El Viaje de una Alerta (Flujo Completo)

Vamos a seguir dos alertas desde que entran hasta que sale el diagnóstico. Como un "día en la vida de un ticket".

---

### Escenario 1: "No puedo iniciar sesión" (L1/L2)

**Paso 1 — Llega el paciente**

Alguien envía una alerta a la recepción:

```bash
curl -X POST http://localhost:8000/v1/alert \
  -H "Content-Type: application/json" \
  -d '{
    "source": "manual",
    "severity": "low",
    "title": "No puedo iniciar sesión",
    "description": "Me sale error 403 cuando intento entrar a la aplicación"
  }'
```

**Paso 2 — Identificación**

La recepción (endpoint `POST /v1/alert`) pide identificación. Lee el header `X-API-Key`. Si no hay (modo desarrollo), usa el tenant "default". Si hay, busca la key en la base de datos y obtiene el tenant.

**Paso 3 — Verificación de seguro**

El sistema revisa el plan del tenant. Si es "shield", cuenta cuántos incidentes ha usado este mes. Si ya llegó al límite (50), responde con HTTP 429: "Ya no te quedan consultas este mes, actualiza tu plan".

**Paso 4 — Triage: ¿Es grave?**

La función `route_severity()` analiza:
- `severity = "low"` → No es crítica
- La descripción no contiene palabras como "outage", "down", "500" → No es crítica

Resultado: **L1/L2** → Va al clasificador.

**Paso 5 — Diagnóstico L1/L2**

El clasificador (`classifier_service.classify()`) hace lo siguiente:

1. **Convierte el texto a embedding:** Toma "No puedo iniciar sesión, me sale error 403" y lo convierte en un vector de 384 números que representa su significado.

2. **Busca en ChromaDB:** Busca los 5 tickets históricos más parecidos por significado. Encuentra tickets como:
   - "User cannot log in, error 403 forbidden" → ACCESS (distancia: 0.15)
   - "Need access to Salesforce, account not provisioned" → ACCESS (distancia: 0.32)
   - "Password reset requested" → ACCESS (distancia: 0.41)

3. **Votación ponderada:** Cada ticket "vota" por su categoría, pero los más cercanos tienen más peso. ACCESS gana con 88.4% de confianza.

4. **Verifica umbral:** 88.4% > 45% → Confianza alta, no necesita keyword fallback.

5. **Prepara respuesta:** Toma la resolución del ticket más cercano: "Added user to correct AD group, cleared cache".

**Paso 6 — Registro de la visita**

Se guarda un `UsageRecord` en la base de datos: "El tenant X usó el endpoint /v1/alert el 20/06/2026".

**Paso 7 — Respuesta**

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

**Tiempo total: ~2 segundos.** El ticket está clasificado y tiene una resolución sugerida.

---

### Escenario 2: "El servidor de base de datos se cayó" (L3/L4)

**Paso 1 — Llega el paciente**

PagerDuty envía una alerta crítica:

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

**Pasos 2 y 3 — Identificación y verificación de seguro**

Igual que en el escenario anterior.

**Paso 4 — Triage: ¿Es grave?**

`route_severity()` detecta:
- `severity = "critical"` → ¡Alerta roja!
- La descripción contiene "timeout", "500" → Confirmado

Resultado: **L3/L4** → Va al orquestador.

**Paso 5 — Diagnóstico L3/L4**

El orquestador (`orchestrator_service.diagnose()`) hace lo siguiente:

1. **Carga la biblioteca médica:** Lee `AEGIS_PATTERNS.md` completo (1142 líneas, 20 patrones).

2. **Construye el prompt:** Prepara un mensaje para el LLM con:
   - **System prompt:** "Eres Aegis, un agente autónomo de triage. Compara los síntomas de la alerta contra los patrones. Responde SOLO con JSON."
   - **User prompt:** La alerta del usuario + los 20 patrones completos.

3. **LLM analiza:** DeepSeek recibe el prompt, compara los síntomas de la alerta ("500 errors", "connection pool exhausted", "replication lag 300s") contra cada patrón, y determina que el más parecido es **AEGIS-005 (Database Failover)**.

4. **Genera respuesta:** DeepSeek devuelve un JSON con:
   - `id`: "AEGIS-005"
   - `name`: "Database Failover"
   - `diagnosis`: Explicación adaptada a la alerta específica
   - `script`: Script bash de remediación del patrón

**Paso 6 — Registro de la visita**

Se guarda un `UsageRecord` en la base de datos.

**Paso 7 — Respuesta**

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

**Tiempo total: ~10-15 segundos.** El incidente crítico tiene un diagnóstico y un script de remediación listos.

---

## 4. 📂 Conociendo los Archivos Clave

Cada archivo se presenta como un "personaje" del proyecto. Aquí te explicamos **qué hace**, **cómo se usa** y **qué contiene**.

---

### 4.1 `classifier.py` — El Clasificador

```
🎭 Personalidad: El recepcionista experto en clasificar tickets
```

**¿Qué hace?**
Toma la descripción de un ticket y la compara con 77 tickets históricos para determinar la categoría y sugerir una solución. Usa un sistema híbrido: primero busca por significado (vectores) y si no está seguro, usa palabras clave.

**¿Cómo se usa?**
- **Como librería:** Otros archivos importan `classify_ticket()` para clasificar tickets.
- **Como programa independiente:** `python classifier.py` abre un menú interactivo:
  - Opción 1: Clasificar un ticket nuevo
  - Opción 2: Añadir un ticket resuelto (para enseñarle)
  - Opción 3: Ver estadísticas de la base de datos
  - Opción 4: Salir

**¿Qué contiene?**
- **8 categorías** con palabras clave: ACCESS, DATABASE, LICENSE, API, PERFORMANCE, NETWORK, SECURITY, HOWTO
- **Modelo de embeddings:** `all-MiniLM-L6-v2` (convierte texto a vectores de 384 números)
- **ChromaDB:** Base de datos vectorial con los 77 tickets históricos
- **Sistema de votación ponderada:** Los tickets más parecidos tienen más peso en la decisión
- **Keyword fallback:** Plan B por si la búsqueda vectorial no da buena confianza

**🔍 Archivo:** `classifier.py` (529 líneas)

---

### 4.2 `orchestrator.py` — El Diagnosticador

```
🎭 Personalidad: El médico especialista en incidentes graves
```

**¿Qué hace?**
Toma la descripción de una alerta crítica, la compara con 20 patrones de incidentes reales, y genera un diagnóstico + script de remediación usando un LLM (DeepSeek).

**¿Cómo se usa?**
- **Como librería:** Otros archivos importan `diagnose()` para diagnosticar incidentes.
- **Como programa independiente:** `python orchestrator.py` abre un loop interactivo donde tú escribes la alerta y él la diagnostica.

**¿Qué contiene?**
- **Cargador de knowledge base:** Lee `AEGIS_PATTERNS.md` completo
- **Cliente DeepSeek:** Se conecta a la API de DeepSeek (compatible con OpenAI)
- **Sistema de prompts:** Instrucciones claras para que el LLM devuelva JSON válido
- **Parseo de respuesta:** Extrae `id`, `name`, `diagnosis` y `script` del JSON
- **Manejo de errores:** Si la API falla o el JSON es inválido, devuelve UNKNOWN

**🔍 Archivo:** `orchestrator.py` (176 líneas)

---

### 4.3 `slack_bot.py` — El Bot de Slack

```
🎭 Personalidad: El asistente que vive en Slack
```

**¿Qué hace?**
Escucha mensajes en Slack y responde con diagnósticos de AEGIS. Puede ser @mencionado en canales, recibir mensajes directos, o usar el comando `/aegis`.

**¿Cómo se usa?**
```bash
python slack_bot.py
```
Luego en Slack:
- `@AEGIS No puedo iniciar sesión` → Responde con diagnóstico
- Mensaje directo al bot: "El servidor está dando error 500" → Diagnostica
- `/aegis diagnose Se cayó la base de datos` → Diagnostica

**¿Qué contiene?**
- **Conexión Socket Mode:** Se conecta a Slack sin necesidad de servidor público
- **Dual-mode:** Usa los servicios SaaS (`app/services/`) si están disponibles, o los módulos legacy si no
- **Routeo de severidad:** Decide si la consulta es L1/L2 o L3/L4 según las palabras clave
- **Formateo de respuestas:** Usa emojis y formato de Slack para respuestas claras

**🔍 Archivo:** `slack_bot.py` (262 líneas)

---

### 4.4 `AEGIS_PATTERNS.md` — La Biblioteca de Patrones

```
🎭 Personalidad: El libro de casos clínicos
```

**¿Qué contiene?**
20 patrones de incidentes reales que ocurrieron en empresas como AWS, Cloudflare, Google, GitHub, Netflix y Azure. Cada patrón documenta:

- **Síntomas:** ¿Qué señales de alerta se ven? (presentado en tabla)
- **Diagnóstico:** ¿Qué ocurrió realmente? (explicación detallada)
- **Script de remediación:** ¿Cómo se solucionó? (código bash listo para ejecutar)

**¿Cómo se usa en el sistema?**
El orquestador lo lee completo y se lo pasa al LLM como contexto. El LLM compara la alerta actual contra cada patrón y elige el que más se parece.

**Ejemplo de un patrón (AEGIS-001):**
- **Source:** AWS Kinesis Event - November 2020
- **Síntomas:** API 503, latencia aumenta, throttling, excepciones Kinesis
- **Diagnóstico:** Efecto dominó por dependencia no resiliente (cascade dependency saturation)
- **Script:** Bash que identifica la dependencia lenta, activa circuit breaker, escala y reinicia

**🔍 Archivo:** `AEGIS_PATTERNS.md` (1142 líneas, 20 patrones)

---

### 4.5 `integration_module.py` — El Webhook Universal (Legacy)

```
🎭 Personalidad: La versión anterior del recepcionista
```

**¿Qué hace?**
Es la versión standalone del webhook que recibía alertas antes de que existiera el SaaS (`app/`). Sigue siendo funcional y útil como referencia.

**Endpoints:**
- `POST /alert` — Recibe alertas y las diagnostica (igual que `/v1/alert` del SaaS)
- `GET /health` — Verifica el estado del sistema
- `POST /pagerduty` — Webhook para PagerDuty (parsea payloads v2 y v3)
- `GET /stats` — Estadísticas del clasificador

**¿Por qué existe si ya está el SaaS?**
El módulo de integración fue la primera versión. Cuando se añadió multi-tenancy, facturación y autenticación, se creó la carpeta `app/`. Pero `integration_module.py` sigue siendo útil para:
- Entender la evolución del proyecto
- Tener un punto de referencia simple
- Ejecutar pruebas rápidas sin toda la infraestructura SaaS

**🔍 Archivo:** `integration_module.py` (520 líneas)

---

## 5. 🛠️ Comandos Útiles (Tu Caja de Herramientas)

Comandos agrupados por misión, para que encuentres rápido lo que necesitas.

---

### 🚀 Para arrancar el proyecto

```bash
# 1. Clonar (si no lo has hecho)
git clone https://github.com/laral5173/aegis-itsm-agent.git
cd aegis-itsm-agent

# 2. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar API key (crear archivo .env)
# echo DEEPSEEK_API_KEY=tu-key >> .env

# 5. ¡A correr!
python app/main.py

# 6. Abre la documentación interactiva:
#    http://localhost:8000/docs
```

---

### 🧪 Para probar componentes individuales

```bash
# Clasificador L1/L2 (menú interactivo)
python classifier.py

# Orquestador L3/L4 (describe una alerta)
python orchestrator.py

# Slack Bot (requiere tokens en .env)
python slack_bot.py
```

---

### 📊 Para evaluar el modelo

```bash
# Pruebas de precisión (22 tickets de prueba)
python test_classifier.py

# Validación cruzada 5-fold
python cross_validation.py
```

---

### 🐳 Para usar Docker

```bash
# Levanta todo: app + PostgreSQL + ChromaDB
docker-compose up
```

---

### 📬 Para probar la API

```bash
# Ticket simple (L1/L2) — Windows CMD
curl -X POST http://localhost:8000/v1/alert ^
  -H "Content-Type: application/json" ^
  -d "{\"source\":\"manual\",\"severity\":\"low\",\"title\":\"No puedo entrar\",\"description\":\"Error 403 al iniciar sesión\"}"

# Ticket simple (L1/L2) — PowerShell
curl -X POST http://localhost:8000/v1/alert `
  -H "Content-Type: application/json" `
  -d '{"source":"manual","severity":"low","title":"No puedo entrar","description":"Error 403 al iniciar sesión"}'

# Incidente crítico (L3/L4)
curl -X POST http://localhost:8000/v1/alert ^
  -H "Content-Type: application/json" ^
  -d "{\"source\":\"pagerduty\",\"severity\":\"critical\",\"title\":\"DB caída\",\"description\":\"Timeout en conexión a base de datos\"}"

# Ver estado del sistema
curl http://localhost:8000/v1/health

# Ver estadísticas de uso
curl http://localhost:8000/v1/stats
```

---

### 🔧 Para administración

```bash
# Crear un nuevo tenant (cliente)
curl -X POST http://localhost:8000/v1/admin/tenants ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Mi Empresa\",\"slug\":\"mi-empresa\",\"plan\":\"shield\"}"

# Listar todos los tenants
curl http://localhost:8000/v1/admin/tenants

# Ver uso de un tenant específico
curl http://localhost:8000/v1/admin/usage/{tenant_id}
```

---

## 6. ❓ Preguntas Frecuentes

---

### 1. "No tengo API key de DeepSeek, ¿puedo probar el proyecto igual?"

**Sí.** El clasificador L1/L2 funciona completamente sin API key. Solo el orquestador L3/L4 (que usa el LLM) la necesita. Puedes probar:
- `python classifier.py` — Menú interactivo del clasificador
- `POST /v1/alert` con severity "low" o "medium" — Usará el clasificador
- `GET /v1/health` — Verás que el sistema responde

Si intentas un diagnóstico L3/L4 sin API key, el sistema devolverá UNKNOWN con un mensaje indicando que falta la key.

---

### 2. "¿Puedo usar ChatGPT en lugar de DeepSeek?"

**Sí.** En tu archivo `.env`, cambia:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=tu-key-de-openai
OPENAI_MODEL=gpt-4o-mini
```
También puedes usar Ollama (modelos locales):
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3
```
El sistema usa una interfaz común (OpenAI-compatible), así que cambiar de proveedor es solo cuestión de configuración.

---

### 3. "¿Cómo le enseño al clasificador un ticket nuevo?"

Dos formas:

**Opción A — Desde el menú interactivo:**
```bash
python classifier.py
# Opción 2: "Add a resolved ticket"
# Te pedirá: descripción, resolución y categoría
```

**Opción B — Editando el CSV:**
Abre `tickets_dataset.csv` y agrega una nueva fila:
```csv
id,description,resolution,category
T078,User cannot access VPN from home,Added user to VPN group and updated firewall rules,ACCESS
```
El clasificador carga el CSV automáticamente al iniciar.

---

### 4. "¿Qué significa que la respuesta sea UNKNOWN?"

Significa que el clasificador no encontró ningún ticket histórico lo suficientemente parecido. La confianza no alcanzó el umbral del 45%. Esto puede pasar por dos razones:

1. **El ticket es de un tipo nuevo** que no existe en los 77 tickets históricos.
2. **El ticket está mal escrito** o usa vocabulario muy diferente.

**¿Qué hacer?** Revisar el ticket manualmente y, una vez resuelto, añadirlo a la base de datos para que el clasificador aprenda.

---

### 5. "¿Necesito PostgreSQL sí o sí?"

**No.** El sistema tiene fallback automático a SQLite. Si no tienes PostgreSQL instalado:
1. El sistema lo detecta al iniciar
2. Crea un archivo `aegis_dev.db` en la raíz del proyecto
3. Todo funciona igual

Para desarrollo local, SQLite es perfecto. Para producción, se recomienda PostgreSQL.

---

### 6. "¿Cómo creo un nuevo cliente (tenant)?"

Usa el endpoint de administración:

```bash
curl -X POST http://localhost:8000/v1/admin/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "slug": "acme-corp", "plan": "shield"}'
```

La respuesta incluirá la API key del nuevo tenant. **Guárdala**, solo se muestra una vez.

Planes disponibles:
- **shield:** Hasta 50 incidentes/mes
- **guard:** Incidentes ilimitados
- **fortress:** Incidentes ilimitados + características enterprise

---

### 7. "¿Cómo agrego un nuevo patrón de incidente?"

Edita `AEGIS_PATTERNS.md` y agrega un nuevo bloque al final siguiendo el formato existente:

```markdown
## Pattern AEGIS-021
**Name:** Nombre de tu patrón
**Source:** Fuente del incidente

### Symptoms (automatically detectable)

| Symptom | Where to see | Typical format |
|---------|--------------|----------------|
| Síntoma 1 | Dónde verlo | Formato típico |

### Diagnosis (root cause)

Explicación de qué ocurrió realmente.

### Remediation Script

```bash
#!/bin/bash
# Comandos de remediación
```
```

El orquestador lo cargará automáticamente en el próximo diagnóstico.

---

### 8. "El Slack Bot no funciona, ¿qué reviso?"

Sigue esta lista de verificación:

1. **¿Están los tokens en `.env`?**
   ```
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_APP_TOKEN=xapp-...
   ```

2. **¿La app de Slack tiene Socket Mode habilitado?**
   Ve a tu app en [api.slack.com/apps](https://api.slack.com/apps) → Socket Mode → Activado

3. **¿Tiene los scopes correctos?**
   - `chat:write` — Para enviar mensajes
   - `commands` — Para el comando `/aegis`
   - `app_mentions:read` — Para detectar @menciones

4. **¿El Slash Command está configurado?**
   `/aegis` con Request URL vacío (Socket Mode no necesita URL)

5. **¿El bot está en el canal?**
   Invita al bot al canal donde quieres usarlo.

---

### 9. "¿Dónde se guardan los embeddings de ChromaDB?"

En la carpeta `tickets_db/` en la raíz del proyecto. Esta carpeta se crea automáticamente la primera vez que ejecutas el clasificador.

Si quieres empezar de cero (por ejemplo, con un nuevo dataset), solo borra la carpeta `tickets_db/` y el clasificador la recreará.

---

### 10. "¿Cómo contribuyo al proyecto?"

1. Revisa [`CONTRIBUTING.md`](./CONTRIBUTING.md) para las guías de contribución.
2. El proyecto sigue un [Código de Conducta](./CODE_OF_CONDUCT.md).
3. Las contribuciones pueden ser:
   - **Nuevos patrones** en `AEGIS_PATTERNS.md`
   - **Mejoras al clasificador** (más tickets, mejor precisión)
   - **Nuevas integraciones** (Jira, ServiceNow, Datadog)
   - **Correcciones de bugs** y mejoras de código
   - **Documentación** como esta guía

---

### 11. "¿Qué significan los niveles de confianza HIGH / MEDIUM / LOW?"

Son etiquetas para que sea más fácil interpretar la confianza del clasificador:

| Etiqueta | Rango | Significado |
|----------|-------|-------------|
| **HIGH** | ≥ 75% | El clasificador está muy seguro. La categoría es confiable. |
| **MEDIUM** | 50% – 74% | Confianza moderada. Revisar manualmente antes de actuar. |
| **LOW** | < 50% | Baja confianza. Probablemente requiere revisión humana. |

---

### 12. "¿Cómo ejecuto pruebas para verificar que todo funciona?"

```bash
# Pruebas del clasificador (22 tickets de prueba)
python test_classifier.py

# Validación cruzada (5-fold, mide precisión real)
python cross_validation.py

# Verificar que el servidor responde
curl http://localhost:8000/v1/health

# Verificar que los imports funcionan
python test_integration.py
```

---

### 13. "¿Qué es el Script Executor y cómo se usa?"

El **Script Executor** es una funcionalidad planeada (Phase 3 del roadmap). Actualmente, el orquestador genera scripts de remediación, pero **no los ejecuta automáticamente**. En su lugar:

1. El orquestador devuelve el script en la respuesta JSON
2. Un humano revisa el script
3. Si es seguro, lo ejecuta manualmente

En el futuro (Phase 3), los scripts se ejecutarán en un sandbox aislado con aprobación humana.

---

### 14. "¿Puedo ejecutar el clasificador sin levantar el servidor?"

**Sí.** El clasificador y el orquestador se pueden ejecutar como programas independientes:

```bash
# Clasificador con menú interactivo
python classifier.py

# Orquestador con loop interactivo
python orchestrator.py
```

Esto es útil para:
- Probar el clasificador con tickets personalizados
- Añadir tickets a la base de datos
- Ver estadísticas sin necesidad del servidor web

---

### 15. "¿Qué hago si veo un error 'DEEPSEEK_API_KEY not configured'?"

Significa que el orquestador L3/L4 no encuentra la API key de DeepSeek. Solución:

1. Crea un archivo `.env` en la raíz del proyecto (puedes copiar `.env.example`)
2. Agrega: `DEEPSEEK_API_KEY=tu-api-key`
3. Consigue una key gratis en [platform.deepseek.com](https://platform.deepseek.com)

Si solo quieres probar el clasificador L1/L2, este error no te afecta.

---

> **¿Encontraste algo que mejorar en esta guía?**  
> Las contribuciones son bienvenidas. Revisa [`CONTRIBUTING.md`](./CONTRIBUTING.md) para saber cómo ayudar.


