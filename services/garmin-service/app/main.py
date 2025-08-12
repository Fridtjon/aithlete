from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.core.config import settings
from app.core.database import init_db
from app.api.routes import router
from app.core.logging import setup_logging

logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Garmin Data Service")
    setup_logging()
    await init_db()
    yield
    # Shutdown
    logger.info("Shutting down Garmin Data Service")

app = FastAPI(
    title="AIthlete Garmin Data Service",
    description="Service for fetching and managing Garmin Connect data",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "garmin-service",
        "status": "healthy",
        "version": "0.1.0"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "AIthlete Garmin Data Service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_config=None  # Use our custom logging
    )