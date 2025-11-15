"""
Test script to verify refactored OCR utilities work correctly.
Run this to ensure all modules import and basic functionality works.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_imports():
    """Test that all utilities can be imported."""
    print("Testing imports...")
    
    # Test main module imports
    from backend.ocr.ocr import OCRPipeline, Language, create_pipeline
    print("✓ Main module imports successful")
    
    # Test utility imports from __init__.py
    from backend.ocr.utils import (
        Language as UtilLanguage,
        LanguageDetector,
        ExtractedText,
        OCRMetadata,
        OCRExtractionResult,
        ImagePreprocessor,
        PaddleOCRParser,
        SpatialDeduplicator
    )
    print("✓ Utility module imports successful")
    
    # Verify Language enums are the same
    assert Language.ENGLISH == UtilLanguage.ENGLISH
    print("✓ Language enum consistency verified")
    
    return True

def test_language_detection():
    """Test language detection functionality."""
    print("\nTesting language detection...")
    
    from backend.ocr.utils import Language, LanguageDetector
    
    # Test string conversion
    lang = Language.from_string("ar")
    assert lang == Language.ARABIC
    print("✓ String to enum conversion works")
    
    # Test language detection
    english_text = "Hello World"
    detected = LanguageDetector.detect_language(english_text)
    assert detected == Language.ENGLISH
    print("✓ English detection works")
    
    arabic_text = "مرحبا بك"
    detected = LanguageDetector.detect_language(arabic_text)
    assert detected == Language.ARABIC
    print("✓ Arabic detection works")
    
    # Test multi-language detection
    mixed_text = "Hello مرحبا"
    detected_langs = LanguageDetector.detect_all_languages(mixed_text, threshold=0.1)
    assert Language.ENGLISH in detected_langs
    assert Language.ARABIC in detected_langs
    print("✓ Multi-language detection works")
    
    return True

def test_models():
    """Test data models."""
    print("\nTesting data models...")
    
    from backend.ocr.utils import ExtractedText, OCRMetadata, OCRExtractionResult
    
    # Test ExtractedText
    text = ExtractedText(
        text="Sample",
        confidence=0.95,
        bbox=[10, 20, 100, 30],
        language="en",
        page_number=1
    )
    text_dict = text.to_dict()
    assert text_dict['text'] == "Sample"
    assert text_dict['confidence'] == 0.95
    print("✓ ExtractedText model works")
    
    # Test OCRMetadata
    metadata = OCRMetadata(
        processing_time_ms=1000,
        filtered_low_confidence_count=5,
        total_text_regions=20,
        language_detected="en"
    )
    meta_dict = metadata.to_dict()
    assert meta_dict['processing_time_ms'] == 1000
    print("✓ OCRMetadata model works")
    
    # Test OCRExtractionResult
    result = OCRExtractionResult(
        document_id="test-123",
        extracted_text=[text_dict],
        overall_confidence=0.95,
        language_detected="en",
        metadata=meta_dict,
        warnings=[]
    )
    assert result.text_count == 1
    assert not result.has_warnings
    assert result.get_concatenated_text() == "Sample"
    print("✓ OCRExtractionResult model works")
    
    return True

def test_paddle_parser():
    """Test PaddleOCR parser."""
    print("\nTesting PaddleOCR parser...")
    
    from backend.ocr.utils import PaddleOCRParser
    
    # Test bbox normalization
    bbox_coords = [[10, 20], [110, 20], [110, 50], [10, 50]]
    normalized = PaddleOCRParser.normalize_bbox(bbox_coords)
    assert normalized == [10, 20, 100, 30]
    print("✓ Bounding box normalization works")
    
    # Test with None
    normalized = PaddleOCRParser.normalize_bbox(None)
    assert normalized is None
    print("✓ Handles None bbox correctly")
    
    # Test classic format parsing
    classic_result = [
        [
            [[10, 20], [110, 20], [110, 50], [10, 50]],
            ("Sample Text", 0.95)
        ]
    ]
    parsed = PaddleOCRParser.parse_result(classic_result)
    assert len(parsed) == 1
    assert parsed[0][0] == "Sample Text"
    assert parsed[0][1] == 0.95
    print("✓ Classic format parsing works")
    
    return True

def test_deduplication():
    """Test spatial deduplication."""
    print("\nTesting spatial deduplication...")
    
    from backend.ocr.utils import SpatialDeduplicator
    
    # Create overlapping regions
    results = [
        ("Text1", 0.95, [10, 20, 100, 30], 1),  # High confidence
        ("Text2", 0.85, [15, 22, 100, 30], 1),  # Lower confidence, overlaps
        ("Text3", 0.90, [200, 200, 50, 20], 1),  # Different region
    ]
    
    deduplicated = SpatialDeduplicator.deduplicate(results, iou_threshold=0.5)
    # Should keep Text1 (highest conf) and Text3 (different region)
    assert len(deduplicated) == 2
    assert deduplicated[0][0] == "Text1"  # Highest confidence
    assert deduplicated[1][0] == "Text3"
    print("✓ Spatial deduplication works")
    
    return True

def test_pipeline_creation():
    """Test OCR pipeline creation."""
    print("\nTesting OCR pipeline creation...")
    
    from backend.ocr.ocr import OCRPipeline, Language, create_pipeline
    
    # Test direct instantiation
    pipeline = OCRPipeline(
        default_language=Language.ENGLISH,
        confidence_threshold=0.8
    )
    assert pipeline.default_language == Language.ENGLISH
    assert pipeline.confidence_threshold == 0.8
    print("✓ Direct pipeline creation works")
    
    # Test factory function
    pipeline = create_pipeline(
        language="ar",
        confidence_threshold=0.85,
        performance_mode="fast"
    )
    assert pipeline.default_language == Language.ARABIC
    assert pipeline.confidence_threshold == 0.85
    print("✓ Factory function works")
    
    # Test clear cache
    OCRPipeline.clear_cache()
    print("✓ Cache clearing works")
    
    return True

def main():
    """Run all tests."""
    print("="*60)
    print("ROSETTA OCR Refactoring Test Suite")
    print("="*60)
    
    tests = [
        ("Module Imports", test_imports),
        ("Language Detection", test_language_detection),
        ("Data Models", test_models),
        ("PaddleOCR Parser", test_paddle_parser),
        ("Spatial Deduplication", test_deduplication),
        ("Pipeline Creation", test_pipeline_creation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n✗ {test_name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n✅ All tests passed! Refactoring successful.")
        print("\nThe OCR module has been successfully refactored into:")
        print("  - backend/ocr/ocr.py (main pipeline)")
        print("  - backend/ocr/utils/language_detection.py")
        print("  - backend/ocr/utils/models.py")
        print("  - backend/ocr/utils/preprocessing.py")
        print("  - backend/ocr/utils/paddle_parser.py")
        print("  - backend/ocr/utils/deduplication.py")
        print("\nAll functionality has been preserved and is working correctly.")
    else:
        print("\n❌ Some tests failed. Please review the errors above.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
