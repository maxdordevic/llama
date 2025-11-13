"""
Image Generation Agent
Supports multiple image generation providers: DALL-E, Stable Diffusion, Replicate
"""

import asyncio
import base64
import logging
import os
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import aiohttp

from ..core.llm_providers import LLMManager, LLMProvider

logger = logging.getLogger(__name__)


class ImageProvider(str, Enum):
    """Supported image generation providers"""
    DALLE_3 = "dalle-3"
    DALLE_2 = "dalle-2"
    STABLE_DIFFUSION_XL = "stable-diffusion-xl"
    STABLE_DIFFUSION_2 = "stable-diffusion-2"
    MIDJOURNEY = "midjourney"


class ImageSize(str, Enum):
    """Standard image sizes"""
    SQUARE_1024 = "1024x1024"
    SQUARE_512 = "512x512"
    LANDSCAPE_1792_1024 = "1792x1024"
    PORTRAIT_1024_1792 = "1024x1792"
    WIDE_1920_1080 = "1920x1080"


class ImageStyle(str, Enum):
    """Image generation styles"""
    NATURAL = "natural"
    VIVID = "vivid"
    ARTISTIC = "artistic"
    PHOTOREALISTIC = "photorealistic"
    ANIME = "anime"
    OIL_PAINTING = "oil_painting"
    WATERCOLOR = "watercolor"
    CYBERPUNK = "cyberpunk"
    FANTASY = "fantasy"


@dataclass
class ImageRequest:
    """Image generation request"""
    prompt: str
    provider: ImageProvider = ImageProvider.DALLE_3
    size: ImageSize = ImageSize.SQUARE_1024
    style: Optional[ImageStyle] = None
    quality: str = "standard"  # standard or hd
    n: int = 1  # number of images
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None


