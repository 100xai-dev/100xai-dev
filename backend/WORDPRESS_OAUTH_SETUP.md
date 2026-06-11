# WordPress.com OAuth Setup with Ngrok

This guide walks you through setting up WordPress.com OAuth integration using ngrok tunneling for public access.

## 🎯 Prerequisites

- ✅ 100xAI backend running locally
- ✅ Ngrok installed and authenticated
- ✅ WordPress.com account

## 📋 Step-by-Step Setup

### 1. Install and Configure Ngrok

```bash
# Install ngrok (if not already installed)
brew install ngrok

# OR download from https://ngrok.com/download

# Sign up for free account
# Visit: https://dashboard.ngrok.com/signup

# Get your auth token
# Visit: https://dashboard.ngrok.com/get-started/your-authtoken

# Configure ngrok with your auth token
ngrok config add-authtoken YOUR_AUTH_TOKEN_HERE
```

### 2. Start the Backend Server

```bash
# Navigate to backend directory
cd /Users/shubhamrathod/Downloads/100xai/backend

# Start the backend (will run on port 8000)
./start_backend.sh

# OR manual start:
PYTHONPATH=. venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Verify backend is running:**
- ✅ Health check: http://localhost:8000/health
- ✅ API docs: http://localhost:8000/docs

### 3. Start Ngrok Tunnel

```bash
# In a new terminal, start ngrok tunnel
./setup_ngrok_tunnel.sh

# OR manual command:
ngrok http 8000 --region=us
```

**Note your ngrok URL:** `https://[random-string].ngrok-free.app`

### 4. Create WordPress.com OAuth Application

1. **Visit WordPress.com Developer Console:**
   https://developer.wordpress.com/apps/

2. **Create New Application:**
   - Click "Create New Application"
   - Name: "100xAI Content Publisher"
   - Description: "AI-powered content publishing platform"
   - Website URL: `https://your-ngrok-url.ngrok-free.app`
   - Redirect URL: `https://your-ngrok-url.ngrok-free.app/v1/auth/wpcom/callback`
   - JavaScript Origins: `https://your-ngrok-url.ngrok-free.app`

3. **Application Type:** Web Application
4. **Click "Create"**

### 5. Configure Environment Variables

Add your WordPress.com OAuth credentials to your environment:

```bash
# Add to your .env file or export directly:
export WPCOM_CLIENT_ID="your_client_id_here"
export WPCOM_CLIENT_SECRET="your_client_secret_here"
export WPCOM_REDIRECT_URI="https://your-ngrok-url.ngrok-free.app/v1/auth/wpcom/callback"

# Restart your backend after adding these variables
```

### 6. Update Backend Configuration

Edit `app/config.py` to ensure WordPress.com OAuth is configured:

```python
# In app/config.py, verify these settings exist:
class Settings:
    # ... existing settings ...
    
    # WordPress.com OAuth
    wpcom_client_id: str = ""
    wpcom_client_secret: str = ""
    wpcom_redirect_uri: str = ""
```

### 7. Test WordPress.com OAuth Flow

**Step 7.1: Initiate OAuth Flow**

Visit the authorization URL in your browser:
```
https://your-ngrok-url.ngrok-free.app/v1/auth/wpcom/authorize?brand_id=YOUR_BRAND_ID
```

**Step 7.2: Grant Permissions**

You'll be redirected to WordPress.com to:
- ✅ Log in to your WordPress.com account
- ✅ Grant permissions to the 100xAI app
- ✅ Select which WordPress.com site to connect

**Step 7.3: Complete Authorization**

After granting permissions, you'll be redirected back to:
```
https://your-ngrok-url.ngrok-free.app/v1/auth/wpcom/callback?code=AUTH_CODE&state=BRAND_ID
```

**Step 7.4: Verify Integration**

The backend will:
- ✅ Exchange auth code for access token
- ✅ Store credentials securely
- ✅ Test the connection
- ✅ Redirect you to success page

## 🧪 Testing the Integration

### Test API Endpoints

