"""Webhook publishing adapter for custom sites."""

import requests
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from .base import (
    BasePublisher, 
    PublishingError, 
    AuthenticationError, 
    ContentValidationError,
    RateLimitError
)


class WebhookPublisher(BasePublisher):
    """Publisher for custom sites using webhook integration."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Webhook publisher.
        
        Required config:
            - webhook_url: str - Target webhook URL
        
        Optional config:
            - secret: str - Webhook secret for HMAC signing
            - timeout: int - Request timeout (default: 30)
            - verify_ssl: bool - Verify SSL certificates (default: True)
            - headers: dict - Additional headers to send
            - method: str - HTTP method (default: "POST")
            - auth_type: str - Authentication type ("bearer", "basic", "api_key")
            - auth_token: str - Authentication token/key
        """
        super().__init__(config)
        
        # Required fields
        self.webhook_url = config.get("webhook_url", "")
        
        # Optional fields
        self.secret = config.get("secret", "")
        self.timeout = config.get("timeout", 30)
        self.verify_ssl = config.get("verify_ssl", True)
        self.custom_headers = config.get("headers", {})
        self.method = config.get("method", "POST").upper()
        self.auth_type = config.get("auth_type", "")
        self.auth_token = config.get("auth_token", "")
        
        # Create session for reuse
        self.session = requests.Session()
        self.session.timeout = self.timeout
        self.session.verify = self.verify_ssl
        
        # Set up headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': '100xAI-Publisher/1.0'
        })
        
        # Add custom headers
        if self.custom_headers:
            self.session.headers.update(self.custom_headers)
        
        # Set up authentication
        if self.auth_type and self.auth_token:
            if self.auth_type.lower() == "bearer":
                self.session.headers['Authorization'] = f'Bearer {self.auth_token}'
            elif self.auth_type.lower() == "basic":
                self.session.headers['Authorization'] = f'Basic {self.auth_token}'
            elif self.auth_type.lower() == "api_key":
                self.session.headers['X-API-Key'] = self.auth_token
    
    def validate_config(self) -> bool:
        """Validate webhook configuration."""
        # Check required fields
        if not self.webhook_url:
            raise AuthenticationError("Missing required webhook config: webhook_url")
        
        # Validate URL format
        parsed = urlparse(self.webhook_url)
        if not parsed.scheme or not parsed.netloc:
            raise AuthenticationError(f"Invalid webhook URL: {self.webhook_url}")
        
        try:
            # Test webhook with a ping request
            test_payload = {
                "action": "test_connection",
                "timestamp": str(self._get_current_timestamp()),
                "source": "100xai"
            }
            
            response = self._send_webhook(test_payload)
            
            # Accept various success status codes
            if response.status_code in [200, 201, 202, 204]:
                self.logger.info(f"Webhook connection validated: {self.webhook_url}")
                return True
            elif response.status_code == 401:
                raise AuthenticationError("Webhook authentication failed")
            elif response.status_code == 403:
                raise AuthenticationError("Webhook access forbidden")
            elif response.status_code == 404:
                raise AuthenticationError(f"Webhook URL not found: {self.webhook_url}")
            else:
                # Some webhooks might return different codes for test requests
                self.logger.warning(f"Webhook test returned {response.status_code}, but continuing")
                return True
                
        except requests.exceptions.Timeout:
            raise AuthenticationError(f"Webhook connection timeout to {self.webhook_url}")
        except requests.exceptions.ConnectionError:
            raise AuthenticationError(f"Cannot connect to webhook: {self.webhook_url}")
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Webhook connection error: {str(e)}")
    
    def publish(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Publish content via webhook."""
        try:
            # Prepare webhook payload
            payload = {
                "action": "publish",
                "timestamp": str(self._get_current_timestamp()),
                "content": {
                    "title": content.get("title", "Untitled"),
                    "content": content.get("content", ""),
                    "excerpt": content.get("excerpt", ""),
                    "slug": content.get("slug", ""),
                    "tags": content.get("tags", []),
                    "categories": content.get("categories", []),
                    "featured_image_url": content.get("featured_image_url", ""),
                    "meta_description": content.get("meta_description", ""),
                    "status": "publish"
                }
            }
            
            response = self._send_webhook(payload)
            
            if response.status_code == 429:
                raise RateLimitError("Webhook rate limit exceeded")
            elif response.status_code == 400:
                raise ContentValidationError(f"Webhook rejected content: {response.text}")
            elif response.status_code == 401:
                raise AuthenticationError("Webhook authentication failed")
            elif response.status_code == 403:
                raise AuthenticationError("Webhook permission denied")
            elif response.status_code not in [200, 201, 202]:
                raise PublishingError(f"Webhook publishing failed: {response.status_code} - {response.text}")
            
            # Parse response
            try:
                result = response.json()
            except json.JSONDecodeError:
                # If response is not JSON, create a default result
                result = {
                    "status": "success",
                    "message": response.text
                }
            
            return {
                "url": result.get("url", result.get("published_url", "")),
                "external_id": result.get("id", result.get("external_id", "")),
                "status": result.get("status", "published"),
                "webhook_response": result
            }
            
        except (AuthenticationError, ContentValidationError, RateLimitError):
            raise
        except requests.exceptions.Timeout:
            raise PublishingError(f"Webhook request timeout")
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"Webhook request error: {str(e)}")
        except Exception as e:
            raise PublishingError(f"Unexpected webhook publishing error: {str(e)}")
    
    def update(self, external_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Update content via webhook."""
        try:
            payload = {
                "action": "update",
                "timestamp": str(self._get_current_timestamp()),
                "external_id": external_id,
                "content": {
                    "title": content.get("title"),
                    "content": content.get("content"),
                    "excerpt": content.get("excerpt"),
                    "slug": content.get("slug"),
                    "tags": content.get("tags"),
                    "categories": content.get("categories"),
                    "featured_image_url": content.get("featured_image_url"),
                    "meta_description": content.get("meta_description")
                }
            }
            
            # Remove None values
            payload["content"] = {k: v for k, v in payload["content"].items() if v is not None}
            
            response = self._send_webhook(payload)
            
            if response.status_code == 404:
                raise PublishingError(f"Content not found for update: {external_id}")
            elif response.status_code == 401:
                raise AuthenticationError("Webhook authentication failed")
            elif response.status_code == 403:
                raise AuthenticationError("Webhook permission denied")
            elif response.status_code not in [200, 201, 202]:
                raise PublishingError(f"Webhook update failed: {response.status_code} - {response.text}")
            
            try:
                result = response.json()
            except json.JSONDecodeError:
                result = {"status": "success", "message": response.text}
            
            return {
                "url": result.get("url", ""),
                "external_id": result.get("id", external_id),
                "status": result.get("status", "updated")
            }
            
        except (AuthenticationError, PublishingError):
            raise
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"Webhook update error: {str(e)}")
    
    def delete(self, external_id: str) -> bool:
        """Delete content via webhook."""
        try:
            payload = {
                "action": "delete",
                "timestamp": str(self._get_current_timestamp()),
                "external_id": external_id
            }
            
            response = self._send_webhook(payload)
            
            if response.status_code == 404:
                self.logger.warning(f"Content {external_id} not found for deletion")
                return True  # Already deleted
            elif response.status_code == 401:
                raise AuthenticationError("Webhook authentication failed")
            elif response.status_code == 403:
                raise AuthenticationError("Webhook permission denied")
            elif response.status_code not in [200, 201, 202, 204]:
                raise PublishingError(f"Webhook deletion failed: {response.status_code} - {response.text}")
            
            return True
            
        except (AuthenticationError, PublishingError):
            raise
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"Webhook deletion error: {str(e)}")
    
    def _send_webhook(self, payload: Dict[str, Any]) -> requests.Response:
        """Send webhook request with optional HMAC signing."""
        # Convert payload to JSON
        json_payload = json.dumps(payload, separators=(',', ':'))
        
        # Add HMAC signature if secret is provided
        headers = {}
        if self.secret:
            signature = self._generate_signature(json_payload, self.secret)
            headers['X-Hub-Signature-256'] = f'sha256={signature}'
        
        # Send request
        if self.method == "POST":
            return self.session.post(
                self.webhook_url,
                data=json_payload,
                headers=headers
            )
        elif self.method == "PUT":
            return self.session.put(
                self.webhook_url,
                data=json_payload,
                headers=headers
            )
        else:
            raise PublishingError(f"Unsupported HTTP method: {self.method}")
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC SHA256 signature for webhook security."""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _get_current_timestamp(self) -> int:
        """Get current Unix timestamp."""
        import time
        return int(time.time())