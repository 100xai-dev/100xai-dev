"""Webflow publishing adapter using CMS API."""

import requests
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse
import time

from .base import (
    BasePublisher, 
    PublishingError, 
    AuthenticationError, 
    ContentValidationError,
    RateLimitError
)


class WebflowPublisher(BasePublisher):
    """Publisher for Webflow CMS using CMS API."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Webflow publisher.
        
        Required config:
            - site_id: str - Webflow site ID
            - collection_id: str - CMS collection ID for blog posts
            - api_token: str - Webflow API token
        
        Optional config:
            - timeout: int - Request timeout (default: 30)
            - verify_ssl: bool - Verify SSL certificates (default: True)
            - default_status: str - Default publishing status ("published" or "draft", default: "published")
            - auto_publish: bool - Auto-publish items after creation (default: True)
            - featured_image_field: str - Field name for featured images (default: "featured-image")
            - excerpt_field: str - Field name for excerpts (default: "excerpt")
        """
        super().__init__(config)
        
        # Required fields
        self.site_id = config.get("site_id", "").strip()
        self.collection_id = config.get("collection_id", "").strip()
        self.api_token = config.get("api_token", "")
        
        # Optional fields
        self.timeout = config.get("timeout", 30)
        self.verify_ssl = config.get("verify_ssl", True)
        self.default_status = config.get("default_status", "published")
        self.auto_publish = config.get("auto_publish", True)
        self.featured_image_field = config.get("featured_image_field", "featured-image")
        self.excerpt_field = config.get("excerpt_field", "excerpt")
        
        # Webflow API configuration
        self.api_base = "https://api.webflow.com/v2"
        self.rate_limit_remaining = 120  # Default rate limit
        self.rate_limit_reset = None
        
        # Create session for reuse
        self.session = requests.Session()
        self.session.timeout = self.timeout
        self.session.verify = self.verify_ssl
        
        # Set up authentication
        if self.api_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Accept-Version': '1.0.0'
            })
    
    def validate_config(self) -> bool:
        """Validate Webflow configuration and test connection."""
        # Check required fields
        if not all([self.site_id, self.collection_id, self.api_token]):
            raise AuthenticationError("Missing required Webflow config: site_id, collection_id, or api_token")
        
        try:
            # Test authentication by fetching site info
            response = self._make_request('GET', f"/sites/{self.site_id}")
            site_data = response.json()
            self.logger.info(f"Webflow connection validated for site: {site_data['displayName']}")
            
            # Verify collection exists and get its schema
            collection_response = self._make_request('GET', f"/collections/{self.collection_id}")
            collection_data = collection_response.json()
            self.logger.info(f"Webflow collection validated: {collection_data['displayName']}")
            
            # Store collection schema for field mapping
            self.collection_fields = {field['slug']: field for field in collection_data.get('fields', [])}
            
            return True
            
        except requests.exceptions.Timeout:
            raise AuthenticationError(f"Webflow connection timeout")
        except requests.exceptions.ConnectionError:
            raise AuthenticationError(f"Cannot connect to Webflow API")
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Webflow connection error: {str(e)}")
    
    def publish(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Publish content to Webflow CMS."""
        try:
            # Prepare Webflow item data
            item_data = self._prepare_webflow_item(content)
            
            # Create the item
            response = self._make_request('POST', f"/collections/{self.collection_id}/items", json=item_data)
            
            if response.status_code not in [200, 201]:
                raise PublishingError(f"Webflow item creation failed: {response.status_code} - {response.text}")
            
            result = response.json()
            item_id = result.get('id')
            
            if not item_id:
                raise PublishingError("Webflow item created but no ID returned")
            
            # Auto-publish if configured
            if self.auto_publish and self.default_status == "published":
                publish_response = self._publish_item(item_id)
                if not publish_response:
                    self.logger.warning(f"Webflow item {item_id} created but publishing failed")
            
            # Get the live site URL (approximated)
            site_url = self._get_site_url()
            slug = content.get("slug", "").strip("/")
            item_url = f"{site_url}/blog/{slug}" if slug else f"{site_url}/blog"
            
            return {
                "url": item_url,
                "external_id": item_id,
                "status": "published" if self.auto_publish else "draft",
                "admin_url": f"https://webflow.com/design/{self.site_id}/cms/collections/{self.collection_id}/items/{item_id}"
            }
            
        except (AuthenticationError, ContentValidationError, RateLimitError):
            raise
        except requests.exceptions.Timeout:
            raise PublishingError(f"Webflow request timeout")
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"Webflow request error: {str(e)}")
        except Exception as e:
            raise PublishingError(f"Unexpected Webflow publishing error: {str(e)}")
    
    def update(self, external_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing Webflow item."""
        try:
            # Prepare update data
            item_data = self._prepare_webflow_item(content, is_update=True)
            
            # Update the item
            response = self._make_request('PATCH', f"/collections/{self.collection_id}/items/{external_id}", json=item_data)
            
            if response.status_code == 404:
                raise PublishingError(f"Webflow item not found: {external_id}")
            elif response.status_code not in [200, 202]:
                raise PublishingError(f"Webflow update failed: {response.status_code} - {response.text}")
            
            # Re-publish if auto-publish is enabled
            if self.auto_publish:
                publish_response = self._publish_item(external_id)
                if not publish_response:
                    self.logger.warning(f"Webflow item {external_id} updated but republishing failed")
            
            # Get the live site URL
            site_url = self._get_site_url()
            slug = content.get("slug", "").strip("/")
            item_url = f"{site_url}/blog/{slug}" if slug else f"{site_url}/blog"
            
            return {
                "url": item_url,
                "external_id": external_id,
                "status": "published" if self.auto_publish else "draft"
            }
            
        except (AuthenticationError, PublishingError):
            raise
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"Webflow update error: {str(e)}")
    
    def delete(self, external_id: str) -> bool:
        """Delete Webflow item."""
        try:
            response = self._make_request('DELETE', f"/collections/{self.collection_id}/items/{external_id}")
            
            if response.status_code == 404:
                self.logger.warning(f"Webflow item {external_id} not found for deletion")
                return True  # Already deleted
            elif response.status_code not in [200, 204]:
                raise PublishingError(f"Webflow deletion failed: {response.status_code} - {response.text}")
            
            return True
            
        except (AuthenticationError, PublishingError):
            raise
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"Webflow deletion error: {str(e)}")
    
    def _prepare_webflow_item(self, content: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
        """Prepare content for Webflow CMS item format."""
        # Start with basic required fields
        item_data = {
            "isArchived": False,
            "isDraft": self.default_status != "published"
        }
        
        # Map standard fields to Webflow CMS fields
        field_mapping = {
            "name": content.get("title", "Untitled"),  # Standard name field
            "slug": self._sanitize_slug(content.get("slug", "")),
        }
        
        # Add post content - typically in a RichText field
        if content.get("content"):
            # Check if there's a specific content field in the collection
            if "post-body" in self.collection_fields:
                field_mapping["post-body"] = content["content"]
            elif "content" in self.collection_fields:
                field_mapping["content"] = content["content"]
            elif "body" in self.collection_fields:
                field_mapping["body"] = content["content"]
            else:
                # Default to first RichText field found
                richtext_fields = [f for f in self.collection_fields.values() if f.get('type') == 'RichText']
                if richtext_fields:
                    field_mapping[richtext_fields[0]['slug']] = content["content"]
        
        # Add excerpt/summary
        if content.get("excerpt") and self.excerpt_field in self.collection_fields:
            field_mapping[self.excerpt_field] = content["excerpt"]
        
        # Add meta description
        if content.get("meta_description"):
            if "meta-description" in self.collection_fields:
                field_mapping["meta-description"] = content["meta_description"]
            elif "seo-description" in self.collection_fields:
                field_mapping["seo-description"] = content["meta_description"]
        
        # Handle featured image
        if content.get("featured_image_url") and self.featured_image_field in self.collection_fields:
            # For Image fields, Webflow expects an object with url
            field_mapping[self.featured_image_field] = {
                "url": content["featured_image_url"]
            }
        
        # Handle tags
        if content.get("tags"):
            tags_text = ", ".join(content["tags"])
            if "tags" in self.collection_fields:
                field_mapping["tags"] = tags_text
            elif "categories" in self.collection_fields:
                field_mapping["categories"] = tags_text
        
        # Handle publication date
        if content.get("published_at"):
            if "published-date" in self.collection_fields:
                field_mapping["published-date"] = content["published_at"]
            elif "date" in self.collection_fields:
                field_mapping["date"] = content["published_at"]
        else:
            # Default to current time
            current_time = datetime.now(timezone.utc).isoformat()
            if "published-date" in self.collection_fields:
                field_mapping["published-date"] = current_time
            elif "date" in self.collection_fields:
                field_mapping["date"] = current_time
        
        # Add the field data to the item
        item_data["fieldData"] = field_mapping
        
        return item_data
    
    def _sanitize_slug(self, slug: str) -> str:
        """Sanitize slug for Webflow URL requirements."""
        if not slug:
            return ""
        
        # Remove leading/trailing slashes and spaces
        slug = slug.strip("/ ")
        
        # Replace spaces with hyphens, convert to lowercase
        slug = slug.replace(" ", "-").lower()
        
        # Remove any characters that aren't alphanumeric or hyphens
        import re
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        
        # Remove leading/trailing hyphens
        slug = slug.strip("-")
        
        return slug
    
    def _publish_item(self, item_id: str) -> bool:
        """Publish a specific item in Webflow."""
        try:
            publish_data = {
                "itemIds": [item_id]
            }
            
            response = self._make_request('POST', f"/collections/{self.collection_id}/items/publish", json=publish_data)
            
            if response.status_code in [200, 202]:
                self.logger.info(f"Webflow item {item_id} published successfully")
                return True
            else:
                self.logger.error(f"Webflow publishing failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error publishing Webflow item {item_id}: {e}")
            return False
    
    def _get_site_url(self) -> str:
        """Get the live site URL for the Webflow site."""
        try:
            response = self._make_request('GET', f"/sites/{self.site_id}")
            site_data = response.json()
            
            # Try to get the custom domain first, then fall back to Webflow subdomain
            return site_data.get('customDomain') or site_data.get('shortName', self.site_id) + '.webflow.io'
            
        except Exception:
            # Fallback to a reasonable default
            return f"{self.site_id}.webflow.io"
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a request to Webflow API with rate limiting and error handling."""
        # Check rate limits
        if self.rate_limit_remaining <= 1 and self.rate_limit_reset:
            wait_time = max(0, self.rate_limit_reset - time.time() + 1)
            if wait_time > 0:
                self.logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
        
        # Make the request
        url = f"{self.api_base}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        
        # Update rate limit tracking
        self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 120))
        if 'X-RateLimit-Reset' in response.headers:
            self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
        
        # Handle common errors
        if response.status_code == 429:
            raise RateLimitError("Webflow rate limit exceeded")
        elif response.status_code == 401:
            raise AuthenticationError("Webflow authentication failed - check API token")
        elif response.status_code == 403:
            raise AuthenticationError("Webflow access forbidden - check token permissions")
        elif response.status_code == 422:
            raise ContentValidationError(f"Webflow content validation failed: {response.text}")
        
        return response
    
    def get_collection_schema(self) -> Dict[str, Any]:
        """Get the collection schema for debugging and field mapping."""
        try:
            response = self._make_request('GET', f"/collections/{self.collection_id}")
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to get collection schema: {e}")
            return {}
    
    def list_items(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List items in the collection (for debugging)."""
        try:
            response = self._make_request('GET', f"/collections/{self.collection_id}/items", params={'limit': limit})
            return response.json().get('items', [])
        except Exception as e:
            self.logger.error(f"Failed to list collection items: {e}")
            return []