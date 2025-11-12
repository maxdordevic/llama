"""
Manus AI Clone - Autonomous AI Agent Platform
=============================================

A comprehensive autonomous AI agent system that executes complex tasks end-to-end,
featuring multi-agent architecture, sandboxed execution, and intelligent task planning.

This system completely replaces the original Llama 2 implementation with a modern,
API-based architecture using state-of-the-art LLMs like Gemini 2.5 Pro, Claude Sonnet,
Perplexity, and OpenAI.
"""

__version__ = "1.0.0"
__author__ = "Manus AI Clone Project"

from .core.orchestrator import AgentOrchestrator
from .core.task_planner import TaskPlanner, ExecutionPlan
from .core.session_manager import SessionManager, Session
from .core.llm_providers import LLMManager, LLMProvider

# Agent imports
from .agents.research_agent import ResearchAgent
from .agents.code_agent import CodeAgent
from .agents.web_agent import WebAutomationAgent
from .agents.data_agent import DataAnalysisAgent
from .agents.file_agent import FileProcessingAgent
from .agents.general_agent import GeneralAgent

# Sandbox
from .sandbox.code_executor import CodeExecutor

# Memory
from .memory.memory_system import MemorySystem, MemoryManager

__all__ = [
    # Core
    "AgentOrchestrator",
    "TaskPlanner",
    "ExecutionPlan",
    "SessionManager",
    "Session",
    "LLMManager",
    "LLMProvider",
    # Agents
    "ResearchAgent",
    "CodeAgent",
    "WebAutomationAgent",
    "DataAnalysisAgent",
    "FileProcessingAgent",
    "GeneralAgent",
    # Sandbox
    "CodeExecutor",
    # Memory
    "MemorySystem",
    "MemoryManager",
]
