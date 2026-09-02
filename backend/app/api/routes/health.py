"""
Health check route.
"""

from fastapi import APIRouter
from backend.app.api.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health():
    return HealthResponse(status="ok", service="recongraph")
