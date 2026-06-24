"""
AEGIS SaaS — FastAPI application entry point.
Multi-tenant, with PostgreSQL, ChromaDB, and configurable LLM provider.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db, get_engine
from app.routers import alerts, admin, dashboard

# ── Logging ───────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aegis")


# ── Lifespan ──────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"🛡️ {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    logger.info(f"   LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"   ChromaDB: {'server' if settings.CHROMA_USE_SERVER else 'local'}")
    logger.info(f"   Auth required: {settings.AUTH_REQUIRED}")

    # Initialize database tables (PostgreSQL or SQLite fallback)
    try:
        init_db()
        logger.info("✅ Database tables ready")
    except Exception as e:
        logger.warning(f"⚠️ Database initialization failed: {e}")
        logger.warning("   The app will start, but database-dependent features will fail.")

    yield

    # Shutdown
    logger.info("🛡️ AEGIS shutting down...")


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


# ── Global exception handler ──────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return a clean JSON response."""
    logger.error(f"Unhandled error on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


# ── Include routers ──────────────────────────────────────────

app.include_router(alerts.router)
app.include_router(admin.router)
app.include_router(dashboard.router)


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
            "GET /docs": "Interactive API documentation",
        },
    }


# ── Run ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on http://{settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )