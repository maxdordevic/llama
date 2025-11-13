# 🚀 Manus AI Clone - Advanced Features Guide

This guide covers all the enhanced features added to the Manus AI Clone platform.

## Table of Contents

1. [Vector Database & RAG System](#vector-database--rag-system)
2. [Image Generation Agent](#image-generation-agent)
3. [Token Usage & Cost Management](#token-usage--cost-management)
4. [Multi-Modal Chat Support](#multi-modal-chat-support)
5. [Monitoring & Analytics](#monitoring--analytics)
6. [Plugin System](#plugin-system)
7. [Authentication & API Keys](#authentication--api-keys)
8. [Rate Limiting & Security](#rate-limiting--security)
9. [Workflow Templates](#workflow-templates)

---

## Vector Database & RAG System

### Overview
The vector database integration enables semantic search and Retrieval-Augmented Generation (RAG) for knowledge-enhanced responses.

### Features
- **Semantic Search**: Find relevant information using natural language queries
- **RAG System**: Enhance LLM responses with retrieved context
- **Qdrant Integration**: High-performance vector database
- **Automatic Embeddings**: Using sentence-transformers

### Setup

```bash
# Install dependencies
pip install qdrant-client sentence-transformers

# Start Qdrant server (Docker)
docker run -p 6333:6333 qdrant/qdrant
```

### Usage Example

```python
from manus_ai.core.vector_store import VectorStore, Document, RAGSystem

# Initialize vector store
vector_store = VectorStore(
    collection_name="knowledge_base",
    embedding_model="all-MiniLM-L6-v2",
    qdrant_url="localhost",
    qdrant_port=6333
)

# Add documents
documents = [
    Document(
        id="doc1",
        content="Python is a high-level programming language...",
        metadata={"category": "programming", "language": "en"}
    ),
    Document(
        id="doc2",
        content="Machine learning is a subset of AI...",
        metadata={"category": "ai", "language": "en"}
    )
]

await vector_store.add_documents(documents)

# Search
results = await vector_store.search(
    query="What is Python?",
    limit=5,
    score_threshold=0.7
)

# RAG System
rag = RAGSystem(vector_store)
result = await rag.generate_with_context(
    query="Explain Python programming",
    llm_generate_func=your_llm_function,
    max_context_tokens=2000
)

print(result["response"])
print(result["sources"])
```

### API Endpoints

```bash
# Add documents
POST /api/vector/documents
{
  "documents": [
    {"content": "...", "metadata": {...}}
  ]
}

# Search
POST /api/vector/search
{
  "query": "search query",
  "limit": 5
}

# RAG query
POST /api/vector/rag
{
  "query": "question",
  "max_context_tokens": 2000
}
```

---

## Image Generation Agent

### Overview
Generate high-quality images using state-of-the-art AI models including DALL-E 3, DALL-E 2, and Stable Diffusion.

### Supported Providers
- **DALL-E 3**: OpenAI's latest model (highest quality)
- **DALL-E 2**: OpenAI's previous generation
- **Stable Diffusion XL**: Open-source via Replicate
- **Stable Diffusion 2**: Faster generation

### Setup

```bash
# Required: OpenAI API key for DALL-E
export OPENAI_API_KEY="sk-..."

# Optional: Replicate API key for Stable Diffusion
export REPLICATE_API_KEY="r8_..."

# Optional: Stability AI API key
export STABILITY_API_KEY="sk-..."
```

### Usage Example

```python
from manus_ai.agents.image_agent import ImageGenerationAgent

agent = ImageGenerationAgent()

# Generate image
result = await agent.execute({
    "prompt": "A futuristic city at sunset with flying cars",
    "provider": "dalle-3",
    "size": "1024x1024",
    "style": "vivid",
    "quality": "hd",
    "n": 1,
    "enhance_prompt": True  # Use LLM to enhance prompt
})

print(f"Generated {result['count']} images")
print(f"Cost: ${result['total_cost']:.4f}")

for img in result['images']:
    print(f"URL: {img['url']}")
    print(f"Revised prompt: {img['revised_prompt']}")
```

### API Endpoints

```bash
# Generate image
POST /api/agents/image/generate
{
  "prompt": "description of image",
  "provider": "dalle-3",
  "size": "1024x1024",
  "style": "vivid",
  "quality": "hd",
  "enhance_prompt": true
}
```

### Pricing

| Provider | Size | Cost per Image |
|----------|------|----------------|
| DALL-E 3 | 1024x1024 | $0.040 |
| DALL-E 3 | 1792x1024 | $0.080 |
| DALL-E 2 | 1024x1024 | $0.020 |
| SD XL | Any | $0.003 |

---

## Token Usage & Cost Management

### Overview
Track API usage, monitor costs, and enforce budget limits to prevent overspending.

### Features
- **Real-time Usage Tracking**: Monitor token usage across all LLM calls
- **Cost Calculation**: Automatic cost calculation per provider
- **Budget Limits**: Set spending limits by period (hourly/daily/monthly)
- **Usage Analytics**: Detailed breakdown by user, session, and resource type
- **Cost Forecasting**: Predict future costs based on trends

### Setup & Usage

```python
from manus_ai.core.usage_tracker import UsageTracker, ResourceType, BudgetLimit

tracker = UsageTracker()

# Set budget limit
tracker.add_budget_limit(BudgetLimit(
    limit_amount=100.0,  # $100
    period="monthly",
    resource_types=[ResourceType.LLM_INPUT_TOKENS, ResourceType.LLM_OUTPUT_TOKENS],
    alert_threshold=0.8,  # Alert at 80%
    hard_limit=True  # Block when exceeded
))

# Record usage
await tracker.record_llm_usage(
    model="gemini-2.0-flash-exp",
    input_tokens=1500,
    output_tokens=800,
    session_id="session_123",
    user_id="user_456"
)

# Check budget before operation
budget_check = await tracker.check_budget(
    cost=0.05,
    resource_type=ResourceType.LLM_OUTPUT_TOKENS,
    user_id="user_456"
)

if not budget_check["allowed"]:
    print(f"Budget exceeded: {budget_check['reason']}")

# Get usage summary
summary = await tracker.get_usage_summary(period="daily")
print(f"Total cost: ${summary['total_cost']:.4f}")
print(f"Breakdown: {summary['breakdown']}")

# Cost forecast
forecast = await tracker.get_cost_forecast(period="monthly")
print(f"Projected monthly cost: ${forecast['forecast_cost']:.2f}")
```

### API Endpoints

```bash
# Get usage summary
GET /api/usage/summary?period=daily

# Get forecast
GET /api/usage/forecast?period=monthly

# Export report
GET /api/usage/export?start_date=2024-01-01&end_date=2024-01-31
```

---

## Multi-Modal Chat Support

### Overview
Upload and analyze images, PDFs, documents, and other files in conversations.

### Supported File Types
- **Images**: JPEG, PNG, GIF, WebP, BMP, SVG
- **Documents**: PDF, DOCX, ODT
- **Text**: TXT, Markdown, CSV, HTML
- **Code**: Python, JavaScript, JSON, XML
- **Spreadsheets**: XLSX, XLS

### Features
- **Automatic Text Extraction**: Extract text from PDFs and documents
- **Image Analysis**: Vision-capable LLMs can analyze uploaded images
- **Thumbnail Generation**: Automatic thumbnails for images
- **Metadata Extraction**: File size, dimensions, page count, etc.

### Usage Example

```python
from manus_ai.core.multimodal import MultiModalManager

manager = MultiModalManager()

# Upload file
with open("document.pdf", "rb") as f:
    file_content = f.read()

media_file = await manager.upload_file(
    filename="document.pdf",
    content=file_content,
    session_id="session_123"
)

print(f"File ID: {media_file.file_id}")
print(f"Extracted text: {media_file.text_content[:200]}...")
print(f"Metadata: {media_file.metadata}")

# Use in LLM conversation
llm_input = manager.format_for_llm(media_file)
```

### API Endpoints

```bash
# Upload file
POST /api/files/upload
Content-Type: multipart/form-data
{
  "file": <binary>
}

# Get file
GET /api/files/{file_id}

# Delete file
DELETE /api/files/{file_id}

# List session files
GET /api/files/session/{session_id}
```

---

## Monitoring & Analytics

### Overview
Comprehensive system monitoring with real-time metrics, performance tracking, and health monitoring.

### Features
- **System Health**: Overall status, uptime, error rates
- **Request Tracking**: API request metrics, response times, success rates
- **Agent Analytics**: Agent execution stats, success rates, costs
- **Performance Metrics**: Latency, throughput, resource usage
- **Prometheus Export**: Compatible with Prometheus/Grafana

### Usage Example

```python
from manus_ai.core.analytics import get_monitoring

monitoring = get_monitoring()

# Record request
monitoring.record_request(
    endpoint="/chat",
    method="POST",
    status_code=200,
    duration_ms=1250,
    user_id="user_123"
)

# Record agent execution
monitoring.record_agent_execution(
    agent_name="CodeAgent",
    task_type="generate",
    duration_ms=3500,
    success=True,
    tokens_used=2000,
    cost=0.05
)

# Get system health
health = await monitoring.get_system_health()
print(f"Status: {health.status}")
print(f"Uptime: {health.uptime_seconds}s")
print(f"Active sessions: {health.active_sessions}")
print(f"Requests/min: {health.requests_per_minute}")
print(f"Error rate: {health.error_rate_percent}%")

# Get dashboard data
dashboard = await monitoring.get_dashboard_data()
```

### API Endpoints

```bash
# System health
GET /api/monitoring/health

# Dashboard data
GET /api/monitoring/dashboard

# Agent statistics
GET /api/monitoring/agents

# Export metrics (Prometheus format)
GET /api/metrics
```

### Metrics Dashboard

Key metrics tracked:
- HTTP requests (total, success, errors)
- Response times (avg, p50, p95, p99)
- Agent executions by type
- Token usage and costs
- Active sessions
- Error rates

---

## Plugin System

### Overview
Extend the platform with custom agents through a powerful plugin system.

### Features
- **Dynamic Loading**: Load agents at runtime
- **Hot Reload**: Update plugins without restarting
- **Dependency Management**: Automatic dependency resolution
- **Metadata System**: Rich plugin information
- **Template Generation**: Quick-start templates

### Creating a Plugin

```bash
# Generate plugin template
from manus_ai.core.plugin_system import get_plugin_manager

manager = get_plugin_manager()
template_path = manager.create_plugin_template("my_custom_agent")
print(f"Created template: {template_path}")
```

Edit the generated file:

```python
from manus_ai.core.plugin_system import BaseAgent
from typing import Dict, Any

class MyCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.name = "MyCustomAgent"
        self.description = "Does something awesome"
        self.capabilities = [
            "Custom capability 1",
            "Custom capability 2"
        ]

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Your implementation
        result = f"Processed: {task.get('input')}"

        return {
            "status": "success",
            "agent": self.name,
            "result": result
        }
```

### Loading Plugins

```python
# Discover available plugins
plugins = await manager.discover_plugins()

# Load plugin
success = await manager.load_plugin(
    "my_custom_agent",
    config={"api_key": "..."}
)

# Execute plugin agent
result = await manager.execute_agent(
    "MyCustomAgent",
    {"input": "test data"}
)

# Unload plugin
await manager.unload_plugin("my_custom_agent")
```

### API Endpoints

```bash
# List plugins
GET /api/plugins

# Load plugin
POST /api/plugins/{plugin_id}/load

# Unload plugin
POST /api/plugins/{plugin_id}/unload

# Execute plugin agent
POST /api/plugins/{plugin_id}/execute
{
  "task": {...}
}
```

---

## Authentication & API Keys

### Overview
Secure user authentication with JWT tokens and API key management.

### Features
- **User Management**: Create users with roles (admin, user, readonly)
- **JWT Authentication**: Secure session tokens
- **API Key System**: Generate, revoke, and manage API keys
- **Permission-based Access**: Granular permissions per role/key
- **Session Management**: Track and manage active sessions

### Usage Example

```python
from manus_ai.core.auth import get_auth_manager, UserRole, Permission

auth = get_auth_manager()

# Create user
user = await auth.create_user(
    username="john_doe",
    email="john@example.com",
    password="secure_password",
    role=UserRole.USER
)

# Authenticate
authenticated = await auth.authenticate_user("john_doe", "secure_password")

if authenticated:
    # Create session
    session = await auth.create_session(
        user=authenticated,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0..."
    )

    print(f"Session token: {session.token}")

# Create API key
api_key_obj, plain_key = await auth.create_api_key(
    user=user,
    name="Production API Key",
    expires_in_days=365,
    rate_limit=1000  # requests per minute
)

print(f"API Key: {plain_key}")  # Save this!

# Verify API key
verified = await auth.verify_api_key(plain_key)

# Check permissions
has_perm = auth.has_permission(
    user=user,
    api_key=None,
    permission=Permission.EXECUTE_AGENT
)
```

### API Endpoints

```bash
# Register user
POST /api/auth/register
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "password"
}

# Login
POST /api/auth/login
{
  "username": "john_doe",
  "password": "password"
}

# Create API key
POST /api/auth/api-keys
Headers: Authorization: Bearer <jwt_token>
{
  "name": "My API Key",
  "expires_in_days": 365
}

# List API keys
GET /api/auth/api-keys

# Revoke API key
DELETE /api/auth/api-keys/{key_id}
```

---

## Rate Limiting & Security

### Overview
Protect the API from abuse with rate limiting, input validation, and security scanning.

### Features
- **Multiple Strategies**: Fixed window, sliding window, token bucket
- **Flexible Rules**: Per-endpoint, per-user rate limits
- **Input Validation**: SQL injection, XSS, command injection detection
- **Prompt Injection Detection**: Identify malicious prompts
- **Code Scanning**: Security analysis before execution

### Usage Example

```python
from manus_ai.core.security import get_security_manager, RateLimitRule

security = get_security_manager()

# Check request (comprehensive security check)
allowed, details = await security.check_request(
    client_id="user_123",
    rule_name="chat_messages",
    input_text="User's chat message",
    code=None
)

if not allowed:
    print(f"Request blocked: {details['reason']}")
else:
    # Process request
    pass

# Add custom rate limit
security.add_rule(RateLimitRule(
    name="premium_users",
    limit=200,
    period_seconds=60,
    block_duration_seconds=30
))

# Get client stats
stats = security.get_client_stats("user_123")
```

### Default Rate Limits

| Endpoint | Limit | Period | Block Duration |
|----------|-------|--------|----------------|
| API Requests | 100 | 60s | 60s |
| Chat Messages | 50 | 60s | 120s |
| Agent Executions | 20 | 60s | 300s |
| Image Generation | 10 | 300s | 600s |
| File Uploads | 20 | 60s | 180s |

### Security Scanning

```python
from manus_ai.core.security import SecurityScanner

scanner = SecurityScanner()

# Scan code for security issues
scan_result = await scanner.scan_code_execution(code)
if not scan_result["safe"]:
    print(f"Security issues: {scan_result['issues']}")

# Scan for prompt injection
prompt_scan = await scanner.scan_prompt_injection(user_prompt)
if not prompt_scan["safe"]:
    print(f"Prompt injection detected: {prompt_scan['issues']}")
```

---

## Workflow Templates

### Overview
Save and reuse multi-step workflows with dependency management and parallel execution.

### Features
- **Visual Workflow Builder**: Define complex multi-step processes
- **Dependency Management**: Automatic execution ordering
- **Parallel Execution**: Run independent steps concurrently
- **Conditional Logic**: Branch based on results
- **Template Library**: Built-in and custom templates

### Creating Workflows

```python
from manus_ai.core.workflows import (
    get_workflow_library, WorkflowStep, StepType, WorkflowEngine
)

library = get_workflow_library()

# Create workflow template
template = library.create_template(
    name="Research and Summarize",
    description="Research a topic and create summary",
    category="research",
    tags=["research", "ai"],
    steps=[
        WorkflowStep(
            step_id="research",
            step_type=StepType.AGENT_EXECUTION,
            name="Research Topic",
            description="Conduct research",
            agent_name="ResearchAgent",
            parameters={"query": "$input.topic"}
        ),
        WorkflowStep(
            step_id="summarize",
            step_type=StepType.AGENT_EXECUTION,
            name="Summarize",
            description="Create summary",
            agent_name="GeneralAgent",
            parameters={"text": "$research.result"},
            depends_on=["research"]
        )
    ]
)

# Execute workflow
engine = WorkflowEngine()
execution = await engine.execute_workflow(
    template=template,
    input_data={"topic": "Quantum Computing"},
    user_id="user_123"
)

print(f"Status: {execution.status}")
print(f"Results: {execution.step_results}")
```

### Built-in Templates

1. **Research and Summarize**: Research + summary generation
2. **Code Generation and Testing**: Generate code + run tests
3. More templates coming soon!

### API Endpoints

```bash
# List templates
GET /api/workflows/templates

# Create template
POST /api/workflows/templates
{
  "name": "...",
  "steps": [...]
}

# Execute workflow
POST /api/workflows/execute
{
  "template_id": "wf_123",
  "input_data": {...}
}

# Get execution status
GET /api/workflows/executions/{execution_id}
```

---

## Next Steps

### Installation

```bash
# Install all dependencies
pip install -r manus_ai/requirements.txt

# Optional: Start supporting services
docker-compose up -d
```

### Configuration

Create `.env` file:

```bash
# LLM API Keys
GEMINI_API_KEY=your_key
PERPLEXITY_API_KEY=your_key
OPENAI_API_KEY=your_key  # For DALL-E
REPLICATE_API_KEY=your_key  # For Stable Diffusion

# Qdrant
QDRANT_URL=localhost
QDRANT_PORT=6333

# Security
JWT_SECRET=your_secret_key

# MongoDB
MONGODB_URI=mongodb://localhost:27017

# Redis
REDIS_URL=redis://localhost:6379
```

### Testing

```bash
# Run all tests
pytest manus_ai/tests/

# Test specific feature
pytest manus_ai/tests/test_vector_store.py
```

---

## Support & Documentation

- **Main README**: [MANUS_AI_README.md](MANUS_AI_README.md)
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
- **Examples**: [EXAMPLES.md](EXAMPLES.md)
- **API Docs**: http://localhost:8000/docs (when running)

## License

MIT License - See LICENSE file for details.
