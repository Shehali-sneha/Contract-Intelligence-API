"""SQLAlchemy models for the Contract Intelligence System."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base
class Document(Base):
    """Model for storing uploaded documents."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(255), unique=True, index=True, nullable=False)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), default="application/pdf")
    num_pages = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    extracted_data = relationship("ExtractedData", back_populates="document", cascade="all, delete-orphan")
    document_chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Model for storing document text chunks for RAG."""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer)
    text_content = Column(Text, nullable=False)
    char_start = Column(Integer)
    char_end = Column(Integer)
    chunk_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="document_chunks")


class ExtractedData(Base):
    """Model for storing extracted structured data from contracts."""
    __tablename__ = "extracted_data"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Contract fields
    parties = Column(JSON)  # List of party names
    effective_date = Column(String(100))
    term = Column(String(200))
    governing_law = Column(String(200))
    payment_terms = Column(Text)
    termination = Column(Text)
    auto_renewal = Column(String(200))
    confidentiality = Column(Text)
    indemnity = Column(Text)
    liability_cap_amount = Column(Float)
    liability_cap_currency = Column(String(10))
    signatories = Column(JSON)  # List of {name, title}
    
    # Metadata
    extraction_method = Column(String(50))  # 'llm' or 'rule-based'
    confidence_score = Column(Float)
    raw_response = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="extracted_data")


class AuditFinding(Base):
    """Model for storing audit/risk findings."""
    __tablename__ = "audit_findings"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    finding_type = Column(String(100), nullable=False)
    severity = Column(String(20))  # 'high', 'medium', 'low'
    description = Column(Text, nullable=False)
    evidence = Column(Text)
    page_number = Column(Integer)
    char_start = Column(Integer)
    char_end = Column(Integer)
    finding_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
