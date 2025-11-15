"""
ROSETTA OCR Extraction Pipeline
PaddleOCR-based multi-language text extraction with confidence filtering.
Supports: English, Arabic, Tamil, Hindi

Refactored into modular components:
- ocr.py: Main OCR pipeline orchestration
- utils/language_detection.py: Language detection and enum
- utils/models.py: Data models (ExtractedText, OCRMetadata, OCRExtractionResult)
- utils/preprocessing.py: Image preprocessing utilities
- utils/paddle_parser.py: PaddleOCR result parsing
- utils/deduplication.py: Spatial deduplication for multi-language extraction

Usage in API:
    from backend.ocr.ocr import OCRPipeline, Language
    
    pipeline = OCRPipeline(default_language=Language.ENGLISH)
    result = pipeline.extract("document.jpg")
    json_output = result.to_dict()
    
Utility Usage:
    from backend.ocr.utils import (
        Language, LanguageDetector,
        ExtractedText, OCRMetadata, OCRExtractionResult,
        ImagePreprocessor, PaddleOCRParser, SpatialDeduplicator
    )
"""

from paddleocr import PaddleOCR
from typing import List, Dict, Tuple, Optional, Union
import time
import uuid
import tempfile
import os
import json
import argparse
import logging
from pathlib import Path

# Import utility modules
from .utils import (
    Language,
    LanguageDetector,
    ExtractedText,
    OCRMetadata,
    OCRExtractionResult,
    ImagePreprocessor,
    PaddleOCRParser,
    SpatialDeduplicator
)

try:
    from pdf2image import convert_from_path, convert_from_bytes
    _HAS_PDF2IMAGE = True
except Exception:
    convert_from_path = None
    convert_from_bytes = None
    _HAS_PDF2IMAGE = False

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



















