"""
Infrastructure Integration Examples
Demonstrates combining Job Queue, Caching, and Event Systems

Real-world scenarios showing how to leverage all 3 infrastructure features together.
"""

import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json

# Import infrastructure components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.jobs import (
    get_job_manager, get_scheduled_jobs_manager,
    JobPriority, ScheduledJob
)
from core.cache import (
    get_cache_manager, get_llm_cache, get_embedding_cache,
    CacheNamespace
)
from core.events import (
    get_event_bus, get_webhook_manager, get_event_emitter,
    EventType
)


# ==================== Example 1: Cached Agent Execution with Webhooks ====================

async def example_cached_agent_with_notifications():
    """
    Scenario: Execute an expensive agent task, cache the result, and notify via webhook

    Benefits:
    - First execution runs the full agent (expensive)
    - Subsequent identical requests use cache (fast + cheap)
    - Webhook notifies external systems when agent completes
    - Cost savings tracked automatically
    """
    print("\n" + "="*70)
    print("Example 1: Cached Agent Execution with Webhook Notifications")
    print("="*70)

    # Setup
    job_manager = get_job_manager()
    llm_cache = get_llm_cache()
    webhook_manager = get_webhook_manager()
    event_emitter = get_event_emitter()

    # 1. Register webhook to receive agent completion notifications
    webhook = await webhook_manager.register_webhook(
        url="https://your-app.com/webhooks/agent-completed",
        events=[EventType.AGENT_COMPLETED],
        description="Notify app when agents finish"
    )
    print(f"✓ Registered webhook: {webhook.id}")
    print(f"  Secret: {webhook.secret[:20]}...")

    # 2. Define agent task parameters
    task_params = {
        "agent": "research_agent",
        "query": "Latest developments in quantum computing",
        "depth": "comprehensive"
    }

    # 3. Check cache first (using query as identifier)
    cache_key = json.dumps(task_params, sort_keys=True)
    cached_result = await llm_cache.get_response(
        prompt=cache_key,
        model="research_agent",
        temperature=0.0  # Deterministic for caching
    )

    if cached_result:
        print(f"✓ Cache HIT! Retrieved cached result (saved $0.50)")
        print(f"  Result preview: {cached_result[:100]}...")
        result = json.loads(cached_result)
    else:
        print(f"✗ Cache MISS. Submitting background job...")

        # 4. Submit job if cache miss
        job_id = job_manager.submit_job(
            task_name="execute_agent_async",
            args=[task_params["agent"]],
            kwargs={"query": task_params["query"], "depth": task_params["depth"]},
            priority=JobPriority.HIGH
        )
        print(f"✓ Job submitted: {job_id}")

        # 5. Wait for job completion (in production, use webhooks instead)
        print("  Waiting for job to complete...")
        await asyncio.sleep(5)  # Simulated wait

        # 6. Get result
        job_result = job_manager.get_job_status(job_id)
        result = job_result.result

        # 7. Cache the result for future requests
        await llm_cache.cache_response(
            prompt=cache_key,
            response=json.dumps(result),
            model="research_agent",
            temperature=0.0,
            ttl=86400  # Cache for 24 hours
        )
        print(f"✓ Result cached for 24 hours")

        # 8. Emit completion event (triggers webhook)
        await event_emitter.agent_completed(
            agent_name=task_params["agent"],
            result=result,
            duration_ms=5000,
            session_id="session_123"
        )
        print(f"✓ Event emitted - webhook will be triggered")

    # 9. Show cost savings
    savings = await llm_cache.get_cost_savings()
    print(f"\n💰 Total cost savings: ${savings['estimated_cost_saved_usd']:.2f}")
    print(f"   Cache hit rate: {savings['hit_rate_percent']:.1f}%")

    return result


# ==================== Example 2: Background Data Processing Pipeline ====================

