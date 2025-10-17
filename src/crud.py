"""CRUD operations for database models."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from src import models, schemas
import uuid


def create_document(
    db: Session,
    filename: str,
    file_path: str,
    file_size: int,
    num_pages: int,
    mime_type: str = "application/pdf"
) -> models.Document:
    """Create a new document record."""
    document_id = str(uuid.uuid4())
    db_document = models.Document(
        document_id=document_id,
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        num_pages=num_pages,
        mime_type=mime_type
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document


def get_document_by_id(db: Session, document_id: str) -> Optional[models.Document]:
    """Get document by document_id."""
    return db.query(models.Document).filter(
        models.Document.document_id == document_id
    ).first()


def get_all_documents(db: Session, skip: int = 0, limit: int = 100) -> List[models.Document]:
    """Get all documents with pagination."""
    return db.query(models.Document).offset(skip).limit(limit).all()


def create_document_chunk(
    db: Session,
    document_id: int,
    chunk_index: int,
    text_content: str,
    page_number: Optional[int] = None,
    char_start: Optional[int] = None,
    char_end: Optional[int] = None,
    chunk_metadata: Optional[Dict] = None
) -> models.DocumentChunk:
    """Create a document chunk."""
    db_chunk = models.DocumentChunk(
        document_id=document_id,
        chunk_index=chunk_index,
        page_number=page_number,
        text_content=text_content,
        char_start=char_start,
        char_end=char_end,
        chunk_metadata=chunk_metadata
    )
    db.add(db_chunk)
    db.commit()
    db.refresh(db_chunk)
    return db_chunk


def get_document_chunks(db: Session, document_id: int) -> List[models.DocumentChunk]:
    """Get all chunks for a document."""
    return db.query(models.DocumentChunk).filter(
        models.DocumentChunk.document_id == document_id
    ).order_by(models.DocumentChunk.chunk_index).all()


def create_extracted_data(
    db: Session,
    document_id: int,
    extraction_data: Dict[str, Any],
    extraction_method: str = "llm",
    confidence_score: Optional[float] = None
) -> models.ExtractedData:
    """Create extracted data record."""
    # Check if extraction already exists
    existing = db.query(models.ExtractedData).filter(
        models.ExtractedData.document_id == document_id
    ).first()
    
    if existing:
        # Update existing record
        for key, value in extraction_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        existing.extraction_method = extraction_method
        existing.confidence_score = confidence_score
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new record
    db_extracted = models.ExtractedData(
        document_id=document_id,
        extraction_method=extraction_method,
        confidence_score=confidence_score,
        **extraction_data
    )
    db.add(db_extracted)
    db.commit()
    db.refresh(db_extracted)
    return db_extracted


def get_extracted_data(db: Session, document_id: int) -> Optional[models.ExtractedData]:
    """Get extracted data for a document."""
    return db.query(models.ExtractedData).filter(
        models.ExtractedData.document_id == document_id
    ).first()


def get_extracted_data_by_doc_id(db: Session, document_id: str) -> Optional[models.ExtractedData]:
    """Get extracted data by document_id string."""
    document = get_document_by_id(db, document_id)
    if not document:
        return None
    return get_extracted_data(db, document.id)


def create_audit_finding(
    db: Session,
    document_id: int,
    finding_type: str,
    severity: str,
    description: str,
    evidence: Optional[str] = None,
    page_number: Optional[int] = None,
    char_start: Optional[int] = None,
    char_end: Optional[int] = None,
    finding_metadata: Optional[Dict] = None
) -> models.AuditFinding:
    """Create an audit finding."""
    db_finding = models.AuditFinding(
        document_id=document_id,
        finding_type=finding_type,
        severity=severity,
        description=description,
        evidence=evidence,
        page_number=page_number,
        char_start=char_start,
        char_end=char_end,
        finding_metadata=finding_metadata
    )
    db.add(db_finding)
    db.commit()
    db.refresh(db_finding)
    return db_finding


def get_audit_findings(db: Session, document_id: int) -> List[models.AuditFinding]:
    """Get all audit findings for a document."""
    return db.query(models.AuditFinding).filter(
        models.AuditFinding.document_id == document_id
    ).all()


def get_total_documents(db: Session) -> int:
    """Get total count of documents."""
    return db.query(func.count(models.Document.id)).scalar()


def get_total_extractions(db: Session) -> int:
    """Get total count of extractions."""
    return db.query(func.count(models.ExtractedData.id)).scalar()


def get_total_audit_findings(db: Session) -> int:
    """Get total count of audit findings."""
    return db.query(func.count(models.AuditFinding.id)).scalar()
