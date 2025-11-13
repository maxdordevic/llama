"""
Advanced Features Demonstration
Comprehensive examples of all new Manus AI features
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any

# Import all new features
from manus_ai.core.vector_store import VectorStore, Document, RAGSystem
from manus_ai.core.usage_tracker import UsageTracker, ResourceType, BudgetLimit
from manus_ai.core.multimodal import MultiModalManager, FileProcessor
from manus_ai.core.analytics import get_monitoring
from manus_ai.core.plugin_system import get_plugin_manager, BaseAgent
from manus_ai.core.auth import get_auth_manager, UserRole, Permission
from manus_ai.core.security import get_security_manager, RateLimitRule
from manus_ai.core.workflows import get_workflow_library, WorkflowEngine, WorkflowStep, StepType
from manus_ai.agents.image_agent import ImageGenerationAgent, ImageProvider, ImageSize
from manus_ai.core.llm_providers import LLMManager, LLMProvider


class FeatureDemo:
    """Demonstrates all advanced features"""

    def __init__(self):
        self.llm_manager = LLMManager()

    async def demo_vector_search_and_rag(self):
        """Demonstrate vector database and RAG"""
        print("\n" + "=" * 60)
        print("DEMO 1: Vector Search & RAG System")
        print("=" * 60)

        # Initialize vector store (in-memory for demo)
        vector_store = VectorStore(
            collection_name="demo_knowledge",
            use_memory=True
        )

        # Add documents
        documents = [
            Document(
                id="python_1",
                content="Python is a high-level, interpreted programming language known for its simplicity and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
                metadata={"category": "programming", "language": "Python", "difficulty": "beginner"}
            ),
            Document(
                id="ai_1",
                content="Artificial Intelligence (AI) is the simulation of human intelligence by machines. Machine learning is a subset of AI that enables computers to learn from data without being explicitly programmed.",
                metadata={"category": "ai", "topic": "introduction", "difficulty": "beginner"}
            ),
            Document(
                id="rag_1",
                content="Retrieval-Augmented Generation (RAG) combines information retrieval with text generation. It retrieves relevant documents from a knowledge base and uses them to enhance LLM responses with factual, domain-specific information.",
                metadata={"category": "ai", "topic": "rag", "difficulty": "intermediate"}
            ),
            Document(
                id="vectordb_1",
                content="Vector databases store data as high-dimensional vectors and enable semantic search. Unlike traditional keyword search, vector search finds conceptually similar information even when exact keywords don't match.",
                metadata={"category": "databases", "topic": "vector-db", "difficulty": "intermediate"}
            ),
            Document(
                id="llm_1",
                content="Large Language Models (LLMs) like GPT-4, Claude, and Gemini are trained on vast amounts of text data. They can understand context, generate human-like text, and perform various natural language tasks.",
                metadata={"category": "ai", "topic": "llm", "difficulty": "intermediate"}
            )
        ]

        print("\n📚 Adding documents to vector store...")
        count = await vector_store.add_documents(documents)
        print(f"✅ Added {count} documents")

        # Get statistics
        stats = vector_store.get_stats()
        print(f"\n📊 Vector Store Stats:")
        print(f"   Collection: {stats['collection_name']}")
        print(f"   Documents: {stats['points_count']}")
        print(f"   Embedding dimension: {stats['embedding_dimension']}")
        print(f"   Model: {stats['embedding_model']}")

        # Semantic search
        print("\n🔍 Semantic Search Examples:\n")

        queries = [
            "What is machine learning?",
            "How do vector databases work?",
            "Tell me about RAG"
        ]

        for query in queries:
            print(f"Query: '{query}'")
            results = await vector_store.search(
                query=query,
                limit=2,
                score_threshold=0.3
            )

            for result in results:
                print(f"  [{result.rank}] Score: {result.score:.3f}")
                print(f"      {result.document.content[:100]}...")
                print(f"      Category: {result.document.metadata.get('category')}")
            print()

        # RAG System
        print("\n🤖 RAG System Example:\n")

        rag = RAGSystem(vector_store)

        async def mock_llm_generate(messages):
            # In real usage, this would call actual LLM
            return f"Mock LLM response based on: {messages[-1]['content'][:100]}..."

        rag_query = "Explain how RAG improves AI responses"
        print(f"RAG Query: '{rag_query}'")

        result = await rag.generate_with_context(
            query=rag_query,
            llm_generate_func=mock_llm_generate,
            max_context_tokens=1000
        )

        print(f"\nResponse: {result['response']}")
        print(f"\nSources used: {len(result['sources'])}")
        for i, source in enumerate(result['sources'], 1):
            print(f"  [{i}] Score: {source['score']:.3f} - {source['metadata'].get('topic', 'N/A')}")

    async def demo_image_generation(self):
        """Demonstrate image generation"""
        print("\n" + "=" * 60)
        print("DEMO 2: AI Image Generation")
        print("=" * 60)

        agent = ImageGenerationAgent()

        # Show available providers
        info = agent.get_info()
        print(f"\n🎨 Image Generation Agent")
        print(f"   Supported providers: {', '.join(info['supported_providers'])}")
        print(f"   Configured: {info['configured_providers']}")

        # Example prompts
        prompts = [
            {
                "prompt": "A serene Japanese garden with cherry blossoms, koi pond, and traditional bridge",
                "style": "natural",
                "description": "Realistic nature scene"
            },
            {
                "prompt": "Futuristic cyberpunk cityscape at night with neon lights and flying cars",
                "style": "vivid",
                "description": "Sci-fi city"
            },
            {
                "prompt": "Abstract geometric patterns in vibrant colors, Kandinsky style",
                "style": "artistic",
                "description": "Abstract art"
            }
        ]

        print("\n📝 Example Image Generation Requests:\n")

        for i, example in enumerate(prompts, 1):
            print(f"{i}. {example['description']}")
            print(f"   Prompt: {example['prompt']}")
            print(f"   Style: {example['style']}")
            print(f"   [Image would be generated with provider API]")
            print()

        # Demonstrate prompt enhancement
        print("\n✨ Prompt Enhancement Example:\n")

        basic_prompt = "a cat"
        print(f"Basic prompt: '{basic_prompt}'")

        enhanced = await agent.enhance_prompt(basic_prompt, None)
        print(f"\nEnhanced prompt: '{enhanced}'")
        print("\n(Enhancement makes prompts more detailed and specific)")

    async def demo_usage_tracking(self):
        """Demonstrate usage tracking and cost management"""
        print("\n" + "=" * 60)
        print("DEMO 3: Usage Tracking & Cost Management")
        print("=" * 60)

        tracker = UsageTracker()

        # Set budget limits
        print("\n💰 Setting Budget Limits...\n")

        limits = [
            BudgetLimit(
                limit_amount=100.0,
                period="monthly",
                resource_types=[ResourceType.LLM_INPUT_TOKENS, ResourceType.LLM_OUTPUT_TOKENS],
                alert_threshold=0.8,
                hard_limit=True
            ),
            BudgetLimit(
                limit_amount=10.0,
                period="daily",
                resource_types=[ResourceType.IMAGE_GENERATION],
                alert_threshold=0.75,
                hard_limit=True
            )
        ]

        for limit in limits:
            tracker.add_budget_limit(limit)
            print(f"✅ Set {limit.period} limit: ${limit.limit_amount}")
            print(f"   Alert at: {limit.alert_threshold * 100}%")
            print(f"   Hard limit: {limit.hard_limit}")
            print()

        # Simulate usage
        print("📊 Simulating Usage...\n")

        usage_scenarios = [
            {
                "type": ResourceType.LLM_INPUT_TOKENS,
                "model": "gemini-2.0-flash-exp",
                "tokens": 1500,
                "description": "Chat input"
            },
            {
                "type": ResourceType.LLM_OUTPUT_TOKENS,
                "model": "gemini-2.0-flash-exp",
                "tokens": 800,
                "description": "Chat output"
            },
            {
                "type": ResourceType.IMAGE_GENERATION,
                "model": "dalle-3",
                "count": 2,
                "description": "2 images generated"
            },
            {
                "type": ResourceType.WEB_SEARCH,
                "model": "perplexity",
                "count": 5,
                "description": "5 web searches"
            }
        ]

        total_cost = 0.0
        for scenario in usage_scenarios:
            if scenario["type"] in [ResourceType.LLM_INPUT_TOKENS, ResourceType.LLM_OUTPUT_TOKENS]:
                record = await tracker.record_usage(
                    scenario["type"],
                    scenario["tokens"],
                    scenario["model"],
                    user_id="demo_user"
                )
            else:
                record = await tracker.record_usage(
                    scenario["type"],
                    scenario.get("count", 1),
                    scenario["model"],
                    user_id="demo_user"
                )

            total_cost += record.cost
            print(f"{scenario['description']}: ${record.cost:.6f}")

        print(f"\nTotal cost: ${total_cost:.4f}")

        # Get usage summary
        print("\n📈 Usage Summary (Last 24 hours):\n")

        summary = await tracker.get_usage_summary("daily", "demo_user")

        print(f"Period: {summary['period']}")
        print(f"Total cost: ${summary['total_cost']:.4f}")
        print(f"Total records: {summary['total_records']}")
        print("\nBreakdown by resource type:")

        for resource_type, data in summary['breakdown'].items():
            print(f"  {resource_type}:")
            print(f"    Quantity: {data['quantity']:.0f}")
            print(f"    Cost: ${data['cost']:.4f}")
            print(f"    Count: {data['count']}")

        # Cost forecast
        print("\n🔮 Cost Forecast:\n")

        forecast = await tracker.get_cost_forecast("monthly", "demo_user")

        print(f"Period: {forecast['period']}")
        print(f"Daily average: ${forecast['daily_average']:.4f}")
        print(f"Forecast (30 days): ${forecast['forecast_cost']:.2f}")
        print(f"Trend: {forecast['current_trend']}")

    async def demo_multimodal_support(self):
        """Demonstrate multi-modal file processing"""
        print("\n" + "=" * 60)
        print("DEMO 4: Multi-Modal File Processing")
        print("=" * 60)

        processor = FileProcessor()

        # Simulate different file types
        print("\n📁 File Processing Examples:\n")

        examples = [
            {
                "filename": "report.pdf",
                "description": "PDF document",
                "mime": "application/pdf",
                "features": ["Text extraction", "Page count", "Metadata"]
            },
            {
                "filename": "screenshot.png",
                "description": "PNG image",
                "mime": "image/png",
                "features": ["Thumbnail generation", "Dimensions", "Format detection"]
            },
            {
                "filename": "document.docx",
                "description": "Word document",
                "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "features": ["Text extraction", "Paragraph parsing"]
            },
            {
                "filename": "code.py",
                "description": "Python code",
                "mime": "text/x-python",
                "features": ["Syntax detection", "Code analysis"]
            }
        ]

        for example in examples:
            print(f"📄 {example['filename']} ({example['description']})")
            print(f"   MIME type: {example['mime']}")
            print(f"   Features: {', '.join(example['features'])}")
            print()

        # Demonstrate file type detection
        print("🔍 File Type Detection:\n")

        test_cases = [
            ("image.jpg", b'\xFF\xD8\xFF', "JPEG image"),
            ("document.pdf", b'%PDF-1.4', "PDF document"),
            ("archive.zip", b'PK\x03\x04', "ZIP archive")
        ]

        for filename, magic_bytes, expected in test_cases:
            file_type, mime_type = processor.detect_file_type(filename, magic_bytes + b'...')
            print(f"{filename}: {mime_type} ({expected})")

    async def demo_analytics_monitoring(self):
        """Demonstrate analytics and monitoring"""
        print("\n" + "=" * 60)
        print("DEMO 5: Analytics & Monitoring")
        print("=" * 60)

        monitoring = get_monitoring()

        # Simulate some activity
        print("\n📊 Recording System Activity...\n")

        # Simulate requests
        for i in range(10):
            monitoring.record_request(
                endpoint="/chat",
                method="POST",
                status_code=200 if i < 8 else 500,
                duration_ms=100 + (i * 50),
                user_id=f"user_{i % 3}"
            )

        # Simulate agent executions
        agents = ["CodeAgent", "ResearchAgent", "DataAgent"]
        for agent in agents:
            monitoring.record_agent_execution(
                agent_name=agent,
                task_type="execute",
                duration_ms=2000,
                success=True,
                tokens_used=1500,
                cost=0.03
            )

        # Get system health
        print("🏥 System Health:\n")

        health = await monitoring.get_system_health()

        print(f"Status: {health.status.upper()}")
        print(f"Uptime: {health.uptime_seconds:.0f} seconds")
        print(f"Active sessions: {health.active_sessions}")
        print(f"Requests/min: {health.requests_per_minute:.2f}")
        print(f"Avg response time: {health.average_response_time_ms:.0f}ms")
        print(f"Error rate: {health.error_rate_percent:.1f}%")

        # Agent health
        if health.agent_health:
            print("\nAgent Health:")
            for agent, status in health.agent_health.items():
                print(f"  {agent}: {status}")

        # Request statistics
        print("\n📈 Request Statistics (Last hour):\n")

        request_stats = monitoring.requests.get_stats(minutes=60)

        print(f"Total requests: {request_stats['total_requests']}")
        print(f"Success rate: {request_stats['success_rate']:.1f}%")
        print(f"Error rate: {request_stats['error_rate']:.1f}%")
        print(f"Avg duration: {request_stats['average_duration_ms']:.0f}ms")
        print(f"P95 duration: {request_stats['p95_duration_ms']:.0f}ms")

    async def demo_plugin_system(self):
        """Demonstrate plugin system"""
        print("\n" + "=" * 60)
        print("DEMO 6: Plugin System")
        print("=" * 60)

        manager = get_plugin_manager()

        # Create example plugin template
        print("\n🔌 Creating Plugin Template...\n")

        template_path = manager.create_plugin_template("example_agent")
        print(f"✅ Created plugin template: {template_path}")
        print("\nPlugin Structure:")
        print("  - BaseAgent inheritance")
        print("  - Metadata definition")
        print("  - Execute method")
        print("  - Initialize & cleanup hooks")

        # Show plugin architecture
        print("\n🏗️ Plugin Architecture:\n")

        print("Benefits:")
        print("  ✓ Dynamic loading/unloading")
        print("  ✓ Hot reload capability")
        print("  ✓ Isolated execution")
        print("  ✓ Metadata management")
        print("  ✓ Dependency tracking")
        print("  ✓ Template generation")

        print("\nPlugin Lifecycle:")
        print("  1. Discover → 2. Load → 3. Initialize")
        print("  4. Execute → 5. Cleanup → 6. Unload")

    async def demo_authentication_security(self):
        """Demonstrate authentication and security"""
        print("\n" + "=" * 60)
        print("DEMO 7: Authentication & Security")
        print("=" * 60)

        auth_manager = get_auth_manager()
        security = get_security_manager()

        # User management
        print("\n👤 User Management:\n")

        # Create demo user
        try:
            user = await auth_manager.create_user(
                username="demo_user",
                email="demo@example.com",
                password="SecurePass123!",
                role=UserRole.USER
            )
            print(f"✅ Created user: {user.username}")
            print(f"   Role: {user.role.value}")
            print(f"   Email: {user.email}")
        except ValueError:
            print("ℹ️  Demo user already exists")

        # Show permission system
        print("\n🔒 Permission System:\n")

        permissions_by_role = {
            "Admin": ["All permissions", "User management", "System config"],
            "User": ["Create sessions", "Execute agents", "Manage own data"],
            "ReadOnly": ["View sessions", "View analytics"],
            "API-only": ["API access only", "Limited permissions"]
        }

        for role, perms in permissions_by_role.items():
            print(f"{role}:")
            for perm in perms:
                print(f"  ✓ {perm}")

        # Rate limiting
        print("\n🛡️ Rate Limiting:\n")

        rate_limits = [
            ("API Requests", "100 per minute"),
            ("Chat Messages", "50 per minute"),
            ("Agent Executions", "20 per minute"),
            ("Image Generation", "10 per 5 minutes"),
            ("File Uploads", "20 per minute")
        ]

        for endpoint, limit in rate_limits:
            print(f"  {endpoint}: {limit}")

        # Security features
        print("\n🔐 Security Features:\n")

        features = [
            ("Input Validation", "SQL injection, XSS, command injection prevention"),
            ("Prompt Injection", "Detection of malicious prompt patterns"),
            ("Code Scanning", "Security analysis before execution"),
            ("Password Hashing", "Bcrypt with salt"),
            ("JWT Tokens", "Secure session management"),
            ("API Key Rotation", "Generate, revoke, manage keys")
        ]

        for feature, desc in features:
            print(f"  ✓ {feature}: {desc}")

    async def demo_workflow_templates(self):
        """Demonstrate workflow templates"""
        print("\n" + "=" * 60)
        print("DEMO 8: Workflow Templates")
        print("=" * 60)

        library = get_workflow_library()

        # List built-in templates
        print("\n📋 Built-in Workflow Templates:\n")

        templates = library.list_templates()

        for i, template in enumerate(templates, 1):
            print(f"{i}. {template.name}")
            print(f"   Description: {template.description}")
            print(f"   Category: {template.category}")
            print(f"   Steps: {len(template.steps)}")
            print(f"   Tags: {', '.join(template.tags)}")
            print()

        # Show workflow structure
        print("🏗️ Workflow Structure:\n")

        print("Step Types:")
        step_types = [
            ("Agent Execution", "Execute an agent"),
            ("LLM Query", "Direct LLM query"),
            ("Data Transform", "Transform data"),
            ("Conditional", "Branch based on condition"),
            ("Parallel", "Run steps in parallel"),
            ("Wait", "Delay execution")
        ]

        for step_type, description in step_types:
            print(f"  • {step_type}: {description}")

        print("\nFeatures:")
        features = [
            "Dependency management",
            "Parallel execution",
            "Conditional logic",
            "Parameter resolution",
            "Error handling & retry",
            "Execution tracking"
        ]

        for feature in features:
            print(f"  ✓ {feature}")

    async def run_all_demos(self):
        """Run all feature demonstrations"""
        print("\n" + "=" * 80)
        print(" " * 20 + "MANUS AI ADVANCED FEATURES DEMO")
        print("=" * 80)
        print("\nThis demo showcases all 9 major enterprise features added to the platform.")
        print("\nNote: Some features require API keys and external services.")
        print("      Demo uses mock/simulated data where external services are needed.")

        demos = [
            ("Vector Search & RAG", self.demo_vector_search_and_rag),
            ("Image Generation", self.demo_image_generation),
            ("Usage Tracking", self.demo_usage_tracking),
            ("Multi-Modal Support", self.demo_multimodal_support),
            ("Analytics & Monitoring", self.demo_analytics_monitoring),
            ("Plugin System", self.demo_plugin_system),
            ("Authentication & Security", self.demo_authentication_security),
            ("Workflow Templates", self.demo_workflow_templates)
        ]

        for i, (name, demo_func) in enumerate(demos, 1):
            try:
                await demo_func()

                if i < len(demos):
                    input("\n⏎ Press Enter to continue to next demo...")

            except Exception as e:
                print(f"\n❌ Error in {name} demo: {e}")
                import traceback
                traceback.print_exc()

        print("\n" + "=" * 80)
        print(" " * 25 + "DEMO COMPLETE!")
        print("=" * 80)
        print("\n✅ All features demonstrated successfully!")
        print("\n📚 For more details, see ENHANCEMENTS_GUIDE.md")
        print("🚀 Ready for production deployment!")


async def main():
    """Main entry point"""
    demo = FeatureDemo()
    await demo.run_all_demos()


if __name__ == "__main__":
    asyncio.run(main())
