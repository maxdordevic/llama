# 🚀 Production Deployment Guide - Manus AI Clone

Complete guide for deploying Manus AI Clone to production environments.

## 📋 Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Options](#deployment-options)
3. [Docker Deployment](#docker-deployment-recommended)
4. [Cloud Deployment](#cloud-deployment)
5. [Configuration](#configuration)
6. [Security](#security)
7. [Monitoring](#monitoring)
8. [Scaling](#scaling)
9. [Troubleshooting](#troubleshooting)

---

## ✅ Pre-Deployment Checklist

### Required
- [ ] All API keys configured in `.env`
- [ ] Dependencies installed and tested locally
- [ ] Tests passing (`python3 test_dual_providers.py`)
- [ ] Docker installed (for Docker deployment)
- [ ] Domain name configured (for production)
- [ ] SSL certificates ready (for HTTPS)

### Recommended
- [ ] Backup strategy planned
- [ ] Monitoring tools configured
- [ ] Rate limiting configured
- [ ] Error tracking set up
- [ ] Load balancing planned (for high traffic)

---

## 🎯 Deployment Options

### Option 1: Docker Compose (Recommended)
**Best for**: Small to medium deployments, quick setup
**Pros**: Easy, consistent, portable
**Cons**: Single server limitation

### Option 2: Kubernetes
**Best for**: Large scale, high availability
**Pros**: Auto-scaling, self-healing, distributed
**Cons**: Complex setup

### Option 3: Cloud Platform (AWS/GCP/Azure)
**Best for**: Managed services, global scale
**Pros**: Managed infrastructure, easy scaling
**Cons**: Vendor lock-in, costs

### Option 4: Manual/VPS
**Best for**: Full control, custom setup
**Pros**: Complete control
**Cons**: More maintenance

---

## 🐳 Docker Deployment (Recommended)

### Quick Production Deployment

```bash
# 1. Clone repository
git clone <your-repo-url>
cd llama

# 2. Configure environment
cp manus_ai/.env.example manus_ai/.env
nano manus_ai/.env  # Add your API keys

# 3. Update docker-compose.yml for production
nano docker-compose.yml

# 4. Start services
docker-compose up -d

# 5. Verify deployment
curl http://localhost:8000/health
```

### Production docker-compose.yml

```yaml
version: '3.8'

services:
  # Main API Service
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: manus_ai_api
    restart: always
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
      - MAX_PARALLEL_TASKS=3
      - MONGODB_URI=mongodb://mongodb:27017
      - REDIS_URL=redis://redis:6379
    env_file:
      - manus_ai/.env
    depends_on:
      - mongodb
      - redis
    volumes:
      - api_data:/app/data
      - ./logs:/app/logs
    networks:
      - manus_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # MongoDB Database
  mongodb:
    image: mongo:7.0
    container_name: manus_ai_mongodb
    restart: always
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
      - mongodb_config:/data/configdb
      - ./backups:/backups
    environment:
      - MONGO_INITDB_DATABASE=manus_ai
    networks:
      - manus_network
    command: mongod --auth

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: manus_ai_redis
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - manus_network
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}

  # Nginx Reverse Proxy (Optional)
  nginx:
    image: nginx:alpine
    container_name: manus_ai_nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - api
      - frontend
    networks:
      - manus_network

  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: manus_ai_frontend
    restart: always
    environment:
      - REACT_APP_API_URL=https://your-domain.com/api
      - REACT_APP_WS_URL=wss://your-domain.com/ws
    networks:
      - manus_network

volumes:
  mongodb_data:
  mongodb_config:
  redis_data:
  api_data:

networks:
  manus_network:
    driver: bridge
```

### Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # API
        location /api/ {
            proxy_pass http://api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket
        location /ws/ {
            proxy_pass http://api/ws/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
    }
}
```

---

## ☁️ Cloud Deployment

### AWS Deployment

#### Using AWS ECS + Fargate

```bash
# 1. Build and push Docker image
aws ecr create-repository --repository-name manus-ai
docker build -t manus-ai .
docker tag manus-ai:latest ${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/manus-ai:latest
docker push ${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/manus-ai:latest

# 2. Create ECS task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 3. Create ECS service
aws ecs create-service --cluster manus-ai-cluster --service-name manus-ai --task-definition manus-ai
```

#### Using AWS EC2

```bash
# 1. Launch EC2 instance (Ubuntu 22.04)
# 2. SSH into instance
ssh ubuntu@your-ec2-ip

# 3. Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl start docker

# 4. Clone and deploy
git clone <your-repo>
cd llama
docker-compose up -d
```

### Google Cloud Platform (GCP)

#### Using Cloud Run

```bash
# 1. Build and push to GCR
gcloud builds submit --tag gcr.io/${PROJECT_ID}/manus-ai

# 2. Deploy to Cloud Run
gcloud run deploy manus-ai \
  --image gcr.io/${PROJECT_ID}/manus-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Azure Deployment

```bash
# Using Azure Container Instances
az container create \
  --resource-group manus-ai-rg \
  --name manus-ai \
  --image your-registry/manus-ai:latest \
  --dns-name-label manus-ai \
  --ports 8000
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Production .env
# API Keys (Required)
GEMINI_API_KEY=your_production_key
PERPLEXITY_API_KEY=your_production_key
ANTHROPIC_API_KEY=your_production_key  # Optional
OPENAI_API_KEY=your_production_key     # Optional

# Database
MONGODB_URI=mongodb://username:password@mongodb:27017/manus_ai?authSource=admin
REDIS_URL=redis://:password@redis:6379
REDIS_PASSWORD=strong_password_here

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
SECRET_KEY=generate_with_openssl_rand_hex_32

# CORS
ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Features
ENABLE_CODE_EXECUTION=true
ENABLE_WEB_AUTOMATION=false  # Disable in production if not needed
MAX_PARALLEL_TASKS=3

# Sandbox
SANDBOX_TIMEOUT=30
SANDBOX_MAX_MEMORY_MB=512

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring (Optional)
SENTRY_DSN=your_sentry_dsn
```

### Generate Secure Keys

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate Redis password
openssl rand -base64 32

# Generate MongoDB password
openssl rand -base64 32
```

---

## 🔒 Security

### 1. API Key Protection

```bash
# Never commit .env
echo "manus_ai/.env" >> .gitignore

# Use secret management
# AWS: AWS Secrets Manager
# GCP: Secret Manager
# Azure: Key Vault
```

### 2. Database Security

```yaml
# MongoDB with authentication
mongodb:
  environment:
    - MONGO_INITDB_ROOT_USERNAME=admin
    - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
```

### 3. Network Security

```yaml
# Restrict network access
networks:
  manus_network:
    driver: bridge
    internal: true  # No external access
```

### 4. Rate Limiting

Add to `manus_ai/api/main.py`:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, ...):
    ...
```

### 5. HTTPS Only

```nginx
# Force HTTPS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

---

## 📊 Monitoring

### Health Checks

```bash
# API health
curl https://your-domain.com/health

# Database health
docker exec manus_ai_mongodb mongosh --eval "db.adminCommand('ping')"

# Redis health
docker exec manus_ai_redis redis-cli ping
```

### Logging

```yaml
# Configure logging in docker-compose.yml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Monitoring Tools

**Recommended Tools:**
- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **Sentry**: Error tracking
- **CloudWatch/Stackdriver**: Cloud-native monitoring

### Example Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'manus-ai'
    static_configs:
      - targets: ['api:8000']
```

---

## 📈 Scaling

### Horizontal Scaling

```yaml
# Scale API service
docker-compose up -d --scale api=3

# With load balancer
services:
  api:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

### Database Scaling

```yaml
# MongoDB replica set
mongodb:
  command: mongod --replSet rs0

# Redis cluster
redis:
  command: redis-server --cluster-enabled yes
```

### Caching Strategy

```python
# Add caching to frequently used endpoints
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://redis")
    FastAPICache.init(RedisBackend(redis), prefix="manus-cache")
```

---

## 🐛 Troubleshooting

### Common Issues

**1. Container won't start**
```bash
# Check logs
docker-compose logs api

# Check if ports are available
netstat -tulpn | grep 8000
```

**2. Database connection failed**
```bash
# Test MongoDB connection
docker exec -it manus_ai_mongodb mongosh

# Check network
docker network inspect manus_network
```

**3. High memory usage**
```bash
# Check container stats
docker stats

# Adjust resource limits in docker-compose.yml
```

**4. API timeout**
```bash
# Increase timeout in nginx.conf
proxy_read_timeout 300s;
proxy_connect_timeout 300s;
```

---

## 📝 Maintenance

### Backup Strategy

```bash
# MongoDB backup
docker exec manus_ai_mongodb mongodump --out /backups/$(date +%Y%m%d)

# Automated daily backups
0 2 * * * docker exec manus_ai_mongodb mongodump --out /backups/$(date +%Y%m%d)
```

### Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild containers
docker-compose build --no-cache

# Rolling restart
docker-compose up -d --no-deps --build api
```

### Log Rotation

```bash
# Add to /etc/logrotate.d/manus-ai
/path/to/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
}
```

---

## ✅ Production Checklist

Before going live:

### Infrastructure
- [ ] HTTPS configured
- [ ] Domain pointing to server
- [ ] Firewall rules configured
- [ ] Load balancer set up (if needed)

### Application
- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Secrets properly managed
- [ ] Rate limiting enabled
- [ ] Error tracking configured

### Database
- [ ] Backups configured
- [ ] Authentication enabled
- [ ] Monitoring set up
- [ ] Indexes created

### Security
- [ ] API keys rotated
- [ ] Strong passwords set
- [ ] CORS properly configured
- [ ] Security headers added
- [ ] DDoS protection enabled

### Monitoring
- [ ] Health checks configured
- [ ] Alerting set up
- [ ] Logging configured
- [ ] Metrics collected

---

## 🎉 Launch!

Once checklist complete:

```bash
# Final deployment
docker-compose -f docker-compose.prod.yml up -d

# Verify
curl https://your-domain.com/health

# Monitor
docker-compose logs -f
```

---

**Your Manus AI Clone is now in production!** 🚀

For support, see troubleshooting section or review logs.

**Navigation**: [Index](INDEX.md) | [Quick Start](QUICKSTART.md) | [Examples](EXAMPLES.md)
