"""FastAPI endpoints for Contract Intelligence System."""
from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging
import json

from src import crud, schemas, models
from src.database import get_db
from src.utils import PDFProcessor, ContractExtractor, RAGEngine, RiskAuditEngine

logger = logging.getLogger(__name__)

router = APIRouter()
pdf_processor = PDFProcessor()
contract_extractor = ContractExtractor()
rag_engine = RAGEngine()
audit_engine = RiskAuditEngine()


@router.post("/ingest", response_model=schemas.IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Ingest one or more PDF documents.
    
    - **files**: List of PDF files to upload
    
    Returns document IDs for the uploaded files.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    document_ids = []
    errors = []
    
    for file in files:
        try:
            # Validate file type
            if not file.filename.lower().endswith('.pdf'):
                errors.append(f"{file.filename}: Not a PDF file")
                continue
            
            # Read file content
            file_content = await file.read()
            
            if not file_content:
                errors.append(f"{file.filename}: Empty file")
                continue
            
            # Save file to disk
            file_path, file_size = pdf_processor.save_uploaded_file(
                file_content,
                file.filename
            )
            
            # Extract text and metadata
            try:
                full_text, num_pages, page_data = pdf_processor.extract_text_from_pdf(file_path)
            except Exception as e:
                logger.error(f"Error extracting text from {file.filename}: {e}")
                errors.append(f"{file.filename}: Failed to extract text - {str(e)}")
                continue
            
            # Create document record
            document = crud.create_document(
                db=db,
                filename=file.filename,
                file_path=file_path,
                file_size=file_size,
                num_pages=num_pages,
                mime_type=file.content_type or "application/pdf"
            )
            
            # Create chunks for RAG
            chunks = pdf_processor.chunk_text(full_text, chunk_size=1000, chunk_overlap=200)
            
            for idx, chunk in enumerate(chunks):
                # Find which page this chunk belongs to (simple heuristic)
                page_num = None
                for page in page_data:
                    if chunk[:50] in page['text']:
                        page_num = page['page_number']
                        break
                
                crud.create_document_chunk(
                    db=db,
                    document_id=document.id,
                    chunk_index=idx,
                    text_content=chunk,
                    page_number=page_num,
                    chunk_metadata={"chunk_size": len(chunk)}
                )
            
            document_ids.append(document.document_id)
            logger.info(f"Successfully ingested document: {file.filename} ({document.document_id})")
        
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}")
            errors.append(f"{file.filename}: {str(e)}")
    
    if not document_ids and errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to ingest any documents. Errors: {'; '.join(errors)}"
        )
    
    message = f"Successfully ingested {len(document_ids)} document(s)"
    if errors:
        message += f". Errors: {'; '.join(errors)}"
    
    return schemas.IngestResponse(
        document_ids=document_ids,
        total_documents=len(document_ids),
        message=message
    )


