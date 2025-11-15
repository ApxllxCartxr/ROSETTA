"""
ROSETTA OCR Utilities Package
Modular utilities for OCR extraction pipeline.
"""

from .language_detection import Language, LanguageDetector
from .models import ExtractedText, OCRMetadata, OCRExtractionResult
from .preprocessing import ImagePreprocessor
from .paddle_parser import PaddleOCRParser
from .deduplication import SpatialDeduplicator

__all__ = [
    'Language',
    'LanguageDetector',
    'ExtractedText',
    'OCRMetadata',
    'OCRExtractionResult',
    'ImagePreprocessor',
    'PaddleOCRParser',
    'SpatialDeduplicator',
]
