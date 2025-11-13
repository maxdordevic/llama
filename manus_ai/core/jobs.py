"""
Background Job Queue System using Celery
Handles async tasks, scheduled jobs, and long-running operations
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import json

try:
    from celery import Celery, Task, states
    from celery.result import AsyncResult
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    STARTED = "started"
    RETRY = "retry"
    FAILURE = "failure"
    SUCCESS = "success"
    REVOKED = "revoked"


class JobPriority(int, Enum):
    """Job priority levels"""
    LOW = 1
    NORMAL = 5
    HIGH = 7
    CRITICAL = 9


@dataclass
class JobResult:
    """Job execution result"""
    job_id: str
    status: JobStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduledJob:
    """Scheduled job configuration"""
    name: str
    task: str
    schedule: str  # Cron expression
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    description: str = ""


# Initialize Celery app
def create_celery_app(
    broker_url: str = "redis://localhost:6379/0",
    backend_url: str = "redis://localhost:6379/1"
) -> Celery:
    """Create and configure Celery application"""

    app = Celery(
        "manus_ai_worker",
        broker=broker_url,
        backend=backend_url
    )

    # Configure Celery
    app.conf.update(
        # Task settings
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,

        # Result backend settings
        result_expires=3600,  # Results expire after 1 hour
        result_backend_transport_options={
            'master_name': 'mymaster',
        },

        # Task execution settings
        task_acks_late=True,  # Acknowledge after task completes
        task_reject_on_worker_lost=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour hard limit
        task_soft_time_limit=3000,  # 50 minutes soft limit

        # Worker settings
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,

        # Beat (scheduler) settings
        beat_schedule={},

        # Broker settings
        broker_connection_retry_on_startup=True,
        broker_connection_retry=True,
        broker_connection_max_retries=10,
    )

    return app


# Global Celery app instance
celery_app = None


def get_celery_app() -> Celery:
    """Get or create Celery app instance"""
    global celery_app
    if celery_app is None:
        import os
        broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        backend_url = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
        celery_app = create_celery_app(broker_url, backend_url)
    return celery_app


# ==================== Task Definitions ====================

class BaseTask(Task):
    """Base task class with common functionality"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"Task {task_id} failed: {exc}")
        # Could send notification, update database, etc.

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry"""
        logger.warning(f"Task {task_id} retrying: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        logger.info(f"Task {task_id} completed successfully")


# Agent Execution Tasks
@celery_app.task(base=BaseTask, bind=True, max_retries=3)
def execute_agent_async(self, agent_name: str, task_params: Dict[str, Any]):
    """
    Execute agent asynchronously

    Args:
        agent_name: Name of agent to execute
        task_params: Task parameters

    Returns:
        Agent execution result
    """
    try:
        from ..core.orchestrator import Orchestrator

        logger.info(f"Executing agent: {agent_name}")

        orchestrator = Orchestrator()
        result = orchestrator.execute_agent(agent_name, task_params)

        return {
            "status": "success",
            "agent": agent_name,
            "result": result
        }

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


# Workflow Execution Tasks
@celery_app.task(base=BaseTask, bind=True, max_retries=2)
def execute_workflow_async(self, template_id: str, input_data: Dict[str, Any]):
    """Execute workflow asynchronously"""
    try:
        from ..core.workflows import get_workflow_library, WorkflowEngine

        library = get_workflow_library()
        engine = WorkflowEngine()

        template = library.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        execution = engine.execute_workflow(template, input_data)

        return {
            "status": "success",
            "execution_id": execution.execution_id,
            "result": execution.output_data
        }

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise self.retry(exc=e, countdown=120)


# Data Processing Tasks
@celery_app.task(base=BaseTask, bind=True)
def process_large_file(self, file_path: str, processing_type: str):
    """Process large file asynchronously"""
    try:
        logger.info(f"Processing file: {file_path}")

        # Simulated file processing
        time.sleep(5)  # Simulate work

        return {
            "status": "success",
            "file_path": file_path,
            "processing_type": processing_type,
            "records_processed": 10000
        }

    except Exception as e:
        logger.error(f"File processing failed: {e}")
        raise


# Report Generation Tasks
@celery_app.task(base=BaseTask, bind=True)
def generate_report(self, report_type: str, parameters: Dict[str, Any]):
    """Generate report asynchronously"""
    try:
        logger.info(f"Generating report: {report_type}")

        # Report generation logic
        time.sleep(3)

        return {
            "status": "success",
            "report_type": report_type,
            "report_url": f"/reports/{report_type}_123.pdf"
        }

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise


# Cleanup Tasks
@celery_app.task(base=BaseTask)
def cleanup_expired_sessions():
    """Cleanup expired sessions (scheduled task)"""
    try:
        from ..core.auth import get_auth_manager

        auth = get_auth_manager()
        auth.cleanup_expired_sessions()

        logger.info("Expired sessions cleaned up")
        return {"status": "success", "message": "Cleanup completed"}

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


@celery_app.task(base=BaseTask)
def cleanup_old_usage_records():
    """Cleanup old usage records (scheduled task)"""
    try:
        logger.info("Cleaning up old usage records")
        # Cleanup logic here
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


# Analytics Tasks
@celery_app.task(base=BaseTask)
def compute_daily_analytics():
    """Compute daily analytics (scheduled task)"""
    try:
        from ..core.analytics import get_monitoring

        monitoring = get_monitoring()
        dashboard_data = monitoring.get_dashboard_data()

        # Store analytics
        logger.info("Daily analytics computed")

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Analytics computation failed: {e}")
        raise


# Notification Tasks
@celery_app.task(base=BaseTask, bind=True, max_retries=5)
def send_notification(self, user_id: str, notification_type: str, data: Dict[str, Any]):
    """Send notification to user"""
    try:
        logger.info(f"Sending {notification_type} notification to user {user_id}")

        # Notification sending logic (email, SMS, push, etc.)

        return {
            "status": "success",
            "user_id": user_id,
            "notification_type": notification_type
        }

    except Exception as e:
        logger.error(f"Notification failed: {e}")
        raise self.retry(exc=e, countdown=60)


# ==================== Job Manager ====================

class JobManager:
    """Manages background jobs"""

    def __init__(self):
        self.app = get_celery_app()
        self.logger = logging.getLogger(__name__)

    def submit_job(
        self,
        task_name: str,
        args: tuple = (),
        kwargs: Dict[str, Any] = None,
        priority: JobPriority = JobPriority.NORMAL,
        eta: Optional[datetime] = None,
        countdown: Optional[int] = None,
        expires: Optional[datetime] = None
    ) -> str:
        """
        Submit job to queue

        Args:
            task_name: Name of Celery task
            args: Positional arguments
            kwargs: Keyword arguments
            priority: Job priority
            eta: Execute at specific time
            countdown: Execute after N seconds
            expires: Job expires at

        Returns:
            Job ID
        """
        kwargs = kwargs or {}

        # Get task
        task = self.app.tasks.get(task_name)
        if not task:
            raise ValueError(f"Task not found: {task_name}")

        # Submit with options
        result = task.apply_async(
            args=args,
            kwargs=kwargs,
            priority=priority.value,
            eta=eta,
            countdown=countdown,
            expires=expires
        )

        self.logger.info(f"Submitted job: {result.id} (task: {task_name})")
        return result.id

    def get_job_status(self, job_id: str) -> JobResult:
        """Get job status and result"""
        result = AsyncResult(job_id, app=self.app)

        return JobResult(
            job_id=job_id,
            status=JobStatus(result.status.lower()),
            result=result.result if result.successful() else None,
            error=str(result.result) if result.failed() else None,
            started_at=None,  # Could get from backend
            completed_at=None,
            retries=0,
            metadata=result.info if isinstance(result.info, dict) else {}
        )

    def cancel_job(self, job_id: str) -> bool:
        """Cancel pending job"""
        try:
            AsyncResult(job_id, app=self.app).revoke(terminate=True)
            self.logger.info(f"Cancelled job: {job_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    def retry_job(self, job_id: str) -> str:
        """Retry failed job"""
        result = AsyncResult(job_id, app=self.app)

        if result.failed():
            # Get original task and args
            # Resubmit
            pass  # Implementation depends on backend storage

        raise NotImplementedError("Retry requires task metadata storage")

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get list of active jobs"""
        inspector = self.app.control.inspect()

        active = inspector.active()
        scheduled = inspector.scheduled()
        reserved = inspector.reserved()

        jobs = []

        # Process active jobs
        if active:
            for worker, tasks in active.items():
                for task in tasks:
                    jobs.append({
                        "job_id": task['id'],
                        "task": task['name'],
                        "worker": worker,
                        "status": "active",
                        "started_at": task.get('time_start')
                    })

        return jobs

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        inspector = self.app.control.inspect()

        stats = inspector.stats()
        active = inspector.active()

        total_active = sum(len(tasks) for tasks in (active or {}).values())

        return {
            "workers": len(stats or {}),
            "active_jobs": total_active,
            "stats": stats
        }


