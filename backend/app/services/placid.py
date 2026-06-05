# app/services/placid.py
import httpx
import logging
from typing import Optional

from app.config import get_settings
from app.models.onboarding import BrandProfile

logger = logging.getLogger(__name__)


class PlacidService:
    """Placid API service for branded template composition"""
    
    def __init__(self):
        self.api_key = get_settings().placid_api_key
        self.base_url = "https://api.placid.app/v1"
    
    async def composite_branded_template(
        self,
        template_id: str,
        generated_image_url: str,
        title: str,
        brand_profile: BrandProfile
    ) -> str:
        """API · Placid → Composite into branded template"""
        if not self.api_key:
            raise ValueError("Placid API key not configured")
        
        template_data = {
            "background_image": generated_image_url,
            "title_text": title,
            "brand_name": brand_profile.name,
            "brand_colors": brand_profile.image_palette or "#000000,#FFFFFF"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/templates/{template_id}/render",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=template_data,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                if "image_url" not in data:
                    raise ValueError(f"Unexpected Placid API response: {data}")
                
                logger.info(f"Placid template rendered: {template_id}")
                return data["image_url"]
            
            except httpx.HTTPStatusError as e:
                logger.error(f"Placid API error: {e.response.status_code} - {e.response.text}")
                raise ValueError(f"Placid API request failed: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Placid request error: {e}")
                raise
    
    async def render_template_simple(self, template_id: str, data: dict) -> str:
        """Simple template rendering with custom data"""
        if not self.api_key:
            raise ValueError("Placid API key not configured")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/templates/{template_id}/render",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=data,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                if "image_url" not in result:
                    raise ValueError(f"No image_url in Placid response: {result}")
                
                return result["image_url"]
            
            except httpx.HTTPStatusError as e:
                logger.error(f"Placid template rendering failed: {e.response.status_code} - {e.response.text}")
                raise ValueError(f"Placid template rendering failed: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Placid rendering error: {e}")
                raise