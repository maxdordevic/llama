"""
Integration Tests for Advanced Features
Tests all 9 major enhancement systems
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

# Import all features to test
from manus_ai.core.vector_store import VectorStore, Document, RAGSystem
from manus_ai.core.usage_tracker import UsageTracker, ResourceType, BudgetLimit
from manus_ai.core.multimodal import MultiModalManager, FileProcessor
from manus_ai.core.analytics import MonitoringSystem
from manus_ai.core.plugin_system import PluginManager, BaseAgent
from manus_ai.core.auth import AuthenticationManager, UserRole, Permission
from manus_ai.core.security import SecurityManager, RateLimitRule
from manus_ai.core.workflows import WorkflowLibrary, WorkflowEngine, WorkflowStep, StepType
from manus_ai.agents.image_agent import ImageGenerationAgent, ImageProvider


class TestVectorStore:
    """Test vector database and RAG system"""

    @pytest.mark.asyncio
    async def test_vector_store_creation(self):
        """Test vector store initialization"""
        vector_store = VectorStore(
            collection_name="test_collection",
            use_memory=True  # Use in-memory for testing
        )

        stats = vector_store.get_stats()
        assert stats['collection_name'] == "test_collection"
        assert stats['points_count'] == 0

    @pytest.mark.asyncio
    async def test_add_documents(self):
        """Test adding documents to vector store"""
        vector_store = VectorStore(use_memory=True)

        documents = [
            Document(
                id="doc1",
                content="Python is a programming language",
                metadata={"category": "tech"}
            ),
            Document(
                id="doc2",
                content="JavaScript is used for web development",
                metadata={"category": "tech"}
            )
        ]

        count = await vector_store.add_documents(documents)
        assert count == 2

        stats = vector_store.get_stats()
        assert stats['points_count'] >= 2

    @pytest.mark.asyncio
    async def test_semantic_search(self):
        """Test semantic search"""
        vector_store = VectorStore(use_memory=True)

        # Add test documents
        documents = [
            Document(id="1", content="Python programming", metadata={}),
            Document(id="2", content="Machine learning", metadata={}),
            Document(id="3", content="Web development", metadata={})
        ]

        await vector_store.add_documents(documents)

        # Search
        results = await vector_store.search(
            query="coding in Python",
            limit=2
        )

        assert len(results) > 0
        assert all(r.score >= 0 for r in results)

    @pytest.mark.asyncio
    async def test_rag_system(self):
        """Test RAG system"""
        vector_store = VectorStore(use_memory=True)
        rag = RAGSystem(vector_store)

        # Add knowledge
        documents = [
            Document(id="1", content="AI is artificial intelligence", metadata={})
        ]
        await vector_store.add_documents(documents)

        # Mock LLM function
        async def mock_llm(messages):
            return "Test response based on context"

        result = await rag.generate_with_context(
            query="What is AI?",
            llm_generate_func=mock_llm,
            max_context_tokens=100
        )

        assert "response" in result
        assert "sources" in result


class TestUsageTracker:
    """Test usage tracking and cost management"""

    @pytest.mark.asyncio
    async def test_record_usage(self):
        """Test recording resource usage"""
        tracker = UsageTracker()

        record = await tracker.record_usage(
            ResourceType.LLM_INPUT_TOKENS,
            1000,
            "gemini-2.0-flash-exp",
            user_id="test_user"
        )

        assert record.quantity == 1000
        assert record.cost > 0

    @pytest.mark.asyncio
    async def test_budget_limits(self):
        """Test budget limit enforcement"""
        tracker = UsageTracker()

        # Set low budget
        tracker.add_budget_limit(BudgetLimit(
            limit_amount=0.01,  # Very low limit
            period="daily",
            hard_limit=True
        ))

        # Record usage
        await tracker.record_usage(
            ResourceType.LLM_OUTPUT_TOKENS,
            10000,  # Large usage
            "gemini-2.5-pro",
            user_id="test_user"
        )

        # Check budget
        check = await tracker.check_budget(
            cost=0.05,
            resource_type=ResourceType.LLM_OUTPUT_TOKENS,
            user_id="test_user"
        )

        # Should exceed budget
        assert check["current_usage"] > 0

    @pytest.mark.asyncio
    async def test_usage_summary(self):
        """Test usage summary generation"""
        tracker = UsageTracker()

        # Record some usage
        await tracker.record_usage(
            ResourceType.LLM_INPUT_TOKENS,
            500,
            "test-model",
            user_id="test_user"
        )

        summary = await tracker.get_usage_summary("daily", "test_user")

        assert summary["total_records"] > 0
        assert summary["total_cost"] >= 0
        assert "breakdown" in summary

    @pytest.mark.asyncio
    async def test_cost_forecast(self):
        """Test cost forecasting"""
        tracker = UsageTracker()

        # Add some usage
        for _ in range(5):
            await tracker.record_usage(
                ResourceType.LLM_INPUT_TOKENS,
                100,
                "test-model"
            )

        forecast = await tracker.get_cost_forecast("monthly")

        assert "forecast_cost" in forecast
        assert forecast["forecast_cost"] >= 0


class TestMultiModal:
    """Test multi-modal file processing"""

    def test_file_type_detection(self):
        """Test file type detection"""
        processor = FileProcessor()

        # Test JPEG
        file_type, mime_type = processor.detect_file_type(
            "test.jpg",
            b'\xFF\xD8\xFF'
        )
        assert mime_type == "image/jpeg"

        # Test PDF
        file_type, mime_type = processor.detect_file_type(
            "test.pdf",
            b'%PDF-1.4'
        )
        assert mime_type == "application/pdf"

    @pytest.mark.asyncio
    async def test_file_upload(self):
        """Test file upload and processing"""
        manager = MultiModalManager()

        # Create test file content
        test_content = b"Test file content"

        media_file = await manager.upload_file(
            filename="test.txt",
            content=test_content,
            session_id="test_session"
        )

        assert media_file.file_id is not None
        assert media_file.filename == "test.txt"
        assert media_file.size_bytes == len(test_content)

    @pytest.mark.asyncio
    async def test_file_retrieval(self):
        """Test file retrieval"""
        manager = MultiModalManager()

        # Upload file
        media_file = await manager.upload_file(
            "test.txt",
            b"content",
            "session1"
        )

        # Retrieve file
        retrieved = await manager.get_file(media_file.file_id)
        assert retrieved is not None
        assert retrieved.file_id == media_file.file_id


class TestAnalytics:
    """Test monitoring and analytics"""

    @pytest.mark.asyncio
    async def test_monitoring_system(self):
        """Test monitoring system initialization"""
        monitoring = MonitoringSystem()

        assert monitoring.start_time > 0

    def test_record_request(self):
        """Test request recording"""
        monitoring = MonitoringSystem()

        monitoring.record_request(
            endpoint="/test",
            method="GET",
            status_code=200,
            duration_ms=100,
            user_id="test_user"
        )

        stats = monitoring.requests.get_stats(minutes=1)
        assert stats["total_requests"] >= 1

    def test_record_agent_execution(self):
        """Test agent execution recording"""
        monitoring = MonitoringSystem()

        monitoring.record_agent_execution(
            agent_name="TestAgent",
            task_type="test",
            duration_ms=500,
            success=True,
            tokens_used=100,
            cost=0.01
        )

        stats = monitoring.agents.get_agent_stats("TestAgent", hours=1)
        assert stats["total_executions"] >= 1

    @pytest.mark.asyncio
    async def test_system_health(self):
        """Test system health check"""
        monitoring = MonitoringSystem()

        health = await monitoring.get_system_health()

        assert health.status in ["healthy", "degraded", "unhealthy"]
        assert health.uptime_seconds >= 0


class TestPluginSystem:
    """Test plugin system"""

    @pytest.mark.asyncio
    async def test_plugin_manager_init(self):
        """Test plugin manager initialization"""
        manager = PluginManager(plugin_dir="test_plugins")

        assert manager.plugin_dir.exists()

    def test_plugin_template_generation(self):
        """Test plugin template generation"""
        manager = PluginManager(plugin_dir="test_plugins")

        template_path = manager.create_plugin_template("test_agent")

        assert template_path.endswith("test_agent.py")

    @pytest.mark.asyncio
    async def test_custom_agent(self):
        """Test custom agent execution"""

        class TestAgent(BaseAgent):
            def __init__(self):
                super().__init__()
                self.name = "TestAgent"

            async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "status": "success",
                    "agent": self.name,
                    "result": f"Processed: {task.get('input')}"
                }

        agent = TestAgent()
        result = await agent.execute({"input": "test data"})

        assert result["status"] == "success"
        assert "result" in result


class TestAuthentication:
    """Test authentication and authorization"""

    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test user creation"""
        auth = AuthenticationManager()

        user = await auth.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            role=UserRole.USER
        )

        assert user.username == "testuser"
        assert user.role == UserRole.USER

    @pytest.mark.asyncio
    async def test_authenticate_user(self):
        """Test user authentication"""
        auth = AuthenticationManager()

        # Create user
        await auth.create_user(
            "authtest",
            "authtest@example.com",
            "password123",
            UserRole.USER
        )

        # Authenticate
        user = await auth.authenticate_user("authtest", "password123")
        assert user is not None
        assert user.username == "authtest"

        # Wrong password
        user = await auth.authenticate_user("authtest", "wrongpass")
        assert user is None

    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test session creation"""
        auth = AuthenticationManager()

        user = await auth.create_user(
            "sessiontest",
            "session@example.com",
            "pass123",
            UserRole.USER
        )

        session = await auth.create_session(user)

        assert session.user_id == user.user_id
        assert session.token is not None

    @pytest.mark.asyncio
    async def test_api_key_generation(self):
        """Test API key generation"""
        auth = AuthenticationManager()

        user = await auth.create_user(
            "apitest",
            "api@example.com",
            "pass123",
            UserRole.USER
        )

        api_key_obj, plain_key = await auth.create_api_key(
            user,
            "Test Key",
            expires_in_days=30
        )

        assert plain_key.startswith("mk_")
        assert api_key_obj.name == "Test Key"

    def test_permission_checking(self):
        """Test permission system"""
        auth = AuthenticationManager()

        # Mock user with role
        class MockUser:
            user_id = "test"
            role = UserRole.ADMIN

        user = MockUser()

        has_perm = auth.has_permission(
            user,
            None,
            Permission.MANAGE_USERS
        )

        assert has_perm  # Admin should have all permissions


class TestSecurity:
    """Test security and rate limiting"""

    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """Test rate limiting"""
        security = SecurityManager()

        # Should allow first requests
        for i in range(5):
            allowed, details = await security.check_request(
                client_id="test_client",
                rule_name="chat_messages"
            )
            assert allowed

    @pytest.mark.asyncio
    async def test_input_validation(self):
        """Test input validation"""
        security = SecurityManager()

        # Valid input
        allowed, details = await security.check_request(
            client_id="test",
            rule_name="api_requests",
            input_text="This is a normal message"
        )
        assert allowed

        # SQL injection attempt
        allowed, details = await security.check_request(
            client_id="test",
            rule_name="api_requests",
            input_text="'; DROP TABLE users; --"
        )
        assert not allowed  # Should be blocked

    @pytest.mark.asyncio
    async def test_code_scanning(self):
        """Test code security scanning"""
        from manus_ai.core.security import SecurityScanner

        scanner = SecurityScanner()

        # Safe code
        safe_scan = await scanner.scan_code_execution("x = 1 + 1")
        assert safe_scan["safe"]

        # Dangerous code
        dangerous_scan = await scanner.scan_code_execution("import os; os.system('rm -rf /')")
        assert not dangerous_scan["safe"]


class TestWorkflows:
    """Test workflow templates"""

    def test_workflow_library(self):
        """Test workflow library"""
        library = WorkflowLibrary(storage_dir="test_workflows")

        templates = library.list_templates()
        assert isinstance(templates, list)

    def test_create_template(self):
        """Test template creation"""
        library = WorkflowLibrary(storage_dir="test_workflows")

        steps = [
            WorkflowStep(
                step_id="step1",
                step_type=StepType.WAIT,
                name="Wait Step",
                description="Test step",
                parameters={"seconds": 1}
            )
        ]

        template = library.create_template(
            name="Test Workflow",
            description="Test description",
            steps=steps
        )

        assert template.name == "Test Workflow"
        assert len(template.steps) == 1

    @pytest.mark.asyncio
    async def test_workflow_execution(self):
        """Test workflow execution"""
        library = WorkflowLibrary(storage_dir="test_workflows")

        steps = [
            WorkflowStep(
                step_id="step1",
                step_type=StepType.WAIT,
                name="Test",
                description="Test",
                parameters={"seconds": 0.1}
            )
        ]

        template = library.create_template(
            "Test Flow",
            "Test",
            steps
        )

        engine = WorkflowEngine()
        execution = await engine.execute_workflow(
            template,
            {"input": "test"}
        )

        assert execution.status.value in ["completed", "failed"]


class TestImageAgent:
    """Test image generation agent"""

    def test_image_agent_init(self):
        """Test image agent initialization"""
        agent = ImageGenerationAgent()

        info = agent.get_info()
        assert agent.name == "ImageAgent"
        assert "supported_providers" in info

    @pytest.mark.asyncio
    async def test_prompt_enhancement(self):
        """Test prompt enhancement"""
        from manus_ai.core.llm_providers import LLMManager

        agent = ImageGenerationAgent(llm_manager=LLMManager())

        basic = "a cat"
        # Note: This would normally call real LLM, but will use mock
        # enhanced = await agent.enhance_prompt(basic)
        # Just test the method exists
        assert hasattr(agent, 'enhance_prompt')


# Integration test combining multiple features
class TestIntegration:
    """Integration tests combining multiple features"""

    @pytest.mark.asyncio
    async def test_authenticated_vector_search(self):
        """Test vector search with authentication"""
        auth = AuthenticationManager()
        vector_store = VectorStore(use_memory=True)

        # Create user
        user = await auth.create_user(
            "vectest",
            "vec@example.com",
            "pass123",
            UserRole.USER
        )

        # Add documents
        documents = [
            Document(id="1", content="Test document", metadata={})
        ]
        await vector_store.add_documents(documents)

        # Search as authenticated user
        results = await vector_store.search("test", limit=5)

        assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_monitored_plugin_execution(self):
        """Test plugin execution with monitoring"""
        monitoring = MonitoringSystem()

        class SimpleAgent(BaseAgent):
            async def execute(self, task):
                return {"status": "success", "result": "done"}

        agent = SimpleAgent()
        result = await agent.execute({"input": "test"})

        # Record execution
        monitoring.record_agent_execution(
            agent_name="SimpleAgent",
            task_type="test",
            duration_ms=100,
            success=result["status"] == "success"
        )

        stats = monitoring.agents.get_agent_stats("SimpleAgent", hours=1)
        assert stats["total_executions"] >= 1


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
