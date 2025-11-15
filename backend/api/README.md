# ROSETTA API

Dynamic field mapping API for OCR document processing with browser extension support.

## Features

✅ **OCR Extraction** - Multi-language text extraction (English, Arabic, Tamil, Hindi)  
✅ **Dynamic Field Mapping** - LLM-based field extraction with user-defined schemas  
✅ **Synonym Understanding** - Intelligent field name matching  
✅ **Compound Field Splitting** - Automatic splitting (full_name → firstName + lastName)  
✅ **Async Job Processing** - Non-blocking document processing  
✅ **Browser Extension Ready** - CORS-enabled for web extensions  
✅ **In-Memory Cache** - Fast results with TTL-based expiration  

## Installation

### Prerequisites
- Python 3.10+
- PaddleOCR dependencies
- Qwen2.5-1.5B-Instruct GGUF model

### Install Dependencies

```bash
# Install Python packages
pip install fastapi uvicorn pydantic
pip install llama-cpp-python
pip install python-magic  # Optional, for MIME type validation
pip install pyyaml

# Install OCR dependencies (if not already installed)
pip install paddlepaddle paddleocr pillow pdf2image opencv-python

# Download LLM model
# Place qwen2.5-1.5b-instruct-q4_k_m.gguf in models/ directory
```

### Configuration

Edit `backend/api/config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8000

upload:
  max_file_size_mb: 10
  max_pdf_pages: 5

llm:
  model_path: "models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
```

## Usage

### Start API Server

```bash
cd backend/api
python main.py
```

Or with Uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

#### 1. Extract Text (OCR Only)

```bash
POST /api/v1/extract
Content-Type: multipart/form-data

file: <document file>
language: "en"  # Optional
preprocessing: true  # Optional
performance_mode: "balanced"  # fast | balanced | accurate
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2025-11-15T10:30:00Z",
  "websocket_url": "ws://localhost:8000/ws/jobs/..."
}
```

#### 2. Extract Fields (LLM Mapping)

```bash
POST /api/v1/fields/extract
Content-Type: multipart/form-data

document_id: "doc-123"  # From OCR extraction
schema_json: {
  "fields": {
    "firstName": "string",
    "lastName": "string",
    "email": "email",
    "dateOfBirth": {"type": "date", "format": "MM/DD/YYYY"}
  },
  "split_compound_fields": true
}
```

**Response:**
```json
{
  "job_id": "job-456",
  "status": "pending",
  "created_at": "2025-11-15T10:30:05Z"
}
```

#### 3. Process (OCR + Fields)

```bash
POST /api/v1/process
Content-Type: multipart/form-data

file: <document file>
schema_json: {"fields": {"firstName": "string", "lastName": "string"}}
language: "en"
use_llm: true
```

#### 4. Get Job Status

```bash
GET /api/v1/jobs/{job_id}
```

**Response:**
```json
{
  "job_id": "job-456",
  "status": "completed",
  "progress": 100,
  "result": {
    "fields": {
      "firstName": {
        "value": "John",
        "confidence": 0.95,
        "not_found": false
      },
      "email": {
        "value": "",
        "confidence": 0.0,
        "not_found": true
      }
    }
  }
}
```

#### 5. Get Document

```bash
GET /api/v1/documents/{document_id}
```

#### 6. Health Check

```bash
GET /api/v1/health
```

## Browser Extension Integration

### Example JavaScript

```javascript
// Upload and process document
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('schema_json', JSON.stringify({
  fields: {
    firstName: "string",
    lastName: "string",
    email: "email"
  }
}));

// Submit job
const response = await fetch('http://localhost:8000/api/v1/process', {
  method: 'POST',
  body: formData
});

const { job_id } = await response.json();

// Poll for results
const pollJob = async () => {
  const jobResponse = await fetch(`http://localhost:8000/api/v1/jobs/${job_id}`);
  const job = await jobResponse.json();
  
  if (job.status === 'completed') {
    const fields = job.result.fields;
    // Auto-fill form
    document.querySelector('[name="firstName"]').value = fields.firstName.value;
    document.querySelector('[name="lastName"]').value = fields.lastName.value;
  } else if (job.status === 'pending' || job.status === 'processing') {
    setTimeout(pollJob, 1000);  // Poll every second
  }
};

pollJob();
```

## Field Schema Format

### Simple Format
```json
{
  "fields": {
    "firstName": "string",
    "email": "email",
    "age": "number"
  }
}
```

### Advanced Format
```json
{
  "fields": {
    "firstName": {
      "type": "string",
      "required": true,
      "synonyms": ["first_name", "given_name", "fname"]
    },
    "dateOfBirth": {
      "type": "date",
      "format": "MM/DD/YYYY",
      "required": false
    }
  },
  "split_compound_fields": true
}
```

### Supported Field Types
- `string` / `text`
- `number` / `integer` / `float`
- `date`
- `email`
- `phone`
- `boolean`
- `url`

## Synonym Understanding

The LLM automatically understands common field name variations:

- **firstName** = first_name = fname = given_name = forename
- **lastName** = last_name = surname = family_name
- **dateOfBirth** = date_of_birth = DOB = birth_date
- **email** = e-mail = email_address
- **phone** = telephone = phone_number = mobile

## Missing Field Handling

If a field is not found in the document:

```json
{
  "email": {
    "value": "",
    "confidence": 0.0,
    "not_found": true,
    "uncertain": false
  }
}
```

## Project Structure

```
backend/api/
├── main.py                    # FastAPI application
├── config.yaml                # Configuration
├── models/                    # Pydantic models
│   ├── requests.py
│   └── responses.py
├── routes/                    # API endpoints
│   ├── extraction.py
│   ├── jobs.py
│   ├── documents.py
│   └── health.py
├── services/                  # Business logic
│   ├── ocr_service.py
│   ├── field_service.py
│   └── job_worker.py
├── storage/                   # Data storage
│   ├── cache_manager.py
│   └── job_store.py
└── utils/                     # Utilities
    ├── config_loader.py
    ├── validators.py
    └── exceptions.py
```

## Performance

- **OCR**: 1-5 seconds per page (depends on performance_mode)
- **Field Mapping**: 1-3 seconds (LLM inference)
- **Concurrent Jobs**: 3 max (configurable)
- **Cache**: 1000 documents max, 24h TTL (configurable)

## Troubleshooting

### LLM model not found
Ensure `models/qwen2.5-1.5b-instruct-q4_k_m.gguf` exists or update `config.yaml` with correct path.

### CORS errors
Update `config.yaml` cors.allow_origins to include your extension's origin.

### Job timeout
Increase `jobs.timeout_seconds` in `config.yaml` for large documents.

## License

MIT License - See LICENSE file

---

**Built with ❤️ for ROSETTA Project**
