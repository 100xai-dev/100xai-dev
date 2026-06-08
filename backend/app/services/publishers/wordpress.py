"""WordPress publishing adapter using REST API."""

import requests
import base64
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse

from .base import (
    BasePublisher, 
    PublishingError, 
    AuthenticationError, 
    ContentValidationError,
    RateLimitError
)


class WordPressPublisher(BasePublisher):
    """Publisher for WordPress sites using REST API."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize WordPress publisher.
        
        Required config:
            - site_url: str - WordPress site URL
            - username: str - WordPress username
            - password: str - WordPress application password
        
        Optional config:
            - timeout: int - Request timeout (default: 30)
            - verify_ssl: bool - Verify SSL certificates (default: True)
            - default_status: str - Default post status (default: "publish")
        """
        super().__init__(config)
        
        # Required fields
        self.site_url = config.get("site_url", "").rstrip("/")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        
        # Optional fields
        self.timeout = config.get("timeout", 30)
        self.verify_ssl = config.get("verify_ssl", True)
        self.default_status = config.get("default_status", "publish")
        
        # Build API URL
        if self.site_url:
            self.api_url = f"{self.site_url}/wp-json/wp/v2"
        else:
            self.api_url = ""
        
        # Create session for reuse
        self.session = requests.Session()
        self.session.timeout = self.timeout
        self.session.verify = self.verify_ssl
        
        # Set up authentication
        if self.username and self.password:
            auth_string = f"{self.username}:{self.password}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            self.session.headers.update({
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/json'
            })
    
    def validate_config(self) -> bool:
        """Validate WordPress configuration and test connection."""
        # Check required fields
        if not all([self.site_url, self.username, self.password]):
            raise AuthenticationError("Missing required WordPress config: site_url, username, or password")
        
        # Validate URL format
        parsed = urlparse(self.site_url)
        if not parsed.scheme or not parsed.netloc:
            raise AuthenticationError(f"Invalid WordPress site URL: {self.site_url}")
        
        try:
            # Test authentication by fetching current user
            response = self.session.get(f"{self.api_url}/users/me")
            
            if response.status_code == 401:
                raise AuthenticationError("WordPress authentication failed - check username and password")
            elif response.status_code == 403:
                raise AuthenticationError("WordPress access forbidden - check user permissions")
            elif response.status_code == 404:
                raise AuthenticationError(f"WordPress REST API not found at {self.site_url}")
            elif response.status_code != 200:
                raise AuthenticationError(f"WordPress API error: {response.status_code} - {response.text}")
            
            user_data = response.json()
            self.logger.info(f"WordPress connection validated for user: {user_data.get('name', 'Unknown')}")
            return True
            
        except requests.exceptions.Timeout:
            raise AuthenticationError(f"WordPress connection timeout to {self.site_url}")
        except requests.exceptions.ConnectionError:
            raise AuthenticationError(f"Cannot connect to WordPress site: {self.site_url}")
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"WordPress connection error: {str(e)}")
    
    def publish(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Publish content to WordPress."""
        try:
            # Prepare WordPress post data
            post_data = {
                "title": content.get("title", "Untitled"),
                "content": content.get("content", ""),
                "status": self.default_status,
                "excerpt": content.get("excerpt", ""),
                "meta": {
                    "description": content.get("meta_description", "")
                }
            }
            
            # Add slug if provided
            if content.get("slug"):
                post_data["slug"] = content["slug"]
            
            # Handle categories
            categories = content.get("categories", [])
            if categories:
                category_ids = self._get_or_create_categories(categories)
                if category_ids:
                    post_data["categories"] = category_ids
            
            # Handle tags
            tags = content.get("tags", [])
            if tags:
                tag_ids = self._get_or_create_tags(tags)
                if tag_ids:
                    post_data["tags"] = tag_ids
            
            # Handle featured image
            featured_image_url = content.get("featured_image_url")
            if featured_image_url:
                try:
                    media_id = self._upload_featured_image(featured_image_url)
                    if media_id:
                        post_data["featured_media"] = media_id
                except Exception as e:
                    self.logger.warning(f"Failed to upload featured image: {e}")
                    # Continue without featured image
            
            # Create the post
            response = self.session.post(f"{self.api_url}/posts", json=post_data)
            
            if response.status_code == 429:
                raise RateLimitError("WordPress rate limit exceeded")
            elif response.status_code == 400:
                raise ContentValidationError(f"WordPress rejected content: {response.text}")
            elif response.status_code == 403:
                raise AuthenticationError("WordPress permission denied - check user capabilities")
            elif response.status_code != 201:
                raise PublishingError(f"WordPress publishing failed: {response.status_code} - {response.text}")
            
            result = response.json()
            
            return {
                "url": result.get("link", ""),
                "external_id": str(result.get("id", "")),
                "status": result.get("status", ""),
                "edit_url": f"{self.site_url}/wp-admin/post.php?post={result.get('id')}&action=edit"
            }
            
        except (AuthenticationError, ContentValidationError, RateLimitError):
            raise
        except requests.exceptions.Timeout:
            raise PublishingError(f"WordPress request timeout")
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"WordPress request error: {str(e)}")
        except Exception as e:
            raise PublishingError(f"Unexpected WordPress publishing error: {str(e)}")
    
    def update(self, external_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing WordPress post."""
        try:
            # Prepare update data (same as publish but for existing post)
            post_data = {
                "title": content.get("title"),
                "content": content.get("content"),
                "excerpt": content.get("excerpt"),
                "meta": {
                    "description": content.get("meta_description", "")
                }
            }
            
            # Remove None values
            post_data = {k: v for k, v in post_data.items() if v is not None}
            
            # Add slug if provided
            if content.get("slug"):
                post_data["slug"] = content["slug"]
            
            # Update the post
            response = self.session.post(f"{self.api_url}/posts/{external_id}", json=post_data)
            
            if response.status_code == 404:
                raise PublishingError(f"WordPress post not found: {external_id}")
            elif response.status_code == 403:
                raise AuthenticationError("WordPress permission denied for update")
            elif response.status_code != 200:
                raise PublishingError(f"WordPress update failed: {response.status_code} - {response.text}")
            
            result = response.json()
            
            return {
                "url": result.get("link", ""),
                "external_id": str(result.get("id", "")),
                "status": result.get("status", "")
            }
            
        except (AuthenticationError, PublishingError):
            raise
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"WordPress update error: {str(e)}")
    
    def delete(self, external_id: str) -> bool:
        """Delete WordPress post."""
        try:
            response = self.session.delete(f"{self.api_url}/posts/{external_id}")
            
            if response.status_code == 404:
                self.logger.warning(f"WordPress post {external_id} not found for deletion")
                return True  # Already deleted
            elif response.status_code == 403:
                raise AuthenticationError("WordPress permission denied for deletion")
            elif response.status_code != 200:
                raise PublishingError(f"WordPress deletion failed: {response.status_code} - {response.text}")
            
            return True
            
        except (AuthenticationError, PublishingError):
            raise
        except requests.exceptions.RequestException as e:
            raise PublishingError(f"WordPress deletion error: {str(e)}")
    
    def _get_or_create_categories(self, category_names: list[str]) -> list[int]:
        """Get or create WordPress categories and return their IDs."""
        category_ids = []
        
        try:
            for name in category_names:
                # First try to find existing category
                response = self.session.get(f"{self.api_url}/categories", params={"search": name})
                
                if response.status_code == 200:
                    categories = response.json()
                    existing = next((cat for cat in categories if cat["name"].lower() == name.lower()), None)
                    
                    if existing:
                        category_ids.append(existing["id"])
                    else:
                        # Create new category
                        create_response = self.session.post(f"{self.api_url}/categories", json={"name": name})
                        if create_response.status_code == 201:
                            new_category = create_response.json()
                            category_ids.append(new_category["id"])
                        else:
                            self.logger.warning(f"Failed to create category '{name}': {create_response.text}")
                else:
                    self.logger.warning(f"Failed to search categories: {response.text}")
            
            return category_ids
            
        except Exception as e:
            self.logger.warning(f"Error handling categories: {e}")
            return []
    
    def _get_or_create_tags(self, tag_names: list[str]) -> list[int]:
        """Get or create WordPress tags and return their IDs."""
        tag_ids = []
        
        try:
            for name in tag_names:
                # First try to find existing tag
                response = self.session.get(f"{self.api_url}/tags", params={"search": name})
                
                if response.status_code == 200:
                    tags = response.json()
                    existing = next((tag for tag in tags if tag["name"].lower() == name.lower()), None)
                    
                    if existing:
                        tag_ids.append(existing["id"])
                    else:
                        # Create new tag
                        create_response = self.session.post(f"{self.api_url}/tags", json={"name": name})
                        if create_response.status_code == 201:
                            new_tag = create_response.json()
                            tag_ids.append(new_tag["id"])
                        else:
                            self.logger.warning(f"Failed to create tag '{name}': {create_response.text}")
                else:
                    self.logger.warning(f"Failed to search tags: {response.text}")
            
            return tag_ids
            
        except Exception as e:
            self.logger.warning(f"Error handling tags: {e}")
            return []
    
    def _upload_featured_image(self, image_url: str) -> Optional[int]:
        """Upload featured image to WordPress media library."""
        try:
            # Download the image
            img_response = requests.get(image_url, timeout=30)
            if img_response.status_code != 200:
                raise PublishingError(f"Failed to download image: {img_response.status_code}")
            
            # Prepare file data for upload
            filename = image_url.split("/")[-1] or "featured-image.jpg"
            content_type = img_response.headers.get("content-type", "image/jpeg")
            
            # Upload to WordPress
            files = {
                'file': (filename, img_response.content, content_type)
            }
            
            # WordPress media upload requires different headers
            upload_session = requests.Session()
            upload_session.timeout = self.timeout
            upload_session.verify = self.verify_ssl
            upload_session.headers.update({
                'Authorization': self.session.headers['Authorization']
            })
            
            response = upload_session.post(f"{self.api_url}/media", files=files)
            
            if response.status_code == 201:
                media_data = response.json()
                return media_data.get("id")
            else:
                self.logger.warning(f"Failed to upload image to WordPress: {response.text}")
                return None
                
        except Exception as e:
            self.logger.warning(f"Error uploading featured image: {e}")
            return None