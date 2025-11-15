"""
Data Models for OCR Extraction Results
Dataclasses for structured OCR output.
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional


@dataclass
class ExtractedText:
    """Represents a single extracted text region with metadata."""
    text: str
    confidence: float
    bbox: Optional[List[int]] = None  # [x, y, width, height] or None if unsupported
    language: Optional[str] = None
    page_number: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class OCRMetadata:
    """Metadata about the OCR extraction process."""
    processing_time_ms: int
    filtered_low_confidence_count: int
    total_text_regions: int
    language_detected: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class OCRExtractionResult:
    """Complete OCR extraction result with confidence filtering applied."""
    document_id: str
    extracted_text: List[Dict]
    overall_confidence: float
    language_detected: str
    metadata: Dict
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'document_id': self.document_id,
            'extracted_text': self.extracted_text,
            'overall_confidence': self.overall_confidence,
            'language_detected': self.language_detected,
            'metadata': self.metadata,
            'warnings': self.warnings
        }
    
    @property
    def text_count(self) -> int:
        """Number of extracted text regions."""
        return len(self.extracted_text)
    
    @property
    def has_warnings(self) -> bool:
        """Check if result has any warnings."""
        return len(self.warnings) > 0
    
    def get_concatenated_text(self, separator: str = " ") -> str:
        """Get all extracted text as a single string."""
        return separator.join(item['text'] for item in self.extracted_text)
    
    def get_high_confidence_text(self, threshold: float = 0.9) -> List[Dict]:
        """Filter and return only high-confidence text regions."""
        return [item for item in self.extracted_text if item['confidence'] >= threshold]