class OCRPipeline:
    """
    PaddleOCR-based extraction pipeline with confidence filtering.
    
    Features:
    - Multi-language support (English, Arabic, Tamil, Hindi)
    - Confidence filtering (default threshold: 0.80)
    - Overall confidence calculation (excludes low-confidence text)
    - Bounding box extraction for frontend highlighting
    - Automatic language detection and switching
    - Binary data support for API integration
    
    Example:
        >>> pipeline = OCRPipeline()
        >>> result = pipeline.extract("document.jpg")
        >>> print(result.overall_confidence)
        0.92
        
        # For API use with binary data:
        >>> with open("doc.jpg", "rb") as f:
        ...     result = pipeline.extract_from_bytes(f.read())
    """
    
    # Class-level cache for OCR engines (one per language)
    _engine_cache: Dict[str, PaddleOCR] = {}
    
    def __init__(
        self,
        default_language: Union[str, Language] = Language.ENGLISH,
        confidence_threshold: float = 0.80,
        use_gpu: bool = False,
        use_textline_orientation: bool = True,
        enable_preprocessing: bool = True,
        auto_detect_language: bool = False,
        multi_language_mode: bool = False,
        do_denoise: bool = True,
        do_deskew: bool = True,
        do_contrast: bool = True,
        do_sharpen: bool = True,
        # Performance optimizations
        rec_batch_num: int = 6,
        det_db_thresh: float = 0.3,
        det_db_box_thresh: float = 0.6,
        max_side_len: int = 960,
        use_dilation: bool = False
    ):
        """
        Initialize OCR Pipeline.
        
        Args:
            default_language: Default language for OCR (en, ar, ta, hi)
            confidence_threshold: Minimum confidence for text inclusion (0.0-1.0)
            use_gpu: Enable GPU acceleration if available
            use_textline_orientation: Enable automatic rotation detection
            enable_preprocessing: Enable automatic image preprocessing
            auto_detect_language: Auto-detect language from image content
            multi_language_mode: Extract text in ALL detected languages (slower but comprehensive)
            rec_batch_num: Recognition batch size (higher = faster but more memory)
            det_db_thresh: Detection threshold (lower = more sensitive, slower)
            det_db_box_thresh: Box threshold (higher = faster, may miss text)
            max_side_len: Max image dimension (lower = faster but less accurate)
            use_dilation: Use morphological dilation (slower but better for small text)
        """
        if isinstance(default_language, str):
            self.default_language = Language.from_string(default_language)
        else:
            self.default_language = default_language
            
        self.confidence_threshold = max(0.0, min(1.0, confidence_threshold))  # Clamp 0-1
        self.use_gpu = use_gpu
        self.use_textline_orientation = use_textline_orientation
        self.enable_preprocessing = enable_preprocessing
        self.auto_detect_language = auto_detect_language
        self.multi_language_mode = multi_language_mode
        
        # Performance parameters
        self.rec_batch_num = rec_batch_num
        self.det_db_thresh = det_db_thresh
        self.det_db_box_thresh = det_db_box_thresh
        self.max_side_len = max_side_len
        self.use_dilation = use_dilation
        
        # Preprocessing step toggles
        self.do_denoise = do_denoise
        self.do_deskew = do_deskew
        self.do_contrast = do_contrast
        self.do_sharpen = do_sharpen

        logger.info(
            f"OCRPipeline initialized - Language: {self.default_language.value}, "
            f"Threshold: {self.confidence_threshold}, GPU: {self.use_gpu}, "
            f"Auto-detect: {self.auto_detect_language}, Multi-lang: {self.multi_language_mode}, "
            f"Batch: {self.rec_batch_num}, MaxSide: {self.max_side_len}"
        )
        
    def _get_ocr_engine(self, language: Language) -> PaddleOCR:
        """
        Get or create OCR engine for specified language.
        Uses class-level caching to avoid reloading models.
        Thread-safe for single-user deployment.
        """
        lang_code = language.value
        
        if lang_code not in self._engine_cache:
            logger.info(f"Loading PaddleOCR model for language: {lang_code}")
            # Build kwargs dynamically by filtering to supported PaddleOCR args
            paddleo_args = {
                'lang': lang_code,
                'use_textline_orientation': self.use_textline_orientation,
                'text_recognition_batch_size': self.rec_batch_num,
                'text_det_thresh': self.det_db_thresh,
                'text_det_box_thresh': self.det_db_box_thresh,
                'max_side_len': self.max_side_len,
                'use_dilation': self.use_dilation,
            }

            # Filter to only include kwargs present in PaddleOCR constructor
            try:
                from inspect import signature
                sig = signature(PaddleOCR.__init__)
                accepted_params = set(p for p in sig.parameters.keys() if p != 'self')
            except Exception:
                # If reflection fails, fall back to safe minimal args
                accepted_params = {'lang', 'use_textline_orientation'}

            filtered_kwargs = {k: v for k, v in paddleo_args.items() if k in accepted_params}
            logger.info(f"PaddleOCR kwargs accepted: {list(filtered_kwargs.keys())}")
            try:
                self._engine_cache[lang_code] = PaddleOCR(**filtered_kwargs)
            except TypeError as e:
                # In case a parameter causes error (e.g., incompatible value/type), try a minimal fallback
                logger.warning(f"PaddleOCR constructor rejected some args: {e}. Falling back to minimal args.")
                try:
                    self._engine_cache[lang_code] = PaddleOCR(lang=lang_code, use_textline_orientation=self.use_textline_orientation)
                except Exception as e2:
                    logger.error(f"Failed to instantiate PaddleOCR with minimal args: {e2}")
                    raise
            logger.info(f"Model loaded successfully: {lang_code}")
        
        return self._engine_cache[lang_code]

    def get_supported_paddle_args(self, language: Optional[Language] = None) -> List[str]:
        """Return a list of supported kwargs for the installed PaddleOCR constructor.

        Useful for debugging and keeping `.github/copilot-instructions.md` up-to-date.
        """
        try:
            from inspect import signature
            sig = signature(PaddleOCR.__init__)
            accepted_params = [p for p in sig.parameters.keys() if p != 'self']
            return accepted_params
        except Exception:
            return ['lang', 'use_textline_orientation']
    
    @staticmethod
    def clear_cache():
        """Clear all cached OCR engines. Useful for memory management."""
        OCRPipeline._engine_cache.clear()
        logger.info("OCR engine cache cleared")
    
    def _parse_paddleocr_result(self, result: List) -> List[Tuple[str, float, Optional[List[int]]]]:
        """Parse PaddleOCR result using utility parser."""
        return PaddleOCRParser.parse_result(result)
    
    def _preprocess_image(self, image_path: str) -> str:
        """Run preprocessing pipeline using ImagePreprocessor utility."""
        if not self.enable_preprocessing:
            return image_path
        
        try:
            preprocessor = ImagePreprocessor(
                do_denoise=self.do_denoise,
                do_deskew=self.do_deskew,
                do_contrast=self.do_contrast,
                do_sharpen=self.do_sharpen
            )
            return preprocessor.preprocess_image(image_path)
        except ImportError:
            logger.warning("OpenCV is not installed; preprocessing is disabled.")
            return image_path
        except Exception as e:
            logger.warning(f"Preprocessing failed: {e}")
            return image_path
    
    def extract(
        self,
        image_path: Union[str, Path],
        language: Optional[Union[str, Language]] = None,
        document_id: Optional[str] = None
    ) -> OCRExtractionResult:
        """
        Extract text from image file with confidence filtering.
        
        Args:
            image_path: Path to image file or PDF
            language: Language override (uses default if None)
            document_id: Optional document ID (generates UUID if None)
        
        Returns:
            OCRExtractionResult with filtered text and metadata
            
        Raises:
            FileNotFoundError: If image_path doesn't exist
            ValueError: If image format is unsupported
        """
        # Validate file exists
        path_obj = Path(image_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Validate file extension
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.pdf'}
        if path_obj.suffix.lower() not in supported_formats:
            raise ValueError(f"Unsupported format: {path_obj.suffix}. Supported: {supported_formats}")
        
        return self._extract_internal(str(path_obj), language, document_id)
    
    def extract_from_bytes(
        self,
        image_bytes: bytes,
        language: Optional[Union[str, Language]] = None,
        document_id: Optional[str] = None,
        file_extension: str = '.jpg'
    ) -> OCRExtractionResult:
        """
        Extract text from image bytes (for API integration).
        Creates temporary file, extracts, then cleans up.
        
        Args:
            image_bytes: Image data as bytes
            language: Language override (uses default if None)
            document_id: Optional document ID (generates UUID if None)
            file_extension: File extension hint for temp file (.jpg, .png, etc.)
        
        Returns:
            OCRExtractionResult with filtered text and metadata
        """
        # Create temporary file
        # If bytes correspond to a PDF, override file_extension
        if image_bytes[:5] == b'%PDF-':
            file_extension = '.pdf'
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=file_extension,
            mode='wb'
        ) as temp_file:
            temp_file.write(image_bytes)
            temp_path = temp_file.name
        
        try:
            result = self._extract_internal(temp_path, language, document_id)
            return result
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_path}: {e}")
    
    def _extract_internal(
        self,
        image_path: str,
        language: Optional[Union[str, Language]] = None,
        document_id: Optional[str] = None
    ) -> OCRExtractionResult:
        """Internal extraction logic shared by extract() and extract_from_bytes()."""
        start_time = time.time()
        
        # Generate document ID
        doc_id = document_id or str(uuid.uuid4())
        
        # Multi-language mode: extract with ALL detected languages
        if self.multi_language_mode and language is None:
            return self._extract_multi_language(image_path, doc_id, start_time)
        
        # Resolve language with auto-detection
        if language is None:
            if self.auto_detect_language:
                logger.info("Auto-detecting language from image...")
                detected_lang = LanguageDetector.detect_from_file_single(image_path)
                logger.info(f"Detected language: {detected_lang.value}")
                lang = detected_lang
            else:
                lang = self.default_language
        elif isinstance(language, str):
            lang = Language.from_string(language)
        else:
            lang = language
        
        logger.info(f"Starting extraction - Document: {doc_id}, Language: {lang.value}")
        
        # Run OCR (handle potential PDF multipage and preprocessing)
        parsed_results = []  # list of tuples (text, score, bbox, page_number)
        try:
            ocr_engine = self._get_ocr_engine(lang)
            # If PDF, convert to images and process each page
            if Path(image_path).suffix.lower() == '.pdf':
                if not _HAS_PDF2IMAGE:
                    raise RuntimeError("pdf2image is required to process PDF files. Install with 'pip install pdf2image' and ensure poppler is installed.")
                assert convert_from_path is not None
                pages = convert_from_path(image_path, dpi=200)
                for page_idx, pil_img in enumerate(pages, start=1):
                    fd, tmp_path = tempfile.mkstemp(suffix='.png')
                    os.close(fd)
                    pil_img.save(tmp_path, format='PNG')
                    work_path = tmp_path
                    preproc_path = None
                    # Preprocess if requested
                    if self.enable_preprocessing:
                        preproc_path = self._preprocess_image(work_path)
                        if preproc_path and preproc_path != work_path:
                            work_path = preproc_path
                    raw_result = ocr_engine.ocr(work_path)
                    page_parsed = self._parse_paddleocr_result(raw_result)
                    for text, score, bbox in page_parsed:
                        parsed_results.append((text, score, bbox, page_idx))
                    # cleanup temp file(s)
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                    if self.enable_preprocessing and preproc_path and preproc_path != tmp_path:
                        try:
                            os.unlink(preproc_path)
                        except Exception:
                            pass
            else:
                work_path = image_path
                preproc_path = None
                if self.enable_preprocessing:
                    preproc_path = self._preprocess_image(work_path)
                    if preproc_path and preproc_path != work_path:
                        work_path = preproc_path
                raw_result = ocr_engine.ocr(work_path)
                page_parsed = self._parse_paddleocr_result(raw_result)
                for text, score, bbox in page_parsed:
                    parsed_results.append((text, score, bbox, 1))
                # Cleanup preprocessed temp file if created
                if self.enable_preprocessing and preproc_path and preproc_path != image_path:
                    try:
                        os.unlink(preproc_path)
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            # Return empty result with error warning
            return OCRExtractionResult(
                document_id=doc_id,
                extracted_text=[],
                overall_confidence=0.0,
                language_detected=lang.value,
                metadata={
                    "processing_time_ms": int((time.time() - start_time) * 1000),
                    "filtered_low_confidence_count": 0,
                    "total_text_regions": 0,
                    "language_detected": lang.value,
                    "auto_detected": self.auto_detect_language,
                    "multi_language": False
                },
                warnings=[f"OCR extraction failed: {str(e)}"]
            )
        
        # parsed_results is now populated; each item is (text, score, bbox, page_number)
        
        # Apply confidence filtering
        filtered_texts = []
        low_confidence_count = 0
        missing_bbox_count = 0
        confidence_sum = 0.0
        
        for item in parsed_results:
            if len(item) == 4:
                text, confidence, bbox, page_num = item
            else:
                text, confidence, bbox = item
                page_num = 1
            if confidence >= self.confidence_threshold:
                filtered_texts.append(
                    ExtractedText(text=text, confidence=confidence, bbox=bbox, language=lang.value, page_number=page_num)
                )
                confidence_sum += confidence
            else:
                low_confidence_count += 1
            if bbox is None:
                missing_bbox_count += 1
        
        # Calculate overall confidence (average of high-confidence texts only)
        overall_confidence = (confidence_sum / len(filtered_texts)) if filtered_texts else 0.0
        
        # Build metadata
        processing_time = int((time.time() - start_time) * 1000)
        metadata = OCRMetadata(
            processing_time_ms=processing_time,
            filtered_low_confidence_count=low_confidence_count,
            total_text_regions=len(parsed_results),
            language_detected=lang.value
        )
        metadata_dict = metadata.to_dict()
        metadata_dict['missing_bbox_count'] = missing_bbox_count
        metadata_dict['auto_detected'] = self.auto_detect_language
        metadata_dict['multi_language'] = False
        
        # Generate warnings
        warnings = self._generate_warnings(
            overall_confidence, 
            low_confidence_count, 
            len(filtered_texts)
        )
        if missing_bbox_count > 0:
            warnings.append(f"{missing_bbox_count} text regions are missing bounding boxes; frontend may not be able to highlight these.")
        
        logger.info(
            f"Extraction complete - Texts: {len(filtered_texts)}, "
            f"Confidence: {overall_confidence:.2%}, Time: {processing_time}ms"
        )
        
        return OCRExtractionResult(
            document_id=doc_id,
            extracted_text=[text.to_dict() for text in filtered_texts],
            overall_confidence=round(overall_confidence, 4),
            language_detected=lang.value,
            metadata=metadata_dict,
            warnings=warnings
        )
    
    def _extract_multi_language(
        self,
        image_path: str,
        document_id: str,
        start_time: float
    ) -> OCRExtractionResult:
        """
        Extract text using multiple language models (for multi-language documents).
        Detects all languages present and runs OCR with each model, merging results.
        """
        logger.info("Multi-language mode: detecting all languages...")
        detected_languages = LanguageDetector.detect_from_file_all(image_path)
        
        if not detected_languages:
            detected_languages = [Language.ENGLISH]
        
        logger.info(f"Detected languages: {[lang.value for lang in detected_languages]}")
        
        # Extract with each language model (handle PDF multipage and preprocessing)
        all_results = []
        all_parsed_results = []
        
        if Path(image_path).suffix.lower() == '.pdf':
            if not _HAS_PDF2IMAGE:
                raise RuntimeError("pdf2image required for PDF multi-language extraction")
            assert convert_from_path is not None
            pages = convert_from_path(image_path, dpi=200)
            for page_idx, pil_img in enumerate(pages, start=1):
                fd, tmp_path = tempfile.mkstemp(suffix='.png')
                os.close(fd)
                pil_img.save(tmp_path, format='PNG')
                work_path = tmp_path
                preproc_path = None
                if self.enable_preprocessing:
                    preproc_path = self._preprocess_image(work_path)
                    if preproc_path and preproc_path != work_path:
                        work_path = preproc_path
                for lang in detected_languages:
                    try:
                        logger.info(f"Extracting with {lang.value} model on page {page_idx}...")
                        ocr_engine = self._get_ocr_engine(lang)
                        raw_result = ocr_engine.ocr(work_path)
                        parsed = self._parse_paddleocr_result(raw_result)
                        for text, confidence, bbox in parsed:
                            all_parsed_results.append((text, confidence, bbox, lang.value, page_idx))
                    except Exception as e:
                        logger.warning(f"Extraction with {lang.value} on page {page_idx} failed: {e}")
                        continue
                # Cleanup temp files for this page
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                if preproc_path and preproc_path != tmp_path:
                    try:
                        os.unlink(preproc_path)
                    except Exception:
                        pass
        else:
            work_path = image_path
            preproc_path = None
            if self.enable_preprocessing:
                preproc_path = self._preprocess_image(work_path)
                if preproc_path and preproc_path != work_path:
                    work_path = preproc_path
            for lang in detected_languages:
                try:
                    logger.info(f"Extracting with {lang.value} model...")
                    ocr_engine = self._get_ocr_engine(lang)
                    raw_result = ocr_engine.ocr(work_path)
                    parsed = self._parse_paddleocr_result(raw_result)
                    for text, confidence, bbox in parsed:
                        all_parsed_results.append((text, confidence, bbox, lang.value, 1))
                except Exception as e:
                    logger.warning(f"Extraction with {lang.value} failed: {e}")
                    continue
            # cleanup preproc
            if self.enable_preprocessing and preproc_path and preproc_path != work_path:
                try:
                    os.unlink(preproc_path)
                except Exception:
                    pass
        
        # Deduplicate results by spatial proximity
        # If two text regions overlap significantly, keep the one with higher confidence
        deduplicated_results = self._deduplicate_spatial(all_parsed_results)
        
        # Apply confidence filtering
        filtered_texts = []
        low_confidence_count = 0
        missing_bbox_count = 0
        confidence_sum = 0.0
        
        for item in deduplicated_results:
            if len(item) == 5:
                text, confidence, bbox, lang_code, page_num = item
            else:
                text, confidence, bbox, lang_code = item
                page_num = 1
            if confidence >= self.confidence_threshold:
                # Add language tag to extracted text
                text_obj = ExtractedText(text=text, confidence=confidence, bbox=bbox, language=lang_code, page_number=page_num)
                text_dict = text_obj.to_dict()
                filtered_texts.append(text_dict)
                confidence_sum += confidence
            else:
                low_confidence_count += 1
            if bbox is None:
                missing_bbox_count += 1
        
        # Calculate overall confidence
        overall_confidence = (confidence_sum / len(filtered_texts)) if filtered_texts else 0.0
        
        # Build metadata
        processing_time = int((time.time() - start_time) * 1000)
        lang_list = [lang.value for lang in detected_languages]
        
        metadata_dict = {
            "processing_time_ms": processing_time,
            "filtered_low_confidence_count": low_confidence_count,
            "total_text_regions": len(all_parsed_results),
            "language_detected": lang_list,  # List of all languages
            "auto_detected": True,
            "multi_language": True
        }
        metadata_dict['missing_bbox_count'] = missing_bbox_count
        
        # Generate warnings
        warnings = self._generate_warnings(
            overall_confidence, 
            low_confidence_count, 
            len(filtered_texts)
        )
        if missing_bbox_count > 0:
            warnings.append(f"{missing_bbox_count} text regions are missing bounding boxes; frontend may not be able to highlight these.")
        
        if len(detected_languages) > 1:
            warnings.append(f"Multi-language document detected: {', '.join(lang_list)}")
        
        logger.info(
            f"Multi-language extraction complete - Languages: {lang_list}, "
            f"Texts: {len(filtered_texts)}, Confidence: {overall_confidence:.2%}"
        )
        
        return OCRExtractionResult(
            document_id=document_id,
            extracted_text=filtered_texts,
            overall_confidence=round(overall_confidence, 4),
            language_detected='+'.join(lang_list),  # e.g., "en+ar+ta"
            metadata=metadata_dict,
            warnings=warnings
        )
    
    def _deduplicate_spatial(
        self,
        results: List[Tuple]
    ) -> List[Tuple]:
        """Remove duplicate text regions using SpatialDeduplicator utility."""
        return SpatialDeduplicator.deduplicate(results, iou_threshold=0.5)
    
    def _generate_warnings(
        self, 
        overall_confidence: float, 
        low_confidence_count: int, 
        high_confidence_count: int
    ) -> List[str]:
        """Generate contextual warnings based on extraction results."""
        warnings = []
        
        if overall_confidence == 0.0:
            warnings.append("No text extracted above confidence threshold.")
        elif overall_confidence < 0.5:
            warnings.append("Overall confidence is very low (<50%). Document may be poor quality.")
        elif overall_confidence < 0.7:
            warnings.append("Overall confidence is low (<70%). Manual review recommended.")
        
        if low_confidence_count > high_confidence_count and high_confidence_count > 0:
            warnings.append(
                f"High number of low-confidence regions filtered ({low_confidence_count} vs {high_confidence_count})."
            )
        
        if high_confidence_count == 0:
            warnings.append("Document may be unreadable, damaged, or in unsupported language.")
        
        return warnings


