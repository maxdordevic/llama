"""
LLM Provider Integration Layer
Supports multiple SOTA LLMs: Gemini 2.5 Pro, Claude Sonnet, Perplexity, OpenAI
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from enum import Enum
import asyncio
import aiohttp
import json

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers"""
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5"
    CLAUDE_OPUS_4 = "claude-opus-4"
    PERPLEXITY_SONAR_PRO = "perplexity-sonar-pro"
    OPENAI_GPT4 = "gpt-4-turbo"
    OPENAI_O1 = "o1-preview"


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion from messages"""
        pass

    @abstractmethod
    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        """Stream generation from messages"""
        pass


class GeminiClient(BaseLLMClient):
    """Google Gemini 2.5 Pro client"""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion using Gemini API"""
        url = f"{self.BASE_URL}/models/{self.model}:generateContent"

        # Convert OpenAI-style messages to Gemini format
        contents = self._convert_messages(messages)

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": kwargs.get("top_p", 0.95),
                "topK": kwargs.get("top_k", 40),
            }
        }

        headers = {
            "Content-Type": "application/json",
        }

        params = {"key": self.api_key}

        async with self.session.post(url, json=payload, headers=headers, params=params) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Gemini API error: {resp.status} - {error_text}")

            result = await resp.json()

            # Extract text from response
            try:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "content": text,
                    "model": self.model,
                    "usage": result.get("usageMetadata", {}),
                    "finish_reason": result["candidates"][0].get("finishReason", "STOP")
                }
            except (KeyError, IndexError) as e:
                logger.error(f"Error parsing Gemini response: {e}")
                raise

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        """Stream generation using Gemini API"""
        url = f"{self.BASE_URL}/models/{self.model}:streamGenerateContent"

        contents = self._convert_messages(messages)

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key, "alt": "sse"}

        async with self.session.post(url, json=payload, headers=headers, params=params) as resp:
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if "candidates" in data:
                            text = data["candidates"][0]["content"]["parts"][0].get("text", "")
                            if text:
                                yield {"content": text, "type": "content"}
                    except json.JSONDecodeError:
                        continue

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Convert OpenAI-style messages to Gemini format"""
        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        return contents


class ClaudeClient(BaseLLMClient):
    """Anthropic Claude client"""

    BASE_URL = "https://api.anthropic.com/v1"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion using Claude API"""
        url = f"{self.BASE_URL}/messages"

        # Separate system messages
        system_messages = [m["content"] for m in messages if m["role"] == "system"]
        system = "\n".join(system_messages) if system_messages else None

        # Filter out system messages from conversation
        conversation = [m for m in messages if m["role"] != "system"]

        payload = {
            "model": self.model,
            "messages": conversation,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system:
            payload["system"] = system

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        async with self.session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Claude API error: {resp.status} - {error_text}")

            result = await resp.json()

            return {
                "content": result["content"][0]["text"],
                "model": self.model,
                "usage": result.get("usage", {}),
                "finish_reason": result.get("stop_reason", "end_turn")
            }

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        """Stream generation using Claude API"""
        url = f"{self.BASE_URL}/messages"

        system_messages = [m["content"] for m in messages if m["role"] == "system"]
        system = "\n".join(system_messages) if system_messages else None
        conversation = [m for m in messages if m["role"] != "system"]

        payload = {
            "model": self.model,
            "messages": conversation,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }

        if system:
            payload["system"] = system

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        async with self.session.post(url, json=payload, headers=headers) as resp:
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            text = data.get("delta", {}).get("text", "")
                            if text:
                                yield {"content": text, "type": "content"}
                    except json.JSONDecodeError:
                        continue


class PerplexityClient(BaseLLMClient):
    """Perplexity Sonar Pro client"""

    BASE_URL = "https://api.perplexity.ai"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion using Perplexity API"""
        url = f"{self.BASE_URL}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        async with self.session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Perplexity API error: {resp.status} - {error_text}")

            result = await resp.json()

            return {
                "content": result["choices"][0]["message"]["content"],
                "model": self.model,
                "usage": result.get("usage", {}),
                "finish_reason": result["choices"][0].get("finish_reason", "stop"),
                "citations": result.get("citations", [])
            }

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        """Stream generation using Perplexity API"""
        url = f"{self.BASE_URL}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        async with self.session.post(url, json=payload, headers=headers) as resp:
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    if line == 'data: [DONE]':
                        break
                    try:
                        data = json.loads(line[6:])
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield {"content": delta["content"], "type": "content"}
                    except json.JSONDecodeError:
                        continue


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT-4 client"""

    BASE_URL = "https://api.openai.com/v1"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion using OpenAI API"""
        url = f"{self.BASE_URL}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        async with self.session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"OpenAI API error: {resp.status} - {error_text}")

            result = await resp.json()

            return {
                "content": result["choices"][0]["message"]["content"],
                "model": self.model,
                "usage": result.get("usage", {}),
                "finish_reason": result["choices"][0].get("finish_reason", "stop")
            }

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        """Stream generation using OpenAI API"""
        url = f"{self.BASE_URL}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        async with self.session.post(url, json=payload, headers=headers) as resp:
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    if line == 'data: [DONE]':
                        break
                    try:
                        data = json.loads(line[6:])
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield {"content": delta["content"], "type": "content"}
                    except json.JSONDecodeError:
                        continue


class LLMManager:
    """Manages multiple LLM providers and routing"""

    def __init__(self):
        self.providers = {}
        self._load_api_keys()

    def _load_api_keys(self):
        """Load API keys from environment"""
        self.api_keys = {
            "gemini": os.getenv("GEMINI_API_KEY"),
            "claude": os.getenv("ANTHROPIC_API_KEY"),
            "perplexity": os.getenv("PERPLEXITY_API_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
        }

    def get_client(self, provider: Union[LLMProvider, str]) -> BaseLLMClient:
        """Get LLM client for specified provider"""
        if isinstance(provider, str):
            provider = LLMProvider(provider)

        # Map provider to client class and API key
        client_map = {
            LLMProvider.GEMINI_2_5_PRO: (GeminiClient, "gemini-2.0-flash-exp", "gemini"),
            LLMProvider.GEMINI_2_5_FLASH: (GeminiClient, "gemini-2.0-flash-exp", "gemini"),
            LLMProvider.CLAUDE_SONNET_4_5: (ClaudeClient, "claude-sonnet-4-20250514", "claude"),
            LLMProvider.CLAUDE_OPUS_4: (ClaudeClient, "claude-opus-4-20250514", "claude"),
            LLMProvider.PERPLEXITY_SONAR_PRO: (PerplexityClient, "sonar-pro", "perplexity"),
            LLMProvider.OPENAI_GPT4: (OpenAIClient, "gpt-4-turbo", "openai"),
            LLMProvider.OPENAI_O1: (OpenAIClient, "o1-preview", "openai"),
        }

        client_class, model, key_name = client_map[provider]
        api_key = self.api_keys.get(key_name)

        if not api_key:
            raise ValueError(f"API key not found for {key_name}. Set {key_name.upper()}_API_KEY environment variable.")

        return client_class(api_key=api_key, model=model)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        provider: Union[LLMProvider, str] = LLMProvider.GEMINI_2_5_PRO,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion using specified provider"""
        async with self.get_client(provider) as client:
            return await client.generate(messages, temperature, max_tokens, **kwargs)

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        provider: Union[LLMProvider, str] = LLMProvider.GEMINI_2_5_PRO,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        """Stream generation using specified provider"""
        async with self.get_client(provider) as client:
            async for chunk in client.stream_generate(messages, temperature, max_tokens, **kwargs):
                yield chunk

    async def choose_best_provider(self, task_type: str) -> LLMProvider:
        """Choose best LLM provider based on task type"""
        # Smart routing based on task characteristics
        task_routing = {
            "research": LLMProvider.PERPLEXITY_SONAR_PRO,  # Best for web search
            "reasoning": LLMProvider.CLAUDE_SONNET_4_5,    # Best for complex reasoning
            "code": LLMProvider.CLAUDE_SONNET_4_5,         # Excellent for coding
            "creative": LLMProvider.GEMINI_2_5_PRO,        # Great for creative tasks
            "fast": LLMProvider.GEMINI_2_5_FLASH,          # Fastest responses
            "analysis": LLMProvider.CLAUDE_SONNET_4_5,     # Best for analysis
        }

        return task_routing.get(task_type, LLMProvider.GEMINI_2_5_PRO)
