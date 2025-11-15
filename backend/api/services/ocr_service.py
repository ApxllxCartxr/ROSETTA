"""
OCR Service - Wrapper for OCR pipeline.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Add backend directory to path to import ocr module
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import OCR components
try:
    # Try importing as package
    from ocr.ocr import OCRPipeline, create_pipeline  # type: ignore
    from ocr.utils import Language  # type: ignore
except ImportError:
    # Fallback: add ocr to path and import directly
    ocr_path = backend_path / "ocr"
    if str(ocr_path) not in sys.path:
        sys.path.insert(0, str(ocr_path))
    from ocr import OCRPipeline, create_pipeline  # type: ignore
    from utils import Language  # type: ignore

from ..utils.exceptions import ProcessingException

logger = logging.getLogger(__name__)


class OCRService:
    """
    OCR extraction service wrapper.
    Integrates existing OCR pipeline with API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OCR service.
        
        Args:
            config: OCR configuration from config.yaml
        """
        self.config = config
        self._pipeline: Optional[OCRPipeline] = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize OCR pipeline (lazy loading)."""
        if self._initialized:
            return
        
        try:
            ocr_config = self.config.get("ocr", {})
            
            self._pipeline = create_pipeline(
                language=ocr_config.get("default_language", "en"),
                confidence_threshold=ocr_config.get("confidence_threshold", 0.80),
                performance_mode=ocr_config.get("performance_mode", "balanced"),
                enable_preprocessing=ocr_config.get("enable_preprocessing", True),
                do_denoise=ocr_config.get("preprocessing", {}).get("denoise", True),
                do_deskew=ocr_config.get("preprocessing", {}).get("deskew", True),
                do_contrast=ocr_config.get("preprocessing", {}).get("contrast", True),
                do_sharpen=ocr_config.get("preprocessing", {}).get("sharpen", True)
            )
            
            self._initialized = True
            logger.info("OCR pipeline initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize OCR pipeline: {e}")
            raise ProcessingException(f"OCR initialization failed: {str(e)}")
    
    def extract(
        self,
        file_path: str,
        language: Optional[str] = None,
        preprocessing: bool = True,
        performance_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract text from document.
        
        Args:
            file_path: Path to document file
            language: OCR language override
            preprocessing: Enable preprocessing
            performance_mode: Performance mode override
        
        Returns:
            OCR extraction result dictionary
        
        Raises:
            ProcessingException: If extraction fails
        """
        if not self._initialized:
            self.initialize()
        
        if not self._pipeline:
            raise ProcessingException("OCR pipeline not initialized")
        
        try:
            # Update pipeline settings if overrides provided
            if performance_mode and performance_mode != self.config.get("ocr", {}).get("performance_mode"):
                self._pipeline = create_pipeline(
                    language=language or self.config.get("ocr", {}).get("default_language", "en"),
                    confidence_threshold=self.config.get("ocr", {}).get("confidence_threshold", 0.80),
                    performance_mode=performance_mode,
                    enable_preprocessing=preprocessing
                )
            
            # Run extraction
            result = self._pipeline.extract(
                image_path=file_path,
                language=language
            )
            
            logger.info(
                f"OCR extraction completed - "
                f"Confidence: {result.overall_confidence:.2%}, "
                f"Texts: {result.text_count}"
            )
            
            return result.to_dict()
        
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise ProcessingException(f"OCR extraction failed: {str(e)}")
    
    def is_initialized(self) -> bool:
        """Check if OCR pipeline is initialized."""
        return self._initialized
