# Contract Intelligence System

A production-grade FastAPI application for ingesting PDF contracts, extracting structured fields, and performing intelligent analysis.

## Features

✅ **Implemented:**
- 📄 **PDF Ingestion**: Upload multiple PDF contracts with automatic text extraction
- 📊 **Data Extraction**: Extract structured contract fields (parties, dates, terms, etc.)
- 🗄️ **PostgreSQL Database**: Persistent storage with SQLAlchemy ORM
- 🐳 **Docker Support**: Full containerization with Docker Compose
- 📚 **API Documentation**: Auto-generated Swagger/OpenAPI docs
- 🏥 **Health Checks**: Monitor system health and metrics
- 🔍 **Text Chunking**: Prepare documents for RAG pipeline

🚧 **Coming Soon:**
- 💬 **RAG Q&A**: Question answering with citations
- ⚠️ **Risk Audit**: Detect risky clauses
- 🔄 **Streaming**: SSE/WebSocket streaming
- 🔗 **Webhooks**: Event notifications

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)

### 1. Start with Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd tichu

# Copy environment file
cp .env.example .env

# Start all services
make up

# Or using docker-compose directly
docker-compose up -d
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 2. Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL (using Docker)
docker run -d \
  --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=contract_intelligence \
  -p 5432:5432 \
  postgres:15-alpine

# Copy environment file
cp .env.example .env

# Run the application
make dev

# Or directly
uvicorn src.main:app --reload
```

## API Endpoints

### 📥 Ingest Documents
Upload PDF contracts for processing.

```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@contract1.pdf" \
  -F "files=@contract2.pdf"
```

**Response:**
```json
{
  "document_ids": ["uuid-1", "uuid-2"],
  "total_documents": 2,
  "message": "Successfully ingested 2 document(s)"
}
```

### 🔍 Extract Contract Data
Extract structured fields from a contract.

```bash
curl -X POST "http://localhost:8000/api/v1/extract" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "uuid-1"
  }'
```

**Response:**
```json
{
  "document_id": "uuid-1",
  "parties": ["Company A", "Company B"],
  "effective_date": "January 1, 2024",
  "term": "12 months",
  "governing_law": "California",
  "payment_terms": "Net 30 days...",
  "termination": "Either party may terminate...",
  "auto_renewal": "Yes, 30 days notice required",
  "confidentiality": "Both parties agree...",
  "indemnity": "Each party shall indemnify...",
  "liability_cap": {
    "amount": 100000,
    "currency": "USD"
  },
  "signatories": [],
  "extraction_method": "rule-based",
  "confidence_score": 0.7
}
```

### 📋 List Documents
Get all ingested documents.

```bash
curl -X GET "http://localhost:8000/api/v1/documents"
```

### 🏥 Health Check
Check system health.

```bash
curl -X GET "http://localhost:8000/healthz"
```

### 📊 Metrics
View system metrics.

```bash
curl -X GET "http://localhost:8000/metrics"
```

## Project Structure

```
tichu/
├── src/
│   ├── main.py          # FastAPI application entry point
│   ├── api.py           # API endpoints (ingest, extract, etc.)
│   ├── models.py        # SQLAlchemy database models
│   ├── schemas.py       # Pydantic schemas for validation
│   ├── database.py      # Database configuration
│   ├── crud.py          # Database operations
│   └── utils.py         # PDF processing utilities
├── tests/
│   └── test_api.py      # API tests
├── data/
│   └── uploads/         # Uploaded PDF files
├── docker-compose.yml   # Docker Compose configuration
├── Dockerfile           # Docker image definition
├── requirements.txt     # Python dependencies
├── Makefile            # Convenient commands
└── README.md           # This file
```

## Development

### Available Make Commands

```bash
make up         # Start all services
make down       # Stop all services
make build      # Build Docker images
make restart    # Restart services
make logs       # View logs
make shell      # Open shell in API container
make test       # Run tests
make clean      # Clean up containers and volumes
make install    # Install dependencies locally
make dev        # Run locally without Docker
```

### Database Schema

**Documents Table:**
- Stores uploaded PDF metadata
- Fields: document_id, filename, file_path, file_size, num_pages, etc.

**Document Chunks Table:**
- Stores text chunks for RAG
- Fields: chunk_index, text_content, page_number, metadata

**Extracted Data Table:**
- Stores extracted contract fields
- Fields: parties, dates, terms, governing_law, payment_terms, etc.

**Audit Findings Table:**
- Stores risk/audit findings (future)
- Fields: finding_type, severity, description, evidence

## Architecture

### Data Pipeline

1. **Ingest**: 
   - Upload PDF files via multipart/form-data
   - Save files to disk with unique IDs
   - Extract text using PyPDF
   - Create chunks for RAG
   - Store metadata in PostgreSQL

2. **Extract**:
   - Retrieve document chunks from database
   - Apply rule-based extraction patterns
   - Extract key contract fields
   - Store structured data
   - Return formatted response

3. **Storage**:
   - Files stored in `data/uploads/`
   - Metadata in PostgreSQL
   - Chunked text for efficient retrieval

### Extraction Method

Currently using **rule-based extraction** with regex patterns:
- Parties: Pattern matching for "between X and Y"
- Dates: Multiple date format patterns
- Terms: Duration extraction
- Sections: Keyword-based section identification
- Liability: Amount and currency extraction

**Future**: LLM-based extraction with OpenAI/Anthropic for higher accuracy.

## Testing

Run tests using pytest:

```bash
# With Docker
make test

# Locally
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

## Environment Variables

See `.env.example` for available configuration options:

- `DATABASE_URL`: PostgreSQL connection string
- `PORT`: API port (default: 8000)
- `OPENAI_API_KEY`: For LLM-based extraction (optional)
- `UPLOAD_DIR`: Directory for uploaded files
- `MAX_FILE_SIZE`: Maximum upload file size

## Production Considerations

### Security
- [ ] Add authentication/authorization
- [ ] Implement rate limiting
- [ ] Validate and sanitize file uploads
- [ ] Use HTTPS in production
- [ ] Secure environment variables
- [ ] Add PII redaction in logs

### Performance
- [ ] Add Redis caching
- [ ] Implement background task queue (Celery)
- [ ] Add database connection pooling
- [ ] Optimize chunk sizes for RAG
- [ ] Add pagination for large result sets

### Monitoring
- [ ] Add structured logging
- [ ] Implement metrics collection (Prometheus)
- [ ] Add error tracking (Sentry)
- [ ] Set up alerting
- [ ] Add request tracing

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# View database logs
docker logs contract_intelligence_db

# Restart database
make restart
```

### PDF Extraction Errors
- Ensure PDFs are not password-protected
- Check file size limits
- Verify PDF is not corrupted
- Check logs for detailed errors

### Port Already in Use
```bash
# Change port in .env file
PORT=8001

# Or stop conflicting service
lsof -ti:8000 | xargs kill -9
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Run tests locally
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Contact

For questions or issues, please open a GitHub issue or contact the maintainers.
