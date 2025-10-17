"""Pydantic schemas for request/response validation."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Ingest Schemas
class IngestResponse(BaseModel):
    """Response for document ingestion."""
    document_ids: List[str]
    total_documents: int
    message: str

    class Config:
        from_attributes = True


class DocumentMetadata(BaseModel):
    """Metadata for an ingested document."""
    document_id: str
    filename: str
    file_size: int
    num_pages: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# Extract Schemas
class Signatory(BaseModel):
    """Signatory information."""
    name: str
    title: Optional[str] = None


class ExtractRequest(BaseModel):
    """Request for extracting data from a document."""
    document_id: str


class ExtractResponse(BaseModel):
    """Response with extracted contract data."""
    document_id: str
    parties: List[str] = Field(default_factory=list)
    effective_date: Optional[str] = None
    term: Optional[str] = None
    governing_law: Optional[str] = None
    payment_terms: Optional[str] = None
    termination: Optional[str] = None
    auto_renewal: Optional[str] = None
    confidentiality: Optional[str] = None
    indemnity: Optional[str] = None
    liability_cap: Optional[Dict[str, Any]] = None  # {amount, currency}
    signatories: List[Signatory] = Field(default_factory=list)
    extraction_method: Optional[str] = None
    confidence_score: Optional[float] = None

    class Config:
        from_attributes = True


# Ask (RAG) Schemas
class AskRequest(BaseModel):
    """Request for question answering."""
    question: str
    document_ids: Optional[List[str]] = None  # If None, search all documents
    max_results: int = Field(default=5, ge=1, le=20)


class Citation(BaseModel):
    """Citation information for an answer."""
    document_id: str
    page_number: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    text_excerpt: str


class AskResponse(BaseModel):
    """Response with answer and citations."""
    question: str
    answer: str
    citations: List[Citation]
    confidence: Optional[float] = None


# Audit Schemas
class AuditRequest(BaseModel):
    """Request for document audit."""
    document_id: str


class AuditFindingResponse(BaseModel):
    """Individual audit finding."""
    finding_type: str
    severity: str  # 'high', 'medium', 'low'
    description: str
    evidence: Optional[str] = None
    page_number: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None

    class Config:
        from_attributes = True


class AuditResponse(BaseModel):
    """Response with audit findings."""
    document_id: str
    findings: List[AuditFindingResponse]
    total_findings: int
    risk_score: Optional[float] = None


# Error Schemas
class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    status_code: int


# Health/Metrics Schemas
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    timestamp: datetime


class MetricsResponse(BaseModel):
    """Metrics response."""
    total_documents: int
    total_extractions: int
    total_audit_findings: int
    uptime_seconds: float
