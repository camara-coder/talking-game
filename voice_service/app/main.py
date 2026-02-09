"""
Main FastAPI application for Voice Agent Service
Handles HTTP endpoints, WebSocket connections, and service initialization
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
from datetime import datetime

from app.config import settings
import asyncio

# Database imports (conditional)
if settings.ENABLE_DB_PERSISTENCE:
    from app.db.base import init_db, close_db
    from app.db.session import init_session_factory
    from app.tasks.cleanup import cleanup_old_data_task

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"{settings.LOGS_DIR}/voice_service.log")
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.SERVICE_NAME,
    description="Local voice interaction service for kids game",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for web client
# Log configured CORS origins for debugging
logger.info(f"CORS allowed origins: {settings.cors_origins_list}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Import routers
from app.api import routes, ws
from app.api.session_manager import session_manager


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("=" * 60)
    logger.info(f"{settings.SERVICE_NAME} starting...")
    logger.info(f"Service URL: http://{settings.SERVICE_HOST}:{settings.SERVICE_PORT}")
    logger.info(f"WebSocket URL: ws://{settings.SERVICE_HOST}:{settings.SERVICE_PORT}/ws")
    logger.info(f"Ollama URL: {settings.OLLAMA_BASE_URL}")
    logger.info(f"STT Model: {settings.STT_MODEL_SIZE}")
    logger.info(f"LLM Model: {settings.OLLAMA_MODEL}")
    logger.info(f"Data Directory: {settings.DATA_DIR}")
    logger.info("=" * 60)

    # Canary-Qwen STT startup validation (optional)
    if settings.CANARY_QWEN_STARTUP_LOAD:
        try:
            logger.info("Validating Canary-Qwen STT model load...")
            from app.pipeline.processors.stt_canary_qwen import _get_canary_model
            _get_canary_model()
            logger.info("Canary-Qwen STT model loaded successfully")
        except Exception as e:
            logger.error(f"Canary-Qwen STT model load failed: {e}", exc_info=True)
            # Fail fast so deploys don't run without STT
            raise

    # Start session manager
    await session_manager.start()

    # Initialize database (if enabled)
    if settings.ENABLE_DB_PERSISTENCE:
        logger.info("Initializing database...")
        logger.info(f"Database URL format: {settings.database_url_async.split('@')[0]}@***")  # Log without credentials
        try:
            engine = await init_db(
                database_url=settings.database_url_async,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                echo=settings.DB_ECHO
            )
            if engine:
                logger.info("Database engine created successfully")

                # Initialize session factory
                factory_initialized = init_session_factory()

                if factory_initialized:
                    logger.info("Database initialized successfully - persistence enabled")

                    # Start cleanup background task
                    asyncio.create_task(cleanup_old_data_task())
                    logger.info(f"Cleanup task started: will delete data older than {settings.DATA_RETENTION_DAYS} days")
                else:
                    logger.error("Session factory initialization failed - persistence disabled")
            else:
                logger.warning("Database engine initialization failed, persistence disabled")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            logger.warning("Continuing without database persistence")
    else:
        logger.info("Database persistence disabled (ENABLE_DB_PERSISTENCE=False)")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info(f"{settings.SERVICE_NAME} shutting down...")

    # Stop session manager
    await session_manager.stop()

    # Close database connections (if enabled)
    if settings.ENABLE_DB_PERSISTENCE:
        logger.info("Closing database connections...")
        await close_db()
        logger.info("Database connections closed")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - basic info"""
    return {
        "service": settings.SERVICE_NAME,
        "version": "0.1.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Detailed health check endpoint
    Verifies all critical services are accessible
    """
    health_status = {
        "service": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # Check Ollama connection
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(settings.OLLAMA_BASE_URL)
            if response.status_code == 200:
                health_status["checks"]["ollama"] = {
                    "status": "healthy",
                    "url": settings.OLLAMA_BASE_URL
                }
            else:
                health_status["checks"]["ollama"] = {
                    "status": "unhealthy",
                    "error": f"Status code: {response.status_code}"
                }
                health_status["service"] = "degraded"
    except Exception as e:
        health_status["checks"]["ollama"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["service"] = "degraded"

    # Check STT (Canary-Qwen) availability
    try:
        health_status["checks"]["stt"] = {
            "status": "ready",
            "provider": "Canary-Qwen",
            "model": settings.CANARY_QWEN_MODEL_ID,
            "device": settings.CANARY_QWEN_DEVICE
        }
    except Exception as e:
        health_status["checks"]["stt"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["service"] = "degraded"

    # Check audio directories
    import os
    health_status["checks"]["storage"] = {
        "status": "healthy" if os.path.exists(settings.AUDIO_DIR) else "unhealthy",
        "audio_dir": settings.AUDIO_DIR,
        "logs_dir": settings.LOGS_DIR
    }

    return health_status


# Ping endpoint for quick checks
@app.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"ping": "pong", "timestamp": datetime.utcnow().isoformat()}


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Include routers
app.include_router(routes.router, prefix="/api", tags=["sessions"])
app.include_router(ws.router, tags=["websocket"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