# ==================== Scheduled Jobs Manager ====================

class ScheduledJobsManager:
    """Manages scheduled periodic tasks"""

    def __init__(self):
        self.app = get_celery_app()
        self.logger = logging.getLogger(__name__)

    def add_schedule(self, scheduled_job: ScheduledJob):
        """Add scheduled job"""
        # Parse cron expression
        parts = scheduled_job.schedule.split()

        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
            schedule = crontab(
                minute=minute,
                hour=hour,
                day_of_month=day,
                month_of_year=month,
                day_of_week=day_of_week
            )
        else:
            raise ValueError(f"Invalid cron expression: {scheduled_job.schedule}")

        # Add to beat schedule
        self.app.conf.beat_schedule[scheduled_job.name] = {
            'task': scheduled_job.task,
            'schedule': schedule,
            'args': scheduled_job.args,
            'kwargs': scheduled_job.kwargs,
            'options': {'expires': 3600}  # Expire if not run within 1 hour
        }

        self.logger.info(f"Added scheduled job: {scheduled_job.name}")

    def remove_schedule(self, name: str):
        """Remove scheduled job"""
        if name in self.app.conf.beat_schedule:
            del self.app.conf.beat_schedule[name]
            self.logger.info(f"Removed scheduled job: {name}")

    def list_schedules(self) -> List[Dict[str, Any]]:
        """List all scheduled jobs"""
        return [
            {
                "name": name,
                "task": config['task'],
                "schedule": str(config['schedule']),
                "args": config.get('args', ()),
                "kwargs": config.get('kwargs', {})
            }
            for name, config in self.app.conf.beat_schedule.items()
        ]


