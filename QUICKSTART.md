# 🚀 Manus AI Clone - Quick Start Guide

Your Gemini API key has been configured! Follow these steps to get started.

## ⚡ Instant Start with Docker (Recommended)

```bash
# 1. Start all services
docker-compose up -d

# 2. Wait 30 seconds for services to initialize

# 3. Access the system
# - Frontend: http://localhost:3000
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs

# 4. Check logs
docker-compose logs -f api

# 5. Stop services
docker-compose down
```

## 🔧 Manual Setup (Development)

### Backend

```bash
# 1. Install dependencies
cd manus_ai
pip install -r requirements.txt

# 2. Verify API key is set
cat .env | grep GEMINI

# 3. Start the API server
uvicorn manus_ai.api.main:app --reload --host 0.0.0.0 --port 8000

# Server will start at http://localhost:8000
# API docs available at http://localhost:8000/docs
```

### Frontend

```bash
# In a new terminal
cd frontend
npm install
npm run dev

# Frontend will start at http://localhost:3000
```

## 🧪 Testing the System

### Option 1: Run Test Suite

```bash
# Quick connectivity test
python3 quick_test.py

# Full system test
python3 test_manus_ai.py
```

### Option 2: Test via API

```bash
# Health check
curl http://localhost:8000/health

# Send a chat message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "message": "Explain what quantum computing is in simple terms"
  }'

# Create execution plan
curl -X POST http://localhost:8000/plan/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Research AI trends and create a summary"
  }'
```

### Option 3: Test via Python

```python
import asyncio
from manus_ai import AgentOrchestrator

async def main():
    orchestrator = AgentOrchestrator()

    result = await orchestrator.execute_request(
        user_request="Research the latest developments in quantum computing and summarize the top 3 trends"
    )

    print(result['result']['summary'])

asyncio.run(main())
```

## 📊 API Endpoints

### Chat & Execution
- `POST /chat` - Execute task and get response
- `POST /chat/stream` - Streaming execution with SSE
- `WS /ws/{session_id}` - WebSocket for real-time updates

### Sessions
- `POST /sessions` - Create new session
- `GET /sessions/{session_id}` - Get session details
- `GET /users/{user_id}/sessions` - List user sessions
- `DELETE /sessions/{session_id}` - Delete session

### Code Execution
- `POST /execute/code` - Execute Python code in sandbox

### Memory
- `POST /memory/add` - Add memory for user
- `GET /memory/{user_id}` - Get user memory
- `GET /memory/{user_id}/preferences` - Get user preferences

### Task Planning
- `POST /plan/create` - Create execution plan

### System
- `GET /health` - Health check
- `GET /providers` - List available LLM providers
- `GET /docs` - OpenAPI documentation

## 🎯 Example Use Cases

### 1. Research Task

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "researcher",
    "message": "Research the top 5 programming languages in 2024, analyze their strengths, and create a comparison table"
  }'
```

### 2. Code Generation

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "developer",
    "message": "Create a Python REST API for a todo application with FastAPI, including CRUD operations and SQLite database"
  }'
```

### 3. Data Analysis

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "analyst",
    "message": "Generate sample sales data for 12 months, analyze trends, and create visualizations"
  }'
```

## 🔑 Adding More API Keys

To enable additional LLM providers, edit `manus_ai/.env`:

```bash
# Get API keys from:
# - Anthropic Claude: https://console.anthropic.com/
# - OpenAI: https://platform.openai.com/api-keys
# - Perplexity: https://www.perplexity.ai/settings/api

# Add to .env:
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
PERPLEXITY_API_KEY=your_perplexity_key_here
```

Then restart the service:
```bash
docker-compose restart api
# or
# Ctrl+C and restart uvicorn if running manually
```

## 🎨 Frontend Usage

1. Open http://localhost:3000
2. Type your task in the chat interface
3. Watch real-time progress as agents work
4. See the complete result with all subtask outputs

The frontend shows:
- **Task Planning**: See how your request is broken down
- **Agent Assignment**: Which agent handles each subtask
- **Progress Tracking**: Real-time execution status
- **Results**: Complete output with sources and metadata

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Change port in docker-compose.yml or:
docker-compose down
# Kill process using port 8000
sudo lsof -ti:8000 | xargs kill -9
```

### API Key Issues

```bash
# Verify API key is set
grep GEMINI_API_KEY manus_ai/.env

# Test API key manually
curl "https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY"
```

### Dependencies Not Found

```bash
# Reinstall dependencies
cd manus_ai
pip install -r requirements.txt --force-reinstall
```

### Docker Issues

```bash
# Rebuild containers
docker-compose build --no-cache

# Check container logs
docker-compose logs api
docker-compose logs mongodb
docker-compose logs redis
```

## 📚 Next Steps

1. **Explore API Docs**: http://localhost:8000/docs
2. **Read Full README**: See `MANUS_AI_README.md`
3. **Try Examples**: Experiment with different task types
4. **Customize Agents**: Modify agent behavior in `manus_ai/agents/`
5. **Add Features**: Extend the system with new capabilities

## 🔒 Security Note

**IMPORTANT**: Your API key is stored in `manus_ai/.env` which is gitignored for security. Never commit API keys to version control!

## 💡 Tips

- Start with simple tasks to understand the system
- Use the WebSocket endpoint for real-time updates
- Check `/health` endpoint to verify all services are running
- Monitor logs to see agent execution in detail
- Use different user IDs to test multi-user scenarios

---

**Your Gemini API key is configured and ready!** 🎉

Start the system and begin building autonomous AI workflows.
