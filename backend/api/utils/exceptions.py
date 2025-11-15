"""
Custom exceptions for ROSETTA API.
"""


class RosettaAPIException(Exception):
    """Base exception for ROSETTA API."""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InvalidFileException(RosettaAPIException):
    """Raised when uploaded file is invalid."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class ProcessingException(RosettaAPIException):
    """Raised when OCR or LLM processing fails."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class JobNotFoundException(RosettaAPIException):
    """Raised when job ID is not found."""
    
    def __init__(self, job_id: str):
        super().__init__(f"Job not found: {job_id}", status_code=404)


class CacheException(RosettaAPIException):
    """Raised when cache operations fail."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class DocumentNotFoundException(RosettaAPIException):
    """Raised when document is not found in cache."""
    
    def __init__(self, document_id: str):
        super().__init__(f"Document not found or expired: {document_id}", status_code=404)


class SchemaValidationException(RosettaAPIException):
    """Raised when field schema validation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=400)
