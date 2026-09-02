"""
Static isolation tests for backend API package.
"""

import sys
import backend.app.api.demo_state
import backend.app.api.routes.benchmark
import backend.app.api.routes.dashboard
import backend.app.api.routes.graph
import backend.app.api.routes.health
import backend.app.api.routes.investigation
import backend.app.api.routes.scenarios
import backend.app.api.routes.settlements
import backend.app.api.schemas


def test_api_package_isolation():
    """Verify backend/app/api does not import GroundTruth or AnomalyManifest directly in routes."""
    import backend.app.api.app as app_module

    runtime_modules = [
        backend.app.api.routes.dashboard,
        backend.app.api.routes.graph,
        backend.app.api.routes.health,
        backend.app.api.routes.investigation,
        backend.app.api.routes.scenarios,
        backend.app.api.routes.settlements,
        backend.app.api.schemas,
        sys.modules["backend.app.api.app"],
    ]

    for m in runtime_modules:
        src = open(m.__file__, "r", encoding="utf-8").read()
        assert "from simulator.ground_truth" not in src
        assert "GroundTruth(" not in src
        assert "AnomalyManifest(" not in src
