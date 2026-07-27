"""
ITSMLab — FastAPI application entry point.
Multi-tenant, with PostgreSQL, ChromaDB, and configurable LLM provider.
"""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.routers import alerts, admin, dashboard, metrics
from app.logging_config import get_logger, metrics_collector

# ── Logging ───────────────────────────────────────────────────

logger = get_logger("itsmlab")


# ── Lifespan ──────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🛡️ ITSMLab starting...", extra={
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "chroma_mode": "server" if settings.CHROMA_USE_SERVER else "local",
        "auth_required": settings.AUTH_REQUIRED,
    })

    # Initialize database tables (PostgreSQL or SQLite fallback)
    try:
        init_db()
        logger.info("Database tables ready")
    except Exception as e:
        logger.warning("Database initialization failed", extra={"error": str(e)})
        logger.warning("The app will start, but database-dependent features will fail.")

    yield

    # Shutdown
    logger.info("🛡️ ITSMLab shutting down...")


# ── App creation ──────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-tenant SaaS for autonomous IT incident resolution",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware: Request ID + Metrics ──────────────────────────


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """
    Middleware that:
      1. Assigns a unique request_id to every request
      2. Records latency and status code in metrics_collector
      3. Logs the request with structured fields
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()

    # Extract tenant info from headers if available (for logging)
    tenant_id = request.headers.get("X-API-Key", "anonymous")[:12]

    response = await call_next(request)

    latency = time.time() - start_time
    endpoint = f"{request.method} {request.url.path}"

    # Record metrics
    metrics_collector.record_request(
        endpoint=endpoint,
        tenant_id=tenant_id,
        latency=latency,
        status_code=response.status_code,
    )

    # Log the request
    logger.info("Request processed", extra={
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "latency_ms": round(latency * 1000, 2),
        "tenant_id": tenant_id,
    })

    # Add request_id to response headers
    response.headers["X-Request-ID"] = request_id

    return response


# ── Global exception handler ──────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return a clean JSON response."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("Unhandled error", extra={
        "request_id": request_id,
        "method": request.method,
        "path": str(request.url),
        "error": str(exc),
    })
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
    )


# ── Include routers ──────────────────────────────────────────

app.include_router(alerts.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(metrics.router)


# ── Root endpoint ─────────────────────────────────────────────


@app.get("/")
def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "endpoints": {
            "POST /v1/alert": "Submit an alert or ticket for diagnosis",
            "GET /v1/health": "Health check",
            "GET /v1/stats": "Usage statistics",
            "POST /v1/admin/tenants": "Create tenant (admin)",
            "POST /v1/admin/api-keys": "Generate API key (admin)",
            "GET /v1/admin/tenants": "List tenants (admin)",
            "GET /dashboard": "Web dashboard (HTML)",
            "GET /metrics": "System metrics (JSON)",
            "GET /docs": "Interactive API documentation",
        },
    }


# ── Run ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server", extra={"host": settings.HOST, "port": settings.PORT})
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
