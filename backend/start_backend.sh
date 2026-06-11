#!/bin/bash

# 100xAI Backend Startup Script
# Starts the FastAPI backend server for development

echo "🚀 Starting 100xAI Backend Server..."

# Set environment variables for development
export PYTHONPATH=.
export DATABASE_URL=${DATABASE_URL:-"postgresql://100xai:100xai@localhost:5432/100xai"}
export JWT_SECRET=${JWT_SECRET:-"dev-secret-change-me-at-least-32-chars"}
export ENVIRONMENT=${ENVIRONMENT:-"development"}

# Default port
PORT=${1:-8000}

echo ""
echo "📋 Configuration:"
echo "   Port: $PORT"
echo "   Environment: $ENVIRONMENT"
echo "   Database: ${DATABASE_URL}"
echo "   Python Path: $PYTHONPATH"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found at ./venv"
    echo ""
    echo "🔧 To create virtual environment:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Check if dependencies are installed
if ! ./venv/bin/python -c "import fastapi" 2>/dev/null; then
    echo "❌ Dependencies not installed"
    echo ""
    echo "📦 Installing dependencies..."
    ./venv/bin/pip install -r requirements.txt
    echo "✅ Dependencies installed"
fi

# Check database connection
echo "🔍 Checking database connection..."
if ! ./venv/bin/python -c "
from app.db import get_db_session
from sqlalchemy import text
try:
    with get_db_session() as session:
        session.execute(text('SELECT 1'))
    print('✅ Database connected successfully')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    print('')
    print('🔧 Make sure PostgreSQL is running:')
    print('   brew services start postgresql')
    print('   # OR')
    print('   docker run -d --name postgres -p 5432:5432 -e POSTGRES_USER=100xai -e POSTGRES_PASSWORD=100xai -e POSTGRES_DB=100xai postgres:15')
    exit(1)
" 2>/dev/null; then
    echo "❌ Database check failed"
    exit 1
fi

# Run database migrations
echo "🗄️  Running database migrations..."
./venv/bin/alembic upgrade head

# Check if app imports correctly
echo "📦 Checking app imports..."
if ! ./venv/bin/python -c "from app.main import app; print('✅ App imports successfully')" 2>/dev/null; then
    echo "❌ App import failed"
    exit 1
fi

echo ""
echo "🌐 Starting FastAPI server on http://localhost:$PORT"
echo "📚 API Documentation: http://localhost:$PORT/docs"
echo "🔍 Health Check: http://localhost:$PORT/health"
echo ""
echo "💡 Press Ctrl+C to stop the server"
echo "🔗 Use './setup_ngrok_tunnel.sh' to expose publicly for OAuth testing"
echo ""

# Start the server
exec ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload