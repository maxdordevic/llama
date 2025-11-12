# 🚀 START HERE - Manus AI Clone

**Welcome!** You now have a complete, production-ready autonomous AI agent system.

---

## ⚡ Quick Start (3 Commands)

```bash
./setup.sh                    # Setup and test
docker-compose up -d          # Start system
open http://localhost:3000    # Use frontend
```

**Or try examples:**
```bash
python3 examples.py           # Interactive demos
```

---

## ✅ What You Have

### **Complete System** (8,600+ lines)
- ✅ 6 specialized AI agents
- ✅ 2 SOTA LLM providers (Gemini + Perplexity)
- ✅ Smart task planning
- ✅ Real-time progress tracking
- ✅ Sandboxed execution
- ✅ Session management
- ✅ Memory system

### **APIs & Frontend**
- ✅ FastAPI REST API
- ✅ React TypeScript frontend
- ✅ WebSocket real-time updates
- ✅ OpenAPI documentation

### **Deployment Ready**
- ✅ Docker containerization
- ✅ Production configuration
- ✅ Complete documentation

---

## 📚 Documentation Navigation

**Choose your path:**

### 🆕 New User
1. Read [`SETUP_COMPLETE.md`](SETUP_COMPLETE.md) (5 min)
2. Run `./setup.sh`
3. Run `python3 examples.py`
4. Read [`QUICKSTART.md`](QUICKSTART.md)

### 💻 Developer
1. Read [`INDEX.md`](INDEX.md) (navigation)
2. Read [`EXAMPLES.md`](EXAMPLES.md) (usage)
3. Explore `manus_ai/` source code
4. Read [`MANUS_AI_README.md`](MANUS_AI_README.md)

### 🚀 DevOps
1. Read [`DEPLOYMENT.md`](DEPLOYMENT.md)
2. Configure `docker-compose.yml`
3. Run `docker-compose up -d`
4. Set up monitoring

---

## 📖 Complete Documentation

| Guide | Purpose | Time |
|-------|---------|------|
| **[INDEX](INDEX.md)** 📑 | Master navigation | 10 min |
| **[SETUP_COMPLETE](SETUP_COMPLETE.md)** ✅ | What's ready | 5 min |
| **[QUICKSTART](QUICKSTART.md)** ⚡ | Deploy now | 5 min |
| **[EXAMPLES](EXAMPLES.md)** 💡 | Usage guide | 15 min |
| **[PROVIDER_GUIDE](PROVIDER_GUIDE.md)** 🔍 | LLM details | 10 min |
| **[MANUS_AI_README](MANUS_AI_README.md)** 📖 | Complete docs | 20 min |
| **[DEPLOYMENT](DEPLOYMENT.md)** 🚀 | Production | 15 min |

---

## 🎯 What You Can Do

### Research (Uses Perplexity)
```
"Research quantum computing trends with citations"
```

### Code (Uses Gemini)
```
"Build a REST API with FastAPI and tests"
```

### Multi-Step (Uses Both!)
```
"Research Python frameworks, then build a sample app"
```

**Try it:** `python3 examples.py`

---

## 🔑 Configuration

Your API keys are configured in `manus_ai/.env`:
- ✅ **Gemini 2.5 Pro** - Ready
- ✅ **Perplexity Sonar Pro** - Ready
- ⏳ **Claude Sonnet** - Add for enhanced code
- ⏳ **OpenAI GPT-4** - Add for general tasks

---

## 🧪 Test It Now

```bash
# Test providers
python3 test_dual_providers.py

# Run examples
python3 examples.py

# Full test
python3 test_manus_ai.py
```

---

## 🐳 Docker Deployment

```bash
# Start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api

# Stop
docker-compose down
```

**Access:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

---

## 💡 Example Usage

### Via Python
```python
from manus_ai import AgentOrchestrator

orch = AgentOrchestrator()
result = await orch.execute_request(
    "Research AI trends and create a summary"
)
print(result['result']['summary'])
```

### Via REST API
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "demo", "message": "Your task"}'
```

### Via Frontend
1. Open http://localhost:3000
2. Type your task
3. Watch real-time progress
4. Get complete result

---

## 🏗️ Architecture

```
User → Task Planner → Orchestrator
                         ↓
    ┌─────────────────────────────────┐
    │  Research | Code | Web          │
    │  Data | File | General          │
    └─────────────────────────────────┘
                         ↓
    Gemini 2.5 Pro | Perplexity Sonar Pro
                         ↓
              Final Result
```

---

## 📊 System Stats

- **39 Files** - Complete implementation
- **8,600+ Lines** - Production code
- **6 Agents** - Specialized workers
- **2 LLMs** - Configured and ready
- **9 Docs** - Comprehensive guides
- **8+ Examples** - Working demos

---

## 🎉 Next Steps

**Most Popular Path:**

```bash
# 1. Setup
./setup.sh

# 2. Try examples
python3 examples.py

# 3. Deploy
docker-compose up -d

# 4. Use it
open http://localhost:3000
```

**Need Help?**
- Review [`INDEX.md`](INDEX.md) for navigation
- Check [`EXAMPLES.md`](EXAMPLES.md) for usage
- Read [`QUICKSTART.md`](QUICKSTART.md) for deployment

---

## 🔗 Quick Links

- **Navigation**: [`INDEX.md`](INDEX.md)
- **Examples**: [`EXAMPLES.md`](EXAMPLES.md)
- **Deploy**: [`DEPLOYMENT.md`](DEPLOYMENT.md)
- **Full Docs**: [`MANUS_AI_README.md`](MANUS_AI_README.md)
- **API Docs**: http://localhost:8000/docs (after starting)

---

## 🎊 You're Ready!

**Your Manus AI Clone is fully operational.**

**Recommended first step:** Run `./setup.sh`

Then explore with `python3 examples.py`

---

<div align="center">

**Built with state-of-the-art AI technology** 🤖

Gemini 2.5 Pro + Perplexity Sonar Pro

[Get Started](QUICKSTART.md) · [Examples](EXAMPLES.md) · [Deploy](DEPLOYMENT.md)

</div>