# ==================== Default Scheduled Jobs ====================

def setup_default_schedules():
    """Setup default scheduled jobs"""
    manager = ScheduledJobsManager()

    # Cleanup sessions every hour
    manager.add_schedule(ScheduledJob(
        name="cleanup_expired_sessions",
        task="manus_ai.core.jobs.cleanup_expired_sessions",
        schedule="0 * * * *",  # Every hour
        description="Clean up expired user sessions"
    ))

    # Cleanup old usage records daily
    manager.add_schedule(ScheduledJob(
        name="cleanup_old_usage",
        task="manus_ai.core.jobs.cleanup_old_usage_records",
        schedule="0 2 * * *",  # 2 AM daily
        description="Clean up old usage records"
    ))

    # Compute daily analytics
    manager.add_schedule(ScheduledJob(
        name="daily_analytics",
        task="manus_ai.core.jobs.compute_daily_analytics",
        schedule="0 3 * * *",  # 3 AM daily
        description="Compute daily analytics"
    ))


# Global instances
_job_manager: Optional[JobManager] = None
_scheduled_jobs_manager: Optional[ScheduledJobsManager] = None


def get_job_manager() -> JobManager:
    """Get global job manager instance"""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager


def get_scheduled_jobs_manager() -> ScheduledJobsManager:
    """Get global scheduled jobs manager instance"""
    global _scheduled_jobs_manager
    if _scheduled_jobs_manager is None:
        _scheduled_jobs_manager = ScheduledJobsManager()
    return _scheduled_jobs_manager