async def example_background_pipeline_with_events():
    """
    Scenario: Multi-step data processing pipeline with progress tracking

    Benefits:
    - Each step runs as background job (non-blocking)
    - Events track progress through pipeline
    - Results cached at each step
    - Failures trigger retry automatically
    """
    print("\n" + "="*70)
    print("Example 2: Background Data Processing Pipeline")
    print("="*70)

    job_manager = get_job_manager()
    cache_manager = get_cache_manager()
    event_bus = get_event_bus()

    # Subscribe to pipeline events
    pipeline_events = []

    async def track_event(event):
        pipeline_events.append(event)
        print(f"📊 Event: {event.type.value} - {event.data}")

    event_bus.subscribe(EventType.WORKFLOW_STEP_COMPLETED, track_event)

    # Pipeline: Upload → Extract → Process → Analyze → Report
    pipeline_steps = [
        ("upload_file", {"file": "data.csv", "size": "10MB"}),
        ("extract_data", {"format": "csv", "rows": 100000}),
        ("process_data", {"operations": ["clean", "transform", "enrich"]}),
        ("analyze_data", {"models": ["regression", "clustering"]}),
        ("generate_report", {"format": "pdf", "sections": ["summary", "insights"]})
    ]

    results = {}

    for step_name, step_params in pipeline_steps:
        print(f"\n→ Step: {step_name}")

        # Check cache for this step
        cached_result = await cache_manager.get(
            CacheNamespace.QUERY_RESULTS,
            step_name,
            params=step_params
        )

        if cached_result:
            print(f"  ✓ Using cached result")
            results[step_name] = cached_result
        else:
            # Submit background job
            job_id = job_manager.submit_job(
                task_name=f"process_{step_name}",
                kwargs=step_params,
                priority=JobPriority.NORMAL
            )
            print(f"  ✓ Job submitted: {job_id}")

            # Simulate job execution
            await asyncio.sleep(2)

            # Get result and cache it
            job_result = job_manager.get_job_status(job_id)
            results[step_name] = job_result.result

            await cache_manager.set(
                CacheNamespace.QUERY_RESULTS,
                step_name,
                results[step_name],
                ttl=3600,
                params=step_params
            )
            print(f"  ✓ Result cached")

    print(f"\n✅ Pipeline completed! {len(pipeline_events)} events tracked")
    return results


# ==================== Example 3: Real-Time Analytics with Event Streaming ====================

async def example_realtime_analytics_dashboard():
    """
    Scenario: Real-time analytics dashboard tracking system events

    Benefits:
    - Events stream in real-time
    - Metrics cached for fast dashboard loads
    - Webhooks push updates to frontend
    - Historical data available
    """
    print("\n" + "="*70)
    print("Example 3: Real-Time Analytics Dashboard")
    print("="*70)

    event_bus = get_event_bus()
    cache_manager = get_cache_manager()
    webhook_manager = get_webhook_manager()
    event_emitter = get_event_emitter()

    # Register webhook for dashboard updates
    dashboard_webhook = await webhook_manager.register_webhook(
        url="https://dashboard.example.com/api/events",
        events=[
            EventType.AGENT_STARTED,
            EventType.AGENT_COMPLETED,
            EventType.AGENT_FAILED,
            EventType.BUDGET_WARNING
        ],
        description="Dashboard real-time updates"
    )
    print(f"✓ Dashboard webhook registered: {dashboard_webhook.id}")

    # Track metrics
    metrics = {
        "agents_started": 0,
        "agents_completed": 0,
        "agents_failed": 0,
        "total_cost_usd": 0.0,
        "avg_duration_ms": 0.0
    }

    durations = []

    # Event handlers
    async def on_agent_started(event):
        metrics["agents_started"] += 1
        print(f"  🟢 Agent started: {event.data.get('agent')}")

    async def on_agent_completed(event):
        metrics["agents_completed"] += 1
        duration = event.data.get('duration_ms', 0)
        durations.append(duration)
        metrics["avg_duration_ms"] = sum(durations) / len(durations)
        print(f"  ✅ Agent completed: {event.data.get('agent')} ({duration}ms)")

    async def on_agent_failed(event):
        metrics["agents_failed"] += 1
        print(f"  ❌ Agent failed: {event.data.get('agent')}")

    # Subscribe to events
    event_bus.subscribe(EventType.AGENT_STARTED, on_agent_started)
    event_bus.subscribe(EventType.AGENT_COMPLETED, on_agent_completed)
    event_bus.subscribe(EventType.AGENT_FAILED, on_agent_failed)

    # Simulate agent activity
    print("\nSimulating agent activity...")
    for i in range(10):
        await event_emitter.agent_started(
            agent_name=f"agent_{i % 3}",
            task={"query": f"task_{i}"},
            session_id=f"session_{i}"
        )

        await asyncio.sleep(0.5)

        if i % 5 == 0:  # Simulate failure every 5th agent
            await event_emitter.emit(
                EventType.AGENT_FAILED,
                data={"agent": f"agent_{i % 3}", "error": "Timeout"},
                session_id=f"session_{i}"
            )
        else:
            await event_emitter.agent_completed(
                agent_name=f"agent_{i % 3}",
                result={"output": "success"},
                duration_ms=1000 + (i * 100),
                session_id=f"session_{i}"
            )

    # Cache metrics for dashboard
    await cache_manager.set(
        CacheNamespace.ANALYTICS,
        "dashboard_metrics",
        metrics,
        ttl=60  # Cache for 1 minute
    )

    print(f"\n📊 Dashboard Metrics:")
    print(f"   Agents Started: {metrics['agents_started']}")
    print(f"   Agents Completed: {metrics['agents_completed']}")
    print(f"   Agents Failed: {metrics['agents_failed']}")
    print(f"   Success Rate: {(metrics['agents_completed'] / metrics['agents_started'] * 100):.1f}%")
    print(f"   Avg Duration: {metrics['avg_duration_ms']:.0f}ms")

    return metrics


