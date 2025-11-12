# Manus AI Clone - Autonomous AI Agent Platform

A comprehensive, production-ready autonomous AI agent system built with state-of-the-art LLMs (Gemini 2.5 Pro, Claude Sonnet 4.5, Perplexity, and OpenAI). This system executes complex tasks end-to-end with multi-agent collaboration, transparent progress tracking, and intelligent task planning.

## 🌟 Key Features

### Core Capabilities
- **Multi-Agent Architecture**: Specialized agents (Research, Code, Web, Data, File, General) working collaboratively
- **SOTA LLM Integration**: Gemini 2.5 Pro, Claude Sonnet 4.5, Perplexity Sonar Pro, OpenAI GPT-4
- **Intelligent Task Planning**: Automatic breakdown of complex tasks with dependency management
- **Sandboxed Code Execution**: Secure Python code execution with resource limits
- **Real-time Progress Tracking**: WebSocket-based live updates and session replay
- **Memory & Learning System**: Context persistence and user preference learning
- **Async Background Execution**: Tasks run independently in the cloud
- **Multi-modal Support**: Text, code, data, files, and web automation

### Agent Types

1. **Research Agent** (Perplexity-powered)
   - Web research and information gathering
   - Multi-source synthesis
   - Fact-checking and verification

2. **Code Agent** (Claude-powered)
   - Code generation in multiple languages
   - Debugging and optimization
   - Test generation
   - Code review

3. **Web Automation Agent**
   - Browser automation with Playwright
   - Web scraping and data extraction
   - Form automation
   - API interaction

4. **Data Analysis Agent**
   - Statistical analysis
   - Data visualization
   - Insights generation
   - Data cleaning and transformation

5. **File Processing Agent**
   - Format conversion (PDF, DOCX, Excel, etc.)
   - Document generation
   - Batch file operations
   - Presentation and website generation

6. **General Agent**
   - Multi-step reasoning
   - Problem solving
   - Content generation

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                         │
│  Chat Interface | Progress Tracker | Session Management     │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API / WebSocket
┌────────────────────────┴────────────────────────────────────┐
│                   FastAPI Backend                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          Agent Orchestrator                         │   │
│  │  - Task Distribution                                │   │
│  │  - Agent Lifecycle Management                       │   │
│  │  - Result Aggregation                               │   │
│  └────────────┬────────────────────────────────────────┘   │
│               │                                             │
│  ┌────────────┴────────────────────────────────────────┐   │
│  │          Task Planner (LLM-powered)                 │   │
│  │  - Request Analysis                                 │   │
│  │  - Subtask Generation                               │   │
│  │  - Dependency Management                            │   │
│  └────────────┬────────────────────────────────────────┘   │
│               │                                             │
│  ┌────────────┴────────────────────────────────────────┐   │
│  │     Specialized Agents (Parallel Execution)         │   │
│  │  Research | Code | Web | Data | File | General      │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│              LLM Providers                                  │
│  Gemini 2.5 Pro | Claude Sonnet 4.5 | Perplexity | GPT-4   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Docker & Docker Compose (optional but recommended)
- API Keys for LLM providers

### Installation

#### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd llama

# Copy environment file and add your API keys
cp manus_ai/.env.example manus_ai/.env
# Edit manus_ai/.env and add your API keys

# Start all services with Docker Compose
docker-compose up -d

# Access the application
# API: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

#### Option 2: Manual Installation

```bash
# Backend setup
cd manus_ai
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env and add your API keys

# Start the API server
uvicorn manus_ai.api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend setup (in another terminal)
cd frontend
npm install
npm run dev
```

### Required API Keys

Get API keys from:
- **Anthropic Claude**: https://console.anthropic.com/
- **Google Gemini**: https://makersuite.google.com/app/apikey
- **Perplexity**: https://www.perplexity.ai/settings/api
- **OpenAI**: https://platform.openai.com/api-keys

Add them to `manus_ai/.env`:

```env
ANTHROPIC_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
PERPLEXITY_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

## 📖 Usage Examples

### Example 1: Comprehensive Research Task

```python
# Via Python API
from manus_ai.core.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()

result = await orchestrator.execute_request(
    user_request="""
    Research the latest developments in quantum computing,
    analyze the key players and their approaches,
    and create a comprehensive report with visualizations.
    """
)

print(result['result']['summary'])
```

### Example 2: Code Generation with Testing

```python
result = await orchestrator.execute_request(
    user_request="""
    Create a Python REST API for a todo application using FastAPI,
    include CRUD operations, database integration with SQLAlchemy,
    and generate comprehensive unit tests.
    """
)
```

### Example 3: Data Analysis and Visualization

```python
result = await orchestrator.execute_request(
    user_request="""
    Analyze the provided sales data CSV file,
    identify trends and anomalies,
    create visualizations (sales over time, top products, regional performance),
    and generate an executive summary report.
    """
)
```

### Example 4: Website Generation

```python
result = await orchestrator.execute_request(
    user_request="""
    Create a modern, responsive portfolio website for a software developer
    with sections for: About, Projects, Skills, Experience, and Contact.
    Include animations and a dark mode toggle.
    """
)
```

### Via REST API

```bash
# Send chat message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "Research AI trends and create a presentation"
  }'

# Execute code
curl -X POST http://localhost:8000/execute/code \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import pandas as pd\ndf = pd.DataFrame({\"a\": [1,2,3]})\nprint(df)"
  }'
