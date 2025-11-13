"""
Analytics and Monitoring System
Tracks system metrics, performance, and usage patterns
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """Individual metric data point"""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """System health status"""
    status: str  # healthy, degraded, unhealthy
    uptime_seconds: float
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    active_sessions: int = 0
    requests_per_minute: float = 0.0
    average_response_time_ms: float = 0.0
    error_rate_percent: float = 0.0
    agent_health: Dict[str, str] = field(default_factory=dict)
    llm_provider_health: Dict[str, str] = field(default_factory=dict)


class PerformanceTracker:
    """Tracks performance metrics"""

    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.logger = logging.getLogger(__name__)
        self.start_time = time.time()

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None
    ):
        """Record a metric"""
        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            timestamp=datetime.utcnow(),
            labels=labels or {}
        )

        self.metrics[name].append(metric)

        # Update aggregations
        if metric_type == MetricType.COUNTER:
            self.counters[name] += value
        elif metric_type == MetricType.GAUGE:
            self.gauges[name] = value

    def increment_counter(self, name: str, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter"""
        self.record_metric(name, amount, MetricType.COUNTER, labels)

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge value"""
        self.record_metric(name, value, MetricType.GAUGE, labels)

    def record_timer(self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None):
        """Record a timing metric"""
        self.record_metric(name, duration_ms, MetricType.TIMER, labels)

    def get_metric_stats(
        self,
        name: str,
        time_window_minutes: Optional[int] = None
    ) -> Dict[str, float]:
        """Get statistics for a metric"""
        if name not in self.metrics or not self.metrics[name]:
            return {}

        # Filter by time window
        metrics = list(self.metrics[name])
        if time_window_minutes:
            cutoff = datetime.utcnow() - timedelta(minutes=time_window_minutes)
            metrics = [m for m in metrics if m.timestamp >= cutoff]

        if not metrics:
            return {}

        values = [m.value for m in metrics]

        stats = {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values)
        }

        if len(values) > 1:
            stats["stddev"] = statistics.stdev(values)

        # Add percentiles
        sorted_values = sorted(values)
        stats["p50"] = sorted_values[len(sorted_values) // 2]
        stats["p95"] = sorted_values[int(len(sorted_values) * 0.95)]
        stats["p99"] = sorted_values[int(len(sorted_values) * 0.99)]

        return stats

    def get_counter(self, name: str) -> float:
        """Get counter value"""
        return self.counters.get(name, 0.0)

    def get_gauge(self, name: str) -> float:
        """Get gauge value"""
        return self.gauges.get(name, 0.0)

    def reset_counter(self, name: str):
        """Reset a counter"""
        self.counters[name] = 0.0

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "metrics": {name: list(metrics)[-100:] for name, metrics in self.metrics.items()}
        }


class RequestTracker:
    """Tracks API request metrics"""

    def __init__(self, window_minutes: int = 60):
        self.window_minutes = window_minutes
        self.requests: deque = deque(maxlen=10000)
        self.logger = logging.getLogger(__name__)

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Record API request"""
        self.requests.append({
            "timestamp": datetime.utcnow(),
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "error": error,
            "success": 200 <= status_code < 400
        })

    def get_stats(self, minutes: Optional[int] = None) -> Dict[str, Any]:
        """Get request statistics"""
        if minutes is None:
            minutes = self.window_minutes

        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        recent_requests = [r for r in self.requests if r["timestamp"] >= cutoff]

        if not recent_requests:
            return {
                "total_requests": 0,
                "requests_per_minute": 0.0,
                "success_rate": 0.0,
                "error_rate": 0.0,
                "average_duration_ms": 0.0
            }

        total = len(recent_requests)
        successful = sum(1 for r in recent_requests if r["success"])
        failed = total - successful

        durations = [r["duration_ms"] for r in recent_requests]

        # Requests by endpoint
        by_endpoint = defaultdict(int)
        by_status = defaultdict(int)
        for r in recent_requests:
            by_endpoint[r["endpoint"]] += 1
            by_status[r["status_code"]] += 1

        return {
            "total_requests": total,
            "successful_requests": successful,
            "failed_requests": failed,
            "requests_per_minute": total / minutes,
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
            "error_rate": (failed / total * 100) if total > 0 else 0.0,
            "average_duration_ms": statistics.mean(durations) if durations else 0.0,
            "median_duration_ms": statistics.median(durations) if durations else 0.0,
            "p95_duration_ms": sorted(durations)[int(len(durations) * 0.95)] if durations else 0.0,
            "by_endpoint": dict(by_endpoint),
            "by_status": dict(by_status)
        }

    def get_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors"""
        errors = [r for r in self.requests if not r["success"]]
        return sorted(errors, key=lambda x: x["timestamp"], reverse=True)[:limit]


class AgentAnalytics:
    """Analytics for agent performance"""

    def __init__(self):
        self.executions: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.logger = logging.getLogger(__name__)

    def record_execution(
        self,
        agent_name: str,
        task_type: str,
        duration_ms: float,
        success: bool,
        tokens_used: Optional[int] = None,
        cost: Optional[float] = None,
        error: Optional[str] = None
    ):
        """Record agent execution"""
        self.executions[agent_name].append({
            "timestamp": datetime.utcnow(),
            "task_type": task_type,
            "duration_ms": duration_ms,
            "success": success,
            "tokens_used": tokens_used,
            "cost": cost,
            "error": error
        })

    def get_agent_stats(self, agent_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get statistics for an agent"""
        if agent_name not in self.executions:
            return {}

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [e for e in self.executions[agent_name] if e["timestamp"] >= cutoff]

        if not recent:
            return {"total_executions": 0}

        total = len(recent)
        successful = sum(1 for e in recent if e["success"])
        failed = total - successful

        durations = [e["duration_ms"] for e in recent]
        tokens = [e["tokens_used"] for e in recent if e["tokens_used"]]
        costs = [e["cost"] for e in recent if e["cost"]]

        # Group by task type
        by_task = defaultdict(int)
        for e in recent:
            by_task[e["task_type"]] += 1

        return {
            "agent_name": agent_name,
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
            "average_duration_ms": statistics.mean(durations) if durations else 0.0,
            "median_duration_ms": statistics.median(durations) if durations else 0.0,
            "total_tokens_used": sum(tokens) if tokens else 0,
            "average_tokens_per_execution": statistics.mean(tokens) if tokens else 0,
            "total_cost": sum(costs) if costs else 0.0,
            "average_cost_per_execution": statistics.mean(costs) if costs else 0.0,
            "by_task_type": dict(by_task)
        }

    def get_all_agents_stats(self, hours: int = 24) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all agents"""
        return {
            agent_name: self.get_agent_stats(agent_name, hours)
            for agent_name in self.executions.keys()
        }


class MonitoringSystem:
    """Central monitoring and analytics system"""

    def __init__(self):
        self.performance = PerformanceTracker()
        self.requests = RequestTracker()
        self.agents = AgentAnalytics()
        self.start_time = time.time()
        self.logger = logging.getLogger(__name__)

        # System metrics
        self.active_sessions = set()
        self.llm_provider_status: Dict[str, bool] = {}

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Record API request"""
        self.requests.record_request(endpoint, method, status_code, duration_ms, user_id, error)
        self.performance.increment_counter("http_requests_total", labels={"endpoint": endpoint})
        self.performance.record_timer("http_request_duration_ms", duration_ms, labels={"endpoint": endpoint})

        if 200 <= status_code < 400:
            self.performance.increment_counter("http_requests_success")
        else:
            self.performance.increment_counter("http_requests_error")

    def record_agent_execution(
        self,
        agent_name: str,
        task_type: str,
        duration_ms: float,
        success: bool,
        tokens_used: Optional[int] = None,
        cost: Optional[float] = None,
        error: Optional[str] = None
    ):
        """Record agent execution"""
        self.agents.record_execution(agent_name, task_type, duration_ms, success, tokens_used, cost, error)
        self.performance.increment_counter(f"agent_executions_total", labels={"agent": agent_name})

        if success:
            self.performance.increment_counter(f"agent_executions_success", labels={"agent": agent_name})
        else:
            self.performance.increment_counter(f"agent_executions_error", labels={"agent": agent_name})

    def add_session(self, session_id: str):
        """Track active session"""
        self.active_sessions.add(session_id)
        self.performance.set_gauge("active_sessions", len(self.active_sessions))

    def remove_session(self, session_id: str):
        """Remove session"""
        self.active_sessions.discard(session_id)
        self.performance.set_gauge("active_sessions", len(self.active_sessions))

    def update_llm_provider_status(self, provider: str, healthy: bool):
        """Update LLM provider health status"""
        self.llm_provider_status[provider] = healthy

    async def get_system_health(self) -> SystemHealth:
        """Get overall system health"""
        uptime = time.time() - self.start_time
        request_stats = self.requests.get_stats(minutes=5)

        # Determine overall status
        error_rate = request_stats.get("error_rate", 0.0)
        if error_rate > 10:
            status = "unhealthy"
        elif error_rate > 5:
            status = "degraded"
        else:
            status = "healthy"

        # Get agent health
        agent_stats = self.agents.get_all_agents_stats(hours=1)
        agent_health = {}
        for agent_name, stats in agent_stats.items():
            if stats.get("total_executions", 0) > 0:
                success_rate = stats.get("success_rate", 0.0)
                if success_rate > 90:
                    agent_health[agent_name] = "healthy"
                elif success_rate > 70:
                    agent_health[agent_name] = "degraded"
                else:
                    agent_health[agent_name] = "unhealthy"

        # Get LLM provider health
        llm_health = {
            provider: "healthy" if healthy else "unhealthy"
            for provider, healthy in self.llm_provider_status.items()
        }

        return SystemHealth(
            status=status,
            uptime_seconds=uptime,
            active_sessions=len(self.active_sessions),
            requests_per_minute=request_stats.get("requests_per_minute", 0.0),
            average_response_time_ms=request_stats.get("average_duration_ms", 0.0),
            error_rate_percent=error_rate,
            agent_health=agent_health,
            llm_provider_health=llm_health
        )

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        return {
            "system_health": await self.get_system_health(),
            "request_stats": self.requests.get_stats(minutes=60),
            "recent_errors": self.requests.get_errors(limit=20),
            "agent_stats": self.agents.get_all_agents_stats(hours=24),
            "performance_metrics": self.performance.get_all_metrics(),
            "uptime_seconds": time.time() - self.start_time
        }

    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        if format == "prometheus":
            return self._export_prometheus()
        else:
            import json
            dashboard_data = asyncio.run(self.get_dashboard_data())
            # Convert datetime objects to strings
            return json.dumps(dashboard_data, default=str, indent=2)

    def _export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []

        # Counters
        for name, value in self.performance.counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")

        # Gauges
        for name, value in self.performance.gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")

        return "\n".join(lines)


# Global monitoring instance
_monitoring_instance: Optional[MonitoringSystem] = None


def get_monitoring() -> MonitoringSystem:
    """Get global monitoring instance"""
    global _monitoring_instance
    if _monitoring_instance is None:
        _monitoring_instance = MonitoringSystem()
    return _monitoring_instance