# ==================== Example 4: Scheduled Reports with Caching ====================

async def example_scheduled_reports():
    """
    Scenario: Generate daily reports using scheduled jobs and caching

    Benefits:
    - Reports generated automatically via scheduler
    - Previous reports cached for instant access
    - Events notify stakeholders when ready
    - Cost-efficient (cache hits save computation)
    """
    print("\n" + "="*70)
    print("Example 4: Scheduled Reports with Caching")
    print("="*70)

    scheduled_manager = get_scheduled_jobs_manager()
    cache_manager = get_cache_manager()
    webhook_manager = get_webhook_manager()

    # Register webhook for report notifications
    report_webhook = await webhook_manager.register_webhook(
        url="https://example.com/webhooks/report-ready",
        events=[EventType.CUSTOM],
        description="Notify when reports are ready"
    )
    print(f"✓ Report webhook registered: {report_webhook.id}")

    # Create scheduled jobs for different reports
    schedules = [
        {
            "name": "daily_usage_report",
            "task": "generate_report",
            "schedule": "0 2 * * *",  # 2 AM daily
            "description": "Daily usage statistics",
            "report_type": "usage"
        },
        {
            "name": "weekly_performance_report",
            "task": "generate_report",
            "schedule": "0 3 * * 1",  # 3 AM every Monday
            "description": "Weekly performance analysis",
            "report_type": "performance"
        },
        {
            "name": "monthly_cost_report",
            "task": "generate_report",
            "schedule": "0 4 1 * *",  # 4 AM first day of month
            "description": "Monthly cost breakdown",
            "report_type": "cost"
        }
    ]

    for schedule_config in schedules:
        scheduled_job = ScheduledJob(
            name=schedule_config["name"],
            task=schedule_config["task"],
            schedule=schedule_config["schedule"],
            kwargs={
                "report_type": schedule_config["report_type"],
                "parameters": {"period": "latest"}
            },
            description=schedule_config["description"]
        )

        scheduled_manager.add_schedule(scheduled_job)
        print(f"✓ Scheduled: {schedule_config['name']}")
        print(f"  Schedule: {schedule_config['schedule']}")
        print(f"  Description: {schedule_config['description']}")

    # Simulate report access (check cache first)
    report_types = ["usage", "performance", "cost"]

    print("\nAccessing reports...")
    for report_type in report_types:
        # Try cache first
        cached_report = await cache_manager.get(
            CacheNamespace.QUERY_RESULTS,
            f"report_{report_type}",
            params={"date": datetime.utcnow().date().isoformat()}
        )

        if cached_report:
            print(f"  ✓ {report_type.title()} Report: Loaded from cache (instant)")
        else:
            print(f"  ⏳ {report_type.title()} Report: Generating... (first time)")
            # Report would be generated and cached

    return schedules