@router.post("/extract", response_model=schemas.ExtractResponse)
async def extract_contract_data(
    request: schemas.ExtractRequest,
    db: Session = Depends(get_db)
):
    """
    Extract structured data from a contract document.
    
    - **document_id**: ID of the document to extract data from
    
    Returns extracted contract fields including parties, dates, terms, etc.
    """
    # Get document
    document = crud.get_document_by_id(db, request.document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {request.document_id} not found"
        )
    
    # Check if extraction already exists
    existing_extraction = crud.get_extracted_data(db, document.id)
    if existing_extraction:
        logger.info(f"Returning cached extraction for document {request.document_id}")
        return _format_extraction_response(request.document_id, existing_extraction)
    
    # Get document chunks (which contain the text)
    chunks = crud.get_document_chunks(db, document.id)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No text content found for document {request.document_id}"
        )
    
    # Combine all chunks to get full text
    full_text = "\n".join([chunk.text_content for chunk in chunks])
    
    # Extract structured data using rule-based extraction
    try:
        parties = contract_extractor.extract_parties(full_text)
        effective_date = contract_extractor.extract_dates(full_text)
        term = contract_extractor.extract_term(full_text)
        governing_law = contract_extractor.extract_governing_law(full_text)
        liability_cap = contract_extractor.extract_liability_cap(full_text)
        auto_renewal = contract_extractor.extract_auto_renewal(full_text)
        
        # Search for specific sections
        payment_terms = _extract_section(full_text, ["payment", "compensation"])
        termination = _extract_section(full_text, ["termination", "cancellation"])
        confidentiality = _extract_section(full_text, ["confidential", "non-disclosure"])
        indemnity = _extract_section(full_text, ["indemnit", "indemnif"])
        
        # Prepare extraction data
        extraction_data = {
            "parties": parties,
            "effective_date": effective_date,
            "term": term,
            "governing_law": governing_law,
            "payment_terms": payment_terms,
            "termination": termination,
            "auto_renewal": auto_renewal,
            "confidentiality": confidentiality,
            "indemnity": indemnity,
            "liability_cap_amount": liability_cap.get("amount"),
            "liability_cap_currency": liability_cap.get("currency"),
            "signatories": [],  # Would need more sophisticated extraction
        }
        
        # Save extraction to database
        extracted = crud.create_extracted_data(
            db=db,
            document_id=document.id,
            extraction_data=extraction_data,
            extraction_method="rule-based",
            confidence_score=0.7  # Rule-based has moderate confidence
        )
        
        logger.info(f"Successfully extracted data from document {request.document_id}")
        
        return _format_extraction_response(request.document_id, extracted)
    
    except Exception as e:
        logger.error(f"Error extracting data from document {request.document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract data: {str(e)}"
        )


def _extract_section(text: str, keywords: List[str], max_length: int = 500) -> str:
    """Extract a section of text based on keywords."""
    import re
    
    for keyword in keywords:
        pattern = re.compile(
            rf'(?:^|\n)([^\n]*{keyword}[^\n]*\n(?:[^\n]+\n){{0,5}})',
            re.IGNORECASE | re.MULTILINE
        )
        match = pattern.search(text)
        if match:
            section = match.group(0).strip()
            if len(section) > max_length:
                section = section[:max_length] + "..."
            return section
    
    return ""


def _format_extraction_response(
    document_id: str,
    extracted: models.ExtractedData
) -> schemas.ExtractResponse:
    """Format extracted data into response schema."""
    liability_cap = None
    if extracted.liability_cap_amount:
        liability_cap = {
            "amount": extracted.liability_cap_amount,
            "currency": extracted.liability_cap_currency or "USD"
        }
    
    signatories = []
    if extracted.signatories:
        for sig in extracted.signatories:
            if isinstance(sig, dict):
                signatories.append(schemas.Signatory(
                    name=sig.get("name", ""),
                    title=sig.get("title")
                ))
    
    return schemas.ExtractResponse(
        document_id=document_id,
        parties=extracted.parties or [],
        effective_date=extracted.effective_date,
        term=extracted.term,
        governing_law=extracted.governing_law,
        payment_terms=extracted.payment_terms,
        termination=extracted.termination,
        auto_renewal=extracted.auto_renewal,
        confidentiality=extracted.confidentiality,
        indemnity=extracted.indemnity,
        liability_cap=liability_cap,
        signatories=signatories,
        extraction_method=extracted.extraction_method,
        confidence_score=extracted.confidence_score
    )


@router.get("/documents", response_model=List[schemas.DocumentMetadata])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all ingested documents.
    
    - **skip**: Number of documents to skip (for pagination)
    - **limit**: Maximum number of documents to return
    """
    documents = crud.get_all_documents(db, skip=skip, limit=limit)
    
    return [
        schemas.DocumentMetadata(
            document_id=doc.document_id,
            filename=doc.filename,
            file_size=doc.file_size,
            num_pages=doc.num_pages,
            created_at=doc.created_at
        )
        for doc in documents
    ]


@router.get("/documents/{document_id}", response_model=schemas.DocumentMetadata)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Get metadata for a specific document."""
    document = crud.get_document_by_id(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found"
        )
    
    return schemas.DocumentMetadata(
        document_id=document.document_id,
        filename=document.filename,
        file_size=document.file_size,
        num_pages=document.num_pages,
        created_at=document.created_at
    )


# ============================================================================
# Intelligence Layer: RAG-based Q&A + Risk Audit
# ============================================================================

