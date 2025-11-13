"""
API Endpoints for Job Queue, Caching, and Events/Webhooks
Complete REST API for all infrastructure features
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from ..core.jobs import get_job_manager, get_scheduled_jobs_manager, JobPriority, JobStatus
from ..core.cache import get_cache_manager, get_llm_cache, get_embedding_cache, CacheNamespace
from ..core.events import (
    get_event_bus, get_webhook_manager, get_event_emitter,
    EventType, WebhookStatus
)
from ..core.auth import get_auth_manager, User, Permission

# Create routers
jobs_router = APIRouter(prefix="/jobs", tags=["Background Jobs"])
cache_router = APIRouter(prefix="/cache", tags=["Caching"])
webhooks_router = APIRouter(prefix="/webhooks", tags=["Webhooks & Events"])


# ==================== Job Queue Models ====================

class JobSubmitRequest(BaseModel):
    task_name: str = Field(..., description="Celery task name")
    args: List[Any] = Field(default_factory=list, description="Positional arguments")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Keyword arguments")
    priority: JobPriority = Field(default=JobPriority.NORMAL, description="Job priority")
    countdown: Optional[int] = Field(default=None, description="Delay in seconds")
    eta: Optional[datetime] = Field(default=None, description="Execute at specific time")

class ScheduledJobRequest(BaseModel):
    name: str = Field(..., description="Job name")
    task: str = Field(..., description="Celery task name")
    schedule: str = Field(..., description="Cron expression (5 parts)")
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    description: str = Field(default="", description="Job description")


# ==================== Cache Models ====================

class CacheSetRequest(BaseModel):
    namespace: CacheNamespace
    identifier: str
    value: Any
    ttl: Optional[int] = Field(default=None, description="TTL in seconds")
    params: Optional[Dict[str, Any]] = None

class CacheGetRequest(BaseModel):
    namespace: CacheNamespace
    identifier: str
    params: Optional[Dict[str, Any]] = None

class LLMCacheRequest(BaseModel):
    prompt: str
    model: str = "gemini-2.0-flash-exp"
    temperature: float = 0.7
    max_tokens: Optional[int] = None

class LLMCacheSetRequest(LLMCacheRequest):
    response: str
    ttl: int = Field(default=86400, description="TTL in seconds")

class EmbeddingCacheRequest(BaseModel):
    text: str
    model: str = "all-MiniLM-L6-v2"

class EmbeddingCacheSetRequest(EmbeddingCacheRequest):
    embedding: List[float]
    ttl: int = Field(default=604800, description="TTL in seconds")


# ==================== Webhook Models ====================

class WebhookCreateRequest(BaseModel):
    url: str = Field(..., description="Webhook URL")
    events: List[EventType] = Field(..., description="Event types to subscribe")
    secret: Optional[str] = Field(default=None, description="HMAC secret")
    description: str = Field(default="")
    headers: Dict[str, str] = Field(default_factory=dict, description="Custom headers")

class WebhookUpdateRequest(BaseModel):
    url: Optional[str] = None
    events: Optional[List[EventType]] = None
    active: Optional[bool] = None
    description: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

class EventEmitRequest(BaseModel):
    event_type: EventType
    data: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ==================== Dependencies ====================

async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[User]:
    """Get current user from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ")[1]
    auth_manager = get_auth_manager()
    session = await auth_manager.verify_session(token)

    if session:
        return await auth_manager.get_user(session.user_id)
    return None

async def require_auth(user: User = Depends(get_current_user)) -> User:
    """Require authentication"""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


# ==================== Job Queue Endpoints ====================

