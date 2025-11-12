"""
Data Analysis Agent - Handles data processing, analysis, and visualization
"""

import logging
from typing import Dict, Any, List
import json

from .base_agent import BaseAgent
from ..core.llm_providers import LLMProvider

logger = logging.getLogger(__name__)


class DataAnalysisAgent(BaseAgent):
    """
    Specialized agent for data analysis
    Capabilities:
    - Dataset analysis and profiling
    - Statistical analysis
    - Data visualization
    - Data cleaning and transformation
    - Insights generation
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent_type = "data"
        self.default_provider = LLMProvider.CLAUDE_SONNET_4_5
        self.capabilities = [
            "data_analysis",
            "statistical_analysis",
            "data_visualization",
            "data_cleaning",
            "insights_generation",
            "predictive_analytics"
        ]
        self.supported_formats = ["csv", "json", "excel", "parquet", "sql"]

    async def execute(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data analysis task"""
        self.log_execution(task.id, f"Starting data analysis: {task.title}")

        try:
            # Analyze task requirements
            analysis_type = await self._determine_analysis_type(task)

            # Execute appropriate analysis
            if analysis_type == "exploration":
                result = await self._explore_data(task, context)
            elif analysis_type == "statistical":
                result = await self._statistical_analysis(task, context)
            elif analysis_type == "visualization":
                result = await self._create_visualizations(task, context)
            elif analysis_type == "cleaning":
                result = await self._clean_data(task, context)
            else:
                result = await self._general_analysis(task, context)

            self.log_execution(task.id, "Data analysis completed successfully")

            return result

        except Exception as e:
            self.log_execution(task.id, f"Data analysis failed: {e}", "error")
            raise

    async def _determine_analysis_type(self, task: Any) -> str:
        """Determine type of data analysis needed"""
        description = task.description.lower()

        if any(kw in description for kw in ["explore", "profile", "summary", "overview"]):
            return "exploration"
        elif any(kw in description for kw in ["statistic", "correlation", "regression", "trend"]):
            return "statistical"
        elif any(kw in description for kw in ["visualiz", "plot", "chart", "graph"]):
            return "visualization"
        elif any(kw in description for kw in ["clean", "preprocess", "transform"]):
            return "cleaning"
        else:
            return "general"

    async def _explore_data(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform exploratory data analysis"""
        explore_prompt = f"""Perform exploratory data analysis.

Task: {task.description}

Provide Python code using pandas, numpy, and matplotlib to:
1. Load and inspect the data
2. Generate summary statistics
3. Identify data types and missing values
4. Detect outliers
5. Analyze distributions
6. Identify correlations
7. Generate initial insights

Make the code executable and well-documented."""

        messages = [
            {"role": "system", "content": "You are a data scientist expert in exploratory data analysis."},
            {"role": "user", "content": explore_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.3
        )

        return {
            "type": "exploratory_analysis",
            "code": response["content"],
            "insights": self._extract_insights(response["content"]),
            "recommendations": "Execute the code with actual data"
        }

    async def _statistical_analysis(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform statistical analysis"""
        stats_prompt = f"""Perform statistical analysis.

Task: {task.description}

Provide Python code using scipy, statsmodels, and numpy to:
1. Conduct appropriate statistical tests
2. Calculate relevant metrics
3. Test hypotheses if applicable
4. Identify significant patterns
5. Provide confidence intervals
6. Interpret results

Include proper statistical methodology and assumptions."""

        messages = [
            {"role": "system", "content": "You are a statistician providing rigorous statistical analysis."},
            {"role": "user", "content": stats_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.2
        )

        return {
            "type": "statistical_analysis",
            "code": response["content"],
            "methodology": "Statistical methods described in code"
        }

    async def _create_visualizations(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create data visualizations"""
        viz_prompt = f"""Create data visualizations.

Task: {task.description}

Provide Python code using matplotlib, seaborn, or plotly to:
1. Create appropriate chart types for the data
2. Make visualizations clear and informative
3. Use proper labels, titles, and legends
4. Choose appropriate color schemes
5. Handle multiple visualizations if needed
6. Export visualizations as files

Make visualizations publication-ready."""

        messages = [
            {"role": "system", "content": "You are a data visualization expert."},
            {"role": "user", "content": viz_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.3
        )

        return {
            "type": "visualization",
            "code": response["content"],
            "chart_types": self._identify_chart_types(response["content"])
        }

    async def _clean_data(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and preprocess data"""
        clean_prompt = f"""Create data cleaning pipeline.

Task: {task.description}

Provide Python code using pandas to:
1. Handle missing values appropriately
2. Remove or correct outliers
3. Standardize data formats
4. Handle duplicate records
5. Validate data integrity
6. Transform data as needed
7. Document all cleaning steps

Ensure data quality and integrity."""

        messages = [
            {"role": "system", "content": "You are a data engineer specializing in data quality."},
            {"role": "user", "content": clean_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.2
        )

        return {
            "type": "data_cleaning",
            "code": response["content"],
            "cleaning_steps": "Documented in code"
        }

    async def _general_analysis(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general data analysis tasks"""
        messages = [
            {"role": "system", "content": "You are a data scientist providing comprehensive data analysis."},
            {"role": "user", "content": task.description}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.4
        )

        return {
            "type": "general_analysis",
            "result": response["content"]
        }

    def _extract_insights(self, text: str) -> List[str]:
        """Extract key insights from analysis"""
        # Simple keyword-based extraction
        insights = []
        lines = text.split('\n')

        for line in lines:
            if any(kw in line.lower() for kw in ["insight", "finding", "conclusion", "important"]):
                insights.append(line.strip())

        return insights[:5]  # Top 5 insights

    def _identify_chart_types(self, code: str) -> List[str]:
        """Identify chart types in visualization code"""
        chart_types = []
        chart_keywords = {
            "scatter": "scatter plot",
            "bar": "bar chart",
            "line": "line chart",
            "hist": "histogram",
            "box": "box plot",
            "heatmap": "heatmap",
            "pie": "pie chart"
        }

        code_lower = code.lower()
        for keyword, chart_type in chart_keywords.items():
            if keyword in code_lower:
                chart_types.append(chart_type)

        return chart_types

    async def generate_insights_report(
        self,
        data_summary: Dict[str, Any]
    ) -> str:
        """Generate natural language insights report"""
        report_prompt = f"""Generate a comprehensive insights report from this data analysis.

Data Summary:
{json.dumps(data_summary, indent=2)}

Create a report that:
1. Summarizes key findings
2. Highlights important patterns or trends
3. Identifies anomalies or outliers
4. Provides actionable recommendations
5. Notes any limitations or caveats

Make it clear and accessible to non-technical stakeholders."""

        messages = [
            {"role": "system", "content": "You are a data analyst creating an insights report."},
            {"role": "user", "content": report_prompt}
        ]

        response = await self.generate_response(
            messages=messages,
            provider=self.default_provider,
            temperature=0.5
        )

        return response["content"]
