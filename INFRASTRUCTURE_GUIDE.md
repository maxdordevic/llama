# Manus AI Infrastructure Guide

**Complete guide to Job Queue, Caching, and Event Systems**

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Job Queue System](#job-queue-system)
5. [Caching Layer](#caching-layer)
6. [Event & Webhook System](#event--webhook-system)
7. [Production Deployment](#production-deployment)
8. [Monitoring & Observability](#monitoring--observability)
9. [Performance Tuning](#performance-tuning)
10. [Security](#security)
11. [Troubleshooting](#troubleshooting)
12. [Best Practices](#best-practices)

---

## Overview

The Manus AI infrastructure layer provides three critical systems:

### 🔄 Job Queue System (Celery)
- **Purpose**: Execute long-running tasks asynchronously
- **Benefits**: Non-blocking API, horizontal scaling, automatic retries
- **Use cases**: Agent execution, data processing, report generation

### ⚡ Caching Layer (Redis)
- **Purpose**: Reduce costs and improve performance
- **Benefits**: 80%+ cost savings, 10x faster responses
- **Use cases**: LLM responses, embeddings, query results

### 📡 Event System (WebSockets + Webhooks)
- **Purpose**: Real-time notifications and integrations
- **Benefits**: Event-driven architecture, external integrations
- **Use cases**: Progress tracking, Slack notifications, custom triggers

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Manus AI API                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │   Jobs     │  │   Cache    │  │   Events   │                │
│  │   Manager  │  │   Manager  │  │   Manager  │                │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                │
└────────┼───────────────┼───────────────┼────────────────────────┘
         │               │               │
         ▼               ▼               ▼
┌────────────────┐ ┌───────────┐ ┌──────────────┐
│ Redis (Broker) │ │   Redis   │ │  Event Bus   │
│  + Result      │ │  (Cache)  │ │  (In-Memory) │
│   Backend      │ │           │ │              │
└────────┬───────┘ └───────────┘ └──────┬───────┘
         │                               │
         ▼                               ▼
┌─────────────────┐              ┌──────────────┐
│ Celery Workers  │              │  Webhooks    │
│  - Worker 1     │              │  - Slack     │
│  - Worker 2     │              │  - Discord   │
│  - Worker 3     │              │  - Custom    │
│  - Worker N     │              └──────────────┘
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Celery Beat    │
│  (Scheduler)    │
└─────────────────┘
```

---

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Start infrastructure services
docker-compose up -d redis mongodb qdrant

# Start Celery workers
docker-compose up -d celery_worker celery_beat flower

# Verify services are running
docker-compose ps
```

### 2. Basic Usage

```python
from manus_ai.core.jobs import get_job_manager
from manus_ai.core.cache import get_llm_cache
from manus_ai.core.events import get_event_emitter

# Submit background job
job_manager = get_job_manager()
job_id = job_manager.submit_job(
    task_name="execute_agent_async",
    args=["research_agent"],
    kwargs={"query": "AI trends"}
)

# Use LLM cache
llm_cache = get_llm_cache()
cached_response = await llm_cache.get_response(
    prompt="What is AI?",
    model="gpt-4"
)

# Emit event
event_emitter = get_event_emitter()
await event_emitter.agent_completed(
    agent_name="research_agent",
    result={"data": "results"},
    duration_ms=5000
)
```

### 3. Access Dashboards

- **Flower** (Celery monitoring): http://localhost:5555
- **Prometheus** (Metrics): http://localhost:9090
- **Grafana** (Dashboards): http://localhost:3001

---

## Job Queue System

### Core Concepts

#### Job Submission

```python
from manus_ai.core.jobs import get_job_manager, JobPriority

job_manager = get_job_manager()

# Simple job
job_id = job_manager.submit_job(
    task_name="process_large_file",
    args=["/path/to/file.csv"],
    priority=JobPriority.HIGH
)

# Delayed job (run in 1 hour)
job_id = job_manager.submit_job(
    task_name="send_notification",
    kwargs={"user_id": "123", "message": "Hello"},
    countdown=3600  # seconds
)

# Scheduled job (run at specific time)
from datetime import datetime, timedelta
eta = datetime.utcnow() + timedelta(hours=24)

job_id = job_manager.submit_job(
    task_name="generate_report",
    kwargs={"report_type": "monthly"},
    eta=eta
)
```

#### Job Status Monitoring

```python
# Check job status
result = job_manager.get_job_status(job_id)

print(f"Status: {result.status}")
print(f"Result: {result.result}")
print(f"Error: {result.error}")
print(f"Retries: {result.retries}")

# Cancel pending job
success = job_manager.cancel_job(job_id)

# List active jobs
active_jobs = job_manager.get_active_jobs()
for job in active_jobs:
    print(f"{job['job_id']}: {job['task']} on {job['worker']}")
```

#### Creating Custom Tasks

```python
from manus_ai.core.jobs import celery_app, BaseTask

@celery_app.task(base=BaseTask, bind=True, max_retries=3)
def my_custom_task(self, data: dict):
    """Custom background task"""
    try:
        # Your processing logic
        result = process_data(data)
        return {"status": "success", "result": result}
    except Exception as e:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```

#### Scheduled Tasks (Cron-like)

```python
from manus_ai.core.jobs import get_scheduled_jobs_manager, ScheduledJob

scheduler = get_scheduled_jobs_manager()

# Daily cleanup at 2 AM
scheduler.add_schedule(ScheduledJob(
    name="daily_cleanup",
    task="cleanup_old_data",
    schedule="0 2 * * *",  # Cron expression
    description="Clean up old records"
))

# Weekly reports every Monday at 9 AM
scheduler.add_schedule(ScheduledJob(
    name="weekly_reports",
    task="generate_report",
    schedule="0 9 * * 1",
    kwargs={"report_type": "weekly"}
))

# List all scheduled jobs
schedules = scheduler.list_schedules()
```

### Built-in Tasks

| Task Name | Description | Retry Policy |
|-----------|-------------|--------------|
| `execute_agent_async` | Run agent asynchronously | 3 retries, exponential backoff |
| `execute_workflow_async` | Execute workflow | 2 retries, 120s delay |
| `process_large_file` | Process large files | No retry |
| `generate_report` | Generate PDF/Excel reports | No retry |
| `send_notification` | Send email/SMS/push | 5 retries, 60s delay |
| `cleanup_expired_sessions` | Clean sessions | Scheduled hourly |
| `compute_daily_analytics` | Daily analytics | Scheduled daily 3 AM |

---

## Caching Layer

### Cache Namespaces

```python
from manus_ai.core.cache import CacheNamespace

# Available namespaces:
# - LLM_RESPONSES: LLM API responses
# - EMBEDDINGS: Text embeddings
# - VECTOR_SEARCH: Vector search results
# - API_RESPONSES: External API calls
# - USER_SESSIONS: User session data
# - QUERY_RESULTS: Database queries
# - FILE_METADATA: File information
# - ANALYTICS: Analytics data
```

### LLM Response Caching

```python
from manus_ai.core.cache import get_llm_cache

llm_cache = get_llm_cache()

# Try to get cached response
response = await llm_cache.get_response(
    prompt="Explain quantum computing",
    model="gpt-4",
    temperature=0.7,
    max_tokens=1000
)

if response:
    print(f"Cache HIT! Saved $0.01")
else:
    # Call LLM API
    response = await llm_api.complete(prompt)

    # Cache for future requests
    await llm_cache.cache_response(
        prompt="Explain quantum computing",
        response=response,
        model="gpt-4",
        temperature=0.7,
        ttl=86400  # 24 hours
    )

# Get cost savings
savings = await llm_cache.get_cost_savings()
print(f"Total saved: ${savings['estimated_cost_saved_usd']}")
print(f"Hit rate: {savings['hit_rate_percent']}%")
```

### Embedding Caching

```python
from manus_ai.core.cache import get_embedding_cache

embedding_cache = get_embedding_cache()

# Single embedding
embedding = await embedding_cache.get_embedding(
    text="Hello world",
    model="all-MiniLM-L6-v2"
)

if not embedding:
    # Generate and cache
    embedding = model.encode("Hello world")
    await embedding_cache.cache_embedding(
        text="Hello world",
        embedding=embedding.tolist(),
        model="all-MiniLM-L6-v2",
        ttl=604800  # 7 days
    )

# Batch operations
texts = ["Text 1", "Text 2", "Text 3"]
cached_embeddings = await embedding_cache.get_batch(texts)
```

### General Caching

```python
from manus_ai.core.cache import get_cache_manager, CacheNamespace

cache = get_cache_manager()

# Set value
await cache.set(
    namespace=CacheNamespace.QUERY_RESULTS,
    identifier="user_profile_123",
    value={"name": "John", "email": "john@example.com"},
    ttl=300  # 5 minutes
)

# Get value
value = await cache.get(
    namespace=CacheNamespace.QUERY_RESULTS,
    identifier="user_profile_123"
)

# Delete value
await cache.delete(
    namespace=CacheNamespace.QUERY_RESULTS,
    identifier="user_profile_123"
)

# Clear entire namespace
keys_cleared = await cache.clear_namespace(CacheNamespace.QUERY_RESULTS)
```

### Cache Statistics

```python
# Get cache stats
stats = await cache.get_stats()

print(f"Cache hits: {stats.hits}")
print(f"Cache misses: {stats.misses}")
print(f"Hit rate: {stats.hit_rate}%")
print(f"Total keys: {stats.total_keys}")
print(f"Memory used: {stats.memory_used_mb}MB")
```

### Cache Warming

```python
from manus_ai.core.cache import CacheWarmer

warmer = CacheWarmer(get_cache_manager())

# Warm common LLM prompts
common_prompts = [
    {"prompt": "What is AI?", "response": "AI is...", "model": "gpt-4"},
    {"prompt": "Explain ML", "response": "ML is...", "model": "gpt-4"}
]

await warmer.warm_llm_responses(common_prompts)
```

---

## Event & Webhook System

### Event Types

```python
from manus_ai.core.events import EventType

# Available event types:
# SESSION_CREATED, SESSION_UPDATED, SESSION_DELETED
# AGENT_STARTED, AGENT_COMPLETED, AGENT_FAILED
# WORKFLOW_STARTED, WORKFLOW_COMPLETED, WORKFLOW_FAILED
# USER_CREATED, USER_UPDATED, USER_LOGIN, USER_LOGOUT
# FILE_UPLOADED, FILE_PROCESSED, FILE_DELETED
# BUDGET_WARNING, BUDGET_EXCEEDED
# PLUGIN_LOADED, PLUGIN_UNLOADED
# SYSTEM_ERROR, SYSTEM_WARNING
# CUSTOM
```

### Subscribing to Events

```python
from manus_ai.core.events import get_event_bus, EventType

event_bus = get_event_bus()

# Define event handler
async def on_agent_completed(event):
    print(f"Agent {event.data['agent']} completed!")
    print(f"Result: {event.data['result']}")

    # Send to analytics
    await analytics.track_completion(event)

# Subscribe
event_bus.subscribe(EventType.AGENT_COMPLETED, on_agent_completed)

# Unsubscribe
event_bus.unsubscribe(EventType.AGENT_COMPLETED, on_agent_completed)
```

### Emitting Events

```python
from manus_ai.core.events import get_event_emitter, EventType

emitter = get_event_emitter()

# Emit predefined event
await emitter.agent_completed(
    agent_name="research_agent",
    result={"data": "analysis complete"},
    duration_ms=5000,
    session_id="session_123"
)

# Emit custom event
await emitter.emit(
    event_type=EventType.CUSTOM,
    data={
        "action": "custom_action",
        "metadata": {"key": "value"}
    },
    user_id="user_123",
    metadata={"source": "api"}
)
```

### Webhook Registration

```python
from manus_ai.core.events import get_webhook_manager, EventType

webhook_manager = get_webhook_manager()

# Register webhook
webhook = await webhook_manager.register_webhook(
    url="https://your-app.com/webhooks/manus-ai",
    events=[
        EventType.AGENT_COMPLETED,
        EventType.WORKFLOW_COMPLETED,
        EventType.BUDGET_WARNING
    ],
    secret="your_webhook_secret_key",
    description="Main application webhooks",
    headers={
        "X-Custom-Header": "value"
    }
)

print(f"Webhook ID: {webhook.id}")
print(f"Secret: {webhook.secret}")
```

### Webhook Delivery

```python
# List webhooks
webhooks = webhook_manager.list_webhooks(active_only=True)

# Get webhook details
webhook = webhook_manager.get_webhook("webhook_id")

# Get delivery history
deliveries = webhook_manager.get_webhook_deliveries("webhook_id", limit=50)

for delivery in deliveries:
    print(f"Delivery {delivery.id}:")
    print(f"  Status: {delivery.status}")
    print(f"  Attempts: {delivery.attempts}")
    print(f"  Response code: {delivery.response_code}")

    if delivery.error:
        print(f"  Error: {delivery.error}")

# Retry failed delivery
success = await webhook_manager.retry_delivery("delivery_id")
```

### Webhook Signature Verification

When your webhook endpoint receives a request:

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload: dict, signature: str, secret: str) -> bool:
    """Verify webhook signature"""
    payload_json = json.dumps(payload, sort_keys=True)
    expected_signature = hmac.new(
        secret.encode(),
        payload_json.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)

# In your webhook endpoint:
@app.post("/webhooks/manus-ai")
async def handle_webhook(request: Request):
    payload = await request.json()
    signature = request.headers.get("X-Webhook-Signature")

    if not verify_webhook_signature(payload, signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Process webhook
    event_type = request.headers.get("X-Event-Type")
    event_id = request.headers.get("X-Event-ID")

    await process_event(event_type, payload)

    return {"status": "received"}
```

---

## Production Deployment

### Environment Variables

```bash
# Redis Configuration
REDIS_URL=redis://redis:6379
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Worker Configuration
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_MAX_TASKS_PER_CHILD=1000

# Task Limits
CELERY_TASK_TIME_LIMIT=3600  # 1 hour hard limit
CELERY_TASK_SOFT_TIME_LIMIT=3000  # 50 min soft limit

# Cache Configuration
CACHE_DEFAULT_TTL=3600
CACHE_MAX_SIZE_MB=1000
CACHE_STRATEGY=lru  # lru, lfu, fifo, ttl

# Monitoring
FLOWER_BASIC_AUTH=admin:your_password_here
PROMETHEUS_PORT=9090
```

### Docker Compose Production

```yaml
services:
  # Redis with persistence
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    restart: always

  # Celery workers (scale horizontally)
  celery_worker:
    build:
      context: ./manus_ai
      dockerfile: Dockerfile.celery
    deploy:
      replicas: 4  # Run 4 workers
      resources:
        limits:
          cpus: '1'
          memory: 2G
    restart: always

  # Celery beat (single instance)
  celery_beat:
    deploy:
      replicas: 1  # Only one beat scheduler
    restart: always

  # Flower with authentication
  flower:
    environment:
      - FLOWER_BASIC_AUTH=admin:${FLOWER_PASSWORD}
      - FLOWER_UNAUTHENTICATED_API=false
    restart: always
```

### Scaling Workers

```bash
# Scale to 10 workers
docker-compose up -d --scale celery_worker=10

# Scale down to 2 workers
docker-compose up -d --scale celery_worker=2

# Check worker status
docker-compose exec celery_worker celery -A manus_ai.core.jobs:celery_app inspect stats
```

### Health Checks

```python
# Health check endpoint
@app.get("/health/infrastructure")
async def infrastructure_health():
    """Check infrastructure health"""
    health = {
        "redis": "unknown",
        "celery_workers": "unknown",
        "cache": "unknown"
    }

    # Check Redis
    try:
        cache = get_cache_manager()
        await cache.connect()
        health["redis"] = "healthy"
    except Exception as e:
        health["redis"] = f"unhealthy: {e}"

    # Check Celery workers
    try:
        job_manager = get_job_manager()
        stats = job_manager.get_queue_stats()
        health["celery_workers"] = f"healthy ({stats['workers']} workers)"
    except Exception as e:
        health["celery_workers"] = f"unhealthy: {e}"

    # Check cache
    try:
        stats = await cache.get_stats()
        health["cache"] = f"healthy ({stats.total_keys} keys)"
    except Exception as e:
        health["cache"] = f"unhealthy: {e}"

    status_code = 200 if all("healthy" in v for v in health.values()) else 503
    return JSONResponse(content=health, status_code=status_code)
```

---

## Monitoring & Observability

### Flower Dashboard

Access: `http://localhost:5555`

**Features:**
- Real-time worker monitoring
- Task progress tracking
- Queue length graphs
- Worker pool size
- Task success/failure rates

**Key Metrics:**
- Active tasks
- Processed tasks
- Failed tasks
- Task execution time
- Worker utilization

### Prometheus Metrics

The system exports metrics at `/metrics` endpoint:

```prometheus
# Job queue metrics
celery_tasks_total{state="success"}
celery_tasks_total{state="failure"}
celery_task_execution_time_seconds
celery_worker_tasks_active

# Cache metrics
cache_hits_total
cache_misses_total
cache_hit_rate
cache_memory_bytes
cache_keys_total

# Event metrics
events_emitted_total{event_type="agent.completed"}
webhook_deliveries_total{status="sent"}
webhook_delivery_latency_seconds
```

### Grafana Dashboards

Import the provided dashboard configurations:

- `dashboards/job_queue.json` - Celery job metrics
- `dashboards/cache_performance.json` - Cache hit rates and savings
- `dashboards/webhook_deliveries.json` - Webhook success rates

---

## Performance Tuning

### Job Queue Optimization

```python
# Optimize worker concurrency
# CPU-bound tasks: concurrency = num_cores
# I/O-bound tasks: concurrency = num_cores * 2-4

# Configure in docker-compose.yml
environment:
  - CELERY_WORKER_CONCURRENCY=8  # 4 cores * 2

# Task rate limiting
@celery_app.task(rate_limit='10/m')  # 10 tasks per minute
def rate_limited_task():
    pass

# Task routing to specific queues
@celery_app.task(queue='high_priority')
def critical_task():
    pass

@celery_app.task(queue='low_priority')
def batch_task():
    pass
```

### Cache Optimization

```python
# Optimal TTL values
TTL_VALUES = {
    "llm_responses": 86400,      # 24 hours (stable content)
    "embeddings": 604800,         # 7 days (rarely change)
    "api_responses": 300,         # 5 minutes (fresh data)
    "user_sessions": 3600,        # 1 hour (active sessions)
    "query_results": 60,          # 1 minute (frequently updated)
}

# Cache key design (for better hit rates)
def generate_cache_key(prompt: str, **params):
    """Generate deterministic cache key"""
    # Normalize prompt
    prompt_normalized = prompt.lower().strip()

    # Sort parameters
    params_sorted = json.dumps(params, sort_keys=True)

    # Hash for shorter keys
    key_hash = hashlib.md5(f"{prompt_normalized}:{params_sorted}".encode()).hexdigest()
    return key_hash

# Batch operations for efficiency
texts = ["text1", "text2", "text3"]
embeddings = await embedding_cache.get_batch(texts)
missing = [t for t, e in embeddings.items() if e is None]

if missing:
    # Generate missing embeddings
    new_embeddings = model.encode(missing)
    await embedding_cache.cache_batch(dict(zip(missing, new_embeddings)))
```

### Redis Optimization

```redis
# redis.conf optimizations
maxmemory 2gb
maxmemory-policy allkeys-lru  # Evict least recently used
save 900 1  # Persist to disk
appendonly yes  # Enable AOF for durability

# Connection pooling
redis-cli CONFIG SET tcp-keepalive 60
redis-cli CONFIG SET timeout 300
```

---

## Security

### Webhook Security

```python
# Always use HMAC signatures
webhook = await webhook_manager.register_webhook(
    url="https://your-app.com/webhooks",
    events=[EventType.AGENT_COMPLETED],
    secret=secrets.token_urlsafe(32),  # Strong secret
)

# Validate signatures on receiver side
def verify_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        json.dumps(payload, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Cache Security

```python
# Never cache sensitive data without encryption
from cryptography.fernet import Fernet

cipher = Fernet(ENCRYPTION_KEY)

# Encrypt before caching
sensitive_data = {"ssn": "123-45-6789"}
encrypted = cipher.encrypt(json.dumps(sensitive_data).encode())
await cache.set("user_sensitive", encrypted, ttl=300)

# Decrypt after retrieval
encrypted_data = await cache.get("user_sensitive")
if encrypted_data:
    decrypted = cipher.decrypt(encrypted_data)
    sensitive_data = json.loads(decrypted)
```

### Job Queue Security

```python
# Validate task parameters
@celery_app.task
def secure_task(user_id: str, action: str):
    # Validate inputs
    if not user_id or not action:
        raise ValueError("Invalid parameters")

    # Check permissions
    if not has_permission(user_id, action):
        raise PermissionError("Unauthorized")

    # Execute
    return perform_action(action)
```

---

## Troubleshooting

### Common Issues

#### Workers Not Starting

```bash
# Check logs
docker-compose logs celery_worker

# Common causes:
# 1. Redis not accessible
docker-compose exec celery_worker ping redis

# 2. Import errors
docker-compose exec celery_worker python -c "from manus_ai.core.jobs import celery_app"

# 3. Permission issues
docker-compose exec celery_worker ls -la /app
```

#### Cache Misses

```python
# Debug cache keys
from manus_ai.core.cache import get_cache_manager, CacheNamespace

cache = get_cache_manager()

# List all keys in namespace
pattern = f"{CacheNamespace.LLM_RESPONSES.value}:*"
# Use Redis CLI: redis-cli KEYS "llm_responses:*"

# Check if key exists
exists = await cache.redis.exists("llm_responses:query_hash")
print(f"Key exists: {exists}")

# Get TTL
ttl = await cache.redis.ttl("llm_responses:query_hash")
print(f"TTL: {ttl} seconds")
```

#### Webhook Failures

```python
# Check delivery status
deliveries = webhook_manager.get_webhook_deliveries("webhook_id")

for delivery in deliveries:
    if delivery.status == WebhookStatus.FAILED:
        print(f"Failed delivery {delivery.id}:")
        print(f"  Error: {delivery.error}")
        print(f"  Response: {delivery.response_body}")
        print(f"  Attempts: {delivery.attempts}")

        # Retry manually
        await webhook_manager.retry_delivery(delivery.id)
```

---

## Best Practices

### 1. Use Appropriate TTL Values

```python
# Short TTL for dynamic data
await cache.set(namespace, "stock_price", value, ttl=60)

# Long TTL for stable data
await cache.set(namespace, "company_info", value, ttl=86400)

# No TTL for permanent data (use with caution)
await cache.set(namespace, "constants", value, ttl=None)
```

### 2. Handle Job Failures Gracefully

```python
@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,))
def resilient_task(self, data):
    try:
        return process(data)
    except CriticalError as e:
        # Don't retry critical errors
        raise
    except TemporaryError as e:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```

### 3. Monitor Cost Savings

```python
# Track cache ROI
async def calculate_cache_roi():
    savings = await llm_cache.get_cost_savings()

    # Redis cost (estimate)
    redis_cost_monthly = 50  # $50/month

    # LLM cost without cache
    total_requests = savings['cache_hits'] + savings['cache_misses']
    cost_without_cache = total_requests * 0.01

    # ROI
    monthly_savings = savings['estimated_cost_saved_usd'] - redis_cost_monthly
    roi = (monthly_savings / redis_cost_monthly) * 100

    print(f"ROI: {roi}%")
    print(f"Net savings: ${monthly_savings}/month")
```

### 4. Implement Circuit Breakers

```python
from datetime import datetime, timedelta

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure = None
        self.state = "closed"  # closed, open, half_open

    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if datetime.utcnow() - self.last_failure > timedelta(seconds=self.timeout):
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    def on_success(self):
        self.failures = 0
        self.state = "closed"

    def on_failure(self):
        self.failures += 1
        self.last_failure = datetime.utcnow()

        if self.failures >= self.failure_threshold:
            self.state = "open"
```

### 5. Use Dead Letter Queues

```python
# Configure DLQ for failed tasks
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    ignore_result=False
)
def task_with_dlq(self, data):
    try:
        return process(data)
    except Exception as e:
        if self.request.retries >= self.max_retries:
            # Send to DLQ
            send_to_dlq(self.request.id, data, str(e))
        raise self.retry(exc=e)
```

---

## API Reference

See `INFRASTRUCTURE_API.md` for complete API documentation.

---

## Support

- **Documentation**: https://docs.manusai.dev
- **Issues**: https://github.com/manusai/issues
- **Slack**: https://manusai.slack.com

---

**Last Updated**: 2024-01-13
**Version**: 2.0.0
