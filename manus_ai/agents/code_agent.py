"""
Code Agent - Handles code generation, debugging, and software development
"""

import logging
from typing import Dict, Any, List
import asyncio
import tempfile
import os

from .base_agent import BaseAgent
from ..core.llm_providers import LLMProvider

logger = logging.getLogger(__name__)


class CodeAgent(BaseAgent):
    """
    Specialized agent for coding tasks
    Capabilities:
    - Code generation in multiple languages
    - Debugging and error fixing
    - Code review and optimization
    - Test generation
    - Documentation generation
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent_type = "code"
        self.default_provider = LLMProvider.CLAUDE_SONNET_4_5  # Best for coding
        self.capabilities = [
            "code_generation",
            "debugging",
            "code_review",
            "test_generation",
            "documentation",
            "refactoring",
            "multi_language_support"
        ]
        self.supported_languages = [
            "python", "javascript", "typescript", "java", "c++", "c#",
            "go", "rust", "ruby", "php", "swift", "kotlin", "html", "css"
        ]

    async def execute(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute coding task"""
        self.log_execution(task.id, f"Starting code task: {task.title}")

        try:
            # Analyze task type
            task_type = await self._analyze_code_task(task)

            # Execute appropriate coding workflow
            if task_type == "generation":
                result = await self._generate_code(task, context)
            elif task_type == "debugging":
                result = await self._debug_code(task, context)
            elif task_type == "review":
                result = await self._review_code(task, context)
            elif task_type == "testing":
                result = await self._generate_tests(task, context)
            else:
                result = await self._general_code_task(task, context)

            self.log_execution(task.id, "Code task completed successfully")

            return result

        except Exception as e:
            self.log_execution(task.id, f"Code task failed: {e}", "error")
            raise

    async def _analyze_code_task(self, task: Any) -> str:
        """Analyze what type of coding task this is"""
        description = task.description.lower()

        if any(kw in description for kw in ["generate", "create", "write", "build", "implement"]):
            return "generation"
        elif any(kw in description for kw in ["debug", "fix", "error", "bug"]):
            return "debugging"
        elif any(kw in description for kw in ["review", "analyze", "check", "audit"]):
            return "review"
        elif any(kw in description for kw in ["test", "unit test", "testing"]):
            return "testing"
        else:
            return "general"

    async def _generate_code(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code based on specifications"""
        code_prompt = f"""You are an expert software developer. Generate clean, efficient, well-documented code.

Task: {task.description}

Requirements:
1. Write production-ready code
2. Include appropriate error handling
3. Add clear comments and docstrings
4. Follow best practices and design patterns
5. Ensure code is secure (no SQL injection, XSS, etc.)
6. Make code modular and maintainable

Provide:
1. Complete, working code
2. Explanation of approach
3. Usage examples
4. Any dependencies needed"""

        messages = [
            {"role": "system", "content": "You are an expert software developer with deep knowledge of multiple programming languages, design patterns, and best practices."},
            {"role": "user", "content": code_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.3
        )

        # Extract code blocks
        code_blocks = self._extract_code_blocks(response["content"])

        return {
            "type": "code_generation",
            "code": code_blocks,
            "explanation": response["content"],
            "language": self._detect_language(response["content"]),
            "full_response": response
        }

    async def _debug_code(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Debug and fix code issues"""
        debug_prompt = f"""You are debugging code. Find and fix all issues.

Task: {task.description}

Analyze the code for:
1. Syntax errors
2. Logic errors
3. Runtime errors
4. Performance issues
5. Security vulnerabilities
6. Edge cases

Provide:
1. Identified issues
2. Fixed code
3. Explanation of what was wrong
4. Recommendations to prevent similar issues"""

        messages = [
            {"role": "system", "content": "You are an expert debugger who can quickly identify and fix code issues."},
            {"role": "user", "content": debug_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.2
        )

        return {
            "type": "debugging",
            "fixed_code": self._extract_code_blocks(response["content"]),
            "issues_found": response["content"],
            "recommendations": response["content"]
        }

    async def _review_code(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Review code for quality, security, and best practices"""
        review_prompt = f"""Perform a comprehensive code review.

Task: {task.description}

Review for:
1. Code quality and readability
2. Security vulnerabilities (OWASP Top 10)
3. Performance optimization opportunities
4. Best practices adherence
5. Test coverage
6. Documentation quality
7. Maintainability

Provide detailed feedback with specific recommendations."""

        messages = [
            {"role": "system", "content": "You are a senior software engineer conducting a thorough code review."},
            {"role": "user", "content": review_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.4
        )

        return {
            "type": "code_review",
            "review": response["content"],
            "severity_levels": self._categorize_issues(response["content"])
        }

    async def _generate_tests(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate unit tests for code"""
        test_prompt = f"""Generate comprehensive unit tests.

Task: {task.description}

Create tests that:
1. Cover all major code paths
2. Test edge cases
3. Test error handling
4. Are well-organized and maintainable
5. Include clear test descriptions
6. Use appropriate testing framework

Aim for high code coverage."""

        messages = [
            {"role": "system", "content": "You are an expert at writing comprehensive, effective unit tests."},
            {"role": "user", "content": test_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.3
        )

        return {
            "type": "test_generation",
            "tests": self._extract_code_blocks(response["content"]),
            "explanation": response["content"],
            "framework": self._detect_test_framework(response["content"])
        }

    async def _general_code_task(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general coding tasks"""
        messages = [
            {"role": "system", "content": "You are an expert software developer."},
            {"role": "user", "content": task.description}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.4
        )

        return {
            "type": "general_code",
            "result": response["content"],
            "code_blocks": self._extract_code_blocks(response["content"])
        }

    def _extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """Extract code blocks from markdown"""
        blocks = []
        lines = text.split('\n')
        in_block = False
        current_block = []
        current_language = ""

        for line in lines:
            if line.strip().startswith('```'):
                if in_block:
                    # End of block
                    blocks.append({
                        "language": current_language,
                        "code": '\n'.join(current_block)
                    })
                    current_block = []
                    in_block = False
                else:
                    # Start of block
                    in_block = True
                    current_language = line.strip()[3:].strip()
            elif in_block:
                current_block.append(line)

        return blocks

    def _detect_language(self, text: str) -> str:
        """Detect programming language from text"""
        text_lower = text.lower()
        for lang in self.supported_languages:
            if lang in text_lower:
                return lang
        return "unknown"

    def _detect_test_framework(self, text: str) -> str:
        """Detect testing framework used"""
        frameworks = {
            "pytest": ["pytest", "import pytest"],
            "unittest": ["import unittest", "unittest.TestCase"],
            "jest": ["jest", "describe(", "it("],
            "mocha": ["mocha", "describe(", "it("],
            "junit": ["@Test", "junit"],
        }

        for framework, patterns in frameworks.items():
            if any(pattern in text for pattern in patterns):
                return framework

        return "unknown"

    def _categorize_issues(self, review_text: str) -> Dict[str, int]:
        """Categorize code review issues by severity"""
        # Simple heuristic-based categorization
        critical_keywords = ["security", "vulnerability", "sql injection", "xss", "critical"]
        major_keywords = ["bug", "error", "issue", "problem"]
        minor_keywords = ["style", "formatting", "suggestion"]

        review_lower = review_text.lower()

        return {
            "critical": sum(1 for kw in critical_keywords if kw in review_lower),
            "major": sum(1 for kw in major_keywords if kw in review_lower),
            "minor": sum(1 for kw in minor_keywords if kw in review_lower)
        }
