"""
Validation utilities for file uploads and schemas.
"""

from pathlib import Path
from typing import Dict, Any, List

try:
    import magic  # python-magic for MIME type detection
    _HAS_MAGIC = True
except (ImportError, OSError):
    magic = None  # type: ignore
    _HAS_MAGIC = False

from .exceptions import InvalidFileException, SchemaValidationException


def validate_file(
    file_path: str,
    allowed_formats: List[str],
    max_size_mb: int
) -> None:
    """
    Validate uploaded file.
    
    Args:
        file_path: Path to uploaded file
        allowed_formats: List of allowed extensions (e.g., ['pdf', 'jpg'])
        max_size_mb: Maximum file size in MB
    
    Raises:
        InvalidFileException: If file is invalid
    """
    path = Path(file_path)
    
    # Check file exists
    if not path.exists():
        raise InvalidFileException("File does not exist")
    
    # Check file size
    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise InvalidFileException(
            f"File size ({file_size_mb:.2f}MB) exceeds limit ({max_size_mb}MB)"
        )
    
    # Check file extension
    extension = path.suffix.lower().lstrip('.')
    if extension not in allowed_formats:
        raise InvalidFileException(
            f"File format '.{extension}' not supported. "
            f"Allowed: {', '.join(allowed_formats)}"
        )
    
    # Verify MIME type matches extension (if magic is available)
    if _HAS_MAGIC and magic:
        try:
            mime = magic.from_file(str(path), mime=True)
            
            expected_mimes = {
                'pdf': 'application/pdf',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'tiff': 'image/tiff',
                'tif': 'image/tiff'
            }
            
            expected = expected_mimes.get(extension)
            if expected and not mime.startswith(expected.split('/')[0]):
                raise InvalidFileException(
                    f"File content doesn't match extension. "
                    f"Expected {expected}, got {mime}"
                )
        except Exception:
            # MIME check failed, skip
            pass


def validate_schema(schema: Dict[str, Any]) -> None:
    """
    Validate field schema structure.
    
    Args:
        schema: Field schema dictionary
    
    Raises:
        SchemaValidationException: If schema is invalid
    
    Expected schema format:
    {
        "fieldName": {
            "type": "string" | "number" | "date" | "email" | "phone",
            "required": true | false,
            "format": "...",  # Optional format hint
            "synonyms": ["alternative_name", ...]  # Optional
        },
        ...
    }
    """
    if not isinstance(schema, dict):
        raise SchemaValidationException("Schema must be a dictionary")
    
    if len(schema) == 0:
        raise SchemaValidationException("Schema cannot be empty")
    
    valid_types = ["string", "text", "number", "integer", "float", "date", "email", "phone", "boolean"]
    
    for field_name, field_config in schema.items():
        if not isinstance(field_name, str) or not field_name.strip():
            raise SchemaValidationException("Field names must be non-empty strings")
        
        # Allow simple string type specification
        if isinstance(field_config, str):
            if field_config not in valid_types:
                raise SchemaValidationException(
                    f"Invalid type '{field_config}' for field '{field_name}'. "
                    f"Allowed: {', '.join(valid_types)}"
                )
            continue
        
        # Validate detailed field config
        if not isinstance(field_config, dict):
            raise SchemaValidationException(
                f"Field '{field_name}' config must be string or dict"
            )
        
        field_type = field_config.get("type")
        if field_type and field_type not in valid_types:
            raise SchemaValidationException(
                f"Invalid type '{field_type}' for field '{field_name}'. "
                f"Allowed: {', '.join(valid_types)}"
            )
