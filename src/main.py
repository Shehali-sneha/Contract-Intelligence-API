"""Main FastAPI application for Contract Intelligence System."""
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

from src.database import init_db, get_db
from src import api, schemas, crud

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Track application start time for metrics
APP_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application."""
    # Startup
    logger.info("Starting Contract Intelligence API...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Create upload directory
    os.makedirs("data/uploads", exist_ok=True)
    logger.info("Upload directory created")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Contract Intelligence API...")


# Create FastAPI application
app = FastAPI(
    title="Contract Intelligence API",
    description="""
    Production-grade Contract Intelligence API for ingesting PDFs, extracting structured fields,
    answering questions, and running clause-risk checks.
    
    ## Features
    
    * **Ingest**: Upload and process PDF contracts
    * **Extract**: Extract structured data (parties, dates, terms, etc.)
    * **Ask**: Question answering with RAG (coming soon)
    * **Audit**: Detect risky clauses (coming soon)
    * **Health & Metrics**: Monitor system health and usage
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Time: {process_time:.3f}s"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url.path} - Error: {str(e)}")
        raise


# Include routers
app.include_router(api.router, prefix="/api/v1", tags=["contracts"])


# Health check endpoint
@app.get("/healthz", response_model=schemas.HealthResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the health status of the API and database connection.
    """
    db_status = "healthy"
    
    try:
        # Test database connection
        db = next(get_db())
        # Use text() for raw SQL in SQLAlchemy 2.0
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    return schemas.HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
        timestamp=datetime.now()
    )


# Metrics endpoint
@app.get("/metrics", response_model=schemas.MetricsResponse, tags=["health"])
async def get_metrics():
    """
    Get system metrics.
    
    Returns counts of documents, extractions, and audit findings.
    """
    try:
        db = next(get_db())
        
        total_documents = crud.get_total_documents(db)
        total_extractions = crud.get_total_extractions(db)
        total_audit_findings = crud.get_total_audit_findings(db)
        
        db.close()
        
        uptime = time.time() - APP_START_TIME
        
        return schemas.MetricsResponse(
            total_documents=total_documents,
            total_extractions=total_extractions,
            total_audit_findings=total_audit_findings,
            uptime_seconds=uptime
        )
    
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to retrieve metrics", "detail": str(e)}
        )


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Contract Intelligence API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/healthz",
        "metrics": "/metrics"
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "detail": f"The requested resource was not found: {request.url.path}",
            "status_code": 404
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Please try again later.",
            "status_code": 500
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
