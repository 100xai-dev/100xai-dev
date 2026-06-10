# 100xAI Platform - Integration Setup Guide

This guide explains how to integrate Shopify, Ghost, and Webflow APIs with the 100xAI content publishing platform.

## 📋 Table of Contents
- [Architecture Overview](#architecture-overview)
- [Shopify Integration](#shopify-integration)
- [Ghost Integration](#ghost-integration)
- [Webflow Integration (Planned)](#webflow-integration-planned)
- [WordPress Integration](#wordpress-integration)
- [Common Integration Issues](#common-integration-issues)

---

## 🏗️ Architecture Overview

100xAI supports two integration systems:

### **Legacy Publisher System** (Currently Active)
- **Location**: `app/services/publishers/`
- **Implemented**: Shopify, Ghost, WordPress, Webhook
- **Status**: Fully functional, production-ready

### **New Integration System** (Future)
- **Location**: `app/integrations/`
- **Implemented**: WordPress only
- **Status**: Framework ready, needs migration

---

## 🛍️ Shopify Integration

### **Prerequisites**
- Shopify Partner account or Shopify store admin access
- Custom App or Private App with Admin API access

### **Step 1: Create Shopify App**
1. **Go to Shopify Partner Dashboard** or **Store Admin** → **Apps** → **App and sales channel settings**
2. **Create Custom App**:
   - App name: "100xAI Content Publisher"
   - App URL: `https://your-domain.com` (optional)

### **Step 2: Configure API Permissions**
Grant the following Admin API scopes:
- ✅ `write_content` - Create/update blog posts
- ✅ `read_content` - Read existing content
- ✅ `write_products` - (Optional) For product-related posts

### **Step 3: Generate Access Token**
1. In the Custom App settings, generate an **Admin API access token**
2. **IMPORTANT**: Save this token securely - it won't be shown again

### **Step 4: Get Configuration Details**
You'll need:
- **Shop Name**: Your Shopify store name (e.g., "mystore" for mystore.myshopify.com)
- **Access Token**: The generated Admin API token
- **Blog ID**: (Optional) Specific blog ID, or leave empty for main blog

### **Step 5: Integration Configuration**

```json
{
  "provider": "shopify",
  "config": {
    "shop_name": "mystore",
    "default_status": "published",
    "timeout": 30,
    "verify_ssl": true
  },
  "credentials": {
    "access_token": "shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  }
}
```

### **Step 6: Test Integration**
Use the 100xAI integration test endpoint:

```bash
# Test Shopify connection
curl -X POST "http://localhost:8000/v1/brands/{brand_id}/integrations/test" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "provider": "shopify",
    "config": {
      "shop_name": "mystore"
    },
    "credentials": {
      "access_token": "shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Shopify connection validated",
  "site_info": {
    "shop_name": "My Store",
    "blog_title": "News",
    "admin_url": "https://mystore.myshopify.com/admin"
  }
}
```

### **Common Shopify Issues:**
- ❌ **401 Unauthorized**: Check access token validity
- ❌ **403 Forbidden**: Verify API permissions/scopes
- ❌ **404 Not Found**: Verify shop name spelling
- ❌ **422 Unprocessable**: Content validation errors

---

## 👻 Ghost Integration

### **Prerequisites**
- Ghost publication (self-hosted or Ghost Pro)
- Admin access to create integrations

### **Step 1: Create Custom Integration**
1. **Go to Ghost Admin** → **Settings** → **Integrations**
2. **Click "Add custom integration"**
3. **Name**: "100xAI Content Publisher"
4. **Description**: "Automated content publishing from 100xAI"

### **Step 2: Get Admin API Key**
1. After creating the integration, copy the **Admin API Key**
2. **Format**: `key_id:secret_in_hex`
3. **Example**: `6571c4b2e17b5a0e584b4a99:47c9c4b2e17b5a0e584b4a9947c9c4b2e17b5a0e584b4a99`

### **Step 3: Configure Webhooks (Optional)**
1. **Content API Key**: For read-only access (optional)
2. **Webhook URL**: For real-time notifications (optional)

### **Step 4: Integration Configuration**

```json
{
  "provider": "ghost",
  "config": {
    "site_url": "https://mysite.ghost.io",
    "default_status": "published",
    "timeout": 30,
    "verify_ssl": true,
    "author_email": "author@example.com"
  },
  "credentials": {
    "admin_api_key": "6571c4b2e17b5a0e584b4a99:47c9c4b2e17b5a0e584b4a99..."
  }
}
```

### **Step 5: Test Integration**

```bash
# Test Ghost connection
curl -X POST "http://localhost:8000/v1/brands/{brand_id}/integrations/test" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "provider": "ghost",
    "config": {
      "site_url": "https://mysite.ghost.io"
    },
    "credentials": {
      "admin_api_key": "key_id:secret_hex"
    }
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Ghost connection validated",
  "site_info": {
    "site_title": "My Publication",
    "site_description": "A great publication",
    "admin_url": "https://mysite.ghost.io/ghost/"
  }
}
```

### **Common Ghost Issues:**
- ❌ **401 Unauthorized**: Invalid or expired Admin API key
- ❌ **403 Forbidden**: Key lacks required permissions
- ❌ **404 Not Found**: Incorrect Ghost site URL
- ❌ **JWT Error**: Malformed Admin API key format

---

## 🌊 Webflow Integration (Planned)

### **Current Status**: ⚠️ **NOT IMPLEMENTED** - Only stub exists

### **Integration Plan**

#### **Phase 1: API Research & Design** 
- [ ] Analyze Webflow CMS API capabilities
- [ ] Design authentication flow (API key vs OAuth)
- [ ] Map 100xAI content structure to Webflow CMS items
- [ ] Define required Webflow permissions

#### **Phase 2: Implementation**
- [ ] Create `WebflowProvider` class in new integration system
- [ ] Implement authentication and site validation
- [ ] Add content publishing capabilities
- [ ] Support for Webflow CMS collections

#### **Phase 3: Testing & Documentation**
- [ ] Integration testing with various Webflow sites
- [ ] Error handling and edge cases
- [ ] User documentation and setup guides

### **Webflow API Capabilities**
- ✅ **CMS Collections**: Publish to blog collections
- ✅ **Rich Content**: Support for rich text and embeds
- ✅ **Asset Management**: Upload and manage images
- ✅ **SEO Fields**: Meta titles, descriptions, slugs
- ⚠️ **Rate Limits**: 60 requests/minute (free), 120/minute (paid)

### **Required Webflow Setup**
1. **Webflow site** with CMS plan
2. **API access** enabled in project settings
3. **CMS Collection** configured for blog posts
4. **API Token** generated with appropriate permissions

### **Planned Configuration Format**

```json
{
  "provider": "webflow",
  "config": {
    "site_id": "webflow_site_id",
    "collection_id": "blog_collection_id",
    "default_status": "published",
    "timeout": 30
  },
  "credentials": {
    "api_token": "webflow_api_token"
  }
}
```

---

## 🌐 WordPress Integration

### **Self-Hosted WordPress**
- **Authentication**: Application Passwords (WP 5.6+)
- **Requirements**: REST API enabled
- **Setup**: Generate app password in user profile

```json
{
  "provider": "wordpress",
  "config": {
    "site_url": "https://mysite.com",
    "default_status": "published"
  },
  "credentials": {
    "username": "admin",
    "application_password": "xxxx xxxx xxxx xxxx"
  }
}
```

### **WordPress.com**
- **Authentication**: OAuth 2.0
- **Setup**: Use 100xAI's WordPress.com OAuth flow
- **Automatic**: Handled by `/v1/auth/wpcom/` endpoints

---

## 🔧 Common Integration Issues

### **Network Errors**
```
Network error: [Errno 8] nodename nor servname provided, or not known
```
**Solutions**:
- ✅ Verify site URL is correct and accessible
- ✅ Check DNS resolution: `nslookup yoursite.com`
- ✅ Ensure site is not behind firewall

### **Authentication Failures**
```
401 Unauthorized / 403 Forbidden
```
**Solutions**:
- ✅ Regenerate API keys/tokens
- ✅ Verify permissions and scopes
- ✅ Check token expiration dates
- ✅ Validate API key format

### **Rate Limiting**
```
429 Too Many Requests
```
**Solutions**:
- ✅ Implement exponential backoff
- ✅ Respect platform rate limits
- ✅ Consider upgrading API plan

### **Content Validation Errors**
```
422 Unprocessable Entity
```
**Solutions**:
- ✅ Check content format requirements
- ✅ Validate image URLs are accessible
- ✅ Ensure required fields are provided
- ✅ Verify tag/category limits

---

## 🎯 Integration Testing Commands

### **Available Test Commands**

```bash
# Test any integration
PYTHONPATH=. python -c "
from app.services.publishers.shopify import ShopifyPublisher
from app.services.publishers.ghost import GhostPublisher

# Test Shopify
shopify_config = {
    'shop_name': 'mystore',
    'access_token': 'shpat_xxxxx'
}
shopify = ShopifyPublisher(shopify_config)
print('Shopify valid:', shopify.validate_config())

# Test Ghost  
ghost_config = {
    'site_url': 'https://mysite.ghost.io',
    'admin_api_key': 'key_id:secret_hex'
}
ghost = GhostPublisher(ghost_config)
print('Ghost valid:', ghost.validate_config())
"
```

---

## 📞 Support

If you encounter issues with integrations:

1. **Check logs**: Look for detailed error messages in application logs
2. **Verify credentials**: Ensure all API keys are current and valid
3. **Test manually**: Try API calls directly using curl or Postman
4. **Check platform status**: Verify the target platform isn't experiencing outages

For platform-specific support:
- **Shopify**: [Shopify Developer Support](https://help.shopify.com/en/partners)
- **Ghost**: [Ghost Developer Docs](https://ghost.org/docs/admin-api/)
- **WordPress**: [WordPress REST API Handbook](https://developer.wordpress.org/rest-api/)

---

*Last updated: June 10, 2026*