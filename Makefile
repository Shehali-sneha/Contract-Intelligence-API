.PHONY: help up down build restart logs shell test clean install

help:
	@echo "Contract Intelligence API - Available Commands:"
	@echo "  make up         - Start all services with Docker Compose"
	@echo "  make down       - Stop all services"
	@echo "  make build      - Build Docker images"
	@echo "  make restart    - Restart all services"
	@echo "  make logs       - View logs from all services"
	@echo "  make shell      - Open a shell in the API container"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean up Docker containers and volumes"
	@echo "  make install    - Install Python dependencies locally"
	@echo "  make dev        - Run API locally (without Docker)"

up:
	docker-compose up -d
	@echo "Services started. API available at http://localhost:8000"
	@echo "API docs available at http://localhost:8000/docs"

down:
	docker-compose down

build:
	docker-compose build

restart:
	docker-compose restart

logs:
	docker-compose logs -f

shell:
	docker-compose exec api /bin/bash

test:
	docker-compose exec api pytest tests/ -v

clean:
	docker-compose down -v
	rm -rf data/uploads/*
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

install:
	pip install -r requirements.txt

dev:
	@echo "Make sure PostgreSQL is running locally..."
	@cp .env.example .env 2>/dev/null || true
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
