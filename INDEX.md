# 📑 Manus AI Clone - Complete Index

Your comprehensive guide to navigating the entire system.

## 🎯 Quick Navigation

**Just want to start?** → [`QUICKSTART.md`](QUICKSTART.md)
**Want to understand everything?** → [`MANUS_AI_README.md`](MANUS_AI_README.md)
**Ready to deploy?** → [`DEPLOYMENT.md`](DEPLOYMENT.md)
**Want examples?** → [`EXAMPLES.md`](EXAMPLES.md) or run `python3 examples.py`

---

## 📂 Project Structure

```
llama/
├── 📚 Documentation (Start Here)
│   ├── INDEX.md                    ← You are here
│   ├── SETUP_COMPLETE.md          ← What's ready to use
│   ├── QUICKSTART.md              ← 5-minute quick start
│   ├── MANUS_AI_README.md         ← Complete documentation
│   ├── EXAMPLES.md                ← Usage examples
│   ├── PROVIDER_GUIDE.md          ← LLM provider details
│   └── DEPLOYMENT.md              ← Production deployment
│
├── 🧪 Testing & Tools
│   ├── setup.sh                   ← Automated setup script
│   ├── examples.py                ← Interactive examples (8+)
│   ├── test_dual_providers.py     ← Test Gemini + Perplexity
│   ├── test_manus_ai.py          ← Full system test
│   └── quick_test.py             ← Quick connectivity test
│
├── 🤖 Core Application
│   └── manus_ai/
│       ├── agents/                ← 6 Specialized AI Agents
│       │   ├── base_agent.py          - Abstract base class
│       │   ├── research_agent.py      - Web research (Perplexity)
│       │   ├── code_agent.py          - Code generation (Gemini)
│       │   ├── web_agent.py           - Web automation
│       │   ├── data_agent.py          - Data analysis
│       │   ├── file_agent.py          - File processing
│       │   └── general_agent.py       - General tasks
│       │
│       ├── core/                  ← Core System Components
│       │   ├── orchestrator.py        - Multi-agent coordination
│       │   ├── task_planner.py        - Intelligent task planning
│       │   ├── session_manager.py     - Session persistence
│       │   └── llm_providers.py       - LLM integration layer
│       │
│       ├── sandbox/               ← Secure Execution
│       │   └── code_executor.py       - Sandboxed Python execution
│       │
│       ├── memory/                ← Learning System
│       │   └── memory_system.py       - User memory & preferences
│       │
│       ├── api/                   ← REST API Backend
│       │   └── main.py                - FastAPI application
│       │
│       ├── requirements.txt       ← Python dependencies
│       ├── .env.example           ← Environment template
│       └── .env                   ← Your API keys (gitignored)
│
├── 🎨 Frontend
│   └── frontend/
│       ├── src/
│       │   ├── App.tsx                - Main React app
│       │   ├── components/            - React components
│       │   │   └── ChatInterface.tsx  - Chat UI
│       │   ├── services/              - API clients
│       │   │   └── api.ts             - HTTP client
│       │   └── hooks/                 - React hooks
│       │       └── useWebSocket.ts    - WebSocket hook
│       └── package.json               - Node dependencies
│
├── 🐳 Deployment
│   ├── docker-compose.yml         ← Multi-service orchestration
│   ├── Dockerfile                 ← Container definition
│   └── .gitignore                ← Protected files
│
└── 📜 Original Project
    ├── README.md                  ← Original Llama 2 docs
    ├── llama/                     ← Original Llama code (preserved)
    └── ...
```

---

## 🚀 Getting Started Paths

### Path 1: Complete Beginner
1. Read [`SETUP_COMPLETE.md`](SETUP_COMPLETE.md) (5 min)
2. Run `./setup.sh` (auto setup)
3. Run `python3 examples.py` (try it out)
4. Read [`QUICKSTART.md`](QUICKSTART.md) (deployment)

### Path 2: Want to Deploy Now
1. Run `./setup.sh`
2. Run `docker-compose up -d`
3. Open http://localhost:3000
4. Done! 🎉

### Path 3: Want to Understand Everything
1. Read [`MANUS_AI_README.md`](MANUS_AI_README.md) (complete docs)
2. Read [`PROVIDER_GUIDE.md`](PROVIDER_GUIDE.md) (LLM details)
3. Read [`EXAMPLES.md`](EXAMPLES.md) (usage patterns)
4. Explore `manus_ai/` source code

