"""
FastAPI application factory for TinyBase.

Creates and configures the main FastAPI application with all routes,
middleware, and lifecycle hooks.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tinybase.api.routes import admin, auth, collections, functions, schedules
from tinybase.api.routes.static_admin import mount_admin_ui
from tinybase.collections.service import load_collections_into_registry
from tinybase.config import settings
from tinybase.db.core import create_db_and_tables, get_engine
from tinybase.functions.loader import load_functions_from_settings
from tinybase.scheduler import start_scheduler, stop_scheduler
from tinybase.version import __version__

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize database, load collections, load functions, start scheduler
    - Shutdown: Stop scheduler
    """
    # Startup
    logger.info("Starting TinyBase server...")
    
    # Initialize database tables
    logger.info("Initializing database...")
    create_db_and_tables()
    
    # Load collections into registry
    logger.info("Loading collections...")
    from sqlmodel import Session
    engine = get_engine()
    with Session(engine) as session:
        load_collections_into_registry(session)
    
    # Load user functions
    logger.info("Loading functions...")
    loaded = load_functions_from_settings()
    logger.info(f"Loaded {loaded} function file(s)")
    
    # Start scheduler
    logger.info("Starting scheduler...")
    await start_scheduler()
    
    logger.info("TinyBase server started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down TinyBase server...")
    await stop_scheduler()
    logger.info("TinyBase server stopped")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    This factory function creates a new FastAPI app instance with:
    - All API routes mounted
    - CORS middleware configured
    - Admin UI static files mounted
    - Lifespan hooks for startup/shutdown
    
    Returns:
        Configured FastAPI application instance.
    """
    config = settings()
    
    # Create FastAPI app
    app = FastAPI(
        title="TinyBase",
        description="A lightweight, self-hosted Backend-as-a-Service framework for Python developers",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # Configure CORS
    if config.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Mount API routes
    app.include_router(auth.router, prefix="/api")
    app.include_router(collections.router, prefix="/api")
    app.include_router(functions.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(schedules.router, prefix="/api")
    
    # Mount admin UI
    admin_mounted = mount_admin_ui(app)
    if not admin_mounted:
        logger.warning("Admin UI static files not found - /admin will not be available")
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    def root() -> dict:
        """Root endpoint returning API information."""
        return {
            "name": "TinyBase",
            "version": __version__,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "admin": "/admin" if admin_mounted else None,
        }
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    def health() -> dict:
        """Health check endpoint."""
        return {"status": "healthy"}
    
    return app

