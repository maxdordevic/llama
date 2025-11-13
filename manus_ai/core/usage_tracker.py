"""
Token Usage Tracking and Cost Management System
Tracks API usage, costs, and enforces budget limits
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from collections import defaultdict

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Types of billable resources"""
    LLM_INPUT_TOKENS = "llm_input_tokens"
    LLM_OUTPUT_TOKENS = "llm_output_tokens"
    IMAGE_GENERATION = "image_generation"
    WEB_SEARCH = "web_search"
    CODE_EXECUTION = "code_execution"
    VECTOR_STORAGE = "vector_storage"
    AGENT_EXECUTION = "agent_execution"


@dataclass
class UsageRecord:
    """Single usage record"""
    timestamp: datetime
    resource_type: ResourceType
    quantity: float
    cost: float
    provider: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetLimit:
    """Budget limit configuration"""
    limit_amount: float
    period: str  # "hourly", "daily", "weekly", "monthly", "total"
    resource_types: Optional[List[ResourceType]] = None  # None = all types
    user_id: Optional[str] = None  # None = global limit
    alert_threshold: float = 0.8  # Alert at 80% usage
    hard_limit: bool = True  # If True, block requests when exceeded


class PricingConfig:
    """Pricing configuration for different providers and resources"""

    # LLM pricing per 1M tokens (USD)
    LLM_PRICING = {
        "gemini-2.0-flash-exp": {
            "input": 0.10,  # $0.10 per 1M input tokens
            "output": 0.40  # $0.40 per 1M output tokens
        },
        "gemini-2.5-pro": {
            "input": 3.50,
            "output": 10.50
        },
        "sonar-pro": {
            "input": 3.00,
            "output": 15.00
        },
        "claude-3-5-sonnet-20241022": {
            "input": 3.00,
            "output": 15.00
        },
        "gpt-4o": {
            "input": 2.50,
            "output": 10.00
        },
        "gpt-4-turbo": {
            "input": 10.00,
            "output": 30.00
        },
        "gpt-3.5-turbo": {
            "input": 0.50,
            "output": 1.50
        }
    }

    # Image generation pricing (USD per image)
    IMAGE_PRICING = {
        "dalle-3": {
            "1024x1024": 0.040,
            "1792x1024": 0.080,
            "1024x1792": 0.080
        },
        "dalle-2": {
            "1024x1024": 0.020,
            "512x512": 0.018
        },
        "stable-diffusion-xl": 0.003,
        "stable-diffusion-2": 0.002
    }

    # Other resource pricing
    OTHER_PRICING = {
        "web_search": 0.001,  # Per search
        "code_execution": 0.0001,  # Per execution
        "vector_storage": 0.10,  # Per 1M vectors per month
        "agent_execution": 0.0005  # Base cost per agent execution
    }

    @classmethod
    def get_llm_cost(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate LLM cost"""
        if model not in cls.LLM_PRICING:
            logger.warning(f"Unknown model {model}, using default pricing")
            model = "gpt-3.5-turbo"

        pricing = cls.LLM_PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    @classmethod
    def get_image_cost(cls, provider: str, size: str = "1024x1024") -> float:
        """Calculate image generation cost"""
        if provider not in cls.IMAGE_PRICING:
            return 0.02  # Default cost

        pricing = cls.IMAGE_PRICING[provider]
        if isinstance(pricing, dict):
            return pricing.get(size, 0.02)
        return pricing


class UsageTracker:
    """Tracks resource usage and enforces budget limits"""

    def __init__(self, storage_backend: Optional[Any] = None):
        """
        Initialize usage tracker

        Args:
            storage_backend: Optional storage backend (MongoDB, Redis, etc.)
        """
        self.storage = storage_backend
        self.records: List[UsageRecord] = []
        self.budget_limits: List[BudgetLimit] = []
        self.usage_cache = defaultdict(lambda: defaultdict(float))
        self.logger = logging.getLogger(__name__)

    async def record_usage(
        self,
        resource_type: ResourceType,
        quantity: float,
        provider: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageRecord:
        """
        Record resource usage

        Args:
            resource_type: Type of resource used
            quantity: Amount used (tokens, images, etc.)
            provider: Provider name
            session_id: Optional session ID
            user_id: Optional user ID
            metadata: Additional metadata

        Returns:
            Usage record
        """
        # Calculate cost
        cost = self._calculate_cost(resource_type, quantity, provider, metadata or {})

        # Create record
        record = UsageRecord(
            timestamp=datetime.utcnow(),
            resource_type=resource_type,
            quantity=quantity,
            cost=cost,
            provider=provider,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {}
        )

        # Store record
        self.records.append(record)
        if self.storage:
            await self._persist_record(record)

        # Update cache
        self._update_cache(record)

        self.logger.debug(f"Recorded usage: {resource_type.value} - {quantity} units, ${cost:.6f}")
        return record

    async def record_llm_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> tuple[UsageRecord, UsageRecord]:
        """Record LLM token usage"""
        metadata = {"model": model}

        input_record = await self.record_usage(
            ResourceType.LLM_INPUT_TOKENS,
            input_tokens,
            model,
            session_id,
            user_id,
            metadata
        )

        output_record = await self.record_usage(
            ResourceType.LLM_OUTPUT_TOKENS,
            output_tokens,
            model,
            session_id,
            user_id,
            metadata
        )

        return input_record, output_record

    def _calculate_cost(
        self,
        resource_type: ResourceType,
        quantity: float,
        provider: str,
        metadata: Dict[str, Any]
    ) -> float:
        """Calculate cost for resource usage"""
        if resource_type == ResourceType.LLM_INPUT_TOKENS:
            return (quantity / 1_000_000) * PricingConfig.LLM_PRICING.get(provider, {}).get("input", 0.5)
        elif resource_type == ResourceType.LLM_OUTPUT_TOKENS:
            return (quantity / 1_000_000) * PricingConfig.LLM_PRICING.get(provider, {}).get("output", 1.5)
        elif resource_type == ResourceType.IMAGE_GENERATION:
            size = metadata.get("size", "1024x1024")
            return PricingConfig.get_image_cost(provider, size) * quantity
        elif resource_type == ResourceType.WEB_SEARCH:
            return PricingConfig.OTHER_PRICING["web_search"] * quantity
        elif resource_type == ResourceType.CODE_EXECUTION:
            return PricingConfig.OTHER_PRICING["code_execution"] * quantity
        elif resource_type == ResourceType.AGENT_EXECUTION:
            return PricingConfig.OTHER_PRICING["agent_execution"] * quantity
        else:
            return 0.0

    def _update_cache(self, record: UsageRecord):
        """Update usage cache for quick lookups"""
        key = f"{record.user_id or 'global'}:{record.resource_type.value}"
        self.usage_cache[key]["total_cost"] += record.cost
        self.usage_cache[key]["total_quantity"] += record.quantity

    async def _persist_record(self, record: UsageRecord):
        """Persist record to storage backend"""
        if self.storage:
            try:
                # Implement storage-specific logic here
                pass
            except Exception as e:
                self.logger.error(f"Failed to persist usage record: {e}")

    def add_budget_limit(self, limit: BudgetLimit):
        """Add budget limit"""
        self.budget_limits.append(limit)
        self.logger.info(f"Added budget limit: ${limit.limit_amount} per {limit.period}")

    async def check_budget(
        self,
        cost: float,
        resource_type: ResourceType,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if operation is within budget

        Args:
            cost: Estimated cost of operation
            resource_type: Type of resource
            user_id: Optional user ID

        Returns:
            Dictionary with allowed status and details
        """
        for limit in self.budget_limits:
            # Check if limit applies
            if limit.user_id and limit.user_id != user_id:
                continue
            if limit.resource_types and resource_type not in limit.resource_types:
                continue

            # Get current usage for period
            current_usage = await self._get_usage_for_period(
                limit.period,
                resource_type,
                user_id
            )

            projected_usage = current_usage + cost
            usage_percent = projected_usage / limit.limit_amount

            # Check alert threshold
            if usage_percent >= limit.alert_threshold and usage_percent < 1.0:
                self.logger.warning(
                    f"Budget alert: {usage_percent*100:.1f}% of {limit.period} limit used "
                    f"(${projected_usage:.4f} / ${limit.limit_amount})"
                )

            # Check hard limit
            if limit.hard_limit and projected_usage > limit.limit_amount:
                return {
                    "allowed": False,
                    "reason": f"Budget limit exceeded for {limit.period}",
                    "current_usage": current_usage,
                    "limit": limit.limit_amount,
                    "projected_usage": projected_usage,
                    "usage_percent": usage_percent * 100
                }

        return {
            "allowed": True,
            "current_usage": await self._get_usage_for_period("daily", resource_type, user_id)
        }

    async def _get_usage_for_period(
        self,
        period: str,
        resource_type: Optional[ResourceType] = None,
        user_id: Optional[str] = None
    ) -> float:
        """Get total cost for time period"""
        now = datetime.utcnow()

        # Determine time range
        if period == "hourly":
            start_time = now - timedelta(hours=1)
        elif period == "daily":
            start_time = now - timedelta(days=1)
        elif period == "weekly":
            start_time = now - timedelta(weeks=1)
        elif period == "monthly":
            start_time = now - timedelta(days=30)
        else:  # total
            start_time = datetime.min

        # Sum costs
        total = 0.0
        for record in self.records:
            if record.timestamp < start_time:
                continue
            if user_id and record.user_id != user_id:
                continue
            if resource_type and record.resource_type != resource_type:
                continue
            total += record.cost

        return total

    async def get_usage_summary(
        self,
        period: str = "daily",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get usage summary

        Args:
            period: Time period (hourly, daily, weekly, monthly, total)
            user_id: Optional user ID filter

        Returns:
            Usage summary with breakdown by resource type
        """
        now = datetime.utcnow()

        # Determine time range
        if period == "hourly":
            start_time = now - timedelta(hours=1)
        elif period == "daily":
            start_time = now - timedelta(days=1)
        elif period == "weekly":
            start_time = now - timedelta(weeks=1)
        elif period == "monthly":
            start_time = now - timedelta(days=30)
        else:  # total
            start_time = datetime.min

        # Aggregate by resource type
        breakdown = defaultdict(lambda: {"quantity": 0.0, "cost": 0.0, "count": 0})
        total_cost = 0.0
        total_records = 0

        for record in self.records:
            if record.timestamp < start_time:
                continue
            if user_id and record.user_id != user_id:
                continue

            breakdown[record.resource_type.value]["quantity"] += record.quantity
            breakdown[record.resource_type.value]["cost"] += record.cost
            breakdown[record.resource_type.value]["count"] += 1
            total_cost += record.cost
            total_records += 1

        return {
            "period": period,
            "start_time": start_time.isoformat(),
            "end_time": now.isoformat(),
            "total_cost": total_cost,
            "total_records": total_records,
            "breakdown": dict(breakdown),
            "user_id": user_id
        }

    async def get_cost_forecast(
        self,
        period: str = "monthly",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Forecast costs based on current usage trends

        Args:
            period: Forecast period
            user_id: Optional user ID

        Returns:
            Cost forecast
        """
        # Get usage for last 7 days
        week_usage = await self.get_usage_summary("weekly", user_id)
        daily_average = week_usage["total_cost"] / 7

        # Calculate forecast
        if period == "monthly":
            forecast = daily_average * 30
        elif period == "weekly":
            forecast = daily_average * 7
        elif period == "daily":
            forecast = daily_average
        else:
            forecast = daily_average * 365  # yearly

        return {
            "period": period,
            "forecast_cost": forecast,
            "daily_average": daily_average,
            "current_trend": "increasing" if daily_average > 0 else "stable",
            "based_on_days": 7
        }

    def export_usage_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Export usage report as JSON"""
        filtered_records = []
        for record in self.records:
            if start_date and record.timestamp < start_date:
                continue
            if end_date and record.timestamp > end_date:
                continue
            if user_id and record.user_id != user_id:
                continue

            filtered_records.append({
                "timestamp": record.timestamp.isoformat(),
                "resource_type": record.resource_type.value,
                "quantity": record.quantity,
                "cost": record.cost,
                "provider": record.provider,
                "session_id": record.session_id,
                "user_id": record.user_id,
                "metadata": record.metadata
            })

        return json.dumps({
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "user_id": user_id,
            "record_count": len(filtered_records),
            "total_cost": sum(r["cost"] for r in filtered_records),
            "records": filtered_records
        }, indent=2)
