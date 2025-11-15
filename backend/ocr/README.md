# OCR Pipeline - API Integration Guide

## Overview

The OCR pipeline is now **fully modular and API-ready** with clean separation between core logic and CLI utilities. You can use it directly in your API without any CLI dependencies.

## Key Improvements

### ✅ **OOP Architecture**
- `OCRPipeline` class encapsulates all extraction logic
- Data classes for type-safe, structured outputs
- Enum-based language specification
- Factory function for quick instantiation

### ✅ **Binary Data Support**
```python
# Perfect for API file uploads
pipeline = OCRPipeline()
result = pipeline.extract_from_bytes(uploaded_bytes)
```

### ✅ **Enhanced Error Handling**
- File validation (existence, format)
- Graceful OCR failures with informative warnings
- Exception-safe temporary file cleanup

### ✅ **Rich Result Object**
```python
result = pipeline.extract("doc.jpg")

# Check success
if result.is_successful:
    print(f"Extracted {result.text_count} regions")

# Get concatenated text
full_text = result.get_concatenated_text()

# Filter high-confidence only
reliable = result.get_high_confidence_text(threshold=0.95)

# JSON output
json_data = result.to_dict()
```

### ✅ **Better Warnings**
- Contextual warnings based on confidence levels
- Quality assessment (very low < 50%, low < 70%)
- Unreadable document detection

### ✅ **Performance & Memory**
- Class-level model caching (no reloading per request)
- `clear_cache()` for memory management
- Logging for production debugging
- Confidence threshold clamping (0-1 validation)

### ✅ **Production-Ready**
- Thread-safe model caching (single-user deployment)
- Proper logging (can be disabled for APIs)
- Input validation and sanitization
- Comprehensive docstrings

## Quick Start

### Basic Usage (File Path)
```python
from backend.ocr.ocr_util import OCRPipeline

pipeline = OCRPipeline(default_language="en", confidence_threshold=0.80)
result = pipeline.extract("document.jpg")

print(f"Confidence: {result.overall_confidence:.2%}")
print(f"Text: {result.get_concatenated_text()}")
```

### API Usage (Binary Data)
```python
from backend.ocr.ocr_util import create_pipeline

# In your API endpoint
pipeline = create_pipeline(language="en", use_gpu=False)

# From uploaded file
with open("uploaded_file.jpg", "rb") as f:
    result = pipeline.extract_from_bytes(f.read())

# Return JSON
return result.to_dict()
```

## PDF & Multi-Page Example

The pipeline can process multi-page PDFs if `pdf2image` is installed (Poppler required on Windows/macOS). Example:

```python
from backend.ocr.ocr_util import create_pipeline

pipeline = create_pipeline(language="en", performance_mode="balanced", enable_preprocessing=True)

with open('document.pdf', 'rb') as f:
    pdf_bytes = f.read()

result = pipeline.extract_from_bytes(pdf_bytes, file_extension='.pdf')
print(result.to_dict())
```

### FastAPI Example
```python
from fastapi import FastAPI, UploadFile
from backend.ocr.ocr_util import create_pipeline

app = FastAPI()
ocr = create_pipeline(language="en", confidence_threshold=0.85)

@app.post("/api/extract")
async def extract_text(file: UploadFile):
    contents = await file.read()
    result = ocr.extract_from_bytes(contents)
    
    if not result.is_successful:
        return {"error": "Extraction failed", "warnings": result.warnings}
    
    return result.to_dict()
```

### Multi-Language
```python
from backend.ocr.ocr_util import OCRPipeline, Language

# English
pipeline_en = OCRPipeline(default_language=Language.ENGLISH)

# Arabic
pipeline_ar = OCRPipeline(default_language=Language.ARABIC)

# Tamil
pipeline_ta = OCRPipeline(default_language=Language.TAMIL)

# Hindi
pipeline_hi = OCRPipeline(default_language=Language.HINDI)
```

## Output Format

```json
{
  "document_id": "uuid-v4-string",
  "extracted_text": [
    {
      "text": "John Doe",
      "confidence": 0.95,
            "bbox": [10, 20, 100, 40],
            "language": "en"
    }
  ],
  "overall_confidence": 0.915,
  "language_detected": "en",
  "metadata": {
    "processing_time_ms": 1234,
    "filtered_low_confidence_count": 3,
    "total_text_regions": 15,
    "language_detected": "en"
  },
    "warnings": []
}
```

## CLI Usage (Optional)

