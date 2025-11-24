#!/usr/bin/env python3
"""
Manus AI Infrastructure CLI
Command-line tool for managing infrastructure components
"""

import click
import asyncio
import json
import sys
from typing import Optional, List
from datetime import datetime
from tabulate import tabulate

# Import infrastructure managers
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.jobs import get_job_manager, get_scheduled_jobs_manager, JobPriority, ScheduledJob
from core.cache import get_cache_manager, get_llm_cache, CacheNamespace
from core.events import get_webhook_manager, get_event_bus, EventType


@click.group()
@click.version_option(version='2.0.0', prog_name='manus-cli')
def cli():
    """Manus AI Infrastructure Management CLI"""
    pass


# ==================== Job Queue Commands ====================

@cli.group()
def jobs():
    """Manage background jobs and task queue"""
    pass


@jobs.command('list')
@click.option('--limit', default=20, help='Number of jobs to list')
def list_jobs(limit):
    """List active jobs"""
    try:
        manager = get_job_manager()
        active_jobs = manager.get_active_jobs()

        if not active_jobs:
            click.echo("No active jobs")
            return

        table_data = []
        for job in active_jobs[:limit]:
            table_data.append([
                job.get('job_id', 'N/A')[:12],
                job.get('task', 'N/A'),
                job.get('worker', 'N/A'),
                job.get('status', 'N/A')
            ])

        headers = ['Job ID', 'Task', 'Worker', 'Status']
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
        click.echo(f"\nTotal active jobs: {len(active_jobs)}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@jobs.command('status')
@click.argument('job_id')
def job_status(job_id):
    """Get detailed job status"""
    try:
        manager = get_job_manager()
        result = manager.get_job_status(job_id)

        click.echo(f"\n{'='*60}")
        click.echo(f"Job Status: {job_id}")
        click.echo(f"{'='*60}")
        click.echo(f"Status: {result.status.value}")

        if result.started_at:
            click.echo(f"Started: {result.started_at}")
        if result.completed_at:
            click.echo(f"Completed: {result.completed_at}")
            duration = (result.completed_at - result.started_at).total_seconds()
            click.echo(f"Duration: {duration:.2f}s")

        if result.result:
            click.echo(f"\nResult:")
            click.echo(json.dumps(result.result, indent=2))

        if result.error:
            click.echo(f"\nError: {result.error}")

        if result.retries > 0:
            click.echo(f"\nRetries: {result.retries}")

        click.echo(f"{'='*60}\n")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@jobs.command('submit')
@click.option('--task', required=True, help='Task name')
@click.option('--priority', type=click.Choice(['critical', 'high', 'normal', 'low']), default='normal')
@click.option('--args', help='JSON array of positional arguments')
@click.option('--kwargs', help='JSON object of keyword arguments')
def submit_job(task, priority, args, kwargs):
    """Submit a new background job"""
    try:
        manager = get_job_manager()

        # Parse arguments
        task_args = json.loads(args) if args else []
        task_kwargs = json.loads(kwargs) if kwargs else {}

        # Map priority
        priority_map = {
            'critical': JobPriority.CRITICAL,
            'high': JobPriority.HIGH,
            'normal': JobPriority.NORMAL,
            'low': JobPriority.LOW
        }

        job_id = manager.submit_job(
            task_name=task,
            args=tuple(task_args),
            kwargs=task_kwargs,
            priority=priority_map[priority]
        )

        click.echo(f"✓ Job submitted successfully")
        click.echo(f"Job ID: {job_id}")
        click.echo(f"\nCheck status with: manus-cli jobs status {job_id}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@jobs.command('cancel')
@click.argument('job_id')
@click.confirmation_option(prompt='Are you sure you want to cancel this job?')
def cancel_job(job_id):
    """Cancel a pending or running job"""
    try:
        manager = get_job_manager()
        success = manager.cancel_job(job_id)

        if success:
            click.echo(f"✓ Job {job_id} cancelled successfully")
        else:
            click.echo(f"✗ Failed to cancel job {job_id}")
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@jobs.command('stats')
def job_stats():
    """Show job queue statistics"""
    try:
        manager = get_job_manager()
        stats = manager.get_queue_stats()

        click.echo(f"\n{'='*60}")
        click.echo(f"Job Queue Statistics")
        click.echo(f"{'='*60}")
        click.echo(f"Workers: {stats.get('workers', 0)}")
        click.echo(f"Active Jobs: {stats.get('active_jobs', 0)}")

        if 'stats' in stats:
            click.echo(f"\nDetailed Stats:")
            for key, value in stats['stats'].items():
                click.echo(f"  {key}: {value}")

        click.echo(f"{'='*60}\n")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@jobs.command('schedule')
@click.option('--name', required=True, help='Schedule name')
@click.option('--task', required=True, help='Task to schedule')
@click.option('--cron', required=True, help='Cron expression (e.g., "0 2 * * *")')
@click.option('--description', help='Schedule description')
def create_schedule(name, task, cron, description):
    """Create a scheduled job"""
    try:
        manager = get_scheduled_jobs_manager()

        schedule = ScheduledJob(
            name=name,
            task=task,
            schedule=cron,
            description=description or f"Scheduled task: {task}"
        )

        manager.add_schedule(schedule)
        click.echo(f"✓ Schedule '{name}' created successfully")
        click.echo(f"Task: {task}")
        click.echo(f"Schedule: {cron}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@jobs.command('schedules')
def list_schedules():
    """List all scheduled jobs"""
    try:
        manager = get_scheduled_jobs_manager()
        schedules = manager.list_schedules()

        if not schedules:
            click.echo("No scheduled jobs")
            return

        table_data = []
        for schedule in schedules:
            table_data.append([
                schedule.get('name', 'N/A'),
                schedule.get('task', 'N/A'),
                schedule.get('schedule', 'N/A'),
                schedule.get('description', 'N/A')[:40]
            ])

        headers = ['Name', 'Task', 'Cron', 'Description']
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ==================== Cache Commands ====================

@cli.group()
def cache():
    """Manage caching layer"""
    pass


@cache.command('stats')
def cache_stats():
    """Show cache statistics"""
    async def _stats():
        try:
            manager = get_cache_manager()
            stats = await manager.get_stats()

            click.echo(f"\n{'='*60}")
            click.echo(f"Cache Statistics")
            click.echo(f"{'='*60}")
            click.echo(f"Hits: {stats.hits:,}")
            click.echo(f"Misses: {stats.misses:,}")
            click.echo(f"Hit Rate: {stats.hit_rate:.2f}%")
            click.echo(f"Total Keys: {stats.total_keys:,}")
            click.echo(f"Memory Used: {stats.memory_used_mb:.2f} MB")
            click.echo(f"Evictions: {stats.evictions:,}")

            # Calculate efficiency
            total_requests = stats.hits + stats.misses
            if total_requests > 0:
                click.echo(f"\nCache Efficiency:")
                click.echo(f"  Total Requests: {total_requests:,}")
                click.echo(f"  Served from Cache: {stats.hits:,} ({stats.hit_rate:.1f}%)")

            click.echo(f"{'='*60}\n")

        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    asyncio.run(_stats())


@cache.command('llm-savings')
def llm_savings():
    """Show LLM cost savings from caching"""
    async def _savings():
        try:
            llm_cache = get_llm_cache()
            savings = await llm_cache.get_cost_savings()

            click.echo(f"\n{'='*60}")
            click.echo(f"LLM Cost Savings")
            click.echo(f"{'='*60}")
            click.echo(f"Cache Hits: {savings['cache_hits']:,}")
            click.echo(f"Cache Misses: {savings['cache_misses']:,}")
            click.echo(f"Hit Rate: {savings['hit_rate_percent']:.2f}%")
            click.echo(f"💰 Estimated Cost Saved: ${savings['estimated_cost_saved_usd']:.2f}")

            # Monthly projection
            monthly_savings = savings['estimated_cost_saved_usd'] * 30
            click.echo(f"📊 Monthly Projection: ${monthly_savings:.2f}")

            click.echo(f"{'='*60}\n")

        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    asyncio.run(_savings())


@cache.command('clear')
@click.option('--namespace', type=click.Choice([ns.value for ns in CacheNamespace]), help='Namespace to clear')
@click.confirmation_option(prompt='Are you sure you want to clear the cache?')
def clear_cache(namespace):
    """Clear cache namespace"""
    async def _clear():
        try:
            manager = get_cache_manager()

            if namespace:
                ns = CacheNamespace(namespace)
                keys_cleared = await manager.clear_namespace(ns)
                click.echo(f"✓ Cleared {keys_cleared} keys from namespace '{namespace}'")
            else:
                # Clear all namespaces
                total_cleared = 0
                for ns in CacheNamespace:
                    keys_cleared = await manager.clear_namespace(ns)
                    total_cleared += keys_cleared
                    if keys_cleared > 0:
                        click.echo(f"  {ns.value}: {keys_cleared} keys")
                click.echo(f"\n✓ Total cleared: {total_cleared} keys")

        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    asyncio.run(_clear())


# ==================== Webhook Commands ====================

@cli.group()
def webhooks():
    """Manage webhooks and events"""
    pass


@webhooks.command('list')
@click.option('--active-only', is_flag=True, help='Show only active webhooks')
def list_webhooks(active_only):
    """List registered webhooks"""
    async def _list():
        try:
            manager = get_webhook_manager()
            hooks = manager.list_webhooks(active_only=active_only)

            if not hooks:
                click.echo("No webhooks registered")
                return

            table_data = []
            for hook in hooks:
                events_str = ', '.join([e.value for e in hook.events])[:40]
                table_data.append([
                    hook.id[:12],
                    hook.url[:40],
                    '✓' if hook.active else '✗',
                    events_str,
                    hook.description[:30] if hook.description else 'N/A'
                ])

            headers = ['ID', 'URL', 'Active', 'Events', 'Description']
            click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
            click.echo(f"\nTotal: {len(hooks)} webhooks")

        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    asyncio.run(_list())


@webhooks.command('register')
@click.option('--url', required=True, help='Webhook URL')
@click.option('--events', required=True, help='Comma-separated event types')
@click.option('--description', help='Webhook description')
def register_webhook(url, events, description):
    """Register a new webhook"""
    async def _register():
        try:
            manager = get_webhook_manager()

            # Parse events
            event_types = []
            for event_str in events.split(','):
                event_str = event_str.strip()
                try:
                    event_type = EventType(event_str)
                    event_types.append(event_type)
                except ValueError:
                    click.echo(f"Warning: Unknown event type '{event_str}', skipping")

            if not event_types:
                click.echo("Error: No valid event types specified", err=True)
                sys.exit(1)

            webhook = await manager.register_webhook(
                url=url,
                events=event_types,
                description=description or f"Webhook for {url}"
            )

            click.echo(f"✓ Webhook registered successfully")
            click.echo(f"ID: {webhook.id}")
            click.echo(f"URL: {webhook.url}")
            click.echo(f"Secret: {webhook.secret}")
            click.echo(f"Events: {', '.join([e.value for e in webhook.events])}")
            click.echo(f"\n⚠️  Save the secret - it won't be shown again!")

        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    asyncio.run(_register())


@webhooks.command('delete')
@click.argument('webhook_id')
@click.confirmation_option(prompt='Are you sure you want to delete this webhook?')
def delete_webhook(webhook_id):
    """Delete a webhook"""
    async def _delete():
        try:
            manager = get_webhook_manager()
            success = await manager.unregister_webhook(webhook_id)

            if success:
                click.echo(f"✓ Webhook {webhook_id} deleted successfully")
            else:
                click.echo(f"✗ Failed to delete webhook {webhook_id}")
                sys.exit(1)

        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    asyncio.run(_delete())


@webhooks.command('deliveries')
@click.argument('webhook_id')
@click.option('--limit', default=20, help='Number of deliveries to show')
def webhook_deliveries(webhook_id, limit):
    """Show webhook delivery history"""
    try:
        manager = get_webhook_manager()
        deliveries = manager.get_webhook_deliveries(webhook_id, limit=limit)

        if not deliveries:
            click.echo("No deliveries found")
            return

        table_data = []
        for delivery in deliveries:
            table_data.append([
                delivery.id[:12],
                delivery.event_id[:12],
                delivery.status.value,
                delivery.response_code if delivery.response_code else 'N/A',
                delivery.attempts,
                delivery.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])

        headers = ['Delivery ID', 'Event ID', 'Status', 'Response', 'Attempts', 'Created']
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@webhooks.command('events')
@click.option('--limit', default=20, help='Number of events to show')
def event_history(limit):
    """Show recent events"""
    try:
        bus = get_event_bus()
        events = bus.get_event_history(limit=limit)

        if not events:
            click.echo("No events in history")
            return

        table_data = []
        for event in events:
            data_preview = json.dumps(event.data)[:40] if event.data else 'N/A'
            table_data.append([
                event.id[:12],
                event.type.value,
                event.user_id[:12] if event.user_id else 'system',
                data_preview,
                event.timestamp.strftime('%H:%M:%S')
            ])

        headers = ['Event ID', 'Type', 'User', 'Data', 'Time']
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ==================== System Commands ====================

@cli.command('health')
def system_health():
    """Check system health"""
    async def _health():
        try:
            health = {"timestamp": datetime.utcnow().isoformat()}

            # Check cache
            try:
                cache = get_cache_manager()
                stats = await cache.get_stats()
                health["cache"] = f"✓ {stats.total_keys} keys, {stats.hit_rate:.1f}% hit rate"
            except Exception as e:
                health["cache"] = f"✗ Error: {e}"

            # Check job queue
            try:
                jobs_mgr = get_job_manager()
                stats = jobs_mgr.get_queue_stats()
                health["jobs"] = f"✓ {stats.get('workers', 0)} workers, {stats.get('active_jobs', 0)} active"
            except Exception as e:
                health["jobs"] = f"✗ Error: {e}"

            # Check events
            try:
                event_bus = get_event_bus()
                event_count = len(event_bus.event_history)
                health["events"] = f"✓ {event_count} events in history"
            except Exception as e:
                health["events"] = f"✗ Error: {e}"

            # Check webhooks
            try:
                webhook_mgr = get_webhook_manager()
                hooks = webhook_mgr.list_webhooks(active_only=True)
                health["webhooks"] = f"✓ {len(hooks)} active webhooks"
            except Exception as e:
                health["webhooks"] = f"✗ Error: {e}"

            click.echo(f"\n{'='*60}")
            click.echo(f"Manus AI System Health")
            click.echo(f"{'='*60}")
            for component, status in health.items():
                click.echo(f"{component.title()}: {status}")
            click.echo(f"{'='*60}\n")

        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    asyncio.run(_health())


@cli.command('info')
def system_info():
    """Show system information"""
    click.echo(f"\n{'='*60}")
    click.echo(f"Manus AI v2.0.0 - Infrastructure CLI")
    click.echo(f"{'='*60}")
    click.echo(f"Enterprise-grade autonomous AI platform")
    click.echo(f"")
    click.echo(f"Components:")
    click.echo(f"  • Job Queue (Celery)")
    click.echo(f"  • Caching Layer (Redis)")
    click.echo(f"  • Event & Webhook System")
    click.echo(f"")
    click.echo(f"Documentation: INFRASTRUCTURE_GUIDE.md")
    click.echo(f"{'='*60}\n")


if __name__ == '__main__':
    cli()
