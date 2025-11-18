"""
Field Mapping Service - LLM disabled version.
This version avoids llama_cpp dependency and always returns placeholder mapping.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from ..utils.exceptions import ProcessingException

logger = logging.getLogger(__name__)


class FieldMappingService:
    """
    Simplified Field Mapping Service (LLM disabled).
    This version:
    - Does NOT load any GGUF model
    - Does NOT call llama_cpp
    - Always returns a placeholder field mapping
    - Prevents server crashes
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._initialized = False
        self._llm = None  # LLM disabled

    def initialize(self) -> None:
        """
        Disable initialization.
        """
        logger.warning("LLM initialization skipped (disabled).")
        self._initialized = False
        self._llm = None

    def map_fields(
        self,
        ocr_result: Dict[str, Any],
        schema: Dict[str, Any],
        split_compound: bool = True
    ) -> Dict[str, Any]:
        """
        Since LLM is disabled, return placeholder mapping:
        - every field: not_found = True
        - no llama logic
        """
        logger.warning("map_fields() executed with LLM disabled.")

        # Determine field names from schema
        if isinstance(schema, list):
            field_names = [
                f.get("name", f) if isinstance(f, dict) else f
                for f in schema
            ]
        else:
            field_names = list(schema.keys())

        # Create placeholder response
        mapped = {
            name: {
                "value": "",
                "source_text": "",
                "confidence": 0.0,
                "uncertain": True,
                "not_found": True
            }
            for name in field_names
        }

        return {
            "fields": mapped,
            "processing_time_ms": 0,
            "llm_enabled": False,
            "message": "LLM-based field mapping is disabled."
        }

    def is_initialized(self) -> bool:
        """LLM is always disabled."""
        return False
