"""
Job Worker - Background job processing.
"""

import threading
import time
from typing import Dict, Any
import logging

from ..storage import JobStore, JobStatus
from ..storage.cache_manager import CacheManager
from .ocr_service import OCRService
from .field_service import FieldMappingService

logger = logging.getLogger(__name__)


class JobWorker:
    """
    Background job processor.
    Processes OCR extraction and field mapping jobs asynchronously.
    """
    
    def __init__(
        self,
        job_store: JobStore,
        cache_manager: CacheManager,
        ocr_service: OCRService,
        field_service: FieldMappingService,
        config: Dict[str, Any]
    ):
        """Initialize job worker."""
        self.job_store = job_store
        self.cache = cache_manager
        self.ocr_service = ocr_service
        self.field_service = field_service
        self.config = config
        
        self._worker_threads: list[threading.Thread] = []
        self._stop_event = threading.Event()
        self._running = False
    
    def start(self, num_workers: int = 3) -> None:
        """
        Start worker threads.
        
        Args:
            num_workers: Number of concurrent worker threads
        """
        if self._running:
            logger.warning("Worker already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        for i in range(num_workers):
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"JobWorker-{i}",
                daemon=True
            )
            thread.start()
            self._worker_threads.append(thread)
        
        logger.info(f"Started {num_workers} job worker threads")
    
    def stop(self) -> None:
        """Stop all worker threads."""
        if not self._running:
            return
        
        self._stop_event.set()
        self._running = False
        
        for thread in self._worker_threads:
            thread.join(timeout=5)
        
        self._worker_threads.clear()
        logger.info("Stopped all job worker threads")
    
    def _worker_loop(self) -> None:
        """Main worker loop - processes jobs from queue."""
        while not self._stop_event.is_set():
            try:
                # Check if we can process more jobs
                if not self.job_store.can_process_more():
                    time.sleep(1)
                    continue
                
                # Get next pending job
                job = self.job_store.get_next_pending()
                if not job:
                    time.sleep(1)
                    continue
                
                # Mark as processing
                self.job_store.update_status(job.job_id, JobStatus.PROCESSING, progress=0)
                
                # Process based on job type
                try:
                    if job.job_type == "ocr_extraction":
                        result = self._process_ocr_job(job.data)
                    elif job.job_type == "field_mapping":
                        result = self._process_field_job(job.data)
                    elif job.job_type == "full_process":
                        result = self._process_full_job(job.data)
                    else:
                        raise ValueError(f"Unknown job type: {job.job_type}")
                    
                    # Mark as completed
                    self.job_store.update_status(
                        job.job_id,
                        JobStatus.COMPLETED,
                        progress=100,
                        result=result
                    )
                
                except Exception as e:
                    logger.error(f"Job {job.job_id} failed: {e}")
                    self.job_store.update_status(
                        job.job_id,
                        JobStatus.FAILED,
                        error=str(e)
                    )
            
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                time.sleep(1)
    
    def _process_ocr_job(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process OCR extraction job."""
        file_path = data.get("file_path")
        language = data.get("language")
        preprocessing = data.get("preprocessing", True)
        performance_mode = data.get("performance_mode")
        
        # Run OCR
        result = self.ocr_service.extract(
            file_path=file_path,
            language=language,
            preprocessing=preprocessing,
            performance_mode=performance_mode
        )
        
        # Cache result
        document_id = result.get("document_id")
        if document_id:
            ttl_hours = self.config.get("cache", {}).get("ttl_hours", 24)
            self.cache.set(document_id, result, ttl_hours=ttl_hours)
        
        return {"document_id": document_id, "type": "extraction"}
    
    def _process_field_job(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process field mapping job."""
        document_id = data.get("document_id")
        schema = data.get("schema")
        split_compound = data.get("split_compound", True)
        
        # Get OCR result from cache
        ocr_result = self.cache.get(document_id)
        if not ocr_result:
            raise ValueError(f"Document not found in cache: {document_id}")
        
        # Run field mapping
        result = self.field_service.map_fields(
            ocr_result=ocr_result,
            schema=schema,
            split_compound=split_compound
        )
        
        result["document_id"] = document_id
        return result
    
    def _process_full_job(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process full extraction + mapping job."""
        # Step 1: OCR extraction
        ocr_result = self._process_ocr_job(data)
        document_id = ocr_result.get("document_id")
        
        # Step 2: Field mapping (if schema provided and LLM available)
        schema = data.get("schema")
        if schema and data.get("use_llm", True) and self.field_service.is_initialized():
            try:
                field_data = {
                    "document_id": document_id,
                    "schema": schema,
                    "split_compound": data.get("split_compound", True)
                }
                field_result = self._process_field_job(field_data)
                
                return {
                    "document_id": document_id,
                    "ocr": ocr_result,
                    "fields": field_result.get("fields", {}),
                    "processing_time_ms": field_result.get("processing_time_ms", 0)
                }
            except Exception as e:
                logger.warning(f"Field mapping failed, returning OCR only: {e}")
                # Return OCR result with warning
                ocr_result["warning"] = "LLM field mapping failed - OCR only"
                return ocr_result
        
        # Return OCR-only result
        logger.info("Returning OCR-only result (no LLM)")
        return ocr_result
