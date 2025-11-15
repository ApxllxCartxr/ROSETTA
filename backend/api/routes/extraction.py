"""
Extraction API routes.
Handles document upload and processing.
"""

import tempfile
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional, Dict, Any
import json
import logging

from ..models.requests import ExtractRequest, ProcessRequest, FieldSchema
from ..models.responses import JobResponse
from ..utils.validators import validate_file, validate_schema
from ..utils.exceptions import InvalidFileException, SchemaValidationException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["extraction"])


def get_app_state():
    """Dependency to get app state."""
    from ..main import app_state
    return app_state


@router.post("/extract", response_model=JobResponse)
async def extract_document(
    file: UploadFile = File(..., description="Document file (PDF, JPG, PNG, TIFF)"),
    language: Optional[str] = Form("en", description="OCR language"),
    preprocessing: bool = Form(True, description="Enable preprocessing"),
    performance_mode: str = Form("balanced", description="Performance mode"),
    state: Dict[str, Any] = Depends(get_app_state)
):
    """
    Extract text from uploaded document using OCR.
    Returns job_id for async processing.
    """
    try:
        # Save uploaded file
        temp_dir = state["config"].get("upload", {}).get("temp_dir", "temp/uploads")
        os.makedirs(temp_dir, exist_ok=True)
        
        suffix = Path(file.filename or "upload").suffix or ".jpg"
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            dir=temp_dir
        )
        
        # Write file content
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # Validate file
        upload_config = state["config"].get("upload", {})
        validate_file(
            temp_file.name,
            allowed_formats=upload_config.get("allowed_formats", []),
            max_size_mb=upload_config.get("max_file_size_mb", 10)
        )
        
        # Create job
        job_id = state["job_store"].create_job(
            job_type="ocr_extraction",
            data={
                "file_path": temp_file.name,
                "language": language,
                "preprocessing": preprocessing,
                "performance_mode": performance_mode
            }
        )
        
        logger.info(f"Created extraction job: {job_id}")
        
        return JobResponse(
            job_id=job_id,
            status="pending",
            created_at=state["job_store"].get_job(job_id).created_at.isoformat(),  # type: ignore
            message="Job queued for processing",
            websocket_url=f"ws://{state['config']['server']['host']}:{state['config']['server']['port']}/ws/jobs/{job_id}"
        )
    
    except InvalidFileException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Extraction endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/fields/extract", response_model=JobResponse)
async def extract_fields(
    document_id: str = Form(..., description="Document ID from OCR extraction"),
    schema_json: str = Form(..., description="Field schema JSON"),
    state: Dict[str, Any] = Depends(get_app_state)
):
    """
    Extract specific fields from OCR result using LLM.
    Returns job_id for async processing.
    """
    try:
        # Parse schema
        try:
            schema_data = json.loads(schema_json)
            schema_dict = schema_data.get("fields", schema_data)
            validate_schema(schema_dict)
        except json.JSONDecodeError:
            raise SchemaValidationException("Invalid JSON in schema")
        
        # Create job
        job_id = state["job_store"].create_job(
            job_type="field_mapping",
            data={
                "document_id": document_id,
                "schema": schema_dict,
                "split_compound": schema_data.get("split_compound_fields", True)
            }
        )
        
        logger.info(f"Created field mapping job: {job_id}")
        
        return JobResponse(
            job_id=job_id,
            status="pending",
            created_at=state["job_store"].get_job(job_id).created_at.isoformat(),  # type: ignore
            message="Field mapping job queued",
            websocket_url=f"ws://{state['config']['server']['host']}:{state['config']['server']['port']}/ws/jobs/{job_id}"
        )
    
    except SchemaValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Field extraction endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/process", response_model=JobResponse)
async def process_document(
    file: UploadFile = File(..., description="Document file"),
    schema_json: Optional[str] = Form(None, description="Optional field schema JSON"),
    language: Optional[str] = Form("en"),
    preprocessing: bool = Form(True),
    performance_mode: str = Form("balanced"),
    use_llm: bool = Form(True, description="Use LLM for field mapping"),
    state: Dict[str, Any] = Depends(get_app_state)
):
    """
    End-to-end document processing: OCR + field mapping.
    Returns job_id for async processing.
    """
    try:
        # Save uploaded file
        temp_dir = state["config"].get("upload", {}).get("temp_dir", "temp/uploads")
        os.makedirs(temp_dir, exist_ok=True)
        
        suffix = Path(file.filename or "upload").suffix or ".jpg"
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            dir=temp_dir
        )
        
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # Validate file
        upload_config = state["config"].get("upload", {})
        validate_file(
            temp_file.name,
            allowed_formats=upload_config.get("allowed_formats", []),
            max_size_mb=upload_config.get("max_file_size_mb", 10)
        )
        
        # Parse schema if provided
        schema_dict = None
        split_compound = True
        if schema_json:
            try:
                schema_data = json.loads(schema_json)
                # Handle both old dict format and new array format
                if isinstance(schema_data, dict):
                    schema_dict = schema_data.get("fields", schema_data)
                    split_compound = schema_data.get("split_compound_fields", True)
                else:
                    # Array format directly
                    schema_dict = schema_data
                    split_compound = True
                
                # Skip validation for array format
                if isinstance(schema_dict, dict):
                    validate_schema(schema_dict)
                
                logger.info(f"Parsed schema: {type(schema_dict).__name__} with {len(schema_dict) if schema_dict else 0} fields")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                raise SchemaValidationException(f"Invalid JSON in schema: {str(e)}")
        
        # Create job
        job_id = state["job_store"].create_job(
            job_type="full_process",
            data={
                "file_path": temp_file.name,
                "language": language,
                "preprocessing": preprocessing,
                "performance_mode": performance_mode,
                "schema": schema_dict,
                "split_compound": split_compound,
                "use_llm": use_llm
            }
        )
        
        logger.info(f"Created full processing job: {job_id}")
        
        return JobResponse(
            job_id=job_id,
            status="pending",
            created_at=state["job_store"].get_job(job_id).created_at.isoformat(),  # type: ignore
            message="Processing job queued",
            websocket_url=f"ws://{state['config']['server']['host']}:{state['config']['server']['port']}/ws/jobs/{job_id}"
        )
    
    except (InvalidFileException, SchemaValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Process endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
