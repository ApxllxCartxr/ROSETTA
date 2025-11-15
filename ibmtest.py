from pathlib import Path
from llama_cpp import Llama
import json

# Local model path
MODEL_PATH = Path(r"C:\Users\Joseph\Projects\ROSETTA\models\qwen2.5-1.5b-instruct-q4_k_m.gguf")

# NOTE: granite-4.0-micro Q2_K is too small/compressed for structured JSON tasks
# Recommended alternatives:
# - Qwen2.5-1.5B-Instruct (Q4_K_M) - 1GB, good for JSON
# - Llama-3.2-1B-Instruct (Q4_K_M) - 800MB, decent
# - Phi-3.5-mini-instruct (Q4_K_M) - 2.5GB, excellent but larger

llm = Llama(
	model_path=str(MODEL_PATH),
	n_ctx=2048,
	n_threads=8,
	verbose=False  # Reduce noise
)

# Comprehensive prompt for Qwen - structured field extraction
resp = llm.create_completion(
	prompt=(
		"You are a document field extraction system. Extract ALL fields from the OCR text below into a structured JSON format.\n\n"
		"INSTRUCTIONS:\n"
		"1. Output ONLY valid JSON (no markdown, no comments, no explanations)\n"
		"2. Use standardized field names in snake_case (e.g., full_name, date_of_birth, id_number)\n"
		"3. Each field must have: value, source_text, confidence (0.0-1.0), uncertain (boolean)\n"
		"4. Set uncertain=true if:\n"
		"   - Value is partially illegible or has OCR errors\n"
		"   - Multiple interpretations possible\n"
		"   - Field label is ambiguous\n"
		"5. Set confidence based on:\n"
		"   - 1.0: Perfect match, clear label and value\n"
		"   - 0.8-0.9: Minor OCR artifacts but readable\n"
		"   - 0.5-0.7: Significant OCR errors or unclear\n"
		"   - <0.5: Highly uncertain or guessed\n"
		"6. Preserve original formatting in source_text\n"
		"7. Exclude fields that are completely missing\n"
		"8. Handle common variations:\n"
		"   - Name/Full Name/Legal Name → full_name\n"
		"   - DOB/Date of Birth/Birth Date → date_of_birth\n"
		"   - ID/ID Number/Identification → id_number\n"
		"9. Parse dates into ISO format (YYYY-MM-DD) when possible\n"
		"10. Split compound fields if requested by schema\n\n"
		"EXAMPLE INPUT:\n"
		"Name: Alice M. Smith\n"
		"ID Number: A-99871\n"
		"Date of Birth: 07/11/1992\n\n"
		"EXAMPLE OUTPUT:\n"
		"{\n"
		'  "fields": {\n'
		'    "full_name": {\n'
		'      "value": "Alice M. Smith",\n'
		'      "source_text": "Name: Alice M. Smith",\n'
		'      "confidence": 1.0,\n'
		'      "uncertain": false\n'
		'    },\n'
		'    "id_number": {\n'
		'      "value": "A-99871",\n'
		'      "source_text": "ID Number: A-99871",\n'
		'      "confidence": 1.0,\n'
		'      "uncertain": false\n'
		'    },\n'
		'    "date_of_birth": {\n'
		'      "value": "1992-07-11",\n'
		'      "source_text": "Date of Birth: 07/11/1992",\n'
		'      "confidence": 0.95,\n'
		'      "uncertain": false\n'
		'    }\n'
		'  }\n'
		'}\n\n'
		"OCR TEXT TO PROCESS:\n"
		"Name: John Doe\n"
		"ID Number: 123456\n"
		"Date of Birth: 01/15/1990\n"
		"Address: 123 Main St, Springfield\n\n"
		"OUTPUT (valid JSON only):\n"
	),
	max_tokens=512,
	temperature=0.1,  # Slight randomness for better field detection
	stop=["\n\n\n", "OCR TEXT", "EXAMPLE"],  # Stop at section breaks
	stream=False
)

output = resp["choices"][0]["text"].strip()
print("=" * 60)
print("RAW OUTPUT:")
print(output)
print("=" * 60)

# Try to parse JSON
try:
	# Clean up common issues
	output_clean = output.strip()
	
	# Remove markdown code blocks
	if "```json" in output_clean:
		output_clean = output_clean.split("```json")[1].split("```")[0].strip()
	elif "```" in output_clean:
		output_clean = output_clean.split("```")[1].split("```")[0].strip()
	
	# Handle duplicate outputs (take first valid JSON only)
	if output_clean.count("{") > 1 and "}{" in output_clean:
		# Find matching braces for first complete object
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
	
	# Ensure we have valid JSON bounds
	if not output_clean.startswith("{"):
		brace_start = output_clean.find("{")
		if brace_start != -1:
			output_clean = output_clean[brace_start:]
	
	parsed = json.loads(output_clean)
	print("\n✓ PARSED JSON:")
	print(json.dumps(parsed, indent=2, ensure_ascii=False))
	
	# Analyze extraction quality
	if "fields" in parsed:
		fields = parsed["fields"]
		print(f"\n📊 EXTRACTION SUMMARY:")
		print(f"   Total fields extracted: {len(fields)}")
		for field_name, field_data in fields.items():
			conf = field_data.get("confidence", 0)
			unc = field_data.get("uncertain", False)
			status = "⚠️ UNCERTAIN" if unc else "✓"
			print(f"   {status} {field_name}: {field_data.get('value')} (confidence: {conf:.2f})")
	
	print("\n✅ SUCCESS - Comprehensive field extraction working!")
	
except json.JSONDecodeError as e:
	print(f"\n✗ FAILED TO PARSE JSON: {e}")
	if 'output_clean' in locals():
		print(f"\nCleaned output was:")
		print(output_clean[:500])
	else:
		print(f"\nRaw output was:")
		print(output[:500])
	print("\nTry adjusting stop tokens or prompt format.")