def create_pipeline(
    language: str = "en",
    confidence_threshold: float = 0.80,
    use_gpu: bool = False,
    performance_mode: str = "balanced",
    enable_preprocessing: bool = False,
    do_denoise: bool = True,
    do_deskew: bool = True,
    do_contrast: bool = True,
    do_sharpen: bool = True
) -> OCRPipeline:
    """
    Factory function to create OCRPipeline instance.
    Convenience function for API integration.
    
    Args:
        language: Language code (en, ar, ta, hi)
        confidence_threshold: Minimum confidence (0.0-1.0)
        use_gpu: Enable GPU acceleration
        performance_mode: 'fast', 'balanced', or 'accurate'
    
    Returns:
        Configured OCRPipeline instance
    
    Performance Modes:
        - fast: 2-3x faster, slightly lower accuracy, good for high-quality scans
        - balanced: Default settings, good trade-off
        - accurate: Slower but best for poor quality/small text
    """
    # Performance presets
    if performance_mode == "fast":
        return OCRPipeline(
            default_language=language,
            confidence_threshold=confidence_threshold,
            use_gpu=use_gpu,
            rec_batch_num=10,  # Larger batches
            det_db_thresh=0.5,  # Less sensitive detection (faster)
            det_db_box_thresh=0.7,  # Higher threshold
            max_side_len=720,  # Smaller image size
            use_dilation=False,  # Skip dilation
            enable_preprocessing=enable_preprocessing,
            do_denoise=do_denoise,
            do_deskew=do_deskew,
            do_contrast=do_contrast,
            do_sharpen=do_sharpen
        )
    elif performance_mode == "accurate":
        return OCRPipeline(
            default_language=language,
            confidence_threshold=confidence_threshold,
            use_gpu=use_gpu,
            rec_batch_num=4,  # Smaller batches
            det_db_thresh=0.2,  # More sensitive detection
            det_db_box_thresh=0.5,  # Lower threshold
            max_side_len=1280,  # Larger image size
            use_dilation=True,  # Enable dilation for small text
            enable_preprocessing=enable_preprocessing,
            do_denoise=do_denoise,
            do_deskew=do_deskew,
            do_contrast=do_contrast,
            do_sharpen=do_sharpen
        )
    else:  # balanced (default)
        return OCRPipeline(
            default_language=language,
            confidence_threshold=confidence_threshold,
            use_gpu=use_gpu,
            rec_batch_num=6,
            det_db_thresh=0.3,
            det_db_box_thresh=0.6,
            max_side_len=960,
            use_dilation=False,
            enable_preprocessing=enable_preprocessing,
            do_denoise=do_denoise,
            do_deskew=do_deskew,
            do_contrast=do_contrast,
            do_sharpen=do_sharpen
        )


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="ROSETTA OCR Extraction Pipeline - Extract text from documents"
    )
    parser.add_argument("image", help="Path to the image file or PDF")
    parser.add_argument(
        "--lang", 
        default="en", 
        choices=["en", "english", "ar", "arabic", "ta", "tamil", "hi", "hindi"],
        help="Language for OCR (default: en)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.80,
        help="Confidence threshold for filtering (default: 0.80)"
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Use GPU acceleration if available"
    )
    parser.add_argument(
        "--auto-detect",
        action="store_true",
        help="Auto-detect language from image content"
    )
    parser.add_argument(
        "--multi-lang",
        action="store_true",
        help="Extract text in ALL languages present (comprehensive but slower)"
    )
    parser.add_argument(
        "--performance",
        choices=["fast", "balanced", "accurate"],
        default="balanced",
        help="Performance mode: fast (2-3x faster), balanced (default), accurate (slower, best quality)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Recognition batch size (higher = faster but more memory, default: auto-selected by mode)"
    )
    parser.add_argument(
        "--max-size",
        type=int,
        help="Max image dimension in pixels (lower = faster, default: auto-selected by mode)"
    )
    parser.add_argument(
        "--output",
        help="Save results to JSON file (optional)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print PaddleOCR accepted constructor args and continue"
    )
    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Enable preprocessing (denoise, deskew, contrast, sharpen)"
    )
    parser.add_argument(
        "--no-denoise",
        action="store_true",
        help="Disable denoising during preprocessing"
    )
    parser.add_argument(
        "--no-deskew",
        action="store_true",
        help="Disable deskew during preprocessing"
    )
    parser.add_argument(
        "--no-contrast",
        action="store_true",
        help="Disable contrast enhancement during preprocessing"
    )
    parser.add_argument(
        "--no-sharpen",
        action="store_true",
        help="Disable sharpening during preprocessing"
    )
    
    args = parser.parse_args()
    
    # Performance mode presets
    perf_presets = {
        "fast": {"rec_batch_num": 10, "max_side_len": 720, "det_db_thresh": 0.5, "det_db_box_thresh": 0.7},
        "balanced": {"rec_batch_num": 6, "max_side_len": 960, "det_db_thresh": 0.3, "det_db_box_thresh": 0.6},
        "accurate": {"rec_batch_num": 4, "max_side_len": 1280, "det_db_thresh": 0.2, "det_db_box_thresh": 0.5}
    }
    
    preset = perf_presets[args.performance]
    
    # Allow manual overrides
    if args.batch_size:
        preset["rec_batch_num"] = args.batch_size
    if args.max_size:
        preset["max_side_len"] = args.max_size
    
    # Initialize pipeline
    pipeline = OCRPipeline(
        default_language=args.lang,
        confidence_threshold=args.threshold,
        use_gpu=args.gpu,
        auto_detect_language=args.auto_detect,
        multi_language_mode=args.multi_lang,
        **preset
    )
    # Set preprocessing options
    pipeline.enable_preprocessing = args.preprocess
    pipeline.do_denoise = not args.no_denoise
    pipeline.do_deskew = not args.no_deskew
    pipeline.do_contrast = not args.no_contrast
    pipeline.do_sharpen = not args.no_sharpen

    if args.gpu:
        logger.info("GPU flag set: PaddlePaddle will auto-detect GPU at runtime; explicit GPU flag is advisory and is not passed to PaddleOCR constructor.")
    if args.debug:
        # Print supported args and continue
        try:
            print("PaddleOCR accepted constructor args:", pipeline.get_supported_paddle_args())
        except Exception as e:
            print("Failed to inspect PaddleOCR constructor args:", e)
    
    # Extract text
    print(f"\n🔍 Processing: {args.image}")
    print(f"📝 Language: {args.lang}")
    print(f"🎯 Confidence threshold: {args.threshold}\n")
    
    result = pipeline.extract(args.image)
    
    # Display results
    print("=" * 60)
    print(f"Document ID: {result.document_id}")
    print(f"Overall Confidence: {result.overall_confidence:.2%}")
    print(f"Language Detected: {result.language_detected}")
    print(f"Processing Time: {result.metadata['processing_time_ms']}ms")
    print(f"Text Regions Found: {result.metadata['total_text_regions']}")
    print(f"Low Confidence Filtered: {result.metadata['filtered_low_confidence_count']}")
    print(f"Missing Bounding Boxes: {result.metadata.get('missing_bbox_count', 0)}")
    print("=" * 60)
    
    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    print("\n📄 Extracted Text:\n")
    for idx, text_obj in enumerate(result.extracted_text, 1):
        print(f"{idx}. {text_obj['text']}")
        print(f"   Confidence: {text_obj['confidence']:.2%}")
        bbox_display = text_obj['bbox'] if text_obj['bbox'] is not None else 'N/A'
        print(f"   BBox: {bbox_display}\n")
        print(f"   Language: {text_obj.get('language')} | Page: {text_obj.get('page_number')}")
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"✅ Results saved to: {args.output}")
    
    print("\n✨ Done.")