### Path 4: Want to Develop/Extend
1. Read [`MANUS_AI_README.md`](MANUS_AI_README.md) § Development
2. Study `manus_ai/agents/base_agent.py`
3. Review `manus_ai/core/orchestrator.py`
4. Check [`EXAMPLES.md`](EXAMPLES.md) § Custom Agent

---

## 📚 Documentation Guide

### Getting Started
| Document | Purpose | Time | When to Read |
|----------|---------|------|--------------|
| [`SETUP_COMPLETE.md`](SETUP_COMPLETE.md) | What's ready | 3 min | First! |
| [`QUICKSTART.md`](QUICKSTART.md) | Deploy in 5 min | 5 min | Ready to start |
| `setup.sh` | Auto-setup | 2 min | First-time setup |

### Understanding the System
| Document | Purpose | Time | When to Read |
|----------|---------|------|--------------|
| [`MANUS_AI_README.md`](MANUS_AI_README.md) | Complete guide | 20 min | Deep understanding |
| [`PROVIDER_GUIDE.md`](PROVIDER_GUIDE.md) | LLM providers | 10 min | Understanding routing |
| [`EXAMPLES.md`](EXAMPLES.md) | Usage patterns | 15 min | Learning to use |

### Operations
| Document | Purpose | Time | When to Read |
|----------|---------|------|--------------|
| [`DEPLOYMENT.md`](DEPLOYMENT.md) | Production deploy | 15 min | Before deploying |
| `docker-compose.yml` | Service config | 5 min | Customizing setup |
| `.env.example` | Configuration | 5 min | Setting up |

---

## 🧪 Testing & Examples

### Quick Tests
```bash
# Test API connectivity
python3 quick_test.py

# Test both LLM providers
python3 test_dual_providers.py

# Full system test
python3 test_manus_ai.py

# Interactive examples
python3 examples.py
```

### Example Categories
- **Example 1-3**: Basic single-agent tasks
- **Example 4-5**: Multi-step workflows
- **Example 6-8**: Advanced features
- See [`EXAMPLES.md`](EXAMPLES.md) for details

---

## 🔑 Configuration Files

### Required Setup
| File | Purpose | Action Needed |
|------|---------|---------------|
| `manus_ai/.env` | API keys | ✅ Already configured |
| `docker-compose.yml` | Services | 📝 Review ports |
| `requirements.txt` | Dependencies | 🔄 `pip install -r` |

### Environment Variables
```bash
# Currently configured:
✅ GEMINI_API_KEY        # Google Gemini 2.5 Pro
✅ PERPLEXITY_API_KEY    # Perplexity Sonar Pro

# Optional (add for more features):
⏳ ANTHROPIC_API_KEY     # Claude Sonnet 4.5
⏳ OPENAI_API_KEY        # OpenAI GPT-4
```

---

## 🎯 Core Components Explained

### 1. Agents (`manus_ai/agents/`)
**What**: Specialized AI workers for different tasks
**How**: Each agent uses optimal LLM for its task type
**Example**: ResearchAgent → Perplexity, CodeAgent → Gemini

### 2. Orchestrator (`manus_ai/core/orchestrator.py`)
**What**: Coordinates multiple agents working together
**How**: Distributes tasks, manages execution, aggregates results
**Example**: Breaks "research + code" into subtasks

### 3. Task Planner (`manus_ai/core/task_planner.py`)
**What**: Breaks complex requests into subtasks
**How**: Uses LLM to analyze and create execution plan
**Example**: "Build API" → [design, code, test, document]

### 4. LLM Providers (`manus_ai/core/llm_providers.py`)
**What**: Unified interface to multiple LLMs
**How**: Smart routing based on task type
**Example**: Research → Perplexity, Code → Gemini

### 5. Sandbox (`manus_ai/sandbox/code_executor.py`)
**What**: Safe Python code execution
**How**: Resource limits, isolated environment
**Example**: Execute user code safely

### 6. Memory (`manus_ai/memory/memory_system.py`)
**What**: Learns user preferences and patterns
**How**: Stores successful approaches, preferences
**Example**: Remember "user prefers FastAPI"

### 7. API (`manus_ai/api/main.py`)
**What**: REST API + WebSocket server
**How**: FastAPI with real-time updates
**Example**: `POST /chat` → execute task

---

## 🔄 Typical Workflows

### Workflow 1: Simple Task
```
User → API → Orchestrator → Single Agent → LLM → Result
```

### Workflow 2: Research Task
```
User → API → Orchestrator → Research Agent → Perplexity → Result
```

### Workflow 3: Multi-Step Task
```
User → API → Task Planner → Plan with Subtasks
     ↓
Orchestrator → Agent 1 (Research) → Perplexity
            → Agent 2 (Code)     → Gemini
            → Agent 3 (Data)     → Gemini
     ↓
Result Aggregator → Final Response
```

