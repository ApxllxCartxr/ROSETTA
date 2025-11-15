"""Health check API routes."""

from fastapi import APIRouter, Depends
from typing import Dict, Any
import logging

from ..models.responses import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


def get_app_state():
    """Dependency to get app state."""
    from ..main import app_state
    return app_state


@router.get("/health", response_model=HealthResponse)
async def health_check(state: Dict[str, Any] = Depends(get_app_state)):
    """API health check."""
    return HealthResponse(
        status="healthy",
        ocr_loaded=state["ocr_service"].is_initialized(),
        llm_loaded=state["field_service"].is_initialized(),
        cache_stats=state["cache"].get_stats(),
        job_stats=state["job_store"].get_stats(),
        version="1.0.0"
    )


@router.post("/cache/clear")
async def clear_cache(state: Dict[str, Any] = Depends(get_app_state)):
    """Clear all cached documents (admin function)."""
    state["cache"].clear()
    return {"message": "Cache cleared successfully"}
