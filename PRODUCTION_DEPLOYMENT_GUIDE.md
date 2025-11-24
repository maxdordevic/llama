# Manus AI - Production Deployment & Scaling Guide

**Complete guide for deploying Manus AI at enterprise scale**

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Infrastructure Requirements](#infrastructure-requirements)
3. [Environment Configuration](#environment-configuration)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Scaling Strategy](#scaling-strategy)
7. [Load Balancing](#load-balancing)
8. [Database Configuration](#database-configuration)
9. [Security Hardening](#security-hardening)
10. [Monitoring & Alerting](#monitoring--alerting)
11. [Backup & Disaster Recovery](#backup--disaster-recovery)
12. [Performance Tuning](#performance-tuning)
13. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### Configuration

- [ ] All API keys configured in `.env`
- [ ] JWT secret key changed from default
- [ ] Database credentials secured
- [ ] Redis password set
- [ ] Flower authentication configured
- [ ] CORS origins restricted
- [ ] Rate limiting enabled
- [ ] File upload limits set

### Security

- [ ] SSL/TLS certificates obtained
- [ ] Firewall rules configured
- [ ] SSH keys only (no password auth)
- [ ] Non-root user for application
- [ ] Secrets stored in vault (not .env)
- [ ] Webhook signatures enabled
- [ ] Input validation in place

### Infrastructure

- [ ] Load balancer configured
- [ ] Database backups automated
- [ ] Redis persistence enabled
- [ ] Log aggregation setup
- [ ] Monitoring dashboards created
- [ ] Alerting rules configured
- [ ] CDN for static assets

---

## Infrastructure Requirements

### Minimum Production Setup

**API Server (2x instances for HA)**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 50 GB SSD
- OS: Ubuntu 22.04 LTS

**Celery Workers (4x instances minimum)**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 20 GB SSD

**MongoDB (3x replica set)**
- CPU: 4 cores
- RAM: 16 GB
- Storage: 500 GB SSD (RAID 10)

**Redis (2x with sentinel)**
- CPU: 2 cores
- RAM: 8 GB
- Storage: 20 GB SSD

**Qdrant Vector DB**
- CPU: 4 cores
- RAM: 16 GB
- Storage: 200 GB SSD

**Load Balancer**
- CPU: 2 cores
- RAM: 4 GB

### Recommended Production Setup

For 1000+ requests/minute:

**API Servers**: 4-6 instances (8 cores, 16 GB RAM each)
**Celery Workers**: 10-20 instances (8 cores, 16 GB RAM each)
**MongoDB**: 3-node replica set (8 cores, 32 GB RAM, 1 TB SSD each)
**Redis**: 2-node with Redis Sentinel (4 cores, 16 GB RAM each)
**Qdrant**: 3-node cluster (8 cores, 32 GB RAM, 500 GB SSD each)

---

## Environment Configuration

### Production `.env` Template

```bash
# ==================== Application ====================
APP_NAME=Manus AI
APP_VERSION=2.0.0
ENVIRONMENT=production
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000
WORKERS=4

# ==================== Database ====================
MONGODB_URI=mongodb://user:pass@mongo1:27017,mongo2:27017,mongo3:27017/manus_ai?replicaSet=rs0
MONGODB_DB_NAME=manus_ai
MONGODB_MAX_POOL_SIZE=100
MONGODB_MIN_POOL_SIZE=10

# ==================== Redis ====================
REDIS_URL=redis://:your_redis_password@redis-primary:6379
REDIS_HOST=redis-primary
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_MAX_CONNECTIONS=100

# ==================== Celery ====================
CELERY_BROKER_URL=redis://:your_redis_password@redis-primary:6379/0
CELERY_RESULT_BACKEND=redis://:your_redis_password@redis-primary:6379/1
CELERY_WORKER_CONCURRENCY=8
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_MAX_TASKS_PER_CHILD=1000
CELERY_TASK_TIME_LIMIT=3600
CELERY_TASK_SOFT_TIME_LIMIT=3000

# ==================== Cache ====================
CACHE_DEFAULT_TTL=3600
CACHE_LLM_RESPONSE_TTL=86400
CACHE_EMBEDDING_TTL=604800
CACHE_MAX_SIZE_MB=2000
CACHE_STRATEGY=lru

# ==================== Vector Database ====================
QDRANT_HOST=qdrant.internal
QDRANT_PORT=6333
QDRANT_API_KEY=your_qdrant_api_key
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ==================== LLM Providers ====================
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
PERPLEXITY_API_KEY=pplx-...
DEFAULT_LLM_PROVIDER=gemini
LLM_TEMPERATURE=0.7
LLM_TIMEOUT_SECONDS=120

# ==================== Authentication ====================
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=43200
PASSWORD_MIN_LENGTH=12
BCRYPT_ROUNDS=12

# ==================== Security ====================
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW_SECONDS=60
CORS_ALLOWED_ORIGINS=["https://app.yourdomain.com"]
MAX_UPLOAD_SIZE_MB=100
ALLOWED_FILE_EXTENSIONS=[".pdf",".docx",".txt",".csv",".xlsx",".png",".jpg",".jpeg"]

# ==================== Monitoring ====================
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
FLOWER_ENABLED=true
FLOWER_PORT=5555
FLOWER_BASIC_AUTH=admin:your_secure_flower_password
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true

# ==================== Webhooks ====================
WEBHOOK_MAX_RETRIES=3
WEBHOOK_RETRY_DELAY_SECONDS=60
WEBHOOK_TIMEOUT_SECONDS=30

# ==================== Usage Tracking ====================
USAGE_TRACKING_ENABLED=true
DEFAULT_DAILY_BUDGET_USD=1000.0
DEFAULT_MONTHLY_BUDGET_USD=10000.0
BUDGET_WARNING_THRESHOLD=0.8
```

---

## Docker Deployment

### Production `docker-compose.yml`

```yaml
version: '3.8'

services:
  # API Server (scale this)
  api:
    build:
      context: .
      dockerfile: Dockerfile
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env.production
    depends_on:
      - mongodb
      - redis
      - qdrant
    volumes:
      - ./logs:/app/logs
      - api_data:/app/data
    restart: always
    networks:
      - manus_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.yourdomain.com`)"
      - "traefik.http.routers.api.tls=true"

  # Celery Workers (scale this)
  celery_worker:
    build:
      context: ./manus_ai
      dockerfile: Dockerfile.celery
    deploy:
      replicas: 8
      resources:
        limits:
          cpus: '4'
          memory: 8G
    environment:
      - CELERY_WORKER_CONCURRENCY=8
    env_file:
      - .env.production
    depends_on:
      - redis
      - mongodb
    volumes:
      - ./logs:/app/logs
      - celery_data:/app/data
    restart: always
    networks:
      - manus_network

  # Celery Beat (single instance)
  celery_beat:
    build:
      context: ./manus_ai
      dockerfile: Dockerfile.celery-beat
    deploy:
      replicas: 1
    env_file:
      - .env.production
    depends_on:
      - redis
      - celery_worker
    restart: always
    networks:
      - manus_network

  # Flower (monitoring)
  flower:
    build:
      context: ./manus_ai
      dockerfile: Dockerfile.celery
    ports:
      - "5555:5555"
    environment:
      - FLOWER_BASIC_AUTH=${FLOWER_BASIC_AUTH}
    env_file:
      - .env.production
    depends_on:
      - redis
      - celery_worker
    command: ["celery", "-A", "manus_ai.core.jobs:celery_app", "flower", "--port=5555"]
    restart: always
    networks:
      - manus_network

  # Redis (with persistence)
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD} --maxmemory 4gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    restart: always
    networks:
      - manus_network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  # MongoDB (use external replica set in production)
  mongodb:
    image: mongo:7.0
    environment:
      - MONGO_INITDB_ROOT_USERNAME=${MONGO_USERNAME}
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
    volumes:
      - mongodb_data:/data/db
      - mongodb_config:/data/configdb
    restart: always
    networks:
      - manus_network
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 16G

  # Qdrant Vector DB
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}
    restart: always
    networks:
      - manus_network

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    restart: always
    networks:
      - manus_network

  # Grafana
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./manus_ai/dashboards:/etc/grafana/provisioning/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=https://grafana.yourdomain.com
    depends_on:
      - prometheus
    restart: always
    networks:
      - manus_network

  # Traefik (Load Balancer & SSL)
  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_certs:/letsencrypt
    restart: always
    networks:
      - manus_network

volumes:
  mongodb_data:
  mongodb_config:
  redis_data:
  api_data:
  qdrant_data:
  prometheus_data:
  grafana_data:
  celery_data:
  traefik_certs:

networks:
  manus_network:
    driver: bridge
```

### Deployment Commands

```bash
# 1. Build images
docker-compose -f docker-compose.prod.yml build

# 2. Start services
docker-compose -f docker-compose.prod.yml up -d

# 3. Check status
docker-compose -f docker-compose.prod.yml ps

# 4. View logs
docker-compose -f docker-compose.prod.yml logs -f api

# 5. Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker=20

# 6. Rolling update (zero downtime)
docker-compose -f docker-compose.prod.yml up -d --no-deps --build api

# 7. Health check
curl https://api.yourdomain.com/health/detailed
```

---

## Kubernetes Deployment

### Production Kubernetes Manifests

**namespace.yaml**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: manus-ai
```

**api-deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: manus-api
  namespace: manus-ai
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: manus-api
  template:
    metadata:
      labels:
        app: manus-api
    spec:
      containers:
      - name: api
        image: yourdockerhub/manus-ai:2.0.0
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: manus-config
        - secretRef:
            name: manus-secrets
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/detailed
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

**celery-worker-deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: manus-ai
spec:
  replicas: 10
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: worker
        image: yourdockerhub/manus-ai-celery:2.0.0
        envFrom:
        - configMapRef:
            name: manus-config
        - secretRef:
            name: manus-secrets
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
```

**api-service.yaml**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: manus-api
  namespace: manus-ai
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: manus-api
```

**ingress.yaml**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: manus-ingress
  namespace: manus-ai
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "1000"
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: manus-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: manus-api
            port:
              number: 8000
```

**hpa.yaml** (Horizontal Pod Autoscaler)
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: manus-api-hpa
  namespace: manus-ai
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: manus-api
  minReplicas: 4
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Deploy to Kubernetes

```bash
# 1. Create namespace
kubectl apply -f namespace.yaml

# 2. Create secrets
kubectl create secret generic manus-secrets \
  --from-env-file=.env.production \
  -n manus-ai

# 3. Deploy all resources
kubectl apply -f k8s/

# 4. Check status
kubectl get pods -n manus-ai

# 5. Scale workers
kubectl scale deployment celery-worker --replicas=20 -n manus-ai

# 6. Rolling update
kubectl set image deployment/manus-api api=yourdockerhub/manus-ai:2.0.1 -n manus-ai

# 7. Monitor rollout
kubectl rollout status deployment/manus-api -n manus-ai

# 8. Rollback if needed
kubectl rollout undo deployment/manus-api -n manus-ai
```

---

## Scaling Strategy

### Vertical Scaling (Scale Up)

**When to scale up:**
- CPU utilization > 80%
- Memory utilization > 85%
- Slow response times
- Queue backlog growing

**How to scale up:**
```bash
# Docker Compose
# Edit docker-compose.yml resources section

# Kubernetes
kubectl set resources deployment manus-api \
  --limits=cpu=8,memory=16Gi \
  --requests=cpu=4,memory=8Gi \
  -n manus-ai
```

### Horizontal Scaling (Scale Out)

**When to scale out:**
- Request rate increasing
- Queue length > 1000
- Response time > 2s (p95)
- Worker utilization > 80%

**How to scale out:**
```bash
# Docker Compose
docker-compose up -d --scale api=6 --scale celery_worker=20

# Kubernetes (auto-scaling)
kubectl autoscale deployment manus-api \
  --cpu-percent=70 \
  --min=4 \
  --max=20 \
  -n manus-ai
```

### Auto-Scaling Rules

**API Servers:**
- Min: 2 (HA)
- Max: 20
- Scale up: CPU > 70% OR Memory > 80% OR Request rate > 100/s per pod
- Scale down: CPU < 30% AND Memory < 50% AND Request rate < 20/s per pod
- Cooldown: 5 minutes

**Celery Workers:**
- Min: 4
- Max: 50
- Scale up: Queue length > 100 OR Worker utilization > 80%
- Scale down: Queue length < 10 AND Worker utilization < 30%
- Cooldown: 10 minutes

---

## Load Balancing

### Nginx Configuration

```nginx
upstream manus_api {
    least_conn;  # Load balancing algorithm
    server api1:8000 max_fails=3 fail_timeout=30s;
    server api2:8000 max_fails=3 fail_timeout=30s;
    server api3:8000 max_fails=3 fail_timeout=30s;
    server api4:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
    limit_req zone=api_limit burst=200 nodelay;

    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 120s;

    # WebSocket support
    location /ws/ {
        proxy_pass http://manus_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 3600s;
    }

    # API endpoints
    location / {
        proxy_pass http://manus_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Caching
        proxy_cache api_cache;
        proxy_cache_valid 200 5m;
        proxy_cache_key "$request_uri";
    }

    # Health check endpoint (no rate limit)
    location /health {
        proxy_pass http://manus_api;
        limit_req off;
    }

    # Metrics endpoint (restricted)
    location /metrics {
        allow 10.0.0.0/8;  # Internal network only
        deny all;
        proxy_pass http://manus_api;
    }
}
```

---

## Database Configuration

### MongoDB Replica Set

```bash
# Initialize replica set
mongosh --host mongodb1:27017 -u admin -p password

rs.initiate({
  _id: "rs0",
  members: [
    { _id: 0, host: "mongodb1:27017", priority: 2 },
    { _id: 1, host: "mongodb2:27017", priority: 1 },
    { _id: 2, host: "mongodb3:27017", priority: 1 }
  ]
})

# Check status
rs.status()

# Connection string
mongodb://user:pass@mongodb1:27017,mongodb2:27017,mongodb3:27017/manus_ai?replicaSet=rs0&retryWrites=true
```

### Redis Sentinel (High Availability)

```bash
# sentinel.conf
sentinel monitor mymaster redis-primary 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 10000
sentinel auth-pass mymaster your_redis_password

# Start sentinel
redis-sentinel /etc/redis/sentinel.conf
```

### Qdrant Cluster

```yaml
# qdrant-config.yaml
service:
  http_port: 6333
  grpc_port: 6334

storage:
  storage_path: /qdrant/storage

cluster:
  enabled: true
  p2p:
    port: 6335
  consensus:
    tick_period_ms: 100
```

---

## Security Hardening

### SSL/TLS Configuration

```bash
# Generate Let's Encrypt certificate
certbot certonly --standalone -d api.yourdomain.com

# Auto-renewal
0 0 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

### Firewall Rules

```bash
# Allow only necessary ports
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp     # SSH
ufw allow 80/tcp     # HTTP
ufw allow 443/tcp    # HTTPS
ufw allow 6379/tcp from 10.0.0.0/8  # Redis (internal only)
ufw allow 27017/tcp from 10.0.0.0/8 # MongoDB (internal only)
ufw enable
```

### Application Security

```python
# Use centralized config
from manus_ai.core.config import get_config

config = get_config()

# Validate configuration
warnings = config.validate()
if warnings:
    for warning in warnings:
        logger.warning(f"Config warning: {warning}")
```

---

## Monitoring & Alerting

### Prometheus Alert Rules

```yaml
# alerts.yml
groups:
- name: manus_ai
  interval: 30s
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"

  - alert: HighCacheEvictions
    expr: rate(cache_evictions_total[5m]) > 10
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Cache eviction rate is high"

  - alert: QueueBacklog
    expr: celery_queue_length > 1000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Job queue backlog growing"

  - alert: WorkerDown
    expr: celery_workers_active < 2
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Not enough Celery workers active"

  - alert: DatabaseConnectionIssue
    expr: mongodb_connections_current > 90
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "MongoDB connection pool exhausted"
```

### Setup Alerting

```bash
# Configure AlertManager
alertmanager --config.file=alertmanager.yml

# Slack webhook
receivers:
- name: 'slack'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    channel: '#alerts'
    title: 'Manus AI Alert'
```

---

## Backup & Disaster Recovery

### MongoDB Backup

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=/backups/mongodb

mongodump \
  --uri="mongodb://user:pass@mongodb1:27017/manus_ai?replicaSet=rs0" \
  --out="$BACKUP_DIR/$DATE" \
  --gzip

# Keep last 30 days
find $BACKUP_DIR -type d -mtime +30 -exec rm -rf {} \;

# Upload to S3
aws s3 sync $BACKUP_DIR s3://your-bucket/mongodb-backups/
```

### Redis Backup

```bash
# Automated backups via redis.conf
save 900 1      # Save after 900s if 1 key changed
save 300 10     # Save after 300s if 10 keys changed
save 60 10000   # Save after 60s if 10000 keys changed

# Manual backup
redis-cli --rdb /backups/redis/dump.rdb
```

### Disaster Recovery Plan

1. **RPO (Recovery Point Objective)**: 1 hour
2. **RTO (Recovery Time Objective)**: 30 minutes

**Recovery Steps:**
```bash
# 1. Restore MongoDB
mongorestore --uri="mongodb://..." --gzip /backups/mongodb/20240113/

# 2. Restore Redis
redis-cli --rdb /backups/redis/dump.rdb

# 3. Restart services
docker-compose up -d

# 4. Verify health
curl https://api.yourdomain.com/health/detailed
```

---

## Performance Tuning

### MongoDB Optimization

```javascript
// Create indexes
db.sessions.createIndex({ user_id: 1, created_at: -1 })
db.sessions.createIndex({ session_id: 1 }, { unique: true })
db.usage_records.createIndex({ user_id: 1, timestamp: -1 })
db.usage_records.createIndex({ timestamp: 1 }, { expireAfterSeconds: 2592000 })  // 30 days

// Enable profiling
db.setProfilingLevel(1, { slowms: 100 })
```

### Redis Optimization

```bash
# redis.conf
maxmemory 4gb
maxmemory-policy allkeys-lru
tcp-keepalive 60
timeout 300
```

### Application Tuning

```python
# Use connection pooling
from manus_ai.core.config import get_config

config = get_config()

# MongoDB pool
motor_client = AsyncIOMotorClient(
    config.database.mongodb_uri,
    maxPoolSize=100,
    minPoolSize=10
)

# Redis pool
redis_pool = redis.ConnectionPool(
    host=config.redis.host,
    port=config.redis.port,
    max_connections=50
)
```

---

## Troubleshooting

### Common Issues

**High Memory Usage**
```bash
# Check memory per service
docker stats

# Solution: Increase CELERY_MAX_TASKS_PER_CHILD
CELERY_MAX_TASKS_PER_CHILD=500
```

**Cache Misses**
```bash
# Check cache stats
manus-cli cache stats

# Solution: Increase TTL or cache size
CACHE_MAX_SIZE_MB=4000
```

**Slow Queries**
```bash
# Check MongoDB slow queries
db.system.profile.find().sort({ millis: -1 }).limit(10)

# Solution: Add indexes
```

**Worker Not Processing Jobs**
```bash
# Check Celery workers
docker-compose exec celery_worker celery -A manus_ai.core.jobs:celery_app inspect active

# Restart workers
docker-compose restart celery_worker
```

---

## CLI Management

Use the Manus CLI for day-to-day operations:

```bash
# Health check
manus-cli health

# Job management
manus-cli jobs list
manus-cli jobs status job_123
manus-cli jobs stats

# Cache management
manus-cli cache stats
manus-cli cache llm-savings

# Webhook management
manus-cli webhooks list
manus-cli webhooks events --limit 50
```

---

## Support & Resources

- **Documentation**: INFRASTRUCTURE_GUIDE.md
- **Examples**: manus_ai/examples/
- **Dashboards**: manus_ai/dashboards/
- **CLI**: `manus-cli --help`

---

**Last Updated**: 2024-01-13
**Version**: 2.0.0