### Workflow 4: With Memory
```
User Request → Memory System → Load Preferences
            ↓
Task Execution → Store Successful Approach
            ↓
Future Tasks → Use Learned Preferences
```

---

## 📊 File Statistics

**Total Files**: 35+
**Lines of Code**: 6,600+
**Documentation**: 7 comprehensive guides
**Examples**: 8+ ready-to-run demonstrations
**Agents**: 6 specialized AI agents
**LLM Providers**: 4 supported (2 configured)

---

## 🛠️ Common Tasks

### Start System
```bash
# With Docker (recommended)
docker-compose up -d

# Manual
uvicorn manus_ai.api.main:app --reload
```

### Test System
```bash
./setup.sh              # Full setup + test
python3 examples.py     # Interactive examples
```

### Add API Key
```bash
# Edit manus_ai/.env
nano manus_ai/.env

# Add your key
ANTHROPIC_API_KEY=sk-ant-your-key

# Restart
docker-compose restart api
```

### View Logs
```bash
docker-compose logs -f api
docker-compose logs -f frontend
```

### Stop System
```bash
docker-compose down
```

---

## 🔍 Finding What You Need

### "How do I...?"

**...start the system?**
→ [`QUICKSTART.md`](QUICKSTART.md) or run `docker-compose up -d`

**...test if it works?**
→ Run `./setup.sh` or `python3 test_dual_providers.py`

**...use the Python API?**
→ [`EXAMPLES.md`](EXAMPLES.md) § Examples 1-8

**...use the REST API?**
→ [`EXAMPLES.md`](EXAMPLES.md) § Example 9 or http://localhost:8000/docs

**...add a new agent?**
→ [`MANUS_AI_README.md`](MANUS_AI_README.md) § Development

**...configure LLM providers?**
→ [`PROVIDER_GUIDE.md`](PROVIDER_GUIDE.md)

**...deploy to production?**
→ [`DEPLOYMENT.md`](DEPLOYMENT.md)

**...understand the architecture?**
→ [`MANUS_AI_README.md`](MANUS_AI_README.md) § Architecture

---

## 🎓 Learning Resources

### Beginner
1. [`SETUP_COMPLETE.md`](SETUP_COMPLETE.md) - Overview
2. Run `python3 examples.py` - Try it
3. [`EXAMPLES.md`](EXAMPLES.md) § Examples 1-3 - Basic usage

### Intermediate
1. [`PROVIDER_GUIDE.md`](PROVIDER_GUIDE.md) - LLM routing
2. [`EXAMPLES.md`](EXAMPLES.md) § Examples 4-8 - Advanced
3. Explore `manus_ai/agents/` - Agent code

### Advanced
1. [`MANUS_AI_README.md`](MANUS_AI_README.md) - Complete system
2. Study `manus_ai/core/orchestrator.py` - Coordination
3. [`DEPLOYMENT.md`](DEPLOYMENT.md) - Production setup

---

## 🚨 Troubleshooting

### Quick Fixes

**"Module not found"**
→ Run `pip install -r manus_ai/requirements.txt`

**"API key error"**
→ Check `manus_ai/.env` has your keys

**"Port 8000 in use"**
→ Change port in `docker-compose.yml`

**"Can't connect to API"**
→ Run `docker-compose logs api`

**See more**: Each documentation file has troubleshooting section

---

## 📞 Support & Community

**Found a bug?**
→ Check logs: `docker-compose logs`

**Need help?**
→ Review documentation in order listed above

**Want to contribute?**
→ See [`MANUS_AI_README.md`](MANUS_AI_README.md) § Contributing

---

## ✅ Quick Checklist

Before you start, ensure:
- [ ] Python 3.11+ installed
- [ ] Docker installed (for Docker deployment)
- [ ] API keys added to `manus_ai/.env`
- [ ] Dependencies installed (`./setup.sh`)
- [ ] Tests pass (`python3 test_dual_providers.py`)

---

## 🎉 You're Ready!

**Next Step**: Choose a path above and start building!

Most users start with:
1. Run `./setup.sh`
2. Run `python3 examples.py`
3. Run `docker-compose up -d`
4. Visit http://localhost:3000

**Happy building with your Manus AI Clone!** 🚀

---

**Navigation**: [Setup](SETUP_COMPLETE.md) | [Quick Start](QUICKSTART.md) | [Examples](EXAMPLES.md) | [Full Docs](MANUS_AI_README.md) | [Deploy](DEPLOYMENT.md)
