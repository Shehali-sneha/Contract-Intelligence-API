"""Tests for the Contract Intelligence API."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app
from src.database import Base, get_db
from src import models

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Contract Intelligence API"
    assert data["status"] == "running"


def test_health_check(test_db):
    """Test health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "timestamp" in data


def test_metrics(test_db):
    """Test metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "total_extractions" in data
    assert "total_audit_findings" in data
    assert "uptime_seconds" in data


def test_list_documents_empty(test_db):
    """Test listing documents when none exist."""
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_extract_nonexistent_document(test_db):
    """Test extracting from a document that doesn't exist."""
    response = client.post(
        "/api/v1/extract",
        json={"document_id": "nonexistent-id"}
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_ingest_no_files(test_db):
    """Test ingesting with no files provided."""
    response = client.post("/api/v1/ingest", files=[])
    assert response.status_code == 422  # Validation error


def test_api_docs():
    """Test that API documentation is available."""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/redoc")
    assert response.status_code == 200


def test_openapi_schema():
    """Test that OpenAPI schema is available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
