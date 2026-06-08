"""Ghost publishing adapter using Admin API."""

import requests
import jwt
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse

from .base import (
    BasePublisher, 
    PublishingError, 
    AuthenticationError, 
    ContentValidationError,
    RateLimitError
)


class GhostPublisher(BasePublisher):
    """Publisher for Ghost publications using Admin API."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Ghost publisher.
        
        Required config:
            - site_url: str - Ghost site URL
            - admin_api_key: str - Ghost Admin API key (JWT format)
        
        Optional config:
            - timeout: int - Request timeout (default: 30)
            - verify_ssl: bool - Verify SSL certificates (default: True)
            - default_status: str - Default post status (default: "published")
            - author_email: str - Author email for posts
        """
        super().__init__(config)
        
        # Required fields
        self.site_url = config.get("site_url", "").rstrip("/")
        self.admin_api_key = config.get("admin_api_key", "")
        
        # Optional fields
        self.timeout = config.get("timeout", 30)
        self.verify_ssl = config.get("verify_ssl", True)
        self.default_status = config.get("default_status", "published")
        self.author_email = config.get("author_email", "")
        
        # Build API URL
        if self.site_url:
            self.api_url = f"{self.site_url}/ghost/api/admin"
        else:
            self.api_url = ""
        
        # Create session for reuse
        self.session = requests.Session()
        self.session.timeout = self.timeout
        self.session.verify = self.verify_ssl
        
        # Set up authentication
        if self.admin_api_key:
            try:
                # Parse the key to get key ID and secret
                key_parts = self.admin_api_key.split(':')
                if len(key_parts) == 2:
                    self.key_id = key_parts[0]
                    self.key_secret = bytes.fromhex(key_parts[1])
                    self.session.headers.update({
                        'Content-Type': 'application/json'
                    })
                else:
                    raise ValueError("Invalid Ghost Admin API key format")
            except Exception as e:
                self.logger.error(f"Failed to parse Ghost API key: {e}")
                self.key_id = None
                self.key_secret = None
        else:
            self.key_id = None
            self.key_secret = None
    
    def validate_config(self) -> bool:
        """Validate Ghost configuration and test connection."""
        # Check required fields
        if not all([self.site_url, self.admin_api_key, self.key_id, self.key_secret]):
            raise AuthenticationError("Missing required Ghost config: site_url, admin_api_key, or invalid key format")
        
        # Validate URL format
        parsed = urlparse(self.site_url)
        if not parsed.scheme or not parsed.netloc:
            raise AuthenticationError(f"Invalid Ghost site URL: {self.site_url}")
        
        try:
            # Test authentication by fetching site info
            token = self._generate_jwt_token()
            headers = {'Authorization': f'Ghost {token}'}
            
            response = self.session.get(f"{self.api_url}/site/", headers=headers)
            
            if response.status_code == 401:
                raise AuthenticationError("Ghost authentication failed - check Admin API key")
            elif response.status_code == 403:
                raise AuthenticationError("Ghost access forbidden - check API key permissions")
            elif response.status_code == 404:
                raise AuthenticationError(f"Ghost Admin API not found at {self.site_url}")
            elif response.status_code != 200:
                raise AuthenticationError(f"Ghost API error: {response.status_code} - {response.text}")
            
            site_data = response.json()
            self.logger.info(f"Ghost connection validated for site: {site_data['site']['title']}")
            return True
            
        except jwt.PyJWTError as e:
            raise AuthenticationError(f"Ghost JWT token error: {str(e)}")
        except requests.exceptions.Timeout:
            raise AuthenticationError(f"Ghost connection timeout to {self.site_url}")
        except requests.exceptions.ConnectionError:
            raise AuthenticationError(f"Cannot connect to Ghost site: {self.site_url}")
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Ghost connection error: {str(e)}")
    
    def publish(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Publish content to Ghost."""
        try:
            # Prepare Ghost post data
            post_data = {
                "posts": [{
                    "title": content.get("title", "Untitled"),
                    "html": content.get("content", ""),
                    "status": self.default_status,
                    "excerpt": content.get("excerpt", ""),
                    "meta_description": content.get("meta_description", ""),
                    "published_at": datetime.now(timezone.utc).isoformat() if self.default_status == "published" else None
                }]
            }
            
            # Add slug if provided
            if content.get("slug"):
                post_data["posts"][0]["slug"] = content["slug"]
            
            # Handle tags
            tags = content.get("tags", [])
            if tags:
                post_data["posts"][0]["tags"] = [{"name": tag} for tag in tags]
            
            # Handle featured image
            featured_image_url = content.get("featured_image_url")
            if featured_image_url:
                post_data["posts"][0]["feature_image"] = featured_image_url
            
            # Set author if configured
            if self.author_email:
                # Note: In practice, you'd need to resolve the author by email
                # For now, we'll let Ghost use the default author
                pass
            
            # Generate JWT token
            token = self._generate_jwt_token()
            headers = {'Authorization': f'Ghost {token}'}
            
            # Create the post
            response = self.session.post(f"{self.api_url}/posts/", json=post_data, headers=headers)
            
            if response.status_code == 429:
                raise RateLimitError("Ghost rate limit exceeded")
            elif response.status_code == 422:
                raise ContentValidationError(f"Ghost rejected content: {response.text}")
            elif response.status_code == 403:
                raise AuthenticationError("Ghost permission denied - check API key scopes")
            elif response.status_code != 201:
                raise PublishingError(f"Ghost publishing failed: {response.status_code} - {response.text}")
            
            result = response.json()
            post = result.get("posts", [{}])[0]
            
            return {
                "url": post.get("url", ""),
                "external_id": post.get("id", ""),
                "status": post.get("status", ""),
                "admin_url": f"{self.site_url}/ghost/#/editor/post/{post.get('id')}"
            }
            
        except (AuthenticationError, ContentValidationError, RateLimitError):
            raise
        except jwt.PyJWTError as e:
            raise PublishingError(f"Ghost JWT error: {str(e)}")
        except requests.exceptions.Timeout:
            raise PublishingError(f"Ghost request timeout")
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"Ghost request error: {str(e)}")
        except Exception as e:
            raise PublishingError(f"Unexpected Ghost publishing error: {str(e)}")
    
    def update(self, external_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing Ghost post."""
        try:
            # First, fetch the existing post to get updated_at timestamp (required for updates)
            token = self._generate_jwt_token()
            headers = {'Authorization': f'Ghost {token}'}
            
            fetch_response = self.session.get(f"{self.api_url}/posts/{external_id}/", headers=headers)
            if fetch_response.status_code != 200:
                raise PublishingError(f"Ghost post not found: {external_id}")
            
            existing_post = fetch_response.json()["posts"][0]
            
            # Prepare update data
            post_data = {
                "posts": [{
                    "id": external_id,
                    "updated_at": existing_post["updated_at"]  # Required for updates
                }]
            }
            
            # Add fields that are being updated
            if content.get("title"):
                post_data["posts"][0]["title"] = content["title"]
            if content.get("content"):
                post_data["posts"][0]["html"] = content["content"]
            if content.get("excerpt"):
                post_data["posts"][0]["excerpt"] = content["excerpt"]
            if content.get("meta_description"):
                post_data["posts"][0]["meta_description"] = content["meta_description"]
            if content.get("slug"):
                post_data["posts"][0]["slug"] = content["slug"]
            if content.get("tags"):
                post_data["posts"][0]["tags"] = [{"name": tag} for tag in content["tags"]]
            if content.get("featured_image_url"):
                post_data["posts"][0]["feature_image"] = content["featured_image_url"]
            
            # Update the post
            response = self.session.put(f"{self.api_url}/posts/{external_id}/", json=post_data, headers=headers)
            
            if response.status_code == 404:
                raise PublishingError(f"Ghost post not found: {external_id}")
            elif response.status_code == 403:
                raise AuthenticationError("Ghost permission denied for update")
            elif response.status_code != 200:
                raise PublishingError(f"Ghost update failed: {response.status_code} - {response.text}")
            
            result = response.json()
            post = result.get("posts", [{}])[0]
            
            return {
                "url": post.get("url", ""),
                "external_id": post.get("id", ""),
                "status": post.get("status", "")
            }
            
        except (AuthenticationError, PublishingError):
            raise
        except jwt.PyJWTError as e:
            raise PublishingError(f"Ghost JWT error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"Ghost update error: {str(e)}")
    
    def delete(self, external_id: str) -> bool:
        """Delete Ghost post."""
        try:
            token = self._generate_jwt_token()
            headers = {'Authorization': f'Ghost {token}'}
            
            response = self.session.delete(f"{self.api_url}/posts/{external_id}/", headers=headers)
            
            if response.status_code == 404:
                self.logger.warning(f"Ghost post {external_id} not found for deletion")
                return True  # Already deleted
            elif response.status_code == 403:
                raise AuthenticationError("Ghost permission denied for deletion")
            elif response.status_code != 204:
                raise PublishingError(f"Ghost deletion failed: {response.status_code} - {response.text}")
            
            return True
            
        except (AuthenticationError, PublishingError):
            raise
        except jwt.PyJWTError as e:
            raise PublishingError(f"Ghost JWT error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"Ghost deletion error: {str(e)}")
    
    def _generate_jwt_token(self) -> str:
        """Generate JWT token for Ghost Admin API authentication."""
        if not self.key_id or not self.key_secret:
            raise AuthenticationError("Ghost API key not properly configured")
        
        # Create JWT payload
        iat = int(datetime.now(timezone.utc).timestamp())
        header = {'typ': 'JWT', 'alg': 'HS256', 'kid': self.key_id}
        payload = {
            'iat': iat,
            'exp': iat + 5 * 60,  # Token expires in 5 minutes
            'aud': '/admin/'
        }
        
        # Generate token
        token = jwt.encode(payload, self.key_secret, algorithm='HS256', headers=header)
        return token