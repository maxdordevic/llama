"""
Specialized AI Agents for Task Execution
"""

from .base_agent import BaseAgent
from .research_agent import ResearchAgent
from .code_agent import CodeAgent
from .web_agent import WebAutomationAgent
from .data_agent import DataAnalysisAgent
from .file_agent import FileProcessingAgent
from .general_agent import GeneralAgent

__all__ = [
    "BaseAgent",
    "ResearchAgent",
    "CodeAgent",
    "WebAutomationAgent",
    "DataAnalysisAgent",
    "FileProcessingAgent",
    "GeneralAgent",
]
