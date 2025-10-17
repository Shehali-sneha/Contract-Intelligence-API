#!/bin/bash

# Quick setup script for Contract Intelligence API

echo "🚀 Setting up Contract Intelligence API..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

# Create data directories
mkdir -p data/uploads
echo "✅ Data directories created"

# Build and start services
echo "🏗️  Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ Setup complete! 🎉"
    echo ""
    echo "📚 API Documentation: http://localhost:8000/docs"
    echo "🔗 API Endpoint: http://localhost:8000"
    echo "🏥 Health Check: http://localhost:8000/healthz"
    echo "📊 Metrics: http://localhost:8000/metrics"
    echo ""
    echo "📖 View logs: docker-compose logs -f"
    echo "🛑 Stop services: docker-compose down"
    echo ""
else
    echo "❌ Services failed to start. Check logs with: docker-compose logs"
    exit 1
fi
