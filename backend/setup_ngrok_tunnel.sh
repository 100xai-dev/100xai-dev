#!/bin/bash

# 100xAI Backend - Ngrok Tunnel Setup for WordPress OAuth Testing
# This script sets up ngrok tunneling to expose the FastAPI backend publicly

echo "🚀 Setting up ngrok tunnel for 100xAI backend..."

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed."
    echo ""
    echo "📥 To install ngrok:"
    echo "1. Visit: https://ngrok.com/download"
    echo "2. Or via Homebrew: brew install ngrok"
    echo "3. Sign up for free account at: https://dashboard.ngrok.com/signup"
    echo "4. Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "5. Configure: ngrok config add-authtoken YOUR_TOKEN"
    exit 1
fi

# Check if ngrok is authenticated
if ! ngrok config check &> /dev/null; then
    echo "❌ ngrok is not authenticated."
    echo ""
    echo "🔑 To authenticate ngrok:"
    echo "1. Sign up at: https://dashboard.ngrok.com/signup"
    echo "2. Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "3. Run: ngrok config add-authtoken YOUR_TOKEN"
    exit 1
fi

# Default values
BACKEND_PORT=${1:-8000}
NGROK_SUBDOMAIN=${2:-""}
NGROK_REGION=${3:-"us"}

echo ""
echo "📋 Configuration:"
echo "   Backend Port: $BACKEND_PORT"
echo "   Ngrok Region: $NGROK_REGION"
if [ ! -z "$NGROK_SUBDOMAIN" ]; then
    echo "   Custom Subdomain: $NGROK_SUBDOMAIN"
fi
echo ""

# Check if backend is running
if ! curl -s http://localhost:$BACKEND_PORT/health > /dev/null; then
    echo "⚠️  Backend not detected on port $BACKEND_PORT"
    echo ""
    echo "🔧 To start the backend:"
    echo "   cd /Users/shubhamrathod/Downloads/100xai/backend"
    echo "   PYTHONPATH=. venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload"
    echo ""
    echo "   Or use the provided script:"
    echo "   ./start_backend.sh"
    echo ""
    read -p "❓ Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "🌐 Starting ngrok tunnel..."

# Build ngrok command
NGROK_CMD="ngrok http $BACKEND_PORT --region=$NGROK_REGION"

# Add subdomain if provided (requires paid ngrok plan)
if [ ! -z "$NGROK_SUBDOMAIN" ]; then
    NGROK_CMD="$NGROK_CMD --subdomain=$NGROK_SUBDOMAIN"
fi

# Add additional options for better stability
NGROK_CMD="$NGROK_CMD --log=stdout --log-level=info"

echo "📡 Running: $NGROK_CMD"
echo ""
echo "🔗 Your backend will be available at:"
echo "   Public URL: https://[random].ngrok-free.app"
if [ ! -z "$NGROK_SUBDOMAIN" ]; then
    echo "   Custom URL: https://$NGROK_SUBDOMAIN.ngrok-free.app"
fi
echo ""
echo "🛠️  For WordPress OAuth setup:"
echo "   Redirect URI: https://[your-ngrok-url]/v1/auth/wpcom/callback"
echo "   Authorization URL: https://[your-ngrok-url]/v1/auth/wpcom/authorize"
echo ""
echo "💡 Press Ctrl+C to stop the tunnel"
echo "📊 Ngrok dashboard: http://localhost:4040"
echo ""
echo "⚡ Starting tunnel now..."

# Start ngrok
$NGROK_CMD