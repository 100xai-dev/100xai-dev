#!/bin/bash

echo "🔗 Quick WordPress.com OAuth Setup for Ngrok"
echo "=============================================="
echo ""
echo "Your ngrok URL: https://267f-43-249-224-202.ngrok-free.app"
echo ""

echo "📋 Step 1: Create WordPress.com OAuth App"
echo "Visit: https://developer.wordpress.com/apps/"
echo ""
echo "Use these settings:"
echo "  Application Name: 100xAI Content Publisher"
echo "  Website URL: https://267f-43-249-224-202.ngrok-free.app"
echo "  Redirect URI: https://267f-43-249-224-202.ngrok-free.app/v1/integrations/wordpress/oauth/callback"
echo ""

read -p "Press Enter after you've created the WordPress.com app..."

echo ""
echo "📝 Step 2: Update Environment Variables"
echo "Please provide your WordPress.com app credentials:"
echo ""

read -p "WordPress.com Client ID: " CLIENT_ID
read -p "WordPress.com Client Secret: " CLIENT_SECRET

if [ ! -z "$CLIENT_ID" ] && [ ! -z "$CLIENT_SECRET" ]; then
    # Update .env file with real credentials
    sed -i '' "s/WPCOM_CLIENT_ID=your_client_id_here/WPCOM_CLIENT_ID=$CLIENT_ID/" .env
    sed -i '' "s/WPCOM_CLIENT_SECRET=your_client_secret_here/WPCOM_CLIENT_SECRET=$CLIENT_SECRET/" .env
    
    echo "✅ Environment variables updated"
else
    echo "⚠️  Skipped credential update (you can update .env file manually)"
fi

echo ""
echo "🔄 Step 3: Restart Backend"
echo "The backend needs to restart to load new environment variables..."
echo ""

# Check if backend is running and get PID
BACKEND_PID=$(ps aux | grep "uvicorn app.main:app" | grep -v grep | awk '{print $2}')

if [ ! -z "$BACKEND_PID" ]; then
    echo "Stopping current backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID
    sleep 2
fi

echo "Starting backend with new configuration..."
PYTHONPATH=. ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

BACKEND_NEW_PID=$!
echo "✅ Backend restarted (PID: $BACKEND_NEW_PID)"

echo ""
echo "⏳ Waiting for backend to start..."
sleep 5

# Test backend
if curl -s https://267f-43-249-224-202.ngrok-free.app/health > /dev/null; then
    echo "✅ Backend is accessible via ngrok"
else
    echo "❌ Backend not accessible - check ngrok tunnel"
fi

echo ""
echo "🧪 Step 4: Test OAuth Flow"
echo ""
echo "Test URLs:"
echo "  Health Check: https://267f-43-249-224-202.ngrok-free.app/health"
echo "  API Docs: https://267f-43-249-224-202.ngrok-free.app/docs"
echo "  OAuth Test: https://267f-43-249-224-202.ngrok-free.app/v1/integrations/wordpress/oauth/authorize?brand_id=test-123"
echo ""
echo "🎯 To test WordPress OAuth:"
echo "1. Visit the OAuth Test URL in your browser"
echo "2. Log in to WordPress.com when prompted"
echo "3. Grant permissions to your 100xAI app"
echo "4. You should be redirected back to the callback URL"
echo ""
echo "✅ Setup complete! Your backend is ready for WordPress.com OAuth testing."