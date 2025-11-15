"""
Field Mapping Service - LLM-based dynamic field extraction.
Supports synonym understanding and compound field splitting.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from llama_cpp import Llama
import logging

from ..utils.exceptions import ProcessingException

logger = logging.getLogger(__name__)


class FieldMappingService:
    """
    LLM-based field mapping with dynamic schema support.
    
    Features:
    - Dynamic field extraction based on user schema
    - Synonym understanding (firstName = first_name = fname)
    - Compound field splitting (full_name → firstName + lastName)
    - Missing field handling (not_found flag)
    - Confidence scoring
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize field mapping service.
        
        Args:
            config: LLM configuration from config.yaml
        """
        self.config = config
        self._llm: Optional[Llama] = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize LLM model (lazy loading)."""
        if self._initialized:
            return
        
        try:
            llm_config = self.config.get("llm", {})
            model_path = llm_config.get("model_path")
            
            if not model_path:
                logger.warning("LLM model_path not configured - LLM field mapping disabled")
                self._initialized = False
                return
            
            model_file = Path(model_path)
            if not model_file.exists():
                logger.warning(f"LLM model not found: {model_path} - LLM field mapping disabled")
                logger.info("To enable LLM field mapping, download the model:")
                logger.info("  Model: Qwen2.5-1.5B-Instruct (Q4_K_M GGUF)")
                logger.info(f"  Place at: {model_path}")
                self._initialized = False
                return
            
            self._llm = Llama(
                model_path=str(model_file),
                n_ctx=llm_config.get("n_ctx", 2048),
                n_threads=llm_config.get("n_threads", 8),
                verbose=False
            )
            
            self._initialized = True
            logger.info(f"LLM model loaded: {model_path}")
        
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self._initialized = False
    
    def map_fields(
        self,
        ocr_result: Dict[str, Any],
        schema: Dict[str, Any],
        split_compound: bool = True
    ) -> Dict[str, Any]:
        """
        Map OCR text to user-defined fields using LLM.
        
        Args:
            ocr_result: OCR extraction result
            schema: User field schema
            split_compound: Enable compound field splitting
        
        Returns:
            Mapped fields dictionary
        
        Raises:
            ProcessingException: If mapping fails
        """
        if not self._initialized:
            self.initialize()
        
        if not self._llm:
            raise ProcessingException("LLM not initialized")
        
        start_time = time.time()
        
        try:
            # Extract OCR text
            ocr_text = self._format_ocr_text(ocr_result)
            
            # Build prompt
            prompt = self._build_prompt(ocr_text, schema, split_compound)
            
            # Run LLM
            response = self._llm.create_completion(
                prompt=prompt,
                max_tokens=self.config.get("llm", {}).get("max_tokens", 512),
                temperature=self.config.get("llm", {}).get("temperature", 0.1),
                stop=["\n\n\n", "OCR TEXT", "EXAMPLE"],
                stream=False
            )
            
            # Parse response
            output = response["choices"][0]["text"].strip()  # type: ignore
            mapped_fields = self._parse_llm_output(output, schema, ocr_text)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"Field mapping completed - "
                f"Fields: {len(mapped_fields)}, "
                f"Time: {processing_time}ms"
            )
            
            return {
                "fields": mapped_fields,
                "processing_time_ms": processing_time
            }
        
        except Exception as e:
            logger.error(f"Field mapping failed: {e}")
            raise ProcessingException(f"Field mapping failed: {str(e)}")
    
    def _format_ocr_text(self, ocr_result: Dict[str, Any]) -> str:
        """Format OCR result into plain text for LLM."""
        texts = ocr_result.get("extracted_text", [])
        
        lines = []
        for item in texts:
            text = item.get("text", "").strip()
            if text:
                lines.append(text)
        
        return "\n".join(lines)
    
    def _build_prompt(
        self,
        ocr_text: str,
        schema: Dict[str, Any],
        split_compound: bool
    ) -> str:
        """
        Build LLM prompt for intelligent form field mapping.
        
        Includes:
        - Form field context (labels, placeholders, types)
        - OCR extracted text
        - Few-shot examples
        - Logical reasoning instructions
        """
        # Build field descriptors with all available context
        field_descriptions = []
        for field in schema:
            if isinstance(field, dict):
                name = field.get('name', '')
                field_type = field.get('type', 'string')
                label = field.get('label', '')
                placeholder = field.get('placeholder', '')
                context = field.get('context', '')
                required = field.get('required', False)
                
                desc = f"- **{name}** (type: {field_type})"
                if required:
                    desc += " [REQUIRED]"
                hints = []
                if label:
                    hints.append(f"label: '{label}'")
                if placeholder:
                    hints.append(f"placeholder: '{placeholder}'")
                if context:
                    hints.append(f"context: '{context}'")
                if hints:
                    desc += f"\n  Hints: {', '.join(hints)}"
                field_descriptions.append(desc)
            else:
                field_descriptions.append(f"- {field}")
        
        fields_str = "\n".join(field_descriptions)
        
        prompt = f"""You are an intelligent form-filling assistant. Your task is to extract and map data from OCR text to specific form fields using LOGICAL REASONING and DATA CLEANING.

**CRITICAL EXTRACTION RULES**:
1. Extract ONLY the actual VALUE, NOT labels or prefixes
   ❌ BAD: "Phone Number: 7305754188"
   ✅ GOOD: "7305754188"

2. Clean and format data appropriately:
   - Phone: Extract ONLY digits (remove "Phone:", "Tel:", etc.)
   - Email: Extract ONLY email address (remove "Email:", "E-mail:", etc.)
   - Names: Extract ONLY the name (remove "Name:", "Full Name:", etc.)
   - Numbers: Extract ONLY numeric values
   - Dates: Format consistently (YYYY-MM-DD if possible)

3. Split compound fields intelligently:
   - "John Doe" → first_name: "John", last_name: "Doe"
   - "Alice Marie Smith" → first_name: "Alice", last_name: "Smith" (or "Marie Smith")
   - "123 Main St, Boston, MA 02101" → street: "123 Main St", city: "Boston", state: "MA", zip: "02101"

4. Use semantic reasoning:
   - If field is "phone" but OCR says "Contact: 555-1234", extract "555-1234"
   - If field is "email" but OCR says "mail:user@example.com", extract "user@example.com"
   - Match by MEANING, not just keywords

5. Return DICTIONARY (not array), matching EXACT field names from form

6. Set flags:
   - "not_found": true if field doesn't exist in OCR
   - "uncertain": true if extraction is ambiguous
   - confidence: 0.0-1.0 based on match quality

**FORM FIELDS TO FILL**:
{fields_str}

**FEW-SHOT EXAMPLES**:

Example 1 - Data Cleaning:
Form Fields:
- **firstName** (type: string), label: 'First Name'
- **lastName** (type: string), label: 'Last Name'  
- **phone** (type: phone), placeholder: 'Phone Number'

OCR Text:
Name: John Doe
Phone Number: 7305754188

Output:
{{
  "firstName": {{
    "value": "John",
    "source_text": "Name: John Doe",
    "confidence": 0.95,
    "uncertain": false,
    "not_found": false
  }},
  "lastName": {{
    "value": "Doe",
    "source_text": "Name: John Doe",
    "confidence": 0.95,
    "uncertain": false,
    "not_found": false
  }},
  "phone": {{
    "value": "7305754188",
    "source_text": "Phone Number: 7305754188",
    "confidence": 0.98,
    "uncertain": false,
    "not_found": false
  }}
}}

Example 2 - Semantic Matching:
Form Fields:
- **inputFieldContact** (type: text), placeholder: 'Enter your contact', context: 'contact form input'
- **userEmail** (type: email), label: 'Email Address'

OCR Text:
Contact: 7305754188
email:josephfernando2k5@gmail.com
Address: 123 Main St

Output:
{{
  "inputFieldContact": {{
    "value": "7305754188",
    "source_text": "Contact: 7305754188",
    "confidence": 0.92,
    "uncertain": false,
    "not_found": false
  }},
  "userEmail": {{
    "value": "josephfernando2k5@gmail.com",
    "source_text": "email:josephfernando2k5@gmail.com",
    "confidence": 0.98,
    "uncertain": false,
    "not_found": false
  }}
}}

Example 3 - Compound Field Splitting:
Form Fields:
- **first_name** (type: string)
- **last_name** (type: string)
- **email_address** (type: email)

OCR Text:
Full Name: Alice Marie Johnson
E-mail: alice.johnson@company.com
DOB: 1990-05-15

Output:
{{
  "first_name": {{
    "value": "Alice",
    "source_text": "Full Name: Alice Marie Johnson",
    "confidence": 0.95,
    "uncertain": false,
    "not_found": false
  }},
  "last_name": {{
    "value": "Johnson",
    "source_text": "Full Name: Alice Marie Johnson",
    "confidence": 0.95,
    "uncertain": false,
    "not_found": false
  }},
  "email_address": {{
    "value": "alice.johnson@company.com",
    "source_text": "E-mail: alice.johnson@company.com",
    "confidence": 0.98,
    "uncertain": false,
    "not_found": false
  }}
}}

**ACTUAL OCR TEXT FROM DOCUMENT**:
{ocr_text}

**YOUR TASK**:
Analyze the OCR text above and map it to the form fields using:
1. DATA CLEANING - Extract only actual values, remove labels
2. LOGICAL REASONING - Match by semantic meaning
3. FIELD SPLITTING - Split compound data (names, addresses)
4. EXACT FIELD NAMES - Use field names from form exactly as shown

Output valid JSON dictionary (not array) with EXACT field names:
"""
        return prompt
    
    def _parse_llm_output(
        self,
        output: str,
        schema: Dict[str, Any],
        ocr_text: str
    ) -> Dict[str, Any]:
        """Parse and validate LLM JSON output."""
        try:
            # Clean output
            output_clean = output.strip()
            
            # Remove markdown code blocks
            if "```json" in output_clean:
                output_clean = output_clean.split("```json")[1].split("```")[0].strip()
            elif "```" in output_clean:
                output_clean = output_clean.split("```")[1].split("```")[0].strip()
            
            # Handle duplicate outputs (take first valid JSON)
            if output_clean.count("{") > 1:
                brace_count = 0
                end_pos = 0
                for i, char in enumerate(output_clean):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                if end_pos > 0:
                    output_clean = output_clean[:end_pos]
            
            # Parse JSON
            parsed = json.loads(output_clean)
            
            # Validate and normalize
            result = {}
            
            # Get field names from schema (handle both dict and array formats)
            if isinstance(schema, list):
                field_names = [f.get('name', f) if isinstance(f, dict) else f for f in schema]
            else:
                field_names = list(schema.keys())
            
            for field_name in field_names:
                if field_name in parsed:
                    field_data = parsed[field_name]
                    
                    # Normalize structure
                    if isinstance(field_data, dict):
                        result[field_name] = {
                            "value": field_data.get("value", ""),
                            "source_text": field_data.get("source_text", ""),
                            "confidence": field_data.get("confidence", 0.0),
                            "uncertain": field_data.get("uncertain", False),
                            "not_found": field_data.get("not_found", False)
                        }
                    else:
                        # Handle simplified output
                        result[field_name] = {
                            "value": str(field_data),
                            "source_text": "",
                            "confidence": 0.8,
                            "uncertain": False,
                            "not_found": False
                        }
                else:
                    # Missing field
                    result[field_name] = {
                        "value": "",
                        "source_text": "",
                        "confidence": 0.0,
                        "uncertain": False,
                        "not_found": True
                    }
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output as JSON: {e}")
            logger.debug(f"LLM output was: {output[:500]}")
            
            # Fallback: return empty results for all fields
            if isinstance(schema, list):
                field_names = [f.get('name', f) if isinstance(f, dict) else f for f in schema]
            else:
                field_names = list(schema.keys())
            
            return {
                field_name: {
                    "value": "",
                    "source_text": "",
                    "confidence": 0.0,
                    "uncertain": True,
                    "not_found": True
                }
                for field_name in field_names
            }
    
    def is_initialized(self) -> bool:
        """Check if LLM is initialized."""
        return self._initialized
