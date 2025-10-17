#!/bin/bash

# Local development setup without Docker

echo "🚀 Setting up Contract Intelligence API (Local Mode)..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Copy environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

# Create data directories
mkdir -p data/uploads
echo "✅ Data directories created"

echo ""
echo "✅ Setup complete! 🎉"
echo ""
echo "📝 Next steps:"
echo "1. Make sure PostgreSQL is running:"
echo "   brew install postgresql"
echo "   brew services start postgresql"
echo "   createdb contract_intelligence"
echo ""
echo "   OR use Docker for just the database:"
echo "   docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15"
echo ""
echo "2. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "3. Run the application:"
echo "   python -m uvicorn src.main:app --reload"
echo ""
echo "4. Open your browser:"
echo "   http://localhost:8000/docs"
echo ""
