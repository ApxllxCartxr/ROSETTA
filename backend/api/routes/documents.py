"""Document retrieval API routes."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

from ..models.responses import OCRResultResponse
from ..utils.exceptions import DocumentNotFoundException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def get_app_state():
    """Dependency to get app state."""
    from ..main import app_state
    return app_state


@router.get("/{document_id}", response_model=OCRResultResponse)
async def get_document(
    document_id: str,
    state: Dict[str, Any] = Depends(get_app_state)
):
    """Retrieve cached OCR extraction result."""
    result = state["cache"].get(document_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Document not found or expired: {document_id}"
        )
    
    return OCRResultResponse(**result, cached=True)


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    state: Dict[str, Any] = Depends(get_app_state)
):
    """Delete cached document."""
    deleted = state["cache"].delete(document_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
    
    return {"message": f"Document deleted: {document_id}"}
