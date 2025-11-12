# 🎯 Usage Examples - Manus AI Clone

Complete guide with practical, ready-to-run examples.

## 🚀 Quick Start

```bash
# Run interactive examples
python3 examples.py

# Run all examples automatically
python3 examples.py --all

# Automated setup
./setup.sh
```

---

## 📚 Example 1: Simple Research Task

**Use Case**: Get latest information with web sources

```python
from manus_ai.core.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()

result = await orchestrator.execute_request(
    "What are the latest developments in quantum computing?"
)

print(result['result']['summary'])
```

**What Happens:**
1. Task Planner creates subtasks
2. Research Agent (Perplexity) searches web
3. Returns result with citations
4. ~15-30 seconds execution time

**Expected Output:**
- Summary of latest quantum computing news
- Source citations
- Structured information

---

## 💻 Example 2: Code Generation

**Use Case**: Generate production-ready code

```python
from manus_ai import AgentOrchestrator

orchestrator = AgentOrchestrator()

result = await orchestrator.execute_request(
    """
    Create a Python REST API for a todo application with:
    - FastAPI framework
    - CRUD operations
    - SQLite database
    - Input validation
    - Error handling
    - Complete with tests
    """
)

# Get generated code
code = result['result']['subtask_results'][0]['result']['code']
```

**What Happens:**
1. Task broken into subtasks
2. Code Agent (Gemini) generates code
3. Returns complete, working implementation
4. ~20-40 seconds execution time

**Expected Output:**
- Complete FastAPI application
- Database models
- API endpoints
- Unit tests

---

## 📊 Example 3: Data Analysis Workflow

**Use Case**: Analyze data and create visualizations

```python
from manus_ai import AgentOrchestrator

orchestrator = AgentOrchestrator()

result = await orchestrator.execute_request(
    """
    Generate sample sales data for 12 months,
    analyze trends and seasonality,
    identify outliers,
    create 3 visualizations (line chart, bar chart, heatmap),
    and write an executive summary.
    """
)
```

**What Happens:**
1. Data Agent generates sample data
2. Performs statistical analysis
3. Creates visualization code
4. Generates summary report
5. ~30-50 seconds execution time

**Expected Output:**
- Python analysis code
- Matplotlib/Seaborn visualizations
- Statistical insights
- Executive summary

---

## 🔄 Example 4: Multi-Step Research → Code

**Use Case**: Research-backed development

```python
from manus_ai import AgentOrchestrator

orchestrator = AgentOrchestrator()

result = await orchestrator.execute_request(
    """
    First, research the most popular Python web frameworks in 2024.
    Then, create a 'Hello World' REST API using the most popular one.
    Include code comments explaining why this framework was chosen.
    """
)
```

**What Happens:**
1. Research Agent (Perplexity) researches frameworks
2. Task Planner uses research results
3. Code Agent (Gemini) generates code with context
4. ~40-60 seconds execution time

**Expected Output:**
- Research summary with sources
- Framework recommendation
- Complete API code
- Contextual explanations

---

## 📄 Example 5: Document Generation

**Use Case**: Create presentations, reports, websites

```python
from manus_ai import AgentOrchestrator

orchestrator = AgentOrchestrator()

result = await orchestrator.execute_request(
    """
    Create a 10-slide presentation about renewable energy with:
    - Title slide
    - Overview of solar, wind, hydro
    - Benefits and challenges
    - Future outlook
    - Conclusion
    Generate Python code using python-pptx.
    """
)
```

**What Happens:**
1. File Processing Agent analyzes requirements
2. Generates presentation structure
3. Creates python-pptx code
4. ~20-35 seconds execution time

**Expected Output:**
- Complete python-pptx code
- Slide structure
- Content for each slide

---

## 🧠 Example 6: Using Memory System

**Use Case**: Learn user preferences

```python
from manus_ai.memory.memory_system import MemorySystem

# Create memory for user
memory = MemorySystem(user_id="developer-123")

# Learn preferences
memory.learn_preference("language", "Python", confidence=0.9)
memory.learn_preference("style", "functional", confidence=0.8)

# Record successful approach
memory.record_successful_approach(
    task_type="api_development",
    approach={"framework": "FastAPI", "testing": "pytest"},
    success_score=0.95
)

# Get context for future requests
context = memory.get_context_summary()
```

**What Happens:**
- Stores user preferences
- Learns from successful approaches
- Provides context for future tasks

---

## 🔒 Example 7: Sandboxed Code Execution

**Use Case**: Safely execute untrusted code

```python
from manus_ai.sandbox.code_executor import CodeExecutor

executor = CodeExecutor(
    timeout=30,
    max_memory_mb=512
)

code = """
import pandas as pd
import numpy as np

# Generate sample data
data = {
    'month': range(1, 13),
    'sales': np.random.randint(1000, 5000, 12)
}
df = pd.DataFrame(data)

print("Sales Summary:")
print(df.describe())
print(f"\\nTotal Sales: ${df['sales'].sum():,}")
"""

result = await executor.execute_code(code)
print(result['output'])
```

