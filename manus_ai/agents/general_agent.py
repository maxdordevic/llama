"""
General Purpose Agent - Handles tasks that don't fit specific categories
"""

import logging
from typing import Dict, Any

from .base_agent import BaseAgent
from ..core.llm_providers import LLMProvider

logger = logging.getLogger(__name__)


class GeneralAgent(BaseAgent):
    """
    General purpose agent for miscellaneous tasks
    Capabilities:
    - Task execution planning
    - Multi-step reasoning
    - General problem solving
    - Task delegation
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent_type = "general"
        self.default_provider = LLMProvider.GEMINI_2_5_PRO
        self.capabilities = [
            "general_reasoning",
            "problem_solving",
            "task_planning",
            "content_generation",
            "question_answering"
        ]

    async def execute(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute general task"""
        self.log_execution(task.id, f"Starting general task: {task.title}")

        try:
            # Analyze task complexity
            complexity = await self._analyze_complexity(task)

            # Choose appropriate strategy
            if complexity == "simple":
                result = await self._execute_simple(task, context)
            elif complexity == "medium":
                result = await self._execute_medium(task, context)
            else:
                result = await self._execute_complex(task, context)

            self.log_execution(task.id, "General task completed successfully")

            return result

        except Exception as e:
            self.log_execution(task.id, f"General task failed: {e}", "error")
            raise

    async def _analyze_complexity(self, task: Any) -> str:
        """Analyze task complexity"""
        description_length = len(task.description)

        # Simple heuristic
        if description_length < 100:
            return "simple"
        elif description_length < 300:
            return "medium"
        else:
            return "complex"

    async def _execute_simple(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute simple task with single LLM call"""
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant completing tasks efficiently."},
            {"role": "user", "content": task.description}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.5
        )

        return {
            "type": "simple_task",
            "result": response["content"],
            "complexity": "simple"
        }

    async def _execute_medium(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute medium complexity task with planning"""
        # First, create a plan
        plan_messages = [
            {"role": "system", "content": "You are creating an execution plan."},
            {"role": "user", "content": f"Create a step-by-step plan for: {task.description}"}
        ]

        plan_response = await self.generate_response(
            messages=plan_messages,
            provider=LLMProvider.CLAUDE_SONNET_4_5,
            temperature=0.3
        )

        # Then execute based on plan
        exec_messages = [
            {"role": "system", "content": "You are executing a planned task."},
            {"role": "user", "content": f"Task: {task.description}\n\nPlan: {plan_response['content']}\n\nExecute this plan."}
        ]

        exec_response = await self.generate_response(
            messages=exec_messages,
            provider=self.default_provider,
            temperature=0.5
        )

        return {
            "type": "medium_task",
            "plan": plan_response["content"],
            "result": exec_response["content"],
            "complexity": "medium"
        }

    async def _execute_complex(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complex task with iterative refinement"""
        # Multi-step execution with refinement
        steps = []

        # Step 1: Understand and plan
        understand_messages = [
            {"role": "system", "content": "You are analyzing a complex task."},
            {"role": "user", "content": f"Analyze this task and break it into steps: {task.description}"}
        ]

        understand_response = await self.generate_response(
            messages=understand_messages,
            provider=LLMProvider.CLAUDE_SONNET_4_5,
            temperature=0.3
        )
        steps.append({"step": "understanding", "result": understand_response["content"]})

        # Step 2: Execute main task
        exec_messages = [
            {"role": "system", "content": "You are executing a complex task."},
            {"role": "user", "content": f"Task: {task.description}\n\nAnalysis: {understand_response['content']}\n\nComplete the task comprehensively."}
        ]

        exec_response = await self.generate_response(
            messages=exec_messages,
            provider=self.default_provider,
            temperature=0.5,
            max_tokens=4096
        )
        steps.append({"step": "execution", "result": exec_response["content"]})

        # Step 3: Review and refine
        review_messages = [
            {"role": "system", "content": "You are reviewing work for completeness."},
            {"role": "user", "content": f"Review this result and suggest improvements:\n\n{exec_response['content']}"}
        ]

        review_response = await self.generate_response(
            messages=review_messages,
            provider=LLMProvider.CLAUDE_SONNET_4_5,
            temperature=0.4
        )
        steps.append({"step": "review", "result": review_response["content"]})

        return {
            "type": "complex_task",
            "steps": steps,
            "final_result": exec_response["content"],
            "review": review_response["content"],
            "complexity": "complex"
        }

    async def answer_question(self, question: str) -> str:
        """Answer a question comprehensively"""
        messages = [
            {"role": "system", "content": "You are a knowledgeable AI assistant providing comprehensive answers."},
            {"role": "user", "content": question}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.6
        )

        return response["content"]

    async def generate_content(
        self,
        content_type: str,
        description: str,
        requirements: Dict[str, Any] = None
    ) -> str:
        """Generate various types of content"""
        prompt = f"""Generate {content_type} content.

Description: {description}
Requirements: {requirements or 'None specified'}

Create high-quality, well-structured content that meets the requirements."""

        messages = [
            {"role": "system", "content": f"You are an expert {content_type} creator."},
            {"role": "user", "content": prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.7
        )

        return response["content"]
