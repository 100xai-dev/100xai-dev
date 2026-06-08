"""Shopify publishing adapter using Admin API."""

import requests
import json
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse

from .base import (
    BasePublisher, 
    PublishingError, 
    AuthenticationError, 
    ContentValidationError,
    RateLimitError
)


class ShopifyPublisher(BasePublisher):
    """Publisher for Shopify blogs using Admin API."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Shopify publisher.
        
        Required config:
            - shop_name: str - Shopify shop name (e.g., "myshop" for myshop.myshopify.com)
            - access_token: str - Shopify Admin API access token
        
        Optional config:
            - blog_id: str - Specific blog ID (default: main blog)
            - timeout: int - Request timeout (default: 30)
            - verify_ssl: bool - Verify SSL certificates (default: True)
            - default_status: str - Default article status (default: "published")
        """
        super().__init__(config)
        
        # Required fields
        self.shop_name = config.get("shop_name", "").strip()
        self.access_token = config.get("access_token", "")
        
        # Optional fields
        self.blog_id = config.get("blog_id", "")
        self.timeout = config.get("timeout", 30)
        self.verify_ssl = config.get("verify_ssl", True)
        self.default_status = config.get("default_status", "published")
        
        # Build API URL
        if self.shop_name:
            if not self.shop_name.endswith('.myshopify.com'):
                self.shop_domain = f"{self.shop_name}.myshopify.com"
            else:
                self.shop_domain = self.shop_name
            self.api_url = f"https://{self.shop_domain}/admin/api/2023-10"
        else:
            self.api_url = ""
        
        # Create session for reuse
        self.session = requests.Session()
        self.session.timeout = self.timeout
        self.session.verify = self.verify_ssl
        
        # Set up authentication
        if self.access_token:
            self.session.headers.update({
                'X-Shopify-Access-Token': self.access_token,
                'Content-Type': 'application/json'
            })
    
    def validate_config(self) -> bool:
        """Validate Shopify configuration and test connection."""
        # Check required fields
        if not all([self.shop_name, self.access_token]):
            raise AuthenticationError("Missing required Shopify config: shop_name or access_token")
        
        try:
            # Test authentication by fetching shop info
            response = self.session.get(f"{self.api_url}/shop.json")
            
            if response.status_code == 401:
                raise AuthenticationError("Shopify authentication failed - check access token")
            elif response.status_code == 403:
                raise AuthenticationError("Shopify access forbidden - check token permissions")
            elif response.status_code == 404:
                raise AuthenticationError(f"Shopify shop not found: {self.shop_domain}")
            elif response.status_code != 200:
                raise AuthenticationError(f"Shopify API error: {response.status_code} - {response.text}")
            
            shop_data = response.json()
            self.logger.info(f"Shopify connection validated for shop: {shop_data['shop']['name']}")
            
            # If no blog_id specified, find the main blog
            if not self.blog_id:
                self.blog_id = self._get_main_blog_id()
                if not self.blog_id:
                    raise AuthenticationError("No blog found in Shopify store")
            
            return True
            
        except requests.exceptions.Timeout:
            raise AuthenticationError(f"Shopify connection timeout to {self.shop_domain}")
        except requests.exceptions.ConnectionError:
            raise AuthenticationError(f"Cannot connect to Shopify shop: {self.shop_domain}")
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Shopify connection error: {str(e)}")
    
    def publish(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Publish content to Shopify blog."""
        try:
            # Prepare Shopify article data
            article_data = {
                "article": {
                    "title": content.get("title", "Untitled"),
                    "content": content.get("content", ""),
                    "published": self.default_status == "published",
                    "summary": content.get("excerpt", ""),
                    "tags": ", ".join(content.get("tags", [])) if content.get("tags") else "",
                    "blog_id": self.blog_id
                }
            }
            
            # Add handle (slug) if provided
            if content.get("slug"):
                article_data["article"]["handle"] = content["slug"]
            
            # Handle featured image
            featured_image_url = content.get("featured_image_url")
            if featured_image_url:
                article_data["article"]["image"] = {
                    "src": featured_image_url
                }
            
            # Add author if configured
            author = self.config.get("author_name", "")
            if author:
                article_data["article"]["author"] = author
            
            # Create the article
            response = self.session.post(f"{self.api_url}/blogs/{self.blog_id}/articles.json", json=article_data)
            
            if response.status_code == 429:
                raise RateLimitError("Shopify rate limit exceeded")
            elif response.status_code == 422:
                raise ContentValidationError(f"Shopify rejected content: {response.text}")
            elif response.status_code == 403:
                raise AuthenticationError("Shopify permission denied - check token scopes")
            elif response.status_code != 201:
                raise PublishingError(f"Shopify publishing failed: {response.status_code} - {response.text}")
            
            result = response.json()
            article = result.get("article", {})
            
            return {
                "url": f"https://{self.shop_domain}/blogs/{self.blog_id}/{article.get('handle', '')}",
                "external_id": str(article.get("id", "")),
                "status": "published" if article.get("published_at") else "draft",
                "admin_url": f"https://{self.shop_domain}/admin/blogs/{self.blog_id}/articles/{article.get('id')}"
            }
            
        except (AuthenticationError, ContentValidationError, RateLimitError):
            raise
        except requests.exceptions.Timeout:
            raise PublishingError(f"Shopify request timeout")
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"Shopify request error: {str(e)}")
        except Exception as e:
            raise PublishingError(f"Unexpected Shopify publishing error: {str(e)}")
    
    def update(self, external_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing Shopify article."""
        try:
            # Prepare update data
            article_data = {
                "article": {
                    "id": int(external_id)
                }
            }
            
            # Add fields that are being updated
            if content.get("title"):
                article_data["article"]["title"] = content["title"]
            if content.get("content"):
                article_data["article"]["content"] = content["content"]
            if content.get("excerpt"):
                article_data["article"]["summary"] = content["excerpt"]
            if content.get("tags"):
                article_data["article"]["tags"] = ", ".join(content["tags"])
            if content.get("slug"):
                article_data["article"]["handle"] = content["slug"]
            
            # Update the article
            response = self.session.put(f"{self.api_url}/blogs/{self.blog_id}/articles/{external_id}.json", json=article_data)
            
            if response.status_code == 404:
                raise PublishingError(f"Shopify article not found: {external_id}")
            elif response.status_code == 403:
                raise AuthenticationError("Shopify permission denied for update")
            elif response.status_code != 200:
                raise PublishingError(f"Shopify update failed: {response.status_code} - {response.text}")
            
            result = response.json()
            article = result.get("article", {})
            
            return {
                "url": f"https://{self.shop_domain}/blogs/{self.blog_id}/{article.get('handle', '')}",
                "external_id": str(article.get("id", "")),
                "status": "published" if article.get("published_at") else "draft"
            }
            
        except (AuthenticationError, PublishingError):
            raise
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"Shopify update error: {str(e)}")
    
    def delete(self, external_id: str) -> bool:
        """Delete Shopify article."""
        try:
            response = self.session.delete(f"{self.api_url}/blogs/{self.blog_id}/articles/{external_id}.json")
            
            if response.status_code == 404:
                self.logger.warning(f"Shopify article {external_id} not found for deletion")
                return True  # Already deleted
            elif response.status_code == 403:
                raise AuthenticationError("Shopify permission denied for deletion")
            elif response.status_code != 200:
                raise PublishingError(f"Shopify deletion failed: {response.status_code} - {response.text}")
            
            return True
            
        except (AuthenticationError, PublishingError):
            raise
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"Shopify deletion error: {str(e)}")
    
    def _get_main_blog_id(self) -> Optional[str]:
        """Get the main blog ID for the Shopify store."""
        try:
            response = self.session.get(f"{self.api_url}/blogs.json")
            
            if response.status_code == 200:
                blogs = response.json().get("blogs", [])
                if blogs:
                    # Return the first blog (usually the main blog)
                    main_blog = blogs[0]
                    self.logger.info(f"Using Shopify blog: {main_blog.get('title', 'Main Blog')}")
                    return str(main_blog["id"])
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to get Shopify blog ID: {e}")
            return None