@dataclass
class GeneratedImage:
    """Generated image result"""
    url: Optional[str] = None
    b64_json: Optional[str] = None
    revised_prompt: Optional[str] = None
    provider: Optional[str] = None
    size: Optional[str] = None
    cost: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ImageGenerationAgent:
    """Agent for image generation using multiple providers"""

    def __init__(self, llm_manager: Optional[LLMManager] = None):
        self.name = "ImageAgent"
        self.description = "Generates images using AI models (DALL-E, Stable Diffusion)"
        self.capabilities = [
            "Generate images from text descriptions",
            "Edit and modify existing images",
            "Create variations of images",
            "Upscale images",
            "Support multiple art styles and sizes",
            "Optimize prompts for better results"
        ]
        self.llm_manager = llm_manager or LLMManager()
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

        # API keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.replicate_api_key = os.getenv("REPLICATE_API_KEY")
        self.stability_api_key = os.getenv("STABILITY_API_KEY")

        # Pricing (USD per image)
        self.pricing = {
            ImageProvider.DALLE_3: {"1024x1024": 0.040, "1792x1024": 0.080, "1024x1792": 0.080},
            ImageProvider.DALLE_2: {"1024x1024": 0.020, "512x512": 0.018, "256x256": 0.016},
            ImageProvider.STABLE_DIFFUSION_XL: {"default": 0.003},
            ImageProvider.STABLE_DIFFUSION_2: {"default": 0.002}
        }

    async def enhance_prompt(self, basic_prompt: str, style: Optional[ImageStyle] = None) -> str:
        """
        Use LLM to enhance and optimize image generation prompt

        Args:
            basic_prompt: User's basic prompt
            style: Desired image style

        Returns:
            Enhanced, detailed prompt
        """
        enhancement_prompt = f"""You are an expert at crafting image generation prompts.
Transform this basic prompt into a detailed, high-quality prompt that will produce stunning results.

Basic prompt: {basic_prompt}
{f"Desired style: {style.value}" if style else ""}

Provide an enhanced prompt that includes:
- Detailed visual descriptions
- Lighting and composition details
- Art style and technique
- Color palette suggestions
- Mood and atmosphere

Return ONLY the enhanced prompt, no explanations."""

        messages = [{"role": "user", "content": enhancement_prompt}]

        try:
            response = await self.llm_manager.generate(
                messages,
                provider=LLMProvider.GEMINI_2_5_PRO,
                temperature=0.7
            )
            enhanced = response.strip()
            self.logger.info(f"Enhanced prompt: {enhanced[:100]}...")
            return enhanced
        except Exception as e:
            self.logger.warning(f"Prompt enhancement failed, using original: {e}")
            return basic_prompt

    async def generate_dalle(
        self,
        request: ImageRequest
    ) -> List[GeneratedImage]:
        """
        Generate images using DALL-E

        Args:
            request: Image generation request

        Returns:
            List of generated images
        """
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set")

        # Map provider to model
        model_map = {
            ImageProvider.DALLE_3: "dall-e-3",
            ImageProvider.DALLE_2: "dall-e-2"
        }
        model = model_map.get(request.provider, "dall-e-3")

        # Build request
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "prompt": request.prompt,
            "n": request.n,
            "size": request.size.value
        }

        # DALL-E 3 specific options
        if model == "dall-e-3":
            payload["quality"] = request.quality
            if request.style:
                # Map styles to DALL-E 3 styles
                style_map = {
                    ImageStyle.NATURAL: "natural",
                    ImageStyle.VIVID: "vivid"
                }
                payload["style"] = style_map.get(request.style, "vivid")

        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"DALL-E API error: {error_text}")

                result = await response.json()

        # Parse results
        images = []
        pricing_key = request.size.value if request.size.value in self.pricing[request.provider] else "1024x1024"
        cost_per_image = self.pricing[request.provider][pricing_key]

        for img_data in result.get("data", []):
            images.append(GeneratedImage(
                url=img_data.get("url"),
                b64_json=img_data.get("b64_json"),
                revised_prompt=img_data.get("revised_prompt"),
                provider=model,
                size=request.size.value,
                cost=cost_per_image,
                metadata={
                    "original_prompt": request.prompt,
                    "quality": request.quality,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ))

        self.logger.info(f"Generated {len(images)} images with {model}")
        return images

    async def generate_stable_diffusion(
        self,
        request: ImageRequest
    ) -> List[GeneratedImage]:
        """
        Generate images using Stable Diffusion via Replicate

        Args:
            request: Image generation request

        Returns:
            List of generated images
        """
        if not self.replicate_api_key:
            raise ValueError("REPLICATE_API_KEY not set")

        # Model versions
        model_map = {
            ImageProvider.STABLE_DIFFUSION_XL: "stability-ai/sdxl:latest",
            ImageProvider.STABLE_DIFFUSION_2: "stability-ai/stable-diffusion:latest"
        }
        model = model_map.get(request.provider, model_map[ImageProvider.STABLE_DIFFUSION_XL])

        headers = {
            "Authorization": f"Token {self.replicate_api_key}",
            "Content-Type": "application/json"
        }

        # Parse size
        width, height = map(int, request.size.value.split("x"))

        payload = {
            "version": model,
            "input": {
                "prompt": request.prompt,
                "width": width,
                "height": height,
                "num_outputs": request.n
            }
        }

        if request.negative_prompt:
            payload["input"]["negative_prompt"] = request.negative_prompt
        if request.seed:
            payload["input"]["seed"] = request.seed

        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 201:
                    error_text = await response.text()
                    raise Exception(f"Replicate API error: {error_text}")

                result = await response.json()

        # Poll for completion
        prediction_url = result.get("urls", {}).get("get")
        output_urls = await self._poll_replicate(prediction_url, headers)

        # Build results
        images = []
        cost = self.pricing[request.provider]["default"]

        for url in output_urls:
            images.append(GeneratedImage(
                url=url,
                provider=model,
                size=request.size.value,
                cost=cost,
                metadata={
                    "original_prompt": request.prompt,
                    "negative_prompt": request.negative_prompt,
                    "seed": request.seed,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ))

        self.logger.info(f"Generated {len(images)} images with {model}")
        return images

    async def _poll_replicate(
        self,
        prediction_url: str,
        headers: Dict[str, str],
        max_wait: int = 300
    ) -> List[str]:
        """Poll Replicate API for prediction completion"""
        async with aiohttp.ClientSession() as session:
            for _ in range(max_wait):
                await asyncio.sleep(1)

                async with session.get(prediction_url, headers=headers) as response:
                    result = await response.json()
                    status = result.get("status")

                    if status == "succeeded":
                        return result.get("output", [])
                    elif status == "failed":
                        raise Exception(f"Image generation failed: {result.get('error')}")

        raise TimeoutError("Image generation timed out")

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute image generation task

        Args:
            task: Task with image generation request

        Returns:
            Result with generated images
        """
        try:
            # Parse task
            prompt = task.get("prompt", "")
            provider = ImageProvider(task.get("provider", "dalle-3"))
            size = ImageSize(task.get("size", "1024x1024"))
            style = ImageStyle(task.get("style")) if task.get("style") else None
            quality = task.get("quality", "standard")
            n = task.get("n", 1)
            enhance = task.get("enhance_prompt", True)
            negative_prompt = task.get("negative_prompt")
            seed = task.get("seed")

            # Enhance prompt if requested
            if enhance:
                prompt = await self.enhance_prompt(prompt, style)

            # Create request
            request = ImageRequest(
                prompt=prompt,
                provider=provider,
                size=size,
                style=style,
                quality=quality,
                n=n,
                negative_prompt=negative_prompt,
                seed=seed
            )

            # Generate based on provider
            if provider in [ImageProvider.DALLE_3, ImageProvider.DALLE_2]:
                images = await self.generate_dalle(request)
            elif provider in [ImageProvider.STABLE_DIFFUSION_XL, ImageProvider.STABLE_DIFFUSION_2]:
                images = await self.generate_stable_diffusion(request)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            total_cost = sum(img.cost for img in images)

            return {
                "status": "success",
                "agent": self.name,
                "images": [
                    {
                        "url": img.url,
                        "revised_prompt": img.revised_prompt,
                        "provider": img.provider,
                        "size": img.size,
                        "cost": img.cost,
                        "metadata": img.metadata
                    }
                    for img in images
                ],
                "total_cost": total_cost,
                "count": len(images),
                "message": f"Generated {len(images)} image(s) using {provider.value}"
            }

        except Exception as e:
            self.logger.error(f"Image generation failed: {e}")
            return {
                "status": "error",
                "agent": self.name,
                "error": str(e),
                "message": f"Failed to generate images: {e}"
            }

    def get_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "supported_providers": [p.value for p in ImageProvider],
            "supported_sizes": [s.value for s in ImageSize],
            "supported_styles": [s.value for s in ImageStyle],
            "configured_providers": {
                "dalle": bool(self.openai_api_key),
                "stable_diffusion": bool(self.replicate_api_key),
                "stability_ai": bool(self.stability_api_key)
            }
        }
