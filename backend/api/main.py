"""
ROSETTA FastAPI Main Application.
Dynamic field mapping API for browser extensions.
"""

import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add parent directory to path for imports
if __name__ == "__main__":
    api_dir = Path(__file__).parent
    backend_dir = api_dir.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

try:
    from api.utils.config_loader import load_config
    from api.utils.exceptions import RosettaAPIException
    from api.storage.cache_manager import CacheManager
    from api.storage.job_store import JobStore
    from api.services.ocr_service import OCRService
    from api.services.field_service import FieldMappingService
    from api.services.job_worker import JobWorker
    from api.routes import extraction, jobs, documents, health
except ImportError:
    # Fallback to relative imports if running as module
    from .utils.config_loader import load_config
    from .utils.exceptions import RosettaAPIException
    from .storage.cache_manager import CacheManager
    from .storage.job_store import JobStore
    from .services.ocr_service import OCRService
    from .services.field_service import FieldMappingService
    from .services.job_worker import JobWorker
    from .routes import extraction, jobs, documents, health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global app state
app_state: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting ROSETTA API...")
    
    # Load configuration
    config = load_config()
    app_state["config"] = config
    
    # Initialize storage
    cache_config = config.get("cache", {})
    app_state["cache"] = CacheManager(
        ttl_hours=cache_config.get("ttl_hours", 24),
        max_size=cache_config.get("max_documents", 1000)
    )
    app_state["cache"].start_cleanup_thread(
        interval_minutes=cache_config.get("cleanup_interval_minutes", 60)
    )
    
    job_config = config.get("jobs", {})
    app_state["job_store"] = JobStore(
        max_concurrent=job_config.get("max_concurrent", 3),
        result_ttl_hours=job_config.get("result_ttl_hours", 1)
    )
    
    # Initialize services
    app_state["ocr_service"] = OCRService(config)
    app_state["field_service"] = FieldMappingService(config)
    
    # Start job worker
    app_state["job_worker"] = JobWorker(
        job_store=app_state["job_store"],
        cache_manager=app_state["cache"],
        ocr_service=app_state["ocr_service"],
        field_service=app_state["field_service"],
        config=config
    )
    app_state["job_worker"].start(num_workers=job_config.get("max_concurrent", 3))
    
    logger.info("ROSETTA API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ROSETTA API...")
    app_state["job_worker"].stop()
    app_state["cache"].stop_cleanup_thread()
    logger.info("ROSETTA API shut down")


# Create FastAPI app
app = FastAPI(
    title="ROSETTA API",
    description="Dynamic field mapping API for OCR document processing",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
cors_config = load_config().get("cors", {})
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config.get("allow_origins", ["*"]),
    allow_credentials=cors_config.get("allow_credentials", True),
    allow_methods=cors_config.get("allow_methods", ["*"]),
    allow_headers=cors_config.get("allow_headers", ["*"])
)

# Register routes
app.include_router(extraction.router)
app.include_router(jobs.router)
app.include_router(documents.router)
app.include_router(health.router)


# Exception handlers
@app.exception_handler(RosettaAPIException)
async def rosetta_exception_handler(request, exc: RosettaAPIException):
    """Handle custom API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message
        }
    )


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "ROSETTA API",
        "version": "1.0.0",
        "description": "Dynamic field mapping for OCR document processing",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    config = load_config()
    server_config = config.get("server", {})
    
    uvicorn.run(
        "api.main:app",
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8000),
        reload=server_config.get("reload", True),
        log_level="info"
    )
