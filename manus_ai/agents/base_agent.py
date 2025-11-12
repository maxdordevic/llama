"""
Base Agent Class - Abstract foundation for all specialized agents
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from ..core.llm_providers import LLMManager, LLMProvider

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents
    Provides common functionality and interface
    """

    def __init__(
        self,
        llm_manager: Optional[LLMManager] = None,
        default_provider: LLMProvider = LLMProvider.GEMINI_2_5_PRO
    ):
        self.llm_manager = llm_manager or LLMManager()
        self.default_provider = default_provider
        self.agent_type = "base"
        self.capabilities = []

    @abstractmethod
    async def execute(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute assigned task

        Args:
            task: SubTask object containing task details
            context: Execution context including session info, dependencies, etc.

        Returns:
            Task execution result
        """
        pass

    async def generate_response(
        self,
        messages: list,
        provider: Optional[LLMProvider] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """Helper method to generate LLM response"""
        provider = provider or self.default_provider

        try:
            return await self.llm_manager.generate(
                messages=messages,
                provider=provider,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    async def stream_response(
        self,
        messages: list,
        provider: Optional[LLMProvider] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ):
        """Helper method to stream LLM response"""
        provider = provider or self.default_provider

        try:
            async for chunk in self.llm_manager.stream_generate(
                messages=messages,
                provider=provider,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            raise

    def log_execution(self, task_id: str, message: str, level: str = "info"):
        """Log execution progress"""
        log_func = getattr(logger, level, logger.info)
        log_func(f"[{self.agent_type}] [{task_id}] {message}")

    def get_capabilities(self) -> list:
        """Return list of agent capabilities"""
        return self.capabilities

    def validate_task(self, task: Any) -> bool:
        """Validate if agent can handle this task"""
        return True  # Base implementation accepts all tasks
