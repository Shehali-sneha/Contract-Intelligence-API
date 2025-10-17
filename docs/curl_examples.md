# Sample cURL Commands for Contract Intelligence API

## Health Check
```bash
curl -X GET "http://localhost:8000/healthz"
```

## Get Metrics
```bash
curl -X GET "http://localhost:8000/metrics"
```

## Ingest a PDF Document
```bash
# Single file
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@path/to/your/contract.pdf"

# Multiple files
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@contract1.pdf" \
  -F "files=@contract2.pdf" \
  -F "files=@contract3.pdf"
```

## List All Documents
```bash
curl -X GET "http://localhost:8000/api/v1/documents"
```

## Get Specific Document Metadata
```bash
curl -X GET "http://localhost:8000/api/v1/documents/{document_id}"
```

## Extract Data from a Document
```bash
# Replace {document_id} with actual ID from ingest response
curl -X POST "http://localhost:8000/api/v1/extract" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "{document_id}"
  }'
```

## Example: Complete Workflow

### Step 1: Ingest a document
```bash
RESPONSE=$(curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@sample_contract.pdf")

echo $RESPONSE
```

### Step 2: Extract document ID from response
```bash
# The response will contain document_ids array
# Example: {"document_ids":["abc-123-def"],"total_documents":1,"message":"Success"}
DOCUMENT_ID="abc-123-def"  # Replace with actual ID
```

### Step 3: Extract contract data
```bash
curl -X POST "http://localhost:8000/api/v1/extract" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": \"$DOCUMENT_ID\"}"
```

## Using jq for Pretty Output
```bash
# Pretty print JSON responses
curl -s http://localhost:8000/healthz | jq '.'

# Extract specific fields
curl -s http://localhost:8000/metrics | jq '.total_documents'

# Save response to file
curl -X POST "http://localhost:8000/api/v1/extract" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "your-id"}' \
  | jq '.' > extraction_result.json
```

## Python Example
```python
import requests

# Ingest a document
with open('contract.pdf', 'rb') as f:
    files = {'files': f}
    response = requests.post(
        'http://localhost:8000/api/v1/ingest',
        files=files
    )
    result = response.json()
    document_id = result['document_ids'][0]
    print(f"Document ID: {document_id}")

# Extract data
response = requests.post(
    'http://localhost:8000/api/v1/extract',
    json={'document_id': document_id}
)
extraction = response.json()
print(f"Parties: {extraction['parties']}")
print(f"Effective Date: {extraction['effective_date']}")
print(f"Term: {extraction['term']}")
```

## Testing with Sample PDF
```bash
# Create a simple test PDF using Python
python3 << 'EOF'
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

c = canvas.Canvas("test_contract.pdf", pagesize=letter)
c.drawString(100, 750, "SERVICE AGREEMENT")
c.drawString(100, 700, "This agreement is entered into between Company A and Company B")
c.drawString(100, 680, "on January 1, 2024.")
c.drawString(100, 650, "Term: 12 months")
c.drawString(100, 630, "Governing Law: California")
c.drawString(100, 610, "Payment Terms: Net 30 days")
c.drawString(100, 590, "This agreement automatically renews with 30 days notice.")
c.drawString(100, 570, "Liability is capped at $100,000 USD.")
c.save()
print("Test PDF created: test_contract.pdf")
EOF

# Then ingest it
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -F "files=@test_contract.pdf"
```
