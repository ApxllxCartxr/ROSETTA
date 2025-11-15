"""
OCR package initialization.
Makes OCR module importable as a package.
"""

from .ocr import OCRPipeline, create_pipeline
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

__all__ = [
    'OCRPipeline',
    'create_pipeline',
    'Language',
    'LanguageDetector',
    'ExtractedText',
    'OCRMetadata',
    'OCRExtractionResult',
    'ImagePreprocessor',
    'PaddleOCRParser',
    'SpatialDeduplicator'
]