The CLI is still available but completely separate:

```bash
# Basic extraction
python ocr-util.py document.jpg

# Multi-language
python ocr-util.py arabic_doc.jpg --lang ar --threshold 0.85

# Save to JSON
python ocr-util.py form.pdf --output results.json --gpu

# Verbose logging
python ocr-util.py doc.jpg --verbose
## Preprocessing Options
When processing photos or noisy scans, enable preprocessing to improve OCR accuracy:

```powershell
# Enable full preprocessing pipeline
python ocr-util.py doc.jpg --preprocess

# Disable specific steps
python ocr-util.py doc.jpg --preprocess --no-denoise --no-sharpen
```


# Debug information (print accepted PaddleOCR constructor args)
python ocr-util.py doc.jpg --debug
```

## Advanced Features

### Batch Processing
```python
pipeline = OCRPipeline()

results = []
for file_path in ["doc1.jpg", "doc2.jpg", "doc3.jpg"]:
    result = pipeline.extract(file_path)
    results.append(result.to_dict())

# Models cached, no reload overhead
```

### Memory Management
```python
# After processing large batch
OCRPipeline.clear_cache()  # Free up memory
```

### Quality Validation
```python
result = pipeline.extract("doc.jpg")

if result.overall_confidence < 0.7:
    # Reject low-quality documents
    return {"error": "Document quality too low", "confidence": result.overall_confidence}

# Filter for reliable text only
reliable_text = result.get_high_confidence_text(threshold=0.95)
```

## Error Handling

```python
try:
    result = pipeline.extract("document.jpg")
    
    if result.warnings:
        logger.warning(f"Extraction warnings: {result.warnings}")
    
    return result.to_dict()
    
except FileNotFoundError:
    return {"error": "File not found"}
except ValueError as e:
    return {"error": f"Invalid format: {e}"}
except Exception as e:
    return {"error": f"Extraction failed: {e}"}
```

## Dependencies

```powershell
# Create and activate conda environment
conda create -n rosetta python=3.10
conda activate rosetta

# Install PaddlePaddle (CPU version for Windows)
python -m pip install paddlepaddle==2.6.0 -i https://pypi.tuna.tsinghua.edu.cn/simple

# OR for CPU-only (simpler, recommended for most users):
pip install paddlepaddle

# Install PaddleOCR and dependencies
pip install paddleocr pillow opencv-python

# Optional for preprocessing and PDF multipage support
```powershell
pip install opencv-python numpy
pip install pdf2image
# On Windows, install Poppler for PDF support (e.g., via Chocolatey: choco install poppler)
```

# Verify installation
python -c "import paddle; print(paddle.__version__)"
python -c "from paddleocr import PaddleOCR; print('PaddleOCR imported successfully')"
```

**Note**: Do NOT install the package named `paddle` - you need `paddlepaddle` instead!

## PaddleOCR Parameter Compatibility

PaddleOCR's constructor parameters have changed across versions. The `OCRPipeline` in this repo dynamically inspects the installed PaddleOCR constructor and only passes supported kwargs to avoid errors like `Unknown argument: max_side_len`.

If you update PaddleOCR and rely on a new parameter, add it to `_get_ocr_engine` `paddleo_args` in `backend/ocr/ocr-util.py`. The pipeline will attempt to pass the param only if the installed PaddleOCR supports it.

### Bounding boxes and languages
Note: PaddleOCR may not always return bounding boxes or their shapes depending on the version and input. In the ROSETTA pipeline:
- `bbox` may be `null` in JSON when PaddleOCR did not provide a valid box.
- Each extracted text region includes a `language` field indicating the language of that region (e.g., `"en"`, `"ar"`).

Frontends should treat `bbox = null` as "no visual region available" and fall back to text-only highlights or manual correction.

### Inspect supported PaddleOCR args at runtime
You can check which args are supported by the PaddleOCR constructor on your environment by using:
```python
from backend.ocr.ocr_util import OCRPipeline
pipeline = OCRPipeline()
print(pipeline.get_supported_paddle_args())
```
This returns the parameter names accepted by the installed PaddleOCR constructor and is useful when updating parameters.

## Next Steps

This pipeline is ready for:
1. **Phase 2**: LLM field matching integration (Qwen1.5-0.5B)
2. **Phase 3**: Storage layer with TTL caching
3. **Phase 4**: RESTful API wrapper (FastAPI)

See `example_api_usage.py` for complete working examples.