**What Happens:**
1. Code runs in isolated environment
2. Resource limits enforced
3. Output captured safely
4. Timeout protection

---

## 🎯 Example 8: Smart Provider Routing

**Use Case**: Automatic optimal provider selection

```python
from manus_ai.core.llm_providers import LLMManager

llm = LLMManager()

# Task routing examples
tasks = {
    "research": "What's the latest in AI?",  # → Perplexity
    "code": "Build a REST API",              # → Gemini
    "creative": "Write a blog post",         # → Gemini
    "analysis": "Analyze this dataset",      # → Gemini
}

for task_type, task in tasks.items():
    provider = await llm.choose_best_provider(task_type)
    print(f"{task_type}: → {provider.value}")
```

---

## 🌐 Example 9: REST API Usage

**Use Case**: Use Manus AI via HTTP API

```bash
# Start the API
uvicorn manus_ai.api.main:app --reload

# Send chat request
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "developer",
    "message": "Research AI trends and create a summary"
  }'

# Execute code
curl -X POST http://localhost:8000/execute/code \
  -H "Content-Type: application/json" \
  -d '{
    "code": "print(\"Hello from Manus AI!\")"
  }'

# Create execution plan
curl -X POST http://localhost:8000/plan/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Build a web scraper"
  }'
```

---

## 🎨 Example 10: Frontend Integration

**Use Case**: Build UI with WebSocket updates

```typescript
// React component example
import { useState, useEffect } from 'react';
import { sendMessage } from './api';
import { useWebSocket } from './hooks/useWebSocket';

function Chat() {
  const [message, setMessage] = useState('');
  const [progress, setProgress] = useState(null);

  const { isConnected } = useWebSocket(
    `ws://localhost:8000/ws/${sessionId}`,
    (data) => setProgress(data)
  );

  const handleSend = async () => {
    const response = await sendMessage({
      user_id: userId,
      message: message
    });

    // Real-time progress updates via WebSocket
    // Final result in response
  };

  return (
    <div>
      <textarea value={message} onChange={e => setMessage(e.target.value)} />
      <button onClick={handleSend}>Send</button>
      {progress && <ProgressTracker progress={progress} />}
    </div>
  );
}
```

---

## 🔧 Example 11: Custom Agent

**Use Case**: Create specialized agent

```python
from manus_ai.agents.base_agent import BaseAgent
from manus_ai.core.llm_providers import LLMProvider

class TranslationAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent_type = "translation"
        self.default_provider = LLMProvider.GEMINI_2_5_PRO

    async def execute(self, task, context):
        messages = [
            {"role": "system", "content": "You are a professional translator."},
            {"role": "user", "content": f"Translate: {task.description}"}
        ]

        response = await self.generate_response(messages)

        return {
            "type": "translation",
            "result": response["content"]
        }

# Register in orchestrator
from manus_ai.core.orchestrator import AgentOrchestrator
orchestrator = AgentOrchestrator()
orchestrator.agents["translation"] = TranslationAgent
```

---

## 📊 Performance Examples

### Fast Tasks (<10s)
- Simple research queries
- Code snippets
- Quick analysis

### Medium Tasks (10-30s)
- Complex research with multiple sources
- Complete function generation
- Data visualization

### Long Tasks (30-60s+)
- Multi-step workflows
- Full application generation
- Comprehensive analysis reports

---

## 🎯 Best Practices

### 1. Clear Task Descriptions
```python
# ❌ Bad
"Make an API"

# ✅ Good
"Create a Python REST API for user management with FastAPI, including: register, login, logout, get profile. Use SQLite database, add input validation, error handling, and JWT authentication."
```

### 2. Use Memory for Consistency
```python
# Store preferences
memory.learn_preference("framework", "FastAPI")

# Future tasks automatically use preferred framework
```

### 3. Break Complex Tasks
```python
# ❌ Avoid one huge task
"Build entire e-commerce platform"

# ✅ Break into phases
"Phase 1: Design database schema for e-commerce"
"Phase 2: Create product catalog API"
"Phase 3: Implement shopping cart"
```

### 4. Leverage Smart Routing
```python
# System automatically uses:
# - Perplexity for "research latest..."
# - Gemini for "build/create/code..."
# - Best provider for each subtask
```

---

## 🚀 Running Examples

```bash
# Interactive menu
python3 examples.py

# Run all examples
python3 examples.py --all

# Test system
python3 test_manus_ai.py

# Test providers
python3 test_dual_providers.py
```

---

## 📖 Next Steps

1. **Start simple**: Run examples 1-3
2. **Try multi-step**: Run examples 4-5
3. **Explore API**: Check http://localhost:8000/docs
4. **Build custom**: Create your own agents
5. **Scale up**: Deploy with Docker

---

**Your Manus AI Clone is ready for autonomous task execution!** 🚀

See `QUICKSTART.md` for deployment instructions.
