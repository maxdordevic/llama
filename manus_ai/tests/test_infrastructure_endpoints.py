"""
Comprehensive Integration Tests for Infrastructure Endpoints
Tests all Job Queue, Cache, and Webhook API endpoints
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

# Test with httpx for async FastAPI testing
from httpx import AsyncClient
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import infrastructure modules
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.jobs import (
    JobManager, ScheduledJobsManager, JobStatus, JobPriority,
    JobResult, ScheduledJob, get_job_manager
)
from core.cache import (
    CacheManager, LLMResponseCache, EmbeddingCache, QueryResultCache,
    CacheNamespace, CacheStrategy, get_cache_manager, get_llm_cache
)
from core.events import (
    EventBus, WebhookManager, EventEmitter, EventType, WebhookStatus,
    Event, WebhookEndpoint, WebhookDelivery,
    get_event_bus, get_webhook_manager, get_event_emitter
)
from core.auth import User, AuthenticationManager


# ==================== Fixtures ====================

@pytest.fixture
def mock_user():
    """Create mock authenticated user"""
    return User(
        user_id="test_user_123",
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        role="admin",
        api_keys=[],
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_auth_manager(mock_user):
    """Mock authentication manager"""
    with patch('api.infrastructure_endpoints.get_auth_manager') as mock:
        auth_manager = Mock()
        auth_manager.verify_token.return_value = mock_user
        auth_manager.verify_api_key.return_value = mock_user
        mock.return_value = auth_manager
        yield auth_manager


@pytest.fixture
def mock_job_manager():
    """Mock job manager"""
    with patch('api.infrastructure_endpoints.get_job_manager') as mock:
        manager = Mock(spec=JobManager)

        # Mock submit_job
        manager.submit_job.return_value = "job_123"

        # Mock get_job_status
        manager.get_job_status.return_value = JobResult(
            job_id="job_123",
            status=JobStatus.SUCCESS,
            result={"output": "Job completed successfully"},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )

        # Mock cancel_job
        manager.cancel_job.return_value = True

        # Mock get_active_jobs
        manager.get_active_jobs.return_value = [
            {
                "job_id": "job_123",
                "task": "execute_agent_async",
                "worker": "worker1",
                "status": "active"
            }
        ]

        # Mock get_queue_stats
        manager.get_queue_stats.return_value = {
            "workers": 2,
            "active_jobs": 3,
            "stats": {"pool_size": 4}
        }

        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_scheduled_jobs_manager():
    """Mock scheduled jobs manager"""
    with patch('api.infrastructure_endpoints.get_scheduled_jobs_manager') as mock:
        manager = Mock(spec=ScheduledJobsManager)

        # Mock add_schedule
        manager.add_schedule.return_value = None

        # Mock list_schedules
        manager.list_schedules.return_value = [
            {
                "name": "cleanup_sessions",
                "task": "cleanup_expired_sessions",
                "schedule": "0 * * * *",
                "args": (),
                "kwargs": {}
            }
        ]

        # Mock remove_schedule
        manager.remove_schedule.return_value = None

        mock.return_value = manager
        yield manager


@pytest.fixture
async def mock_cache_manager():
    """Mock cache manager"""
    with patch('api.infrastructure_endpoints.get_cache_manager') as mock:
        manager = AsyncMock(spec=CacheManager)

        # Mock get
        manager.get.return_value = {"cached": "data"}

        # Mock set
        manager.set.return_value = True

        # Mock delete
        manager.delete.return_value = True

        # Mock clear_namespace
        manager.clear_namespace.return_value = 10

        # Mock get_stats
        from core.cache import CacheStats
        manager.get_stats.return_value = CacheStats(
            hits=1000,
            misses=100,
            hit_rate=90.9,
            total_keys=500,
            memory_used_mb=125.5,
            evictions=5
        )

        mock.return_value = manager
        yield manager


@pytest.fixture
async def mock_llm_cache():
    """Mock LLM response cache"""
    with patch('api.infrastructure_endpoints.get_llm_cache') as mock:
        cache = AsyncMock(spec=LLMResponseCache)

        # Mock get_response
        cache.get_response.return_value = "Cached LLM response"

        # Mock cache_response
        cache.cache_response.return_value = True

        # Mock get_cost_savings
        cache.get_cost_savings.return_value = {
            "cache_hits": 1000,
            "cache_misses": 100,
            "hit_rate_percent": 90.9,
            "estimated_cost_saved_usd": 10.0,
            "avg_cost_per_request_usd": 0.01
        }

        mock.return_value = cache
        yield cache


@pytest.fixture
async def mock_embedding_cache():
    """Mock embedding cache"""
    with patch('api.infrastructure_endpoints.get_embedding_cache') as mock:
        cache = AsyncMock(spec=EmbeddingCache)

        # Mock get_embedding
        cache.get_embedding.return_value = [0.1, 0.2, 0.3, 0.4]

        # Mock cache_embedding
        cache.cache_embedding.return_value = True

        mock.return_value = cache
        yield cache


@pytest.fixture
def mock_webhook_manager():
    """Mock webhook manager"""
    with patch('api.infrastructure_endpoints.get_webhook_manager') as mock:
        manager = AsyncMock(spec=WebhookManager)

        # Mock register_webhook
        webhook = WebhookEndpoint(
            id="webhook_123",
            url="https://example.com/webhook",
            secret="secret_key",
            events={EventType.AGENT_COMPLETED},
            active=True,
            description="Test webhook"
        )
        manager.register_webhook.return_value = webhook

        # Mock list_webhooks
        manager.list_webhooks.return_value = [webhook]

        # Mock get_webhook
        manager.get_webhook.return_value = webhook

        # Mock update_webhook
        manager.update_webhook.return_value = True

        # Mock unregister_webhook
        manager.unregister_webhook.return_value = True

        # Mock get_webhook_deliveries
        delivery = WebhookDelivery(
            id="delivery_123",
            webhook_id="webhook_123",
            event_id="event_123",
            status=WebhookStatus.SENT,
            attempts=1,
            response_code=200
        )
        manager.get_webhook_deliveries.return_value = [delivery]

        # Mock retry_delivery
        manager.retry_delivery.return_value = True

        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_event_emitter():
    """Mock event emitter"""
    with patch('api.infrastructure_endpoints.get_event_emitter') as mock:
        emitter = AsyncMock(spec=EventEmitter)

        event = Event(
            id="event_123",
            type=EventType.CUSTOM,
            timestamp=datetime.utcnow(),
            data={"test": "data"},
            user_id="user_123"
        )
        emitter.emit.return_value = event

        mock.return_value = emitter
        yield emitter


@pytest.fixture
def mock_event_bus():
    """Mock event bus"""
    with patch('api.infrastructure_endpoints.get_event_bus') as mock:
        bus = Mock(spec=EventBus)

        event = Event(
            id="event_123",
            type=EventType.AGENT_COMPLETED,
            timestamp=datetime.utcnow(),
            data={"agent": "test"},
            user_id="user_123"
        )
        bus.get_event_history.return_value = [event]

        mock.return_value = bus
        yield bus


@pytest.fixture
async def test_app(
    mock_auth_manager,
    mock_job_manager,
    mock_scheduled_jobs_manager,
    mock_cache_manager,
    mock_llm_cache,
    mock_embedding_cache,
    mock_webhook_manager,
    mock_event_emitter,
    mock_event_bus
):
    """Create test FastAPI app with all routers"""
    from fastapi import FastAPI
    from api.infrastructure_endpoints import jobs_router, cache_router, webhooks_router

    app = FastAPI()
    app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
    app.include_router(cache_router, prefix="/cache", tags=["cache"])
    app.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])

    return app


# ==================== Job Queue Endpoint Tests ====================

@pytest.mark.asyncio
async def test_submit_job(test_app, mock_job_manager):
    """Test submitting a background job"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/jobs/submit",
            json={
                "task_name": "execute_agent_async",
                "args": ["research_agent"],
                "kwargs": {"query": "test query"},
                "priority": 5
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["job_id"] == "job_123"

    mock_job_manager.submit_job.assert_called_once()


@pytest.mark.asyncio
async def test_get_job_status(test_app, mock_job_manager):
    """Test getting job status"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/jobs/job_123",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job_123"
    assert data["status"] == "success"
    assert "result" in data

    mock_job_manager.get_job_status.assert_called_once_with("job_123")


@pytest.mark.asyncio
async def test_cancel_job(test_app, mock_job_manager):
    """Test cancelling a job"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.delete(
            "/jobs/job_123",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["cancelled"] is True

    mock_job_manager.cancel_job.assert_called_once_with("job_123")


@pytest.mark.asyncio
async def test_list_active_jobs(test_app, mock_job_manager):
    """Test listing active jobs"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/jobs/active/list",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "jobs" in data
    assert len(data["jobs"]) == 1
    assert data["jobs"][0]["job_id"] == "job_123"


@pytest.mark.asyncio
async def test_get_queue_stats(test_app, mock_job_manager):
    """Test getting queue statistics"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/jobs/stats",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["workers"] == 2
    assert data["active_jobs"] == 3


@pytest.mark.asyncio
async def test_create_scheduled_job(test_app, mock_scheduled_jobs_manager):
    """Test creating a scheduled job"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/jobs/schedule",
            json={
                "name": "daily_cleanup",
                "task": "cleanup_old_data",
                "schedule": "0 2 * * *",
                "description": "Daily cleanup at 2 AM"
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["name"] == "daily_cleanup"


@pytest.mark.asyncio
async def test_list_scheduled_jobs(test_app, mock_scheduled_jobs_manager):
    """Test listing scheduled jobs"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/jobs/schedule/list",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "schedules" in data
    assert len(data["schedules"]) == 1
    assert data["schedules"][0]["name"] == "cleanup_sessions"


@pytest.mark.asyncio
async def test_delete_scheduled_job(test_app, mock_scheduled_jobs_manager):
    """Test deleting a scheduled job"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.delete(
            "/jobs/schedule/cleanup_sessions",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    mock_scheduled_jobs_manager.remove_schedule.assert_called_once_with("cleanup_sessions")


# ==================== Cache Endpoint Tests ====================

@pytest.mark.asyncio
async def test_cache_set(test_app, mock_cache_manager):
    """Test setting cache value"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/cache/set",
            json={
                "namespace": "query_results",
                "identifier": "user_data_123",
                "value": {"data": "test"},
                "ttl": 300
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["cached"] is True


@pytest.mark.asyncio
async def test_cache_get(test_app, mock_cache_manager):
    """Test getting cache value"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/cache/get",
            json={
                "namespace": "query_results",
                "identifier": "user_data_123"
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["value"] is not None
    assert data["cached"] is True


@pytest.mark.asyncio
async def test_cache_delete(test_app, mock_cache_manager):
    """Test deleting cache value"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.delete(
            "/cache/delete",
            json={
                "namespace": "query_results",
                "identifier": "user_data_123"
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["deleted"] is True


@pytest.mark.asyncio
async def test_clear_cache_namespace(test_app, mock_cache_manager):
    """Test clearing entire cache namespace"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.delete(
            "/cache/namespace/query_results",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["keys_cleared"] == 10


@pytest.mark.asyncio
async def test_get_cache_stats(test_app, mock_cache_manager):
    """Test getting cache statistics"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/cache/stats",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["hits"] == 1000
    assert data["misses"] == 100
    assert data["hit_rate_percent"] == 90.9
    assert data["total_keys"] == 500


@pytest.mark.asyncio
async def test_get_llm_cache(test_app, mock_llm_cache):
    """Test getting cached LLM response"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/cache/llm/get",
            json={
                "prompt": "What is AI?",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 1000
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["response"] == "Cached LLM response"
    assert data["cached"] is True


@pytest.mark.asyncio
async def test_set_llm_cache(test_app, mock_llm_cache):
    """Test caching LLM response"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/cache/llm/set",
            json={
                "prompt": "What is AI?",
                "response": "AI is artificial intelligence",
                "model": "gpt-4",
                "temperature": 0.7,
                "ttl": 86400
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["cached"] is True


@pytest.mark.asyncio
async def test_get_llm_cost_savings(test_app, mock_llm_cache):
    """Test getting LLM cost savings"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/cache/llm/savings",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["cache_hits"] == 1000
    assert data["estimated_cost_saved_usd"] == 10.0
    assert data["hit_rate_percent"] == 90.9


@pytest.mark.asyncio
async def test_get_embedding_cache(test_app, mock_embedding_cache):
    """Test getting cached embedding"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/cache/embeddings/get",
            json={
                "text": "Hello world",
                "model": "all-MiniLM-L6-v2"
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["embedding"] == [0.1, 0.2, 0.3, 0.4]
    assert data["cached"] is True


@pytest.mark.asyncio
async def test_set_embedding_cache(test_app, mock_embedding_cache):
    """Test caching embedding"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/cache/embeddings/set",
            json={
                "text": "Hello world",
                "embedding": [0.1, 0.2, 0.3, 0.4],
                "model": "all-MiniLM-L6-v2",
                "ttl": 604800
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["cached"] is True


# ==================== Webhook Endpoint Tests ====================

@pytest.mark.asyncio
async def test_create_webhook(test_app, mock_webhook_manager):
    """Test creating a webhook"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook",
                "events": ["agent.completed", "workflow.completed"],
                "description": "Test webhook"
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["webhook_id"] == "webhook_123"
    assert "secret" in data


@pytest.mark.asyncio
async def test_list_webhooks(test_app, mock_webhook_manager):
    """Test listing webhooks"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/webhooks?active_only=true",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "webhooks" in data
    assert len(data["webhooks"]) == 1
    assert data["webhooks"][0]["id"] == "webhook_123"


@pytest.mark.asyncio
async def test_get_webhook(test_app, mock_webhook_manager):
    """Test getting webhook details"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/webhooks/webhook_123",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "webhook" in data
    assert data["webhook"]["id"] == "webhook_123"


@pytest.mark.asyncio
async def test_update_webhook(test_app, mock_webhook_manager):
    """Test updating webhook"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.patch(
            "/webhooks/webhook_123",
            json={
                "active": False,
                "description": "Updated webhook"
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["updated"] is True


@pytest.mark.asyncio
async def test_delete_webhook(test_app, mock_webhook_manager):
    """Test deleting webhook"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.delete(
            "/webhooks/webhook_123",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["deleted"] is True


@pytest.mark.asyncio
async def test_get_webhook_deliveries(test_app, mock_webhook_manager):
    """Test getting webhook delivery history"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/webhooks/webhook_123/deliveries?limit=50",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "deliveries" in data
    assert len(data["deliveries"]) == 1
    assert data["deliveries"][0]["id"] == "delivery_123"


@pytest.mark.asyncio
async def test_retry_webhook_delivery(test_app, mock_webhook_manager):
    """Test retrying failed webhook delivery"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/webhooks/deliveries/delivery_123/retry",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["retried"] is True


@pytest.mark.asyncio
async def test_emit_custom_event(test_app, mock_event_emitter):
    """Test emitting custom event"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/webhooks/events",
            json={
                "event_type": "custom",
                "data": {"message": "Test event"},
                "user_id": "user_123"
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["event_id"] == "event_123"


@pytest.mark.asyncio
async def test_get_event_history(test_app, mock_event_bus):
    """Test getting event history"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/webhooks/events/history?limit=50",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "events" in data
    assert len(data["events"]) == 1


@pytest.mark.asyncio
async def test_get_event_types(test_app):
    """Test getting available event types"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/webhooks/events/types",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "event_types" in data
    assert len(data["event_types"]) > 0


# ==================== Authentication Tests ====================

@pytest.mark.asyncio
async def test_unauthorized_access(test_app):
    """Test that endpoints require authentication"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # Try to access without auth header
        response = await client.get("/jobs/stats")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token(test_app):
    """Test that invalid tokens are rejected"""
    with patch('api.infrastructure_endpoints.get_auth_manager') as mock_auth:
        auth_manager = Mock()
        auth_manager.verify_token.return_value = None
        mock_auth.return_value = auth_manager

        async with AsyncClient(app=test_app, base_url="http://test") as client:
            response = await client.get(
                "/jobs/stats",
                headers={"Authorization": "Bearer invalid_token"}
            )

        assert response.status_code == 401


# ==================== Error Handling Tests ====================

@pytest.mark.asyncio
async def test_job_not_found(test_app, mock_job_manager):
    """Test handling of non-existent job"""
    mock_job_manager.get_job_status.side_effect = ValueError("Job not found")

    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/jobs/nonexistent_job",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_webhook_not_found(test_app, mock_webhook_manager):
    """Test handling of non-existent webhook"""
    mock_webhook_manager.get_webhook.return_value = None

    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/webhooks/nonexistent_webhook",
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invalid_cache_namespace(test_app):
    """Test handling of invalid cache namespace"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/cache/get",
            json={
                "namespace": "invalid_namespace",
                "identifier": "test"
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 422  # Validation error


# ==================== Integration Tests ====================

@pytest.mark.asyncio
async def test_job_submission_and_status_check(test_app, mock_job_manager):
    """Integration test: Submit job and check status"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # Submit job
        submit_response = await client.post(
            "/jobs/submit",
            json={
                "task_name": "execute_agent_async",
                "args": ["research_agent"],
                "kwargs": {"query": "test"}
            },
            headers={"Authorization": "Bearer test_token"}
        )

        assert submit_response.status_code == 200
        job_id = submit_response.json()["job_id"]

        # Check status
        status_response = await client.get(
            f"/jobs/{job_id}",
            headers={"Authorization": "Bearer test_token"}
        )

        assert status_response.status_code == 200
        assert status_response.json()["job_id"] == job_id


@pytest.mark.asyncio
async def test_cache_set_and_get(test_app, mock_cache_manager):
    """Integration test: Set and get cache value"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # Set cache
        set_response = await client.post(
            "/cache/set",
            json={
                "namespace": "query_results",
                "identifier": "test_123",
                "value": {"result": "data"},
                "ttl": 300
            },
            headers={"Authorization": "Bearer test_token"}
        )

        assert set_response.status_code == 200

        # Get cache
        get_response = await client.post(
            "/cache/get",
            json={
                "namespace": "query_results",
                "identifier": "test_123"
            },
            headers={"Authorization": "Bearer test_token"}
        )

        assert get_response.status_code == 200
        assert get_response.json()["cached"] is True


@pytest.mark.asyncio
async def test_webhook_create_and_trigger(test_app, mock_webhook_manager, mock_event_emitter):
    """Integration test: Create webhook and trigger event"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # Create webhook
        create_response = await client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook",
                "events": ["agent.completed"]
            },
            headers={"Authorization": "Bearer test_token"}
        )

        assert create_response.status_code == 200
        webhook_id = create_response.json()["webhook_id"]

        # Emit event
        event_response = await client.post(
            "/webhooks/events",
            json={
                "event_type": "agent.completed",
                "data": {"agent": "test", "result": "success"}
            },
            headers={"Authorization": "Bearer test_token"}
        )

        assert event_response.status_code == 200

        # Check deliveries
        deliveries_response = await client.get(
            f"/webhooks/{webhook_id}/deliveries",
            headers={"Authorization": "Bearer test_token"}
        )

        assert deliveries_response.status_code == 200


# ==================== Performance Tests ====================

@pytest.mark.asyncio
async def test_llm_cache_performance(test_app, mock_llm_cache):
    """Test LLM cache cost savings calculation"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/cache/llm/savings",
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify cost savings calculation
        assert data["cache_hits"] > 0
        assert data["estimated_cost_saved_usd"] > 0
        assert data["hit_rate_percent"] > 50  # Should have >50% hit rate


@pytest.mark.asyncio
async def test_cache_stats_accuracy(test_app, mock_cache_manager):
    """Test cache statistics accuracy"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get(
            "/cache/stats",
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify statistics
        total_requests = data["hits"] + data["misses"]
        expected_hit_rate = (data["hits"] / total_requests) * 100

        assert abs(data["hit_rate_percent"] - expected_hit_rate) < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