@router.post("/ask", response_model=schemas.AskResponse)
async def ask_question(
    request: schemas.AskRequest,
    db: Session = Depends(get_db)
):
    """
    Ask questions about contracts using RAG (Retrieval-Augmented Generation).
    
    - **question**: The question to ask about the documents
    - **document_ids**: Optional list of document IDs to search (if None, searches all)
    - **max_results**: Maximum number of relevant chunks to retrieve
    
    Returns an answer with citations to source documents.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )
    
    # Get documents to search
    if request.document_ids:
        documents = []
        for doc_id in request.document_ids:
            doc = crud.get_document_by_id(db, doc_id)
            if doc:
                documents.append(doc)
        
        if not documents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="None of the specified documents were found"
            )
    else:
        # Search all documents
        documents = crud.get_all_documents(db, skip=0, limit=1000)
    
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents available to search"
        )
    
    # Collect all chunks from the documents
    all_chunks = []
    for doc in documents:
        chunks = crud.get_document_chunks(db, doc.id)
        for chunk in chunks:
            all_chunks.append({
                'document_id': doc.document_id,
                'page_number': chunk.page_number,
                'text_content': chunk.text_content,
                'char_start': chunk.char_start,
                'char_end': chunk.char_end
            })
    
    if not all_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text content available in the specified documents"
        )
    
    # Perform semantic search
    relevant_chunks = rag_engine.semantic_search(
        query=request.question,
        chunks=all_chunks,
        top_k=request.max_results
    )
    
    if not relevant_chunks:
        return schemas.AskResponse(
            question=request.question,
            answer="I couldn't find relevant information to answer this question.",
            citations=[],
            confidence=0.0
        )
    
    # Generate answer
    answer, confidence = rag_engine.generate_answer(
        question=request.question,
        context_chunks=relevant_chunks,
        max_tokens=500
    )
    
    # Build citations
    citations = []
    for chunk in relevant_chunks[:5]:  # Limit to top 5 citations
        # Extract a reasonable excerpt
        text = chunk['text_content']
        excerpt = text[:200] + "..." if len(text) > 200 else text
        
        citations.append(schemas.Citation(
            document_id=chunk['document_id'],
            page_number=chunk.get('page_number'),
            char_start=chunk.get('char_start'),
            char_end=chunk.get('char_end'),
            text_excerpt=excerpt
        ))
    
    logger.info(f"Answered question with {len(relevant_chunks)} relevant chunks")
    
    return schemas.AskResponse(
        question=request.question,
        answer=answer,
        citations=citations,
        confidence=confidence
    )


@router.post("/stream")
async def ask_question_stream(
    request: schemas.AskRequest,
    db: Session = Depends(get_db)
):
    """
    Ask questions about contracts with streaming response.
    
    Similar to /ask but streams the answer as it's generated.
    Returns Server-Sent Events (SSE) format.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )
    
    # Get documents to search
    if request.document_ids:
        documents = []
        for doc_id in request.document_ids:
            doc = crud.get_document_by_id(db, doc_id)
            if doc:
                documents.append(doc)
        
        if not documents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="None of the specified documents were found"
            )
    else:
        # Search all documents
        documents = crud.get_all_documents(db, skip=0, limit=1000)
    
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents available to search"
        )
    
    # Collect all chunks from the documents
    all_chunks = []
    for doc in documents:
        chunks = crud.get_document_chunks(db, doc.id)
        for chunk in chunks:
            all_chunks.append({
                'document_id': doc.document_id,
                'page_number': chunk.page_number,
                'text_content': chunk.text_content,
                'char_start': chunk.char_start,
                'char_end': chunk.char_end
            })
    
    if not all_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text content available in the specified documents"
        )
    
    # Perform semantic search
    relevant_chunks = rag_engine.semantic_search(
        query=request.question,
        chunks=all_chunks,
        top_k=request.max_results
    )
    
    # Build citations to send first
    citations = []
    for chunk in relevant_chunks[:5]:
        text = chunk['text_content']
        excerpt = text[:200] + "..." if len(text) > 200 else text
        
        citations.append({
            'document_id': chunk['document_id'],
            'page_number': chunk.get('page_number'),
            'char_start': chunk.get('char_start'),
            'char_end': chunk.get('char_end'),
            'text_excerpt': excerpt
        })
    
    async def generate_stream():
        """Generate SSE stream."""
        # First, send citations as metadata
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"
        
        if not relevant_chunks:
            yield f"data: {json.dumps({'type': 'text', 'content': 'No relevant information found.'})}\n\n"
            yield "data: [DONE]\n\n"
            return
        
        # Stream the answer
        async for chunk in rag_engine.generate_answer_stream(
            question=request.question,
            context_chunks=relevant_chunks,
            max_tokens=500
        ):
            yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
        
        # Signal completion
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/audit", response_model=schemas.AuditResponse)
async def audit_document(
    request: schemas.AuditRequest,
    db: Session = Depends(get_db)
):
    """
    Audit a document for risks and compliance issues.
    
    - **document_id**: ID of the document to audit
    
    Returns a list of findings with severity levels and a risk score.
    """
    # Get document
    document = crud.get_document_by_id(db, request.document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {request.document_id} not found"
        )
    
    # Check if audit already exists (for caching)
    existing_findings = crud.get_audit_findings(db, document.id)
    if existing_findings:
        logger.info(f"Returning cached audit for document {request.document_id}")
        
        findings_response = [
            schemas.AuditFindingResponse(
                finding_type=f.finding_type,
                severity=f.severity,
                description=f.description,
                evidence=f.evidence,
                page_number=f.page_number,
                char_start=f.char_start,
                char_end=f.char_end
            )
            for f in existing_findings
        ]
        
        risk_score = audit_engine.calculate_risk_score([
            {'severity': f.severity} for f in existing_findings
        ])
        
        return schemas.AuditResponse(
            document_id=request.document_id,
            findings=findings_response,
            total_findings=len(findings_response),
            risk_score=risk_score
        )
    
    # Get document text
    chunks = crud.get_document_chunks(db, document.id)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No text content found for document {request.document_id}"
        )
    
    full_text = "\n".join([chunk.text_content for chunk in chunks])
    
    # Get extracted data if available
    extracted_data = crud.get_extracted_data(db, document.id)
    extracted_dict = None
    if extracted_data:
        extracted_dict = {
            'parties': extracted_data.parties,
            'effective_date': extracted_data.effective_date,
            'term': extracted_data.term,
            'governing_law': extracted_data.governing_law,
            'termination': extracted_data.termination,
            'auto_renewal': extracted_data.auto_renewal
        }
    
    # Perform audit
    try:
        findings, risk_score = audit_engine.audit_document(full_text, extracted_dict)
        
        # Save findings to database
        for finding in findings:
            # Find page number if not provided
            page_num = finding.get('page_number')
            if not page_num and finding.get('char_start') is not None:
                # Try to determine page from char position
                for chunk in chunks:
                    if (chunk.char_start is not None and 
                        chunk.char_end is not None and
                        chunk.char_start <= finding['char_start'] <= chunk.char_end):
                        page_num = chunk.page_number
                        break
            
            crud.create_audit_finding(
                db=db,
                document_id=document.id,
                finding_type=finding['finding_type'],
                severity=finding['severity'],
                description=finding['description'],
                evidence=finding.get('evidence'),
                page_number=page_num,
                char_start=finding.get('char_start'),
                char_end=finding.get('char_end'),
                finding_metadata={}
            )
        
        # Format response
        findings_response = [
            schemas.AuditFindingResponse(
                finding_type=f['finding_type'],
                severity=f['severity'],
                description=f['description'],
                evidence=f.get('evidence'),
                page_number=f.get('page_number'),
                char_start=f.get('char_start'),
                char_end=f.get('char_end')
            )
            for f in findings
        ]
        
        logger.info(f"Audit completed for document {request.document_id}: {len(findings)} findings, risk score {risk_score}")
        
        return schemas.AuditResponse(
            document_id=request.document_id,
            findings=findings_response,
            total_findings=len(findings_response),
            risk_score=risk_score
        )
    
    except Exception as e:
        logger.error(f"Error auditing document {request.document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to audit document: {str(e)}"
        )

