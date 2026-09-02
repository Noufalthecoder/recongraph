"""
FastAPI application factory for ReconGraph.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import (
    benchmark_router,
    dashboard_router,
    graph_router,
    health_router,
    investigation_router,
    scenarios_router,
    settlements_router,
)


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application instance."""
    app = FastAPI(
        title="ReconGraph API",
        description="Deterministic Financial Reconciliation & Investigation Intelligence Platform",
        version="1.0.0",
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(health_router)
    app.include_router(dashboard_router)
    app.include_router(scenarios_router)
    app.include_router(settlements_router)
    app.include_router(graph_router)
    app.include_router(investigation_router)
    app.include_router(benchmark_router)

    # Serve static frontend if built
    dist_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "dist")
    if os.path.isdir(dist_dir):
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")

    return app


app = create_app()