@jobs_router.post("/submit")
async def submit_job(
    request: JobSubmitRequest,
    user: User = Depends(require_auth)
):
    """Submit background job to queue"""
    try:
        manager = get_job_manager()

        job_id = manager.submit_job(
            task_name=request.task_name,
            args=tuple(request.args),
            kwargs=request.kwargs,
            priority=request.priority,
            countdown=request.countdown,
            eta=request.eta
        )

        return {
            "status": "success",
            "job_id": job_id,
            "message": "Job submitted successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@jobs_router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    user: User = Depends(require_auth)
):
    """Get job status and result"""
    try:
        manager = get_job_manager()
        result = manager.get_job_status(job_id)

        return {
            "job_id": result.job_id,
            "status": result.status.value,
            "result": result.result,
            "error": result.error,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "retries": result.retries,
            "metadata": result.metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@jobs_router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    user: User = Depends(require_auth)
):
    """Cancel pending job"""
    try:
        manager = get_job_manager()
        success = manager.cancel_job(job_id)

        if success:
            return {"status": "success", "message": "Job cancelled"}
        else:
            raise HTTPException(status_code=404, detail="Job not found or already completed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@jobs_router.get("/active/list")
async def list_active_jobs(user: User = Depends(require_auth)):
    """List all active jobs"""
    try:
        manager = get_job_manager()
        jobs = manager.get_active_jobs()

        return {
            "status": "success",
            "jobs": jobs,
            "count": len(jobs)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@jobs_router.get("/stats")
async def get_queue_stats(user: User = Depends(require_auth)):
    """Get queue statistics"""
    try:
        manager = get_job_manager()
        stats = manager.get_queue_stats()

        return {
            "status": "success",
            **stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@jobs_router.post("/schedule")
async def create_scheduled_job(
    request: ScheduledJobRequest,
    user: User = Depends(require_auth)
):
    """Create scheduled job"""
    try:
        from ..core.jobs import ScheduledJob

        manager = get_scheduled_jobs_manager()

        scheduled_job = ScheduledJob(
            name=request.name,
            task=request.task,
            schedule=request.schedule,
            args=tuple(request.args),
            kwargs=request.kwargs,
            description=request.description
        )

        manager.add_schedule(scheduled_job)

        return {
            "status": "success",
            "message": f"Scheduled job '{request.name}' created"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@jobs_router.get("/schedule/list")
async def list_scheduled_jobs(user: User = Depends(require_auth)):
    """List all scheduled jobs"""
    try:
        manager = get_scheduled_jobs_manager()
        schedules = manager.list_schedules()

        return {
            "status": "success",
            "schedules": schedules,
            "count": len(schedules)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@jobs_router.delete("/schedule/{name}")
async def delete_scheduled_job(
    name: str,
    user: User = Depends(require_auth)
):
    """Delete scheduled job"""
    try:
        manager = get_scheduled_jobs_manager()
        manager.remove_schedule(name)

        return {
            "status": "success",
            "message": f"Scheduled job '{name}' deleted"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Cache Endpoints ====================

@cache_router.post("/set")
async def set_cache(
    request: CacheSetRequest,
    user: User = Depends(require_auth)
):
    """Set cache value"""
    try:
        cache = get_cache_manager()
        await cache.connect()

        success = await cache.set(
            request.namespace,
            request.identifier,
            request.value,
            request.ttl,
            request.params
        )

        if success:
            return {"status": "success", "message": "Cache set successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to set cache")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@cache_router.post("/get")
async def get_cache(
    request: CacheGetRequest,
    user: User = Depends(require_auth)
):
    """Get cache value"""
    try:
        cache = get_cache_manager()
        await cache.connect()

        value = await cache.get(
            request.namespace,
            request.identifier,
            request.params
        )

        if value is not None:
            return {
                "status": "success",
                "value": value,
                "cached": True
            }
        else:
            return {
                "status": "success",
                "value": None,
                "cached": False
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@cache_router.delete("/delete")
async def delete_cache(
    request: CacheGetRequest,
    user: User = Depends(require_auth)
):
    """Delete cache value"""
    try:
        cache = get_cache_manager()
        await cache.connect()

        success = await cache.delete(
            request.namespace,
            request.identifier,
            request.params
        )

        if success:
            return {"status": "success", "message": "Cache deleted"}
        else:
            return {"status": "success", "message": "Cache key not found"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@cache_router.delete("/namespace/{namespace}")
async def clear_namespace(
    namespace: CacheNamespace,
    user: User = Depends(require_auth)
):
    """Clear all cache keys in namespace"""
    try:
        cache = get_cache_manager()
        await cache.connect()

        count = await cache.clear_namespace(namespace)

        return {
            "status": "success",
            "message": f"Cleared {count} keys from {namespace.value}",
            "count": count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@cache_router.get("/stats")
async def get_cache_stats(user: User = Depends(require_auth)):
    """Get cache statistics"""
    try:
        cache = get_cache_manager()
        await cache.connect()

        stats = await cache.get_stats()

        return {
            "status": "success",
            "hits": stats.hits,
            "misses": stats.misses,
            "hit_rate": stats.hit_rate,
            "total_keys": stats.total_keys,
            "memory_used_mb": stats.memory_used_mb,
            "evictions": stats.evictions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# LLM Cache endpoints
@cache_router.post("/llm/get")
async def get_llm_cache(
    request: LLMCacheRequest,
    user: User = Depends(require_auth)
):
    """Get cached LLM response"""
    try:
        llm_cache = get_llm_cache()

        response = await llm_cache.get_response(
            request.prompt,
            request.model,
            request.temperature,
            request.max_tokens
        )

        return {
            "status": "success",
            "response": response,
            "cached": response is not None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@cache_router.post("/llm/set")
async def set_llm_cache(
    request: LLMCacheSetRequest,
    user: User = Depends(require_auth)
):
    """Cache LLM response"""
    try:
        llm_cache = get_llm_cache()

        success = await llm_cache.cache_response(
            request.prompt,
            request.response,
            request.model,
            request.temperature,
            request.max_tokens,
            request.ttl
        )

        if success:
            return {"status": "success", "message": "LLM response cached"}
        else:
            raise HTTPException(status_code=500, detail="Failed to cache response")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@cache_router.get("/llm/savings")
async def get_llm_savings(user: User = Depends(require_auth)):
    """Get LLM cost savings from cache"""
    try:
        llm_cache = get_llm_cache()
        savings = await llm_cache.get_cost_savings()

        return {
            "status": "success",
            **savings
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Embedding Cache endpoints
@cache_router.post("/embeddings/get")
async def get_embedding_cache(
    request: EmbeddingCacheRequest,
    user: User = Depends(require_auth)
):
    """Get cached embedding"""
    try:
        embedding_cache = get_embedding_cache()

        embedding = await embedding_cache.get_embedding(
            request.text,
            request.model
        )

        return {
            "status": "success",
            "embedding": embedding,
            "cached": embedding is not None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@cache_router.post("/embeddings/set")
async def set_embedding_cache(
    request: EmbeddingCacheSetRequest,
    user: User = Depends(require_auth)
):
    """Cache embedding"""
    try:
        embedding_cache = get_embedding_cache()

        success = await embedding_cache.cache_embedding(
            request.text,
            request.embedding,
            request.model,
            request.ttl
        )

        if success:
            return {"status": "success", "message": "Embedding cached"}
        else:
            raise HTTPException(status_code=500, detail="Failed to cache embedding")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Webhook & Event Endpoints ====================

@webhooks_router.post("")
async def create_webhook(
    request: WebhookCreateRequest,
    user: User = Depends(require_auth)
):
    """Register new webhook endpoint"""
    try:
        manager = get_webhook_manager()

        webhook = await manager.register_webhook(
            url=request.url,
            events=request.events,
            secret=request.secret,
            description=request.description,
            headers=request.headers
        )

        return {
            "status": "success",
            "webhook_id": webhook.id,
            "secret": webhook.secret,  # Return once for user to save
            "message": "Webhook registered successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@webhooks_router.get("")
async def list_webhooks(
    active_only: bool = True,
    user: User = Depends(require_auth)
):
    """List all webhooks"""
    try:
        manager = get_webhook_manager()
        webhooks = manager.list_webhooks(active_only)

        return {
            "status": "success",
            "webhooks": [
                {
                    "id": w.id,
                    "url": w.url,
                    "events": [e.value for e in w.events],
                    "active": w.active,
                    "description": w.description,
                    "created_at": w.created_at.isoformat()
                }
                for w in webhooks
            ],
            "count": len(webhooks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@webhooks_router.get("/{webhook_id}")
async def get_webhook(
    webhook_id: str,
    user: User = Depends(require_auth)
):
    """Get webhook details"""
    try:
        manager = get_webhook_manager()
        webhook = manager.get_webhook(webhook_id)

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        return {
            "status": "success",
            "webhook": {
                "id": webhook.id,
                "url": webhook.url,
                "events": [e.value for e in webhook.events],
                "active": webhook.active,
                "description": webhook.description,
                "headers": webhook.headers,
                "retry_config": webhook.retry_config,
                "created_at": webhook.created_at.isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@webhooks_router.patch("/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdateRequest,
    user: User = Depends(require_auth)
):
    """Update webhook configuration"""
    try:
        manager = get_webhook_manager()

        updates = {k: v for k, v in request.dict().items() if v is not None}

        success = await manager.update_webhook(webhook_id, **updates)

        if success:
            return {"status": "success", "message": "Webhook updated"}
        else:
            raise HTTPException(status_code=404, detail="Webhook not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@webhooks_router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    user: User = Depends(require_auth)
):
    """Unregister webhook"""
    try:
        manager = get_webhook_manager()

        success = await manager.unregister_webhook(webhook_id)

        if success:
            return {"status": "success", "message": "Webhook deleted"}
        else:
            raise HTTPException(status_code=404, detail="Webhook not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@webhooks_router.get("/{webhook_id}/deliveries")
async def get_webhook_deliveries(
    webhook_id: str,
    limit: int = 100,
    user: User = Depends(require_auth)
):
    """Get webhook delivery history"""
    try:
        manager = get_webhook_manager()
        deliveries = manager.get_webhook_deliveries(webhook_id, limit)

        return {
            "status": "success",
            "deliveries": [
                {
                    "id": d.id,
                    "event_id": d.event_id,
                    "status": d.status.value,
                    "attempts": d.attempts,
                    "last_attempt": d.last_attempt.isoformat() if d.last_attempt else None,
                    "response_code": d.response_code,
                    "error": d.error,
                    "created_at": d.created_at.isoformat()
                }
                for d in deliveries
            ],
            "count": len(deliveries)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@webhooks_router.post("/deliveries/{delivery_id}/retry")
async def retry_delivery(
    delivery_id: str,
    user: User = Depends(require_auth)
):
    """Manually retry failed webhook delivery"""
    try:
        manager = get_webhook_manager()

        success = await manager.retry_delivery(delivery_id)

        if success:
            return {"status": "success", "message": "Delivery retried"}
        else:
            raise HTTPException(status_code=404, detail="Delivery not found or already succeeded")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Event endpoints
@webhooks_router.post("/events")
async def emit_event(
    request: EventEmitRequest,
    user: User = Depends(require_auth)
):
    """Emit custom event"""
    try:
        emitter = get_event_emitter()

        event = await emitter.emit(
            request.event_type,
            request.data,
            request.user_id,
            request.session_id,
            request.metadata
        )

        return {
            "status": "success",
            "event_id": event.id,
            "message": "Event emitted"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@webhooks_router.get("/events/history")
async def get_event_history(
    event_type: Optional[EventType] = None,
    limit: int = 100,
    user: User = Depends(require_auth)
):
    """Get event history"""
    try:
        event_bus = get_event_bus()
        events = event_bus.get_event_history(event_type, limit)

        return {
            "status": "success",
            "events": [e.to_dict() for e in events],
            "count": len(events)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@webhooks_router.get("/events/types")
async def list_event_types():
    """List all available event types"""
    return {
        "status": "success",
        "event_types": [
            {
                "value": e.value,
                "name": e.name,
                "category": e.value.split(".")[0]
            }
            for e in EventType
        ],
        "count": len(EventType)
    }


# Export all routers
all_infrastructure_routers = [
    jobs_router,
    cache_router,
    webhooks_router
]