# ==================== Example 5: Multi-Tenant System with Isolation ====================

async def example_multitenant_architecture():
    """
    Scenario: Multi-tenant system with per-tenant job queues and caching

    Benefits:
    - Isolated job queues per tenant
    - Separate cache namespaces
    - Per-tenant webhooks
    - Resource usage tracking per tenant
    """
    print("\n" + "="*70)
    print("Example 5: Multi-Tenant Architecture")
    print("="*70)

    job_manager = get_job_manager()
    cache_manager = get_cache_manager()
    webhook_manager = get_webhook_manager()
    event_bus = get_event_bus()

    tenants = [
        {"id": "tenant_acme", "name": "ACME Corp", "tier": "enterprise"},
        {"id": "tenant_globex", "name": "Globex Inc", "tier": "professional"},
        {"id": "tenant_initech", "name": "Initech", "tier": "starter"}
    ]

    for tenant in tenants:
        print(f"\n🏢 Setting up: {tenant['name']} ({tenant['tier']})")

        # 1. Register tenant-specific webhook
        webhook = await webhook_manager.register_webhook(
            url=f"https://{tenant['id']}.example.com/webhooks",
            events=[
                EventType.AGENT_COMPLETED,
                EventType.BUDGET_WARNING,
                EventType.SYSTEM_ERROR
            ],
            description=f"Webhooks for {tenant['name']}",
            headers={"X-Tenant-ID": tenant['id']}
        )
        print(f"  ✓ Webhook: {webhook.id}")

        # 2. Submit tenant-specific jobs
        job_id = job_manager.submit_job(
            task_name="execute_agent_async",
            kwargs={
                "agent": "research_agent",
                "query": f"Market analysis for {tenant['name']}",
                "tenant_id": tenant['id']
            },
            priority=JobPriority.HIGH if tenant['tier'] == 'enterprise' else JobPriority.NORMAL
        )
        print(f"  ✓ Job submitted: {job_id} (priority: {tenant['tier']})")

        # 3. Set up tenant-specific cache
        tenant_data = {
            "tenant_id": tenant['id'],
            "settings": {"max_agents": 10 if tenant['tier'] == 'enterprise' else 5},
            "usage": {"agents_run": 42, "cost_usd": 15.50}
        }

        await cache_manager.set(
            CacheNamespace.USER_SESSIONS,
            tenant['id'],
            tenant_data,
            ttl=3600
        )
        print(f"  ✓ Tenant data cached")

    # Show tenant isolation
    print("\n📊 Tenant Isolation Verification:")
    for tenant in tenants:
        cached_data = await cache_manager.get(
            CacheNamespace.USER_SESSIONS,
            tenant['id']
        )
        if cached_data:
            print(f"  {tenant['name']}: {cached_data['usage']['agents_run']} agents run")

    return tenants


# ==================== Example 6: Cost Optimization Strategy ====================

