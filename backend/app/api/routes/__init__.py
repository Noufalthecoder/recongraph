"""
API routes for ReconGraph.
"""

from backend.app.api.routes.benchmark import router as benchmark_router
from backend.app.api.routes.dashboard import router as dashboard_router
from backend.app.api.routes.graph import router as graph_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.investigation import router as investigation_router
from backend.app.api.routes.scenarios import router as scenarios_router
from backend.app.api.routes.settlements import router as settlements_router

__all__ = [
    "health_router",
    "dashboard_router",
    "scenarios_router",
    "settlements_router",
    "graph_router",
    "investigation_router",
    "benchmark_router",
]
