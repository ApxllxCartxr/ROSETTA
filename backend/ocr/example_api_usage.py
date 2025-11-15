"""
Example: Using OCR Pipeline in API contexts
Demonstrates clean integration without CLI dependencies.
"""

from ocr import OCRPipeline, Language, create_pipeline
import json


# ============================================================================
# Example 1: Basic file-based extraction
# ============================================================================
def example_file_extraction():
    """Simple file extraction - returns JSON-ready dict."""
    pipeline = OCRPipeline(default_language=Language.ENGLISH)
    result = pipeline.extract("sample_document.jpg")
    
    # Check if successful
    if result.is_successful:
        print(f"✓ Extracted {result.text_count} text regions")
        print(f"✓ Overall confidence: {result.overall_confidence:.2%}")
        
        # Get as JSON for API response
        return result.to_dict()
    else:
        print(f"✗ Extraction failed: {result.warnings}")
        return None


# ============================================================================
# Example 2: Binary data extraction (typical API upload)
# ============================================================================
def example_binary_extraction(image_bytes: bytes):
    """Extract from uploaded file bytes - perfect for FastAPI/Flask."""
    pipeline = create_pipeline(language="en", confidence_threshold=0.85)
    
    # No temp file management needed - handled internally
    result = pipeline.extract_from_bytes(image_bytes, file_extension='.jpg')
    
    return {
        "success": result.is_successful,
        "data": result.to_dict()
    }


# ============================================================================
# Example 3: Multi-language extraction
# ============================================================================
def example_multilingual():
    """Handle multiple languages dynamically."""
    # Create separate pipelines for different languages
    pipelines = {
        'en': OCRPipeline(default_language=Language.ENGLISH),
        'ar': OCRPipeline(default_language=Language.ARABIC),
        'ta': OCRPipeline(default_language=Language.TAMIL),
        'hi': OCRPipeline(default_language=Language.HINDI),
    }
    
    # Extract based on detected/specified language
    detected_lang = 'ar'  # Could come from language detection
    result = pipelines[detected_lang].extract("arabic_document.jpg")
    
    return result.to_dict()


# ============================================================================
# Example 4: Batch processing with single pipeline instance
# ============================================================================
def example_batch_processing(file_paths: list):
    """Process multiple documents efficiently - reuses cached models."""
    pipeline = OCRPipeline(confidence_threshold=0.80)
    
    results = []
    for file_path in file_paths:
        try:
            result = pipeline.extract(file_path)
            results.append({
                "file": file_path,
                "success": True,
                "data": result.to_dict()
            })
        except Exception as e:
            results.append({
                "file": file_path,
                "success": False,
                "error": str(e)
            })
    
    return results


# ============================================================================
# Example 5: FastAPI integration pattern
# ============================================================================
def example_fastapi_endpoint():
    """
    Pseudo-code showing how to use in FastAPI endpoint.
    
    Actual FastAPI code would be:
    
    from fastapi import FastAPI, UploadFile
    from backend.ocr.ocr_util import create_pipeline
    
    app = FastAPI()
    ocr_pipeline = create_pipeline(language="en", use_gpu=True)
    
    @app.post("/api/extract")
    async def extract_text(file: UploadFile):
        contents = await file.read()
        result = ocr_pipeline.extract_from_bytes(contents)
        return result.to_dict()
    """
    pass


# ============================================================================
# Example 6: Advanced - get only high confidence text
# ============================================================================
def example_high_confidence_only():
    """Filter for only very reliable text."""
    pipeline = OCRPipeline(confidence_threshold=0.80)
    result = pipeline.extract("document.jpg")
    
    # Get only text with >95% confidence
    high_conf_text = result.get_high_confidence_text(threshold=0.95)
    
    # Or get all text concatenated
    full_text = result.get_concatenated_text(separator="\n")
    
    return {
        "high_confidence_regions": high_conf_text,
        "full_text": full_text,
        "overall_confidence": result.overall_confidence
    }


# ============================================================================
# Example 7: Error handling and validation
# ============================================================================
def example_error_handling():
    """Proper error handling for production APIs."""
    pipeline = OCRPipeline()
    
    try:
        result = pipeline.extract("document.jpg")
        
        # Check warnings
        if result.warnings:
            print(f"⚠️ Warnings: {result.warnings}")
        
        # Validate quality thresholds
        if result.overall_confidence < 0.7:
            return {
                "status": "low_quality",
                "message": "Document quality too low for reliable extraction",
                "data": result.to_dict()
            }
        
        return {
            "status": "success",
            "data": result.to_dict()
        }
        
    except FileNotFoundError as e:
        return {"status": "error", "message": str(e)}
    except ValueError as e:
        return {"status": "error", "message": f"Invalid format: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Extraction failed: {e}"}


# ============================================================================
# Example 8: Memory management for long-running services
# ============================================================================
def example_memory_management():
    """Clear model cache when needed (e.g., after processing batch)."""
    pipeline = OCRPipeline()
    
    # Process documents...
    results = []
    for doc in ["doc1.jpg", "doc2.jpg", "doc3.jpg"]:
        results.append(pipeline.extract(doc))
    
    # Clear cached models to free memory
    OCRPipeline.clear_cache()
    
    return results


if __name__ == "__main__":
    print("OCR Pipeline API Usage Examples")
    print("=" * 60)
    print("\nThese examples show how to use the OCR pipeline")
    print("in API contexts without CLI dependencies.\n")
    
    # Example usage
    print("Example 1: Basic extraction")
    print("-" * 60)
    print("pipeline = OCRPipeline()")
    print("result = pipeline.extract('document.jpg')")
    print("json_output = result.to_dict()")
    print()
    
    print("Example 2: Binary data (API upload)")
    print("-" * 60)
    print("with open('document.jpg', 'rb') as f:")
    print("    result = pipeline.extract_from_bytes(f.read())")
    print()
    
    print("Example 3: Multi-language")
    print("-" * 60)
    print("pipeline_ar = OCRPipeline(default_language=Language.ARABIC)")
    print("result = pipeline_ar.extract('arabic_doc.jpg')")
    print()
    
    print("\nSee example_api_usage.py for complete examples!")
