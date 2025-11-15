# OCR Utilities Module

This directory contains modular utilities extracted from the main OCR pipeline for better maintainability and reusability.

## Module Structure

### `__init__.py`
Central export point for all utility classes and functions. Import utilities using:
```python
from backend.ocr.utils import Language, LanguageDetector, ExtractedText, ...
```

### `language_detection.py`
**Purpose**: Language detection and enumeration

**Classes**:
- `Language(Enum)`: Supported languages (ENGLISH, ARABIC, TAMIL, HINDI)
- `LanguageDetector`: Unicode-based language detection

**Key Methods**:
- `Language.from_string(lang: str)`: Convert string to Language enum
- `LanguageDetector.detect_language(text: str)`: Detect primary language from text
- `LanguageDetector.detect_all_languages(text: str)`: Detect all languages in text
- `LanguageDetector.detect_from_file_single(file_path: str)`: Detect from image file
- `LanguageDetector.detect_from_file_all(file_path: str)`: Detect all languages from file

**Example**:
```python
from backend.ocr.utils import Language, LanguageDetector

# Convert string to enum
lang = Language.from_string("ar")  # Language.ARABIC

# Detect from text
detected = LanguageDetector.detect_language("مرحبا")  # Language.ARABIC

# Detect from file
langs = LanguageDetector.detect_from_file_all("mixed_doc.jpg")  # [Language.ENGLISH, Language.ARABIC]
```

### `models.py`
**Purpose**: Data models for OCR results

**Classes**:
- `ExtractedText`: Single text region with metadata
- `OCRMetadata`: Processing metadata
- `OCRExtractionResult`: Complete extraction result

**Fields**:
- **ExtractedText**: `text`, `confidence`, `bbox`, `language`, `page_number`
- **OCRMetadata**: `processing_time_ms`, `filtered_low_confidence_count`, `total_text_regions`, `language_detected`
- **OCRExtractionResult**: `document_id`, `extracted_text`, `overall_confidence`, `language_detected`, `metadata`, `warnings`

**Example**:
```python
from backend.ocr.utils import ExtractedText, OCRExtractionResult

# Create extracted text
text = ExtractedText(
    text="John Doe",
    confidence=0.95,
    bbox=[10, 20, 100, 30],
    language="en",
    page_number=1
)

# Access result properties
result.text_count  # Number of regions
result.has_warnings  # Check for warnings
result.get_concatenated_text()  # All text as string
result.get_high_confidence_text(0.9)  # Filter by threshold
```

### `preprocessing.py`
**Purpose**: Image preprocessing for OCR quality improvement

**Classes**:
- `ImagePreprocessor`: Pipeline for image enhancement

**Features**:
- Denoising (bilateral filter)
- Deskewing (rotation correction)
- Contrast enhancement (CLAHE)
- Sharpening (unsharp mask)

**Example**:
```python
from backend.ocr.utils import ImagePreprocessor

preprocessor = ImagePreprocessor(
    do_denoise=True,
    do_deskew=True,
    do_contrast=True,
    do_sharpen=True
)

preprocessed_path = preprocessor.preprocess_image("input.jpg")
# Returns path to temporary preprocessed image
```

**Requirements**: Requires OpenCV (`pip install opencv-python`)

### `paddle_parser.py`
**Purpose**: PaddleOCR result parsing

**Classes**:
- `PaddleOCRParser`: Parser for PaddleOCR output formats

**Key Methods**:
- `parse_result(result: List)`: Parse PaddleOCR output to `(text, confidence, bbox)` tuples
- `normalize_bbox(bbox_coords)`: Normalize bbox to `[x, y, width, height]` format

**Handles**:
- Classic format: `[[bbox, (text, score)], ...]`
- Newer format: `[{'rec_texts': [...], 'rec_scores': [...], 'boxes': [...]}, ...]`
- Multi-page results
- Missing/malformed bounding boxes

**Example**:
```python
from backend.ocr.utils import PaddleOCRParser

# Parse PaddleOCR result
parsed = PaddleOCRParser.parse_result(ocr_result)
# Returns: [(text, confidence, bbox), ...]

# Normalize bbox
bbox = PaddleOCRParser.normalize_bbox([[10,20], [110,20], [110,50], [10,50]])
# Returns: [10, 20, 100, 30]
```

### `deduplication.py`
**Purpose**: Spatial deduplication for multi-language extraction

**Classes**:
- `SpatialDeduplicator`: Remove overlapping text regions

**Key Methods**:
- `deduplicate(results: List[Tuple], iou_threshold: float)`: Remove duplicates using IoU

**Algorithm**:
- Sorts by confidence (highest first)
- Calculates IoU (Intersection over Union) between regions
- Keeps highest-confidence region when overlap exceeds threshold

**Example**:
```python
from backend.ocr.utils import SpatialDeduplicator

# results: [(text, conf, bbox, page_num), ...]
deduplicated = SpatialDeduplicator.deduplicate(results, iou_threshold=0.5)
```

## Design Principles

1. **Modularity**: Each utility has a single, well-defined purpose
2. **Independence**: Utilities can be used standalone or together
3. **Backward Compatibility**: Main OCR pipeline functionality unchanged
4. **Error Handling**: Graceful degradation with logging
5. **Type Safety**: Type hints for all public methods

## Testing

To test utilities independently:

```python
# Test language detection
from backend.ocr.utils import LanguageDetector
lang = LanguageDetector.detect_language("Hello World")
assert lang.value == "en"

# Test preprocessing
from backend.ocr.utils import ImagePreprocessor
preprocessor = ImagePreprocessor()
path = preprocessor.preprocess_image("test.jpg")
assert os.path.exists(path)

# Test parser
from backend.ocr.utils import PaddleOCRParser
bbox = PaddleOCRParser.normalize_bbox([[0,0], [10,0], [10,10], [0,10]])
assert bbox == [0, 0, 10, 10]
```

## Migration Notes

If you have existing code importing from `ocr.py`, update imports:

**Before**:
```python
from backend.ocr.ocr import Language, OCRPipeline
```

**After** (unchanged):
```python
from backend.ocr.ocr import Language, OCRPipeline
```

**New** (direct utility access):
```python
from backend.ocr.utils import LanguageDetector, ImagePreprocessor
```

## Dependencies

- `paddleocr`: OCR engine (required)
- `opencv-python`: Image preprocessing (optional, required for `ImagePreprocessor`)
- `pdf2image`: PDF support (optional)
- `poppler`: PDF rendering backend (system dependency for pdf2image)

## Future Enhancements

Potential additions to this module:
- Field detection utilities (LLM-based field matching)
- Document storage utilities (caching, TTL management)
- Verification utilities (data comparison, confidence scoring)
- Additional preprocessing filters (binarization, noise removal variants)
