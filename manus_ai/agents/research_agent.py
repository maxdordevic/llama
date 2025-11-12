"""
Research Agent - Handles web research, information gathering, and fact-checking
Uses Perplexity for web-grounded research
"""

import logging
from typing import Dict, Any
import asyncio

from .base_agent import BaseAgent
from ..core.llm_providers import LLMProvider

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """
    Specialized agent for research tasks
    Capabilities:
    - Web research and information gathering
    - Multi-source synthesis
    - Fact-checking and verification
    - Citation and reference management
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent_type = "research"
        self.default_provider = LLMProvider.PERPLEXITY_SONAR_PRO  # Best for research
        self.capabilities = [
            "web_search",
            "information_gathering",
            "fact_checking",
            "multi_source_synthesis",
            "citation_management"
        ]

    async def execute(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute research task"""
        self.log_execution(task.id, f"Starting research: {task.title}")

        try:
            # Analyze research requirements
            research_plan = await self._plan_research(task, context)

            # Conduct research
            research_results = await self._conduct_research(
                task.description,
                research_plan
            )

            # Synthesize findings
            synthesis = await self._synthesize_findings(
                task.description,
                research_results
            )

            self.log_execution(task.id, "Research completed successfully")

            return {
                "type": "research",
                "findings": synthesis["content"],
                "sources": research_results.get("citations", []),
                "confidence": "high",
                "research_plan": research_plan,
                "raw_results": research_results
            }

        except Exception as e:
            self.log_execution(task.id, f"Research failed: {e}", "error")
            raise

    async def _plan_research(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Plan research approach"""
        planning_prompt = f"""You are planning a research task.

Task: {task.description}

Create a research plan that includes:
1. Key questions to answer
2. Types of sources to consult
3. Specific search queries to use
4. Verification strategy

Provide a structured research approach."""

        messages = [
            {"role": "system", "content": "You are an expert research planner."},
            {"role": "user", "content": planning_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=LLMProvider.CLAUDE_SONNET_4_5,  # Use Claude for planning
            temperature=0.3
        )

        return {"plan": response["content"]}

    async def _conduct_research(
        self,
        query: str,
        research_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Conduct web research using Perplexity"""
        research_prompt = f"""Research the following topic comprehensively:

Topic: {query}

Research Plan:
{research_plan.get('plan', 'No specific plan')}

Provide:
1. Comprehensive findings on the topic
2. Key facts and statistics
3. Different perspectives or viewpoints
4. Recent developments or trends
5. Reliable sources and citations

Be thorough and factual."""

        messages = [
            {"role": "system", "content": "You are an expert researcher providing comprehensive, well-sourced information."},
            {"role": "user", "content": research_prompt}
        ]

        # Use Perplexity for web-grounded research
        response = await self.generate_response(
            messages=messages,
            provider=LLMProvider.PERPLEXITY_SONAR_PRO,
            temperature=0.2
        )

        return {
            "findings": response["content"],
            "citations": response.get("citations", []),
            "model": response.get("model")
        }

    async def _synthesize_findings(
        self,
        original_query: str,
        research_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize research findings into coherent response"""
        synthesis_prompt = f"""Synthesize the following research findings into a clear, well-organized response.

Original Query: {original_query}

Research Findings:
{research_results.get('findings', 'No findings')}

Provide a comprehensive synthesis that:
1. Directly answers the query
2. Organizes information logically
3. Highlights key insights
4. Notes any uncertainties or conflicting information
5. Suggests further areas for exploration if relevant"""

        messages = [
            {"role": "system", "content": "You are an expert at synthesizing research into clear, actionable insights."},
            {"role": "user", "content": synthesis_prompt}
        ]

        return await self.generate_response(
            messages=messages,
            provider=LLMProvider.CLAUDE_SONNET_4_5,
            temperature=0.4
        )

    async def fact_check(self, claim: str) -> Dict[str, Any]:
        """Fact-check a specific claim"""
        messages = [
            {"role": "system", "content": "You are a fact-checker. Verify claims using reliable sources."},
            {"role": "user", "content": f"Fact-check this claim: {claim}"}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=LLMProvider.PERPLEXITY_SONAR_PRO,
            temperature=0.1
        )

        return {
            "claim": claim,
            "verification": response["content"],
            "sources": response.get("citations", [])
        }
