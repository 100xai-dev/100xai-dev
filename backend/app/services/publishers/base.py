"""Base publisher interface and factory for multi-channel publishing."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PublishingError(Exception):
    """Base exception for publishing errors."""
    pass


class AuthenticationError(PublishingError):
    """Authentication failed with the publishing platform."""
    pass


class ContentValidationError(PublishingError):
    """Content failed platform validation."""
    pass


class RateLimitError(PublishingError):
    """Rate limit exceeded for the publishing platform."""
    pass


class BasePublisher(ABC):
    """Abstract base class for content publishers."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize publisher with configuration.
        
        Args:
            config: Publisher-specific configuration dict
        """
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate the publisher configuration.
        
        Returns:
            bool: True if config is valid
            
        Raises:
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    def publish(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publish content to the platform.
        
        Args:
            content: Content dict with fields:
                - title: str
                - content: str (HTML)
                - excerpt: str (optional)
                - tags: List[str] (optional)
                - categories: List[str] (optional)
                - slug: str (optional)
                - featured_image_url: str (optional)
                - meta_description: str (optional)
        
        Returns:
            Dict with result:
                - url: str - Published content URL
                - external_id: str - Platform-specific ID
                - status: str - Publication status
        
        Raises:
            PublishingError: If publishing fails
        """
        pass
    
    @abstractmethod
    def update(self, external_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update existing published content.
        
        Args:
            external_id: Platform-specific content ID
            content: Updated content dict
        
        Returns:
            Dict with update result
        
        Raises:
            PublishingError: If update fails
        """
        pass
    
    @abstractmethod
    def delete(self, external_id: str) -> bool:
        """
        Delete published content.
        
        Args:
            external_id: Platform-specific content ID
        
        Returns:
            bool: True if deletion succeeded
        
        Raises:
            PublishingError: If deletion fails
        """
        pass
    
    def test_connection(self) -> bool:
        """
        Test connection to the publishing platform.
        
        Returns:
            bool: True if connection is successful
        """
        try:
            return self.validate_config()
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False


class PublisherFactory:
    """Factory for creating publisher instances."""
    
    _publishers = {}
    
    @classmethod
    def register_publisher(cls, channel: str, publisher_class: type):
        """Register a publisher class for a channel."""
        cls._publishers[channel] = publisher_class
    
    @classmethod
    def get_publisher(cls, channel: str, config: Dict[str, Any]) -> BasePublisher:
        """
        Get a publisher instance for the specified channel.
        
        Args:
            channel: Channel name (e.g., 'wordpress', 'webhook')
            config: Publisher configuration
        
        Returns:
            BasePublisher instance
        
        Raises:
            ValueError: If channel is not supported
        """
        if channel not in cls._publishers:
            raise ValueError(f"Unsupported publishing channel: {channel}")
        
        publisher_class = cls._publishers[channel]
        return publisher_class(config)
    
    @classmethod
    def get_supported_channels(cls) -> list[str]:
        """Get list of supported publishing channels."""
        return list(cls._publishers.keys())


# Auto-register publishers when this module is imported
def _register_builtin_publishers():
    """Register built-in publishers."""
    try:
        from .wordpress import WordPressPublisher
        PublisherFactory.register_publisher("wordpress", WordPressPublisher)
    except ImportError:
        logger.warning("WordPress publisher not available")
    
    try:
        from .webhook import WebhookPublisher
        PublisherFactory.register_publisher("webhook", WebhookPublisher)
    except ImportError:
        logger.warning("Webhook publisher not available")
    
    try:
        from .shopify import ShopifyPublisher
        PublisherFactory.register_publisher("shopify", ShopifyPublisher)
    except ImportError:
        logger.warning("Shopify publisher not available")
    
    try:
        from .ghost import GhostPublisher
        PublisherFactory.register_publisher("ghost", GhostPublisher)
    except ImportError:
        logger.warning("Ghost publisher not available")


# Register publishers on module import
_register_builtin_publishers()