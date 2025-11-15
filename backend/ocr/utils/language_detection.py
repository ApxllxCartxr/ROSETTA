"""
Language Detection Utilities
Supports: English, Arabic, Tamil, Hindi
"""

from enum import Enum
from typing import List
import logging

logger = logging.getLogger(__name__)


class Language(Enum):
    """Supported languages for OCR extraction."""
    ENGLISH = "en"
    ARABIC = "ar"
    TAMIL = "ta"
    HINDI = "hi"
    
    @classmethod
    def from_string(cls, lang: str) -> 'Language':
        """Convert string to Language enum."""
        lang_map = {
            'en': cls.ENGLISH,
            'english': cls.ENGLISH,
            'ar': cls.ARABIC,
            'arabic': cls.ARABIC,
            'ta': cls.TAMIL,
            'tamil': cls.TAMIL,
            'hi': cls.HINDI,
            'hindi': cls.HINDI,
            'devanagari': cls.HINDI,
        }
        return lang_map.get(lang.lower(), cls.ENGLISH)


class LanguageDetector:
    """Simple language detection based on Unicode character ranges."""
    
    # Unicode ranges for different scripts
    SCRIPT_RANGES = {
        'arabic': [(0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)],
        'tamil': [(0x0B80, 0x0BFF)],
        'hindi': [(0x0900, 0x097F)],  # Devanagari script
        'latin': [(0x0000, 0x007F), (0x0080, 0x00FF), (0x0100, 0x017F), (0x0180, 0x024F)],
    }
    
    @classmethod
    def detect_language(cls, text: str, threshold: float = 0.3) -> Language:
        """
        Detect language based on character script analysis.
        
        Args:
            text: Text to analyze
            threshold: Minimum ratio of script characters to detect (0.0-1.0)
        
        Returns:
            Detected Language enum (defaults to ENGLISH if uncertain)
        """
        if not text or not text.strip():
            return Language.ENGLISH
        
        # Count characters in each script
        script_counts = {script: 0 for script in cls.SCRIPT_RANGES}
        total_chars = 0
        
        for char in text:
            char_code = ord(char)
            for script, ranges in cls.SCRIPT_RANGES.items():
                if any(start <= char_code <= end for start, end in ranges):
                    script_counts[script] += 1
                    total_chars += 1
                    break
        
        if total_chars == 0:
            return Language.ENGLISH
        
        # Calculate ratios
        script_ratios = {script: count / total_chars for script, count in script_counts.items()}
        
        # Map scripts to languages
        if script_ratios.get('arabic', 0) >= threshold:
            return Language.ARABIC
        elif script_ratios.get('tamil', 0) >= threshold:
            return Language.TAMIL
        elif script_ratios.get('hindi', 0) >= threshold:
            return Language.HINDI
        else:
            return Language.ENGLISH
    
    @classmethod
    def detect_all_languages(cls, text: str, threshold: float = 0.05) -> List[Language]:
        """
        Detect ALL languages present in text (for multi-language documents).
        
        Args:
            text: Text to analyze
            threshold: Minimum ratio to consider a language present
        
        Returns:
            List of detected Language enums (at least ENGLISH if none detected)
        """
        if not text or not text.strip():
            return [Language.ENGLISH]
        
        # Count characters in each script
        script_counts = {script: 0 for script in cls.SCRIPT_RANGES}
        total_chars = 0
        
        for char in text:
            char_code = ord(char)
            for script, ranges in cls.SCRIPT_RANGES.items():
                if any(start <= char_code <= end for start, end in ranges):
                    script_counts[script] += 1
                    total_chars += 1
                    break
        
        if total_chars == 0:
            return [Language.ENGLISH]
        
        # Calculate ratios
        script_ratios = {script: count / total_chars for script, count in script_counts.items()}
        
        # Map scripts to languages
        detected = []
        if script_ratios.get('arabic', 0) >= threshold:
            detected.append(Language.ARABIC)
        if script_ratios.get('tamil', 0) >= threshold:
            detected.append(Language.TAMIL)
        if script_ratios.get('hindi', 0) >= threshold:
            detected.append(Language.HINDI)
        if script_ratios.get('latin', 0) >= threshold or not detected:
            detected.append(Language.ENGLISH)
        
        return detected if detected else [Language.ENGLISH]
    
    @classmethod
    def detect_from_file_single(cls, file_path: str) -> Language:
        """
        Detect primary language from image file using OCR.
        Quick detection - reads first few text regions only.
        """
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(lang='en', use_textline_orientation=True)
            result = ocr.ocr(file_path, cls=True)
            
            # Extract text from first page
            sample_text = ""
            if result and result[0]:
                for item in result[0][:5]:  # Sample first 5 text regions
                    if isinstance(item, list) and len(item) >= 2:
                        sample_text += item[1][0] + " "
            
            return cls.detect_language(sample_text)
        except Exception as e:
            logger.warning(f"Language detection failed: {e}, defaulting to English")
            return Language.ENGLISH
    
    @classmethod
    def detect_from_file_all(cls, file_path: str) -> List[Language]:
        """
        Detect ALL languages present in image file using OCR.
        Comprehensive detection - reads more text regions.
        """
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(lang='en', use_textline_orientation=True)
            result = ocr.ocr(file_path, cls=True)
            
            # Extract text from first page
            sample_text = ""
            if result and result[0]:
                for item in result[0][:20]:  # Sample more regions for multi-lang
                    if isinstance(item, list) and len(item) >= 2:
                        sample_text += item[1][0] + " "
            
            return cls.detect_all_languages(sample_text)
        except Exception as e:
            logger.warning(f"Language detection failed: {e}, defaulting to English")
            return [Language.ENGLISH]
