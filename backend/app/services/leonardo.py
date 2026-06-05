# app/services/leonardo.py
import asyncio
import httpx
import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class LeonardoService:
    """Leonardo AI image generation service"""
    
    def __init__(self):
        self.api_key = get_settings().leonardo_api_key
        self.base_url = "https://cloud.leonardo.ai/api/rest/v1"
    
    async def request_generation(self, prompt: str, style_preset: str = "LEONARDO") -> str:
        """API · Leonardo → Request generation"""
        if not self.api_key:
            raise ValueError("Leonardo API key not configured")
        
        payload = {
            "prompt": prompt,
            "num_images": 1,
            "modelId": "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3",  # Leonardo Creative
            "width": 1024,
            "height": 576,  # 16:9 aspect ratio
            "presetStyle": style_preset
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/generations",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                if "sdGenerationJob" not in data or "generationId" not in data["sdGenerationJob"]:
                    raise ValueError(f"Unexpected Leonardo API response: {data}")
                
                return data["sdGenerationJob"]["generationId"]
            
            except httpx.HTTPStatusError as e:
                logger.error(f"Leonardo API error: {e.response.status_code} - {e.response.text}")
                raise ValueError(f"Leonardo API request failed: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Leonardo request error: {e}")
                raise
    
    async def poll_until_ready(self, generation_id: str, max_attempts: int = 30) -> str:
        """Poll until ready → extract URL"""
        if not self.api_key:
            raise ValueError("Leonardo API key not configured")
        
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/generations/{generation_id}",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=10.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if "generations_by_pk" not in data:
                        logger.warning(f"Unexpected response structure: {data}")
                        await asyncio.sleep(10)
                        continue
                    
                    generation_data = data["generations_by_pk"]
                    status = generation_data.get("status")
                    
                    if status == "COMPLETE":
                        images = generation_data.get("generated_images", [])
                        if images and len(images) > 0:
                            image_url = images[0].get("url")
                            if image_url:
                                logger.info(f"Leonardo generation completed: {generation_id}")
                                return image_url
                            else:
                                logger.warning(f"No URL in completed generation: {images[0]}")
                        else:
                            logger.warning(f"No images in completed generation: {generation_data}")
                    
                    elif status == "FAILED":
                        raise ValueError(f"Leonardo generation failed: {generation_data}")
                    
                    # Status is PENDING or IN_PROGRESS
                    logger.info(f"Leonardo generation {generation_id} status: {status} (attempt {attempt + 1})")
                    await asyncio.sleep(10)  # Wait 10 seconds between polls
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"Leonardo polling error: {e.response.status_code} - {e.response.text}")
                if attempt == max_attempts - 1:
                    raise ValueError(f"Leonardo polling failed: {e.response.status_code}")
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Leonardo polling error: {e}")
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(10)
        
        raise TimeoutError(f"Image generation timed out after {max_attempts * 10} seconds")
    
    async def generate_image(self, prompt: str, style_preset: str = "LEONARDO") -> str:
        """Complete image generation workflow"""
        logger.info(f"Starting Leonardo image generation: {prompt[:100]}...")
        
        # Request generation
        generation_id = await self.request_generation(prompt, style_preset)
        logger.info(f"Leonardo generation requested: {generation_id}")
        
        # Poll until ready
        image_url = await self.poll_until_ready(generation_id)
        logger.info(f"Leonardo image ready: {image_url}")
        
        return image_url