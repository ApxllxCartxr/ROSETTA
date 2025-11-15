"""Job status API routes."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

from ..models.responses import JobStatusResponse
from ..utils.exceptions import JobNotFoundException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def get_app_state():
    """Dependency to get app state."""
    from ..main import app_state
    return app_state


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    state: Dict[str, Any] = Depends(get_app_state)
):
    """Get job status and result."""
    job = state["job_store"].get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        result=job.result,
        error=job.error,
        created_at=job.created_at.isoformat() if job.created_at else None,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None
    )
