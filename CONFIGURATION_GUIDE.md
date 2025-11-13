# 🔧 Manus AI Clone - Complete Configuration Guide

Comprehensive configuration guide for all enhanced features.

---

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [Vector Database Setup](#vector-database-setup)
3. [Image Generation Setup](#image-generation-setup)
4. [Authentication Configuration](#authentication-configuration)
5. [Rate Limiting Configuration](#rate-limiting-configuration)
6. [Monitoring Setup](#monitoring-setup)
7. [Plugin Configuration](#plugin-configuration)
8. [Workflow Configuration](#workflow-configuration)
9. [Production Deployment](#production-deployment)

---

## Environment Variables

Create `.env` file in `manus_ai/` directory:

```bash
# ===========================================
# LLM API Keys
# ===========================================
GEMINI_API_KEY=your_gemini_api_key_here
PERPLEXITY_API_KEY=your_perplexity_api_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here  # Optional
OPENAI_API_KEY=your_openai_api_key_here     # Optional, for DALL-E

# ===========================================
# Image Generation Providers
# ===========================================
# OpenAI (DALL-E) - Already set above as OPENAI_API_KEY
REPLICATE_API_KEY=your_replicate_key_here   # For Stable Diffusion
STABILITY_API_KEY=your_stability_key_here   # Optional, for Stability AI

# ===========================================
# Database Configuration
# ===========================================
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=manus_ai
REDIS_URL=redis://localhost:6379

# ===========================================
# Vector Database (Qdrant)
# ===========================================
QDRANT_URL=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=  # Optional, for cloud Qdrant
EMBEDDING_MODEL=all-MiniLM-L6-v2  # sentence-transformers model

# ===========================================
# Security & Authentication
# ===========================================
JWT_SECRET=your_random_secret_key_min_32_chars_12345678
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Password hashing
BCRYPT_ROUNDS=12  # Higher = more secure but slower

# Session configuration
SESSION_TIMEOUT_MINUTES=1440  # 24 hours
MAX_SESSIONS_PER_USER=5

# ===========================================
# Rate Limiting
# ===========================================
# Format: ENDPOINT_NAME_LIMIT=requests:period_seconds:block_duration
RATE_LIMIT_API=100:60:60                    # 100 req/min, block 60s
RATE_LIMIT_CHAT=50:60:120                   # 50 req/min, block 120s
RATE_LIMIT_AGENTS=20:60:300                 # 20 req/min, block 300s
RATE_LIMIT_IMAGES=10:300:600                # 10 req/5min, block 600s
RATE_LIMIT_FILES=20:60:180                  # 20 req/min, block 180s

# ===========================================
# Budget & Cost Management
# ===========================================
# Default budget limits (USD)
BUDGET_DAILY_LIMIT=50.00
BUDGET_MONTHLY_LIMIT=1000.00
BUDGET_ALERT_THRESHOLD=0.8                  # Alert at 80%
BUDGET_HARD_LIMIT=true                      # Block when exceeded

# Provider-specific cost tracking (USD per 1M tokens)
COST_GEMINI_FLASH_INPUT=0.10
COST_GEMINI_FLASH_OUTPUT=0.40
COST_GEMINI_PRO_INPUT=3.50
COST_GEMINI_PRO_OUTPUT=10.50

# ===========================================
# Multi-Modal Configuration
# ===========================================
MAX_FILE_SIZE_MB=50
MAX_IMAGE_SIZE_MB=10
ALLOWED_FILE_TYPES=image/jpeg,image/png,application/pdf,text/plain
THUMBNAIL_SIZE=256                          # pixels
ENABLE_OCR=false                            # Requires additional setup

# ===========================================
# Monitoring & Analytics
# ===========================================
ENABLE_MONITORING=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
METRICS_RETENTION_DAYS=30
LOG_LEVEL=INFO                              # DEBUG, INFO, WARNING, ERROR

# ===========================================
# Plugin System
# ===========================================
PLUGIN_DIRECTORY=plugins
ENABLE_PLUGIN_HOT_RELOAD=true
PLUGIN_TIMEOUT_SECONDS=300

# ===========================================
# Workflow Configuration
# ===========================================
WORKFLOW_DIRECTORY=workflows
MAX_WORKFLOW_STEPS=50
WORKFLOW_TIMEOUT_SECONDS=3600               # 1 hour
ENABLE_PARALLEL_EXECUTION=true
MAX_PARALLEL_STEPS=5

# ===========================================
# API Configuration
# ===========================================
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RELOAD=false                            # Set true for development
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# ===========================================
# Development / Production
# ===========================================
ENVIRONMENT=production                      # development or production
DEBUG=false
TESTING=false
```

---

## Vector Database Setup

### Local Qdrant (Docker)

```bash
# Start Qdrant
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant

# Verify it's running
curl http://localhost:6333/
```

### Qdrant Cloud

```bash
# Set environment variables
QDRANT_URL=your-cluster.cloud.qdrant.io
QDRANT_PORT=6333
QDRANT_API_KEY=your_cloud_api_key
```

### Python Configuration

```python
from manus_ai.core.vector_store import VectorStore

# Local Qdrant
vector_store = VectorStore(
    collection_name="my_knowledge",
    embedding_model="all-MiniLM-L6-v2",
    qdrant_url="localhost",
    qdrant_port=6333
)

# Qdrant Cloud
vector_store = VectorStore(
    collection_name="my_knowledge",
    embedding_model="all-MiniLM-L6-v2",
    qdrant_url="your-cluster.cloud.qdrant.io",
    qdrant_port=6333,
    api_key="your_api_key"
)
```

### Embedding Models

Choose embedding model based on your needs:

| Model | Dimensions | Speed | Quality | Use Case |
|-------|-----------|-------|---------|----------|
| all-MiniLM-L6-v2 | 384 | Fast | Good | General purpose |
| all-mpnet-base-v2 | 768 | Medium | Better | Higher quality |
| multi-qa-mpnet-base-dot-v1 | 768 | Medium | Better | Q&A tasks |

```python
vector_store = VectorStore(
    embedding_model="all-mpnet-base-v2"  # Higher quality
)
```

---

## Image Generation Setup

### DALL-E (OpenAI)

1. Get API key: https://platform.openai.com/api-keys
2. Set environment variable: `OPENAI_API_KEY=sk-...`
3. Usage:

```python
from manus_ai.agents.image_agent import ImageGenerationAgent, ImageProvider

agent = ImageGenerationAgent()

result = await agent.execute({
    "prompt": "A beautiful landscape",
    "provider": "dalle-3",
    "size": "1024x1024",
    "quality": "hd"
})
```

### Stable Diffusion (Replicate)

1. Get API key: https://replicate.com/account
2. Set environment variable: `REPLICATE_API_KEY=r8_...`
3. Usage:

```python
result = await agent.execute({
    "prompt": "A futuristic city",
    "provider": "stable-diffusion-xl",
    "size": "1024x1024",
    "negative_prompt": "blurry, low quality"
})
```

### Cost Optimization

```python
# Use cheaper provider for testing
result = await agent.execute({
    "prompt": "test image",
    "provider": "stable-diffusion-2",  # Cheaper than DALL-E
    "enhance_prompt": False  # Save LLM costs
})
```

---

## Authentication Configuration

### Create Admin User

```python
from manus_ai.core.auth import get_auth_manager, UserRole

auth = get_auth_manager()

admin = await auth.create_user(
    username="admin",
    email="admin@example.com",
    password="SecurePassword123!",
    role=UserRole.ADMIN
)
```

### Role Configuration

Customize role permissions in `manus_ai/core/auth.py`:

```python
ROLE_PERMISSIONS = {
    UserRole.ADMIN: {
        Permission.CREATE_SESSION,
        Permission.EXECUTE_AGENT,
        Permission.MANAGE_USERS,
        # ... all permissions
    },
    UserRole.CUSTOM_ROLE: {
        Permission.CREATE_SESSION,
        Permission.EXECUTE_AGENT,
        # custom permissions
    }
}
```

### JWT Configuration

```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set in .env
JWT_SECRET=generated_secret_key_here
```

### API Key Management

```python
# Create API key for user
api_key_obj, plain_key = await auth.create_api_key(
    user=user,
    name="Production API Key",
    expires_in_days=365,
    rate_limit=1000  # requests per minute
)

print(f"API Key: {plain_key}")  # Save this!
```

---

## Rate Limiting Configuration

### Custom Rate Limits

```python
from manus_ai.core.security import get_security_manager, RateLimitRule, RateLimitStrategy

security = get_security_manager()

# Add custom rule
security.add_rule(RateLimitRule(
    name="premium_tier",
    limit=1000,  # requests
    period_seconds=60,  # per minute
    strategy=RateLimitStrategy.SLIDING_WINDOW,
    block_duration_seconds=60
))
```

### Per-User Limits

```python
# Different limits for different users
user_tiers = {
    "free": {"limit": 50, "period": 60},
    "premium": {"limit": 500, "period": 60},
    "enterprise": {"limit": 5000, "period": 60}
}

# Apply based on user tier
user_tier = user.metadata.get("tier", "free")
tier_config = user_tiers[user_tier]

security.add_rule(RateLimitRule(
    name=f"user_{user.user_id}",
    limit=tier_config["limit"],
    period_seconds=tier_config["period"]
))
```

---

## Monitoring Setup

### Prometheus Configuration

`prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'manus_ai'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboards

Access: http://localhost:3001

Default credentials:
- Username: admin
- Password: admin (change immediately)

Import dashboard:
1. Go to Dashboards → Import
2. Use template ID or JSON
3. Configure data source (Prometheus)

### Application Metrics

```python
from manus_ai.core.analytics import get_monitoring

monitoring = get_monitoring()

# Custom metrics
monitoring.performance.increment_counter("custom_event")
monitoring.performance.set_gauge("active_users", 42)
monitoring.performance.record_timer("operation_time", 123.45)
```

---

## Plugin Configuration

### Plugin Directory Structure

```
plugins/
├── __init__.py
├── my_plugin.py
├── another_plugin.py
└── config/
    ├── my_plugin.yml
    └── another_plugin.yml
```

### Plugin Configuration File

`plugins/config/my_plugin.yml`:

```yaml
plugin_id: my_plugin
enabled: true
auto_load: true

config:
  api_key: ${ENV_VAR_NAME}  # Load from environment
  option1: value1
  option2: value2

permissions:
  - execute_agent
  - read_data

rate_limit:
  requests_per_minute: 60

dependencies:
  - numpy
  - requests
```

### Load Plugins Programmatically

```python
from manus_ai.core.plugin_system import get_plugin_manager

manager = get_plugin_manager()

# Discover all plugins
plugins = await manager.discover_plugins()

# Load specific plugin
await manager.load_plugin(
    "my_plugin",
    config={"api_key": "xxx"}
)

# Execute plugin
result = await manager.execute_agent(
    "MyPluginAgent",
    {"input": "data"}
)
```

---

## Workflow Configuration

### Workflow Template File

`workflows/data_pipeline.json`:

```json
{
  "name": "Data Analysis Pipeline",
  "description": "End-to-end data analysis workflow",
  "category": "data",
  "tags": ["analytics", "reporting"],
  "steps": [
    {
      "step_id": "fetch_data",
      "step_type": "agent_execution",
      "name": "Fetch Data",
      "agent_name": "DataAgent",
      "parameters": {
        "source": "$input.data_source",
        "filters": "$input.filters"
      }
    },
    {
      "step_id": "analyze",
      "step_type": "agent_execution",
      "name": "Analyze Data",
      "agent_name": "DataAgent",
      "parameters": {
        "data": "$fetch_data.result",
        "analysis_type": "statistical"
      },
      "depends_on": ["fetch_data"]
    },
    {
      "step_id": "generate_report",
      "step_type": "agent_execution",
      "name": "Generate Report",
      "agent_name": "FileAgent",
      "parameters": {
        "template": "report",
        "data": "$analyze.result"
      },
      "depends_on": ["analyze"]
    }
  ]
}
```

### Load and Execute Workflow

```python
from manus_ai.core.workflows import get_workflow_library, WorkflowEngine

library = get_workflow_library()
engine = WorkflowEngine()

# Load template
template = library.get_template("data_pipeline")

# Execute
execution = await engine.execute_workflow(
    template,
    input_data={
        "data_source": "database",
        "filters": {"date": "2024-01-01"}
    }
)

print(f"Status: {execution.status}")
print(f"Results: {execution.output_data}")
```

---

## Production Deployment

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api

# Scale API service
docker-compose up -d --scale api=4
```

### Environment-specific Configuration

```bash
# Production
cp .env.production .env
docker-compose -f docker-compose.prod.yml up -d

# Staging
cp .env.staging .env
docker-compose -f docker-compose.staging.yml up -d
```

### Health Checks

```bash
# API health
curl http://localhost:8000/api/analytics/health

# Services health
docker-compose ps
docker-compose exec api python -c "from manus_ai.core.analytics import get_monitoring; import asyncio; asyncio.run(get_monitoring().get_system_health())"
```

### Backup Configuration

```bash
# Backup MongoDB
docker-compose exec mongodb mongodump --out=/backup

# Backup Qdrant
docker-compose exec qdrant tar -czf /backup/qdrant.tar.gz /qdrant/storage

# Backup Redis
docker-compose exec redis redis-cli --rdb /backup/dump.rdb
```

### SSL/TLS Configuration

```yaml
# docker-compose.yml
api:
  environment:
    - SSL_CERT_PATH=/certs/cert.pem
    - SSL_KEY_PATH=/certs/key.pem
  volumes:
    - ./certs:/certs:ro
```

### Scaling Considerations

1. **API Service**: Scale horizontally with load balancer
2. **MongoDB**: Use replica set for high availability
3. **Redis**: Use Redis Cluster or Sentinel
4. **Qdrant**: Use distributed mode for large datasets

```yaml
# Load balancer (nginx)
upstream manus_api {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}
```

---

## Security Checklist

- [ ] Change default admin password
- [ ] Set strong JWT secret
- [ ] Configure CORS properly
- [ ] Enable HTTPS in production
- [ ] Set up firewall rules
- [ ] Configure rate limiting
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Backup encryption
- [ ] API key rotation policy

---

## Performance Tuning

### Database Optimization

```python
# MongoDB indexes
db.sessions.createIndex({"user_id": 1})
db.sessions.createIndex({"expires_at": 1})

# Qdrant optimization
vector_store = VectorStore(
    collection_name="optimized",
    embedding_model="all-MiniLM-L6-v2",  # Faster model
    # Add HNSW parameters for better performance
)
```

### Caching Strategy

```python
# Redis caching
import redis
cache = redis.Redis(host='localhost', port=6379)

# Cache expensive operations
@cache_result(ttl=3600)  # 1 hour
async def expensive_operation():
    # ...
    pass
```

### Resource Limits

```yaml
# docker-compose.yml
api:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
      reservations:
        cpus: '1'
        memory: 2G
```

---

## Troubleshooting

### Common Issues

**Issue: Vector search not working**
```bash
# Check Qdrant is running
curl http://localhost:6333/collections

# Check collection exists
curl http://localhost:6333/collections/manus_knowledge
```

**Issue: Authentication failing**
```bash
# Check JWT secret is set
echo $JWT_SECRET

# Test user creation
python -c "from manus_ai.core.auth import get_auth_manager; ..."
```

**Issue: Rate limiting too strict**
```python
# Temporarily disable
from manus_ai.core.security import get_security_manager
security = get_security_manager()
security.rate_limiter.reset_client("client_id")
```

---

## Support & Resources

- Documentation: [ENHANCEMENTS_GUIDE.md](./ENHANCEMENTS_GUIDE.md)
- Examples: [examples/](./manus_ai/examples/)
- Issues: GitHub Issues
- API Docs: http://localhost:8000/docs

---

**Last Updated**: 2025-11-13
**Version**: 2.0.0
