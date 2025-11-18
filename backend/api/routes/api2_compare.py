from fastapi import APIRouter, UploadFile, File, Form
from ocr.ocr import OCRPipeline   # ✅ FIXED IMPORT
import json
import difflib

router = APIRouter(
    prefix="/api/v2",
    tags=["API2 - Comparison"]
)

pipeline = OCRPipeline()

def score(text1, text2):
    """Return similarity score out of 100."""
    return int(difflib.SequenceMatcher(None, text1, text2).ratio() * 100)

@router.post("/compare")
async def compare(
    file: UploadFile = File(...),
    extracted_json: str = Form(...)
):
    # Load JSON output from API1
    old_data = json.loads(extracted_json)

    # Run OCR again on uploaded file
    content = await file.read()
    new_data = pipeline.extract_from_bytes(content).to_dict()

    # Combine all extracted text into one string
    old_text = " ".join([x["text"] for x in old_data["extracted_text"]])
    new_text = " ".join([x["text"] for x in new_data["extracted_text"]])

    # Compute similarity score
    similarity = score(old_text, new_text)

    # Compute word-by-word diff
    differences = list(difflib.unified_diff(
        old_text.split(),
        new_text.split(),
        lineterm=""
    ))

    return {
        "score": similarity,
        "old_data": old_data,
        "re_ocr": new_data,
        "differences": differences
    }
