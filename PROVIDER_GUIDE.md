# 🤖 LLM Provider Guide - Manus AI Clone

## 🎉 Currently Configured Providers

Your system now has **2 powerful LLM providers** configured:

### ✅ Gemini 2.5 Pro (Google)
- **Best for**: Creative tasks, code generation, data analysis, general reasoning
- **Strengths**: Fast, multimodal, 100K+ context window
- **Use cases**: Code generation, content creation, complex reasoning

### ✅ Perplexity Sonar Pro
- **Best for**: Research, fact-checking, real-time web information
- **Strengths**: Web-grounded responses, citations, up-to-date information
- **Use cases**: Research, news, fact verification, current events

---

## 🎯 Smart Task Routing

The system **automatically selects** the best provider for each task:

| Task Type | Provider Used | Why |
|-----------|---------------|-----|
| 🔍 Research & Information | **Perplexity** | Real-time web access, citations |
| 💻 Code Generation | **Gemini** | Excellent code understanding |
| 📊 Data Analysis | **Gemini** | Strong analytical capabilities |
| 🎨 Creative Content | **Gemini** | Creative and engaging output |
| ✅ Fact Checking | **Perplexity** | Source verification |
| 🌐 Current Events | **Perplexity** | Up-to-date information |
| 🧮 Complex Reasoning | **Gemini** | Large context, deep analysis |

---

## 💡 Example Tasks by Provider

### Using Perplexity (Research Agent)

```bash
# Best for research tasks
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{
  "user_id": "researcher",
  "message": "What are the latest developments in quantum computing in 2024?"
}'
```

**Perfect for:**
- "Research the top AI companies and their recent achievements"
- "What's the current status of climate change initiatives?"
- "Find the latest research papers on neural networks"
- "Fact-check: Did GPT-5 release in 2024?"

### Using Gemini (Code, Data, General Agents)

```bash
# Best for code and creative tasks
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{
  "user_id": "developer",
  "message": "Build a Python web scraper with error handling and rate limiting"
}'
```

**Perfect for:**
- "Create a REST API for a blog with FastAPI"
- "Analyze this dataset and create visualizations"
- "Write a technical article about microservices"
- "Generate a presentation about renewable energy"

---

## 🔄 How Routing Works

The system routes tasks automatically in `manus_ai/core/orchestrator.py`:

```python
# Research tasks → Perplexity
if task.agent_type == "research":
    provider = LLMProvider.PERPLEXITY_SONAR_PRO

# Code tasks → Gemini (or Claude if available)
elif task.agent_type == "code":
    provider = LLMProvider.GEMINI_2_5_PRO

# Data tasks → Gemini
elif task.agent_type == "data":
    provider = LLMProvider.GEMINI_2_5_PRO

# General → Gemini (fastest)
else:
    provider = LLMProvider.GEMINI_2_5_PRO
```

---

## 🚀 Unlocking More Capabilities

### Add Claude Sonnet (Recommended for Code)

```bash
# Get key from: https://console.anthropic.com/
# Add to manus_ai/.env:
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Benefits:**
- Best-in-class code generation
- Superior debugging and code review
- Enhanced reasoning capabilities
- Longer context (200K tokens)

### Add OpenAI GPT-4

```bash
# Get key from: https://platform.openai.com/api-keys
# Add to manus_ai/.env:
OPENAI_API_KEY=sk-your-key-here
```

**Benefits:**
- Additional fallback option
- General-purpose intelligence
- Broad task versatility

---

## 🧪 Test Your Providers

Run the test script to verify all providers:

```bash
python3 test_dual_providers.py
```

This will:
- ✅ Test Gemini connectivity
- ✅ Test Perplexity connectivity
- ✅ Show smart routing examples
- ✅ Verify both APIs are working

---

## 📊 Provider Comparison

| Feature | Gemini 2.5 Pro | Perplexity Sonar Pro | Claude Sonnet 4 | GPT-4 Turbo |
|---------|----------------|----------------------|-----------------|-------------|
| **Speed** | ⚡⚡⚡ Very Fast | ⚡⚡ Fast | ⚡⚡ Fast | ⚡⚡ Fast |
| **Context** | 100K+ tokens | Standard | 200K tokens | 128K tokens |
| **Code** | ⭐⭐⭐⭐ Excellent | ⭐⭐ Good | ⭐⭐⭐⭐⭐ Best | ⭐⭐⭐⭐ Excellent |
| **Research** | ⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Best | ⭐⭐⭐ Good | ⭐⭐⭐ Good |
| **Creative** | ⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Excellent |
| **Web Access** | ❌ No | ✅ Yes | ❌ No | ❌ No |
| **Citations** | ❌ No | ✅ Yes | ❌ No | ❌ No |
| **Cost** | 💰 Low | 💰💰 Medium | 💰💰 Medium | 💰💰💰 Higher |

**Currently Active:** ✅ Gemini | ✅ Perplexity

---

## 🎯 Optimization Tips

### 1. Task-Specific Provider Selection

For critical tasks, you can specify the provider:

```python
from manus_ai.core.llm_providers import LLMManager, LLMProvider

llm_manager = LLMManager()

# Force use of specific provider
response = await llm_manager.generate(
    messages=[{"role": "user", "content": "Your prompt"}],
    provider=LLMProvider.PERPLEXITY_SONAR_PRO,  # Or GEMINI_2_5_PRO
    temperature=0.7
)
```

### 2. Temperature Settings

- **Research (Perplexity)**: 0.2 - More factual
- **Code (Gemini)**: 0.3 - Deterministic
- **Creative (Gemini)**: 0.7 - More creative
- **Analysis (Gemini)**: 0.4 - Balanced

### 3. Cost Optimization

- Use **Gemini** for most tasks (fast + cheap)
- Use **Perplexity** only for research (web access costs more)
- Use **Claude** for complex code (if available, best quality)

---

## 🔒 API Key Security

Your API keys are stored in `manus_ai/.env` which is:
- ✅ **Gitignored** - Won't be committed
- ✅ **Local only** - Never uploaded
- ✅ **Protected** - Only accessible to the app

**Never share your .env file or commit it to version control!**

---

## 📈 Usage Examples

### Multi-Step Research → Code Task

```
User: "Research modern web frameworks, then build a sample app using the best one"

System routing:
1. Task: Research web frameworks
   → Perplexity (web research with sources)

2. Task: Generate code for sample app
   → Gemini (code generation)

Result: Research-backed code implementation
```

### Complex Analysis Task

```
User: "Analyze tech industry trends, create visualizations, and write a report"

System routing:
1. Research trends → Perplexity
2. Data analysis → Gemini
3. Create charts → Gemini
4. Write report → Gemini

Result: Comprehensive, source-backed analysis
```

---

## 🎉 What You Can Do Now

With **Gemini + Perplexity** configured:

✅ **Research anything** with real-time web information
✅ **Build applications** with code generation
✅ **Analyze data** and create visualizations
✅ **Verify facts** with cited sources
✅ **Create content** with creative AI
✅ **Automate workflows** with multi-step tasks

---

## 🚀 Next Steps

1. **Test providers**: `python3 test_dual_providers.py`
2. **Start system**: `docker-compose up -d`
3. **Try research task**: "What's the latest in AI?"
4. **Try code task**: "Build a Python REST API"
5. **Explore combinations**: Multi-step research + code tasks

---

**Your Manus AI Clone now has dual LLM power!** 🚀

Research with Perplexity + Create with Gemini = Unstoppable AI Agent