async def example_cost_optimization():
    """
    Scenario: Aggressive cost optimization using caching and job prioritization

    Benefits:
    - 80%+ cost reduction through intelligent caching
    - Job prioritization saves money on rate limits
    - Budget tracking prevents overspending
    - Cost analytics show ROI
    """
    print("\n" + "="*70)
    print("Example 6: Cost Optimization Strategy")
    print("="*70)

    llm_cache = get_llm_cache()
    embedding_cache = get_embedding_cache()
    job_manager = get_job_manager()
    event_emitter = get_event_emitter()

    # Common queries that will benefit from caching
    common_queries = [
        "What is artificial intelligence?",
        "Explain machine learning",
        "What are neural networks?",
        "Define deep learning",
        "What is NLP?"
    ]

    print("Simulating LLM requests with caching...")

    total_cost_without_cache = 0.0
    total_cost_with_cache = 0.0
    cache_hits = 0
    cache_misses = 0

    # Simulate 100 requests (many repeated)
    import random
    for i in range(100):
        query = random.choice(common_queries)

        # Check cache
        cached_response = await llm_cache.get_response(
            prompt=query,
            model="gpt-4",
            temperature=0.7
        )

        cost_per_request = 0.01  # $0.01 per LLM call

        if cached_response:
            cache_hits += 1
            # Cache hit costs nothing
        else:
            cache_misses += 1
            total_cost_with_cache += cost_per_request

            # Simulate LLM call and cache response
            response = f"Response to: {query}"
            await llm_cache.cache_response(
                prompt=query,
                response=response,
                model="gpt-4",
                temperature=0.7,
                ttl=86400
            )

        total_cost_without_cache += cost_per_request

    # Calculate savings
    savings = total_cost_without_cache - total_cost_with_cache
    savings_percent = (savings / total_cost_without_cache) * 100

    print(f"\n💰 Cost Analysis (100 requests):")
    print(f"   Without caching: ${total_cost_without_cache:.2f}")
    print(f"   With caching: ${total_cost_with_cache:.2f}")
    print(f"   💎 Savings: ${savings:.2f} ({savings_percent:.1f}%)")
    print(f"   Cache hits: {cache_hits}")
    print(f"   Cache misses: {cache_misses}")
    print(f"   Hit rate: {(cache_hits / 100) * 100:.1f}%")

    # Emit budget warning if approaching limit
    if total_cost_with_cache > 0.50:  # $0.50 threshold
        await event_emitter.budget_warning(
            user_id="system",
            current_usage=total_cost_with_cache,
            limit=1.00,
            period="daily"
        )
        print(f"\n⚠️  Budget warning emitted (${total_cost_with_cache:.2f} / $1.00)")

    return {
        "total_cost_without_cache": total_cost_without_cache,
        "total_cost_with_cache": total_cost_with_cache,
        "savings": savings,
        "savings_percent": savings_percent,
        "cache_hit_rate": (cache_hits / 100) * 100
    }


# ==================== Run All Examples ====================

async def run_all_examples():
    """Run all integration examples"""
    print("\n" + "="*70)
    print("MANUS AI - INFRASTRUCTURE INTEGRATION EXAMPLES")
    print("="*70)
    print("\nDemonstrating: Job Queue + Caching + Event System")
    print("="*70)

    examples = [
        ("Cached Agent with Webhooks", example_cached_agent_with_notifications),
        ("Background Pipeline", example_background_pipeline_with_events),
        ("Real-Time Analytics", example_realtime_analytics_dashboard),
        ("Scheduled Reports", example_scheduled_reports),
        ("Multi-Tenant System", example_multitenant_architecture),
        ("Cost Optimization", example_cost_optimization)
    ]

    results = {}

    for name, example_func in examples:
        try:
            result = await example_func()
            results[name] = result
            print(f"\n✅ {name} completed successfully!")
        except Exception as e:
            print(f"\n❌ {name} failed: {e}")
            results[name] = {"error": str(e)}

        await asyncio.sleep(1)  # Brief pause between examples

    print("\n" + "="*70)
    print("ALL EXAMPLES COMPLETED")
    print("="*70)

    return results


if __name__ == "__main__":
    # Run examples
    print("Starting infrastructure integration examples...")
    print("Note: This demo uses mock data. In production, connect to real services.")

    results = asyncio.run(run_all_examples())

    print("\n📊 Summary:")
    print(f"   Examples run: {len(results)}")
    print(f"   Successful: {sum(1 for r in results.values() if 'error' not in r)}")
    print(f"   Failed: {sum(1 for r in results.values() if 'error' in r)}")
