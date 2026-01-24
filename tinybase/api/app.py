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
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from tinybase.api.routes import admin, auth, collections, extensions, files, functions, schedules
from tinybase.api.routes.static_admin import mount_admin_ui
from tinybase.api.routes.static_auth import mount_auth_portal
from tinybase.collections.service import load_collections_into_registry
from tinybase.db.core import get_db_engine, init_db
from tinybase.extensions import load_enabled_extensions, run_shutdown_hooks, run_startup_hooks
from tinybase.functions.loader import load_functions_from_settings
from tinybase.logs import setup_logging
from tinybase.schedule import start_scheduler, stop_scheduler
from tinybase.settings import config
from tinybase.utils import generate_operation_id
from tinybase.version import __version__

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events:
    - Startup: Initialize database, load collections, load functions, load extensions, start scheduler
    - Shutdown: Run extension shutdown hooks, stop scheduler
    """
    # Startup
    logger.info("Starting TinyBase server...")

    # Initialize database tables
    logger.info("Initializing database...")
    init_db()

    # Load collections into registry
    logger.info("Loading collections...")
    from sqlmodel import Session

    engine = get_db_engine()
    with Session(engine) as session:
        load_collections_into_registry(session)

    # Load user functions
    logger.info("Loading functions...")
    loaded = load_functions_from_settings()
    logger.info(f"Loaded {loaded} function(s)")

    # Load extensions
    logger.info("Loading extensions...")
    with Session(engine) as session:
        ext_loaded = load_enabled_extensions(session)
        logger.info(f"Loaded {ext_loaded} extension(s)")

    # Run extension startup hooks (only if extensions are loaded)
    if ext_loaded > 0:
        logger.info("Running extension startup hooks...")
        await run_startup_hooks()

    # Start scheduler
    logger.info("Starting scheduler...")
    await start_scheduler()

    # Start function process pool for cold start optimization
    from tinybase.functions.pool import get_pool

    pool = get_pool()
    pool.start()

    # Mark application as ready
    app.state.ready = True
    logger.info("TinyBase server started successfully")

    yield

    # Shutdown
    logger.info("Shutting down TinyBase server...")

    # Run extension shutdown hooks (only if extensions were loaded)
    if ext_loaded > 0:
        logger.info("Running extension shutdown hooks...")
        await run_shutdown_hooks()

    await stop_scheduler()

    # Stop function process pool
    from tinybase.functions.pool import get_pool

    pool = get_pool()
    pool.stop()

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
    # Reset the operation ID tracker for this app instance
    if hasattr(generate_operation_id, "_seen_ids"):
        generate_operation_id._seen_ids = set()  # type: ignore

    # Create FastAPI app with custom operation ID generator
    app = FastAPI(
        title="TinyBase",
        description="A lightweight, self-hosted Backend-as-a-Service framework for Python developers",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        generate_unique_id_function=generate_operation_id,
    )

    # Initialize readiness state
    app.state.ready = False

    # Configure rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    app.include_router(files.router, prefix="/api")
    app.include_router(extensions.router, prefix="/api")

    # Mount admin UI
    admin_mounted = mount_admin_ui(app)
    if not admin_mounted:
        logger.warning("Admin UI static files not found - /admin will not be available")

    # Mount auth portal
    auth_mounted = mount_auth_portal(app)
    if not auth_mounted:
        logger.warning("Auth portal static files not found - /auth will not be available")

    # Root endpoint
    @app.get("/", tags=["system"])
    def get_root() -> dict:
        """Root endpoint returning API information."""
        return {
            "name": "TinyBase",
            "version": __version__,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "admin": "/admin" if admin_mounted else None,
            "auth": "/auth" if auth_mounted else None,
        }

    # Basic health check endpoints (no auth required)
    @app.get("/health", tags=["system"])
    def get_health() -> dict:
        """
        Basic health check endpoint (liveness probe).

        Returns healthy if the application process is running.
        This is a simple liveness probe that doesn't require authentication.
        Suitable for container orchestrators to check if the process is alive.
        """
        return {"status": "healthy"}

    @app.get("/healthz", tags=["system"])
    def get_healthz() -> dict:
        """
        Kubernetes-style health check endpoint.

        Returns a simple status for Kubernetes liveness probes.
        Does NOT require authentication.
        """
        return {"status": "ok"}

    return app
