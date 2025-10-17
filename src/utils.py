"""PDF processing utilities for text extraction and metadata."""
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pypdf import PdfReader
from datetime import datetime
import logging
from openai import OpenAI
import tiktoken

logger = logging.getLogger(__name__)

# Initialize OpenAI client
try:
    openai_client = OpenAI()
    OPENAI_AVAILABLE = True
except Exception as e:
    logger.warning(f"OpenAI not available: {e}")
    openai_client = None
    OPENAI_AVAILABLE = False


class PDFProcessor:
    """Handles PDF text extraction and processing."""
    
    def __init__(self, upload_dir: str = "data/uploads"):
        """Initialize PDF processor.
        
        Args:
            upload_dir: Directory to store uploaded PDFs
        """
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, int, List[Dict[str, Any]]]:
        """Extract text from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (full_text, num_pages, page_data)
            page_data is a list of dicts with page number and text
        """
        try:
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
            full_text = ""
            page_data = []
            
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"\n--- Page {page_num} ---\n{page_text}"
                        page_data.append({
                            "page_number": page_num,
                            "text": page_text,
                            "char_start": len(full_text) - len(page_text),
                            "char_end": len(full_text)
                        })
                except Exception as e:
                    logger.error(f"Error extracting text from page {page_num}: {e}")
                    continue
            
            return full_text, num_pages, page_data
        
        except Exception as e:
            logger.error(f"Error reading PDF {pdf_path}: {e}")
            raise ValueError(f"Failed to read PDF: {str(e)}")
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """Split text into chunks for processing.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk
            chunk_overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence endings near the chunk boundary
                search_start = max(start, end - 100)
                search_text = text[search_start:end + 100]
                
                # Find last sentence ending
                match = None
                for pattern in [r'\.\s', r'\!\s', r'\?\s', r'\n\n']:
                    matches = list(re.finditer(pattern, search_text))
                    if matches:
                        match = matches[-1]
                        break
                
                if match:
                    end = search_start + match.end()
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - chunk_overlap
        
        return chunks
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with PDF metadata
        """
        try:
            reader = PdfReader(pdf_path)
            metadata = {}
            
            if reader.metadata:
                metadata = {
                    "title": reader.metadata.get("/Title", ""),
                    "author": reader.metadata.get("/Author", ""),
                    "subject": reader.metadata.get("/Subject", ""),
                    "creator": reader.metadata.get("/Creator", ""),
                    "producer": reader.metadata.get("/Producer", ""),
                    "creation_date": reader.metadata.get("/CreationDate", ""),
                }
            
            return metadata
        
        except Exception as e:
            logger.error(f"Error extracting metadata from {pdf_path}: {e}")
            return {}
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> Tuple[str, int]:
        """Save uploaded file to disk.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Tuple of (file_path, file_size)
        """
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        
        # Add timestamp to avoid collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"{timestamp}_{safe_filename}"
        file_path = os.path.join(self.upload_dir, final_filename)
        
        # Write file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        file_size = len(file_content)
        return file_path, file_size
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent security issues.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove any path components
        filename = os.path.basename(filename)
        
        # Replace spaces and special characters
        filename = re.sub(r'[^\w\s.-]', '', filename)
        filename = re.sub(r'\s+', '_', filename)
        
        return filename


