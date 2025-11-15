"""
Job queue and status tracking.
"""

import uuid
import threading
from enum import Enum
from typing import Any, Dict, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Job data structure."""
    job_id: str
    job_type: str  # "ocr_extraction" | "field_mapping" | "full_process"
    status: JobStatus
    data: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: int = 0
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d["status"] = self.status.value
        # Convert datetime to ISO format
        for key in ["created_at", "started_at", "completed_at"]:
            if d[key]:
                d[key] = d[key].isoformat()
        return d


class JobStore:
    """
    Thread-safe job storage and queue management.
    """
    
    def __init__(self, max_concurrent: int = 3, result_ttl_hours: int = 1):
        """
        Initialize job store.
        
        Args:
            max_concurrent: Maximum concurrent processing jobs
            result_ttl_hours: How long to keep completed job results
        """
        self.max_concurrent = max_concurrent
        self.result_ttl_hours = result_ttl_hours
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.RLock()
        self._processing_count = 0
        
        logger.info(f"JobStore initialized (max_concurrent: {max_concurrent})")
    
    def create_job(self, job_type: str, data: Dict[str, Any]) -> str:
        """
        Create a new job.
        
        Args:
            job_type: Type of job
            data: Job data
        
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        with self._lock:
            job = Job(
                job_id=job_id,
                job_type=job_type,
                status=JobStatus.PENDING,
                data=data,
                created_at=datetime.now()
            )
            self._jobs[job_id] = job
        
        logger.info(f"Created job: {job_id} (type: {job_type})")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID.
        
        Args:
            job_id: Job ID
        
        Returns:
            Job object or None if not found
        """
        with self._lock:
            return self._jobs.get(job_id)
    
    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Update job status.
        
        Args:
            job_id: Job ID
            status: New status
            progress: Progress percentage (0-100)
            result: Job result (for completed jobs)
            error: Error message (for failed jobs)
        
        Returns:
            True if updated, False if job not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            
            old_status = job.status
            job.status = status
            
            if progress is not None:
                job.progress = progress
            
            if result is not None:
                job.result = result
            
            if error is not None:
                job.error = error
            
            # Update timestamps
            if status == JobStatus.PROCESSING and not job.started_at:
                job.started_at = datetime.now()
                self._processing_count += 1
            
            if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                if not job.completed_at:
                    job.completed_at = datetime.now()
                if old_status == JobStatus.PROCESSING:
                    self._processing_count = max(0, self._processing_count - 1)
            
            logger.debug(f"Job {job_id}: {old_status.value} → {status.value}")
            return True
    
    def can_process_more(self) -> bool:
        """
        Check if more jobs can be processed concurrently.
        
        Returns:
            True if under max_concurrent limit
        """
        with self._lock:
            return self._processing_count < self.max_concurrent
    
    def get_next_pending(self) -> Optional[Job]:
        """
        Get next pending job (FIFO).
        
        Returns:
            Next pending job or None
        """
        with self._lock:
            for job in self._jobs.values():
                if job.status == JobStatus.PENDING:
                    return job
            return None
    
    def cleanup_old_jobs(self) -> int:
        """
        Remove completed jobs older than TTL.
        
        Returns:
            Number of jobs removed
        """
        with self._lock:
            now = datetime.now()
            old_jobs = []
            
            for job_id, job in self._jobs.items():
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                    if job.completed_at:
                        age_hours = (now - job.completed_at).total_seconds() / 3600
                        if age_hours > self.result_ttl_hours:
                            old_jobs.append(job_id)
            
            for job_id in old_jobs:
                del self._jobs[job_id]
            
            if old_jobs:
                logger.info(f"Cleaned up {len(old_jobs)} old jobs")
            
            return len(old_jobs)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get job statistics.
        
        Returns:
            Dictionary with job stats
        """
        with self._lock:
            stats = {
                "total_jobs": len(self._jobs),
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }
            
            for job in self._jobs.values():
                stats[job.status.value] += 1
            
            return stats