```

### Via Frontend

1. Open http://localhost:3000
2. Type your task in the chat interface
3. Watch real-time progress as agents work
4. Review the complete result with all subtask outputs

## 🛠️ Configuration

### Agent Configuration

Configure agent behavior in your code:

```python
from manus_ai.core.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator(
    max_parallel_tasks=3,  # Number of parallel agent executions
)

# Customize task planning
from manus_ai.core.task_planner import TaskPlanner

planner = TaskPlanner(llm_manager, planning_provider=LLMProvider.CLAUDE_SONNET_4_5)
```

### LLM Provider Selection

Smart routing automatically chooses the best provider for each task:

```python
from manus_ai.core.llm_providers import LLMManager

llm_manager = LLMManager()

# Manual provider selection
response = await llm_manager.generate(
    messages=[{"role": "user", "content": "Your prompt"}],
    provider=LLMProvider.GEMINI_2_5_PRO,  # or CLAUDE_SONNET_4_5, PERPLEXITY_SONAR_PRO
    temperature=0.7,
    max_tokens=4096
)
```

### Sandbox Configuration

Configure code execution safety:

```python
from manus_ai.sandbox.code_executor import CodeExecutor

executor = CodeExecutor(
    timeout=30,  # Maximum execution time in seconds
    max_memory_mb=512,  # Memory limit
    restricted_imports=["os", "subprocess"]  # Blocked imports
)
```

## 📊 Performance Metrics

- **Task Completion Time**: Target <4 minutes for typical tasks
- **Parallel Execution**: Up to 3 agents simultaneously
- **Context Window**: Optimized for 100K+ tokens (Gemini 2.5 Pro)
- **Session Persistence**: Unlimited storage in MongoDB
- **Real-time Updates**: <100ms WebSocket latency

## 🔒 Security Features

- **Sandboxed Execution**: All code runs in isolated environments
- **Resource Limits**: CPU, memory, and time restrictions
- **Import Restrictions**: Blocked dangerous system calls
- **API Rate Limiting**: Built-in rate limiting and quotas
- **Input Validation**: Comprehensive request validation
- **Docker Isolation**: Optional containerized execution

## 🧪 Testing

```bash
# Run all tests
pytest manus_ai/tests/

# Run with coverage
pytest --cov=manus_ai --cov-report=html

# Run specific test categories
pytest manus_ai/tests/test_agents.py
pytest manus_ai/tests/test_orchestrator.py
pytest manus_ai/tests/test_llm_providers.py
```

## 📚 API Documentation

Interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

- `POST /chat` - Send chat message and execute task
- `POST /chat/stream` - Streaming chat with SSE
- `WS /ws/{session_id}` - WebSocket for real-time updates
- `POST /sessions` - Create new session
- `GET /sessions/{session_id}` - Get session details
- `POST /execute/code` - Execute Python code
- `POST /memory/add` - Add memory for user
- `POST /plan/create` - Create execution plan

## 🗂️ Project Structure

```
llama/
├── manus_ai/                 # Main application
│   ├── agents/              # Specialized agents
│   │   ├── base_agent.py
│   │   ├── research_agent.py
│   │   ├── code_agent.py
│   │   ├── web_agent.py
│   │   ├── data_agent.py
│   │   ├── file_agent.py
│   │   └── general_agent.py
│   ├── core/                # Core components
│   │   ├── orchestrator.py
│   │   ├── task_planner.py
│   │   ├── session_manager.py
│   │   └── llm_providers.py
│   ├── sandbox/             # Code execution
│   │   └── code_executor.py
│   ├── memory/              # Memory system
│   │   └── memory_system.py
│   ├── api/                 # FastAPI backend
│   │   └── main.py
│   ├── tests/               # Test suite
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── App.tsx
│   └── package.json
├── docker-compose.yml
├── Dockerfile
└── MANUS_AI_README.md
```

## 🔧 Development

### Adding a New Agent

```python
# manus_ai/agents/custom_agent.py
from .base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent_type = "custom"
        self.capabilities = ["capability1", "capability2"]

    async def execute(self, task, context):
        # Implementation
        return {"type": "custom", "result": "..."}
```

Register in orchestrator:

```python
# In orchestrator.py
self.agents = {
    # ...existing agents...
    "custom": CustomAgent,
}
```

### Extending LLM Providers

```python
# Add new provider in llm_providers.py
class NewLLMClient(BaseLLMClient):
    async def generate(self, messages, **kwargs):
        # Implementation
        pass
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is for educational and research purposes. Ensure compliance with all LLM provider terms of service.

## 🙏 Acknowledgments

Built with:
- **Anthropic Claude** - Advanced reasoning and coding
- **Google Gemini** - Fast, multimodal capabilities
- **Perplexity** - Real-time web research
- **OpenAI GPT-4** - General intelligence

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the API documentation at `/docs`
- Review example code in `/examples`

## 🚦 Roadmap

- [ ] Enhanced vector memory with embeddings
- [ ] Image and video generation integration
- [ ] Advanced web automation with headless browsers
- [ ] Multi-user collaboration features
- [ ] Custom model fine-tuning support
- [ ] Mobile applications (iOS/Android)
- [ ] Enterprise deployment guides
- [ ] Advanced analytics dashboard

## 💡 Example Use Cases

1. **Research & Analysis**: Market research, competitive analysis, academic research
2. **Software Development**: Full-stack applications, APIs, testing suites
3. **Data Science**: Data analysis, visualization, ML model exploration
4. **Content Creation**: Articles, presentations, websites, documentation
5. **Business Automation**: Report generation, data processing, workflow automation
6. **Education**: Learning assistance, code tutoring, concept explanation

---

**Built with ❤️ using state-of-the-art AI technology**