class ContractExtractor:
    """Extract structured data from contract text using rule-based methods."""
    
    @staticmethod
    def extract_parties(text: str) -> List[str]:
        """Extract party names from contract."""
        parties = []
        
        # Common patterns for party identification
        patterns = [
            r'between\s+([A-Z][A-Za-z\s&,\.]+?)\s+(?:and|&)',
            r'entered into by\s+([A-Z][A-Za-z\s&,\.]+?)\s+(?:and|&)',
            r'PARTY\s+(?:A|1):\s*([A-Z][A-Za-z\s&,\.]+?)(?:\n|$)',
            r'(?:Client|Vendor|Contractor):\s*([A-Z][A-Za-z\s&,\.]+?)(?:\n|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text[:2000], re.IGNORECASE | re.MULTILINE)
            for match in matches:
                party = match.strip().strip(',').strip('.')
                if party and len(party) > 3:
                    parties.append(party)
        
        return list(set(parties))[:5]  # Limit to 5 unique parties
    
    @staticmethod
    def extract_dates(text: str) -> Optional[str]:
        """Extract effective date from contract."""
        date_patterns = [
            r'(?:effective|dated?|entered into).*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(?:effective|dated?|entered into).*?([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
            r'Effective Date:\s*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text[:2000], re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def extract_term(text: str) -> Optional[str]:
        """Extract contract term/duration."""
        term_patterns = [
            r'(?:term|duration).*?(\d+\s+(?:year|month|day)s?)',
            r'for a period of\s+(\d+\s+(?:year|month|day)s?)',
            r'Term:\s*([^\n]+)',
        ]
        
        for pattern in term_patterns:
            match = re.search(pattern, text[:3000], re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    @staticmethod
    def extract_governing_law(text: str) -> Optional[str]:
        """Extract governing law information."""
        patterns = [
            r'governed by.*?laws of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'governing law.*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+law',
            r'Governing Law:\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    @staticmethod
    def extract_liability_cap(text: str) -> Dict[str, Any]:
        """Extract liability cap information."""
        patterns = [
            r'liability.*?(?:limited|capped|exceed).*?(?:USD|EUR|\$|€|£)\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(?:USD|EUR|\$|€|£)\s*(\d+(?:,\d{3})*(?:\.\d{2})?).*?liability',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    # Determine currency
                    currency_match = re.search(r'(USD|EUR|GBP|\$|€|£)', match.group(0))
                    currency = "USD"
                    if currency_match:
                        curr = currency_match.group(1)
                        if curr in ['€', 'EUR']:
                            currency = 'EUR'
                        elif curr in ['£', 'GBP']:
                            currency = 'GBP'
                    
                    return {"amount": amount, "currency": currency}
                except ValueError:
                    pass
        
        return {}
    
    @staticmethod
    def extract_auto_renewal(text: str) -> Optional[str]:
        """Extract auto-renewal information."""
        if re.search(r'auto(?:matic)?(?:ally)?\s+renew', text, re.IGNORECASE):
            # Try to find notice period
            notice_match = re.search(
                r'(\d+)\s+day[s]?\s+(?:notice|prior)',
                text,
                re.IGNORECASE
            )
            if notice_match:
                return f"Yes, {notice_match.group(1)} days notice required"
            return "Yes"
        
        return "No"


class RAGEngine:
    """RAG-based Question Answering engine."""
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """Initialize RAG engine.
        
        Args:
            model: OpenAI model to use
        """
        self.model = model
        self.client = openai_client
        self.tokenizer = tiktoken.encoding_for_model(model) if OPENAI_AVAILABLE else None
    
    def semantic_search(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Perform semantic search on document chunks.
        
        This is a simple keyword-based implementation.
        For production, use vector embeddings with a vector database.
        
        Args:
            query: Search query
            chunks: List of chunk dictionaries with 'text_content' key
            top_k: Number of results to return
            
        Returns:
            List of most relevant chunks with scores
        """
        # Simple keyword matching (upgrade to embeddings for production)
        query_words = set(query.lower().split())
        
        scored_chunks = []
        for chunk in chunks:
            text = chunk.get('text_content', '').lower()
            # Count matching words
            score = sum(1 for word in query_words if word in text)
            if score > 0:
                scored_chunks.append({
                    **chunk,
                    'relevance_score': score
                })
        
        # Sort by score and return top_k
        scored_chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
        return scored_chunks[:top_k]
    
    def generate_answer(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        max_tokens: int = 500
    ) -> Tuple[str, float]:
        """Generate answer using LLM based on retrieved context.
        
        Args:
            question: User question
            context_chunks: Retrieved relevant chunks
            max_tokens: Maximum tokens for response
            
        Returns:
            Tuple of (answer, confidence_score)
        """
        if not OPENAI_AVAILABLE or not self.client:
            return "OpenAI API not configured. Please set OPENAI_API_KEY.", 0.0
        
        if not context_chunks:
            return "No relevant information found in the documents.", 0.0
        
        # Build context from chunks
        context_texts = []
        for i, chunk in enumerate(context_chunks[:5], 1):
            doc_id = chunk.get('document_id', 'Unknown')
            page = chunk.get('page_number', 'N/A')
            text = chunk.get('text_content', '')
            context_texts.append(f"[Document {doc_id}, Page {page}]\n{text}")
        
        context = "\n\n".join(context_texts)
        
        # Create prompt
        prompt = f"""You are a helpful assistant that answers questions about contracts and legal documents.
Use ONLY the information from the provided context to answer the question.
If the answer cannot be found in the context, say so.

Context:
{context}

Question: {question}

Answer:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a legal document analysis assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Estimate confidence based on context relevance
            confidence = min(0.5 + (len(context_chunks) * 0.1), 0.95)
            
            return answer, confidence
        
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"Error generating answer: {str(e)}", 0.0
    
    async def generate_answer_stream(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        max_tokens: int = 500
    ):
        """Generate answer with streaming response.
        
        Args:
            question: User question
            context_chunks: Retrieved relevant chunks
            max_tokens: Maximum tokens for response
            
        Yields:
            Chunks of the answer as they are generated
        """
        if not OPENAI_AVAILABLE or not self.client:
            yield "OpenAI API not configured. Please set OPENAI_API_KEY."
            return
        
        if not context_chunks:
            yield "No relevant information found in the documents."
            return
        
        # Build context from chunks
        context_texts = []
        for i, chunk in enumerate(context_chunks[:5], 1):
            doc_id = chunk.get('document_id', 'Unknown')
            page = chunk.get('page_number', 'N/A')
            text = chunk.get('text_content', '')
            context_texts.append(f"[Document {doc_id}, Page {page}]\n{text}")
        
        context = "\n\n".join(context_texts)
        
        # Create prompt
        prompt = f"""You are a helpful assistant that answers questions about contracts and legal documents.
Use ONLY the information from the provided context to answer the question.
If the answer cannot be found in the context, say so.

Context:
{context}

Question: {question}

Answer:"""
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a legal document analysis assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            logger.error(f"Error generating streaming answer: {e}")
            yield f"Error: {str(e)}"


class RiskAuditEngine:
    """Risk and compliance audit engine."""
    
    # Define risk rules
    RISK_RULES = [
        {
            "id": "MISSING_TERMINATION",
            "name": "Missing Termination Clause",
            "severity": "high",
            "patterns": [],
            "check_func": "check_termination_clause"
        },
        {
            "id": "UNLIMITED_LIABILITY",
            "name": "Unlimited Liability",
            "severity": "high",
            "patterns": [r'unlimited\s+liability', r'no\s+(?:limit|cap).*?liability'],
            "check_func": None
        },
        {
            "id": "AUTO_RENEWAL",
            "name": "Automatic Renewal Without Notice",
            "severity": "medium",
            "patterns": [r'auto(?:matic)?(?:ally)?\s+renew'],
            "check_func": "check_auto_renewal"
        },
        {
            "id": "MISSING_GOVERNING_LAW",
            "name": "Missing Governing Law",
            "severity": "medium",
            "patterns": [],
            "check_func": "check_governing_law"
        },
        {
            "id": "UNILATERAL_MODIFICATION",
            "name": "Unilateral Modification Rights",
            "severity": "high",
            "patterns": [
                r'(?:may|can|shall)\s+(?:modify|change|amend).*?(?:at any time|without notice)',
                r'reserves?\s+the\s+right\s+to\s+(?:modify|change|amend)'
            ],
            "check_func": None
        },
        {
            "id": "SHORT_NOTICE_TERMINATION",
            "name": "Short Notice Period",
            "severity": "medium",
            "patterns": [r'(?:terminate|cancel).*?(\d+)\s+days?\s+notice'],
            "check_func": "check_termination_notice"
        },
        {
            "id": "BROAD_INDEMNITY",
            "name": "Broad Indemnity Clause",
            "severity": "high",
            "patterns": [
                r'indemnify.*?(?:from\s+(?:any|all)|harmless)',
                r'hold\s+harmless'
            ],
            "check_func": None
        },
        {
            "id": "NO_WARRANTY",
            "name": "No Warranty Disclaimer",
            "severity": "low",
            "patterns": [r'as\s+is', r'without\s+warranty', r'no\s+warranties'],
            "check_func": None
        }
    ]
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """Initialize risk audit engine.
        
        Args:
            model: OpenAI model for advanced analysis
        """
        self.model = model
        self.client = openai_client
    
    def audit_document(
        self,
        text: str,
        extracted_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Audit document for risks and compliance issues.
        
        Args:
            text: Full document text
            extracted_data: Pre-extracted structured data
            
        Returns:
            Tuple of (findings list, risk_score)
        """
        findings = []
        
        # Run rule-based checks
        for rule in self.RISK_RULES:
            # Check patterns
            if rule['patterns']:
                for pattern in rule['patterns']:
                    matches = list(re.finditer(pattern, text, re.IGNORECASE))
                    for match in matches:
                        # Get context around match
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 100)
                        evidence = text[start:end].strip()
                        
                        finding = {
                            'finding_type': rule['id'],
                            'severity': rule['severity'],
                            'description': rule['name'],
                            'evidence': evidence,
                            'char_start': match.start(),
                            'char_end': match.end()
                        }
                        findings.append(finding)
                        break  # Only add one finding per rule
            
            # Run custom check function
            if rule['check_func']:
                check_method = getattr(self, rule['check_func'], None)
                if check_method:
                    result = check_method(text, extracted_data)
                    if result:
                        findings.append({
                            'finding_type': rule['id'],
                            'severity': rule['severity'],
                            'description': rule['name'],
                            'evidence': result.get('evidence', ''),
                            'char_start': result.get('char_start'),
                            'char_end': result.get('char_end')
                        })
        
        # Calculate risk score
        risk_score = self.calculate_risk_score(findings)
        
        return findings, risk_score
    
    def check_termination_clause(
        self,
        text: str,
        extracted_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Check for presence of termination clause."""
        # Check if termination is mentioned
        if not re.search(r'terminat(?:ion|e)', text, re.IGNORECASE):
            return {
                'evidence': 'No termination clause found in document'
            }
        
        # Check extracted data
        if extracted_data and not extracted_data.get('termination'):
            return {
                'evidence': 'Termination clause not clearly defined'
            }
        
        return None
    
    def check_auto_renewal(
        self,
        text: str,
        extracted_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Check for auto-renewal with insufficient notice."""
        auto_renewal_match = re.search(
            r'auto(?:matic)?(?:ally)?\s+renew',
            text,
            re.IGNORECASE
        )
        
        if auto_renewal_match:
            # Check if there's sufficient notice period
            notice_match = re.search(
                r'(\d+)\s+days?\s+(?:notice|prior)',
                text[max(0, auto_renewal_match.start() - 500):auto_renewal_match.end() + 500],
                re.IGNORECASE
            )
            
            if notice_match:
                days = int(notice_match.group(1))
                if days < 30:
                    start = auto_renewal_match.start()
                    end = min(len(text), start + 200)
                    return {
                        'evidence': text[start:end],
                        'char_start': start,
                        'char_end': end
                    }
            else:
                # No notice period mentioned
                start = auto_renewal_match.start()
                end = min(len(text), start + 200)
                return {
                    'evidence': text[start:end],
                    'char_start': start,
                    'char_end': end
                }
        
        return None
    
    def check_governing_law(
        self,
        text: str,
        extracted_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Check for presence of governing law."""
        if not re.search(r'governing\s+law', text, re.IGNORECASE):
            return {
                'evidence': 'No governing law clause found'
            }
        
        if extracted_data and not extracted_data.get('governing_law'):
            return {
                'evidence': 'Governing law not clearly specified'
            }
        
        return None
    
    def check_termination_notice(
        self,
        text: str,
        extracted_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Check for short termination notice periods."""
        matches = re.finditer(
            r'(?:terminate|cancel).*?(\d+)\s+days?\s+notice',
            text,
            re.IGNORECASE
        )
        
        for match in matches:
            days = int(match.group(1))
            if days < 30:
                start = match.start()
                end = min(len(text), match.end() + 100)
                return {
                    'evidence': text[start:end],
                    'char_start': start,
                    'char_end': end
                }
        
        return None
    
    def calculate_risk_score(self, findings: List[Dict[str, Any]]) -> float:
        """Calculate overall risk score based on findings.
        
        Args:
            findings: List of audit findings
            
        Returns:
            Risk score from 0 (low risk) to 100 (high risk)
        """
        if not findings:
            return 0.0
        
        severity_weights = {
            'high': 30,
            'medium': 15,
            'low': 5
        }
        
        total_score = sum(
            severity_weights.get(f.get('severity', 'low'), 5)
            for f in findings
        )
        
        # Cap at 100
        return min(total_score, 100.0)
    
    def generate_audit_summary(
        self,
        findings: List[Dict[str, Any]],
        risk_score: float
    ) -> str:
        """Generate a human-readable audit summary using LLM.
        
        Args:
            findings: List of audit findings
            risk_score: Overall risk score
            
        Returns:
            Summary text
        """
        if not OPENAI_AVAILABLE or not self.client:
            return self._generate_simple_summary(findings, risk_score)
        
        if not findings:
            return "No significant risks identified in this document."
        
        findings_text = "\n".join([
            f"- {f['severity'].upper()}: {f['description']}"
            for f in findings
        ])
        
        prompt = f"""Provide a brief executive summary of the following contract audit findings:

{findings_text}

Overall Risk Score: {risk_score}/100

Summarize the key risks in 2-3 sentences:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a legal risk analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"Error generating audit summary: {e}")
            return self._generate_simple_summary(findings, risk_score)
    
    def _generate_simple_summary(
        self,
        findings: List[Dict[str, Any]],
        risk_score: float
    ) -> str:
        """Generate simple summary without LLM."""
        if not findings:
            return "No significant risks identified."
        
        high = sum(1 for f in findings if f.get('severity') == 'high')
        medium = sum(1 for f in findings if f.get('severity') == 'medium')
        low = sum(1 for f in findings if f.get('severity') == 'low')
        
        return f"Found {len(findings)} issues: {high} high, {medium} medium, {low} low severity. Risk score: {risk_score}/100."