```bash
# 1. Test authorization endpoint
curl "https://your-ngrok-url.ngrok-free.app/v1/auth/wpcom/authorize?brand_id=test-brand-123"

# 2. Test sites list (after OAuth completion)
curl -X GET "https://your-ngrok-url.ngrok-free.app/v1/auth/wpcom/sites" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 3. Test posting to WordPress.com
curl -X POST "https://your-ngrok-url.ngrok-free.app/v1/brands/BRAND_ID/integrations/publish" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "title": "Test Post from 100xAI",
    "content": "<p>This is a test post published via the 100xAI platform!</p>",
    "status": "draft"
  }'
```

### Manual WordPress.com API Test

```bash
# Test direct WordPress.com API access (after OAuth)
curl "https://public-api.wordpress.com/rest/v1.1/me" \
  -H "Authorization: Bearer WORDPRESS_ACCESS_TOKEN"
```

## 🔧 Troubleshooting

### Common Issues

**❌ "ngrok not found"**
```bash
# Install ngrok
brew install ngrok
# OR download from https://ngrok.com/download
```

**❌ "ngrok authentication required"**
```bash
# Get token from https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_TOKEN
```

**❌ "Backend not responding"**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Restart backend
./start_backend.sh
```

**❌ "OAuth redirect mismatch"**
- ✅ Ensure redirect URI in WordPress.com app matches ngrok URL exactly
- ✅ Update WordPress.com app settings if ngrok URL changes
- ✅ Include `/v1/auth/wpcom/callback` path in redirect URI

**❌ "CORS errors"**
- ✅ Add ngrok domain to CORS allowed origins in backend
- ✅ Verify `https://` protocol is used (not `http://`)

### Debug OAuth Flow

**Enable debug logging:**

```python
# In app/routers/wpcom_oauth.py, add debug logging:
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# View logs during OAuth flow
tail -f logs/app.log
```

**Check OAuth state management:**

```bash
# Verify OAuth state in database
psql -h localhost -p 5432 -U 100xai -d 100xai -c "
SELECT * FROM oauth_states WHERE provider = 'wpcom' ORDER BY created_at DESC LIMIT 5;
"
```

## 🔐 Security Notes

### Development vs Production

**Development (Ngrok):**
- ✅ Use ngrok for testing only
- ✅ URLs change frequently - update WordPress.com app accordingly
- ✅ Not suitable for production traffic

**Production:**
- ✅ Use permanent domain with SSL certificate
- ✅ Update WordPress.com OAuth app with production URLs
- ✅ Use environment variables for credentials
- ✅ Enable CSRF protection and secure session handling

### OAuth Security Best Practices

- ✅ **State Parameter**: Always use state parameter to prevent CSRF
- ✅ **HTTPS Only**: Never use OAuth over HTTP
- ✅ **Token Storage**: Store access tokens securely (encrypted at rest)
- ✅ **Token Rotation**: Implement refresh token handling
- ✅ **Scope Limitation**: Request minimal necessary permissions

## 📱 Frontend Integration

Once OAuth is working, update your frontend to use the flow:

```javascript
// Initiate OAuth from frontend
const initiateWordPressOAuth = (brandId) => {
  const authUrl = `${process.env.NEXT_PUBLIC_API_URL}/v1/auth/wpcom/authorize?brand_id=${brandId}`;
  window.location.href = authUrl;
};

// Handle OAuth completion
const handleOAuthCallback = () => {
  // The backend handles the callback and redirects to success page
  // You can then refresh integration status
  fetchIntegrationStatus(brandId);
};
```

## ✅ Success Checklist

After completing setup, verify:

- ✅ Ngrok tunnel is running and accessible
- ✅ Backend responds on ngrok URL
- ✅ WordPress.com OAuth app is configured correctly
- ✅ OAuth flow completes without errors
- ✅ Access tokens are stored and working
- ✅ Can publish test posts to WordPress.com
- ✅ Integration status shows "connected" in frontend

## 📞 Support

If you encounter issues:

1. **Check logs**: Review backend logs for detailed error messages
2. **Verify URLs**: Ensure all URLs are HTTPS and match exactly
3. **Test manually**: Use curl commands to test each step
4. **WordPress.com status**: Check if WordPress.com APIs are operational

---

*Setup guide updated: June 10, 2026*  
*Supports: WordPress.com OAuth 2.0 integration*