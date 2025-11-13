"""
Enhanced API Endpoints for All New Features
Comprehensive REST API for vector search, image generation, analytics, etc.
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Header, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import io

from ..core.vector_store import VectorStore, Document, RAGSystem
from ..core.usage_tracker import UsageTracker, ResourceType, BudgetLimit
from ..core.multimodal import MultiModalManager
from ..core.analytics import get_monitoring
from ..core.plugin_system import get_plugin_manager, PluginStatus
from ..core.auth import get_auth_manager, User, Permission, UserRole
from ..core.security import get_security_manager, RateLimitRule
from ..core.workflows import get_workflow_library, WorkflowEngine, WorkflowStep, StepType
from ..agents.image_agent import ImageGenerationAgent, ImageProvider, ImageSize, ImageStyle

# Initialize routers
vector_router = APIRouter(prefix="/vector", tags=["Vector Database"])
image_router = APIRouter(prefix="/images", tags=["Image Generation"])
usage_router = APIRouter(prefix="/usage", tags=["Usage Tracking"])
multimodal_router = APIRouter(prefix="/files", tags=["Multi-Modal"])
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])
plugin_router = APIRouter(prefix="/plugins", tags=["Plugins"])
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
security_router = APIRouter(prefix="/security", tags=["Security"])
workflow_router = APIRouter(prefix="/workflows", tags=["Workflows"])


# ==================== Pydantic Models ====================

# Vector Database Models
class DocumentInput(BaseModel):
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AddDocumentsRequest(BaseModel):
    documents: List[DocumentInput]
    collection_name: Optional[str] = "manus_knowledge"

class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=50)
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    filters: Optional[Dict[str, Any]] = None

class RAGRequest(BaseModel):
    query: str
    max_context_tokens: int = Field(default=2000, ge=100, le=8000)
    system_prompt: Optional[str] = None
    provider: str = "gemini-2.0-flash-exp"


# Image Generation Models
class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    provider: ImageProvider = ImageProvider.DALLE_3
    size: ImageSize = ImageSize.SQUARE_1024
    style: Optional[ImageStyle] = None
    quality: str = Field(default="standard", pattern="^(standard|hd)$")
    n: int = Field(default=1, ge=1, le=4)
    enhance_prompt: bool = True
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None


# Usage Tracking Models
class UsageRecordRequest(BaseModel):
    resource_type: ResourceType
    quantity: float
    provider: str
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BudgetLimitRequest(BaseModel):
    limit_amount: float = Field(..., gt=0)
    period: str = Field(..., pattern="^(hourly|daily|weekly|monthly|total)$")
    resource_types: Optional[List[ResourceType]] = None
    alert_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    hard_limit: bool = True


# Authentication Models
class UserRegistration(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.USER

class UserLogin(BaseModel):
    username: str
    password: str

class APIKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3650)
    rate_limit: Optional[int] = Field(default=None, ge=1, le=10000)


# Workflow Models
class WorkflowTemplateRequest(BaseModel):
    name: str
    description: str
    category: str = "general"
    tags: List[str] = Field(default_factory=list)
    steps: List[Dict[str, Any]]
    is_public: bool = False

class WorkflowExecutionRequest(BaseModel):
    template_id: str
    input_data: Dict[str, Any]


# Plugin Models
class PluginLoadRequest(BaseModel):
    plugin_id: str
    config: Optional[Dict[str, Any]] = None

class PluginExecuteRequest(BaseModel):
    task: Dict[str, Any]


# ==================== Dependencies ====================

async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
) -> Optional[User]:
    """Get current user from JWT token or API key"""
    auth_manager = get_auth_manager()

    # Try API key first
    if x_api_key:
        api_key_obj = await auth_manager.verify_api_key(x_api_key)
        if api_key_obj:
            user = await auth_manager.get_user(api_key_obj.user_id)
            return user

    # Try JWT token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        session = await auth_manager.verify_session(token)
        if session:
            user = await auth_manager.get_user(session.user_id)
            return user

    return None


async def require_auth(user: User = Depends(get_current_user)) -> User:
    """Require authentication"""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_permission(permission: Permission):
    """Require specific permission"""
    async def check_permission(user: User = Depends(require_auth)):
        auth_manager = get_auth_manager()
        if not auth_manager.has_permission(user, None, permission):
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
        return user
    return check_permission


# ==================== Vector Database Endpoints ====================

@vector_router.post("/documents")
async def add_documents(
    request: AddDocumentsRequest,
    user: User = Depends(require_auth),
    background_tasks: BackgroundTasks = None
):
    """Add documents to vector store"""
    try:
        vector_store = VectorStore(collection_name=request.collection_name)

        documents = [
            Document(
                id=None,  # Auto-generate
                content=doc.content,
                metadata=doc.metadata
            )
            for doc in request.documents
        ]

        count = await vector_store.add_documents(documents)

        return {
            "status": "success",
            "documents_added": count,
            "collection": request.collection_name
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@vector_router.post("/search")
async def search_documents(
    request: SearchRequest,
    user: User = Depends(require_auth)
):
    """Search documents by semantic similarity"""
    try:
        vector_store = VectorStore()

        results = await vector_store.search(
            query=request.query,
            limit=request.limit,
            score_threshold=request.score_threshold,
            filters=request.filters
        )

        return {
            "status": "success",
            "query": request.query,
            "results": [
                {
                    "rank": r.rank,
                    "score": r.score,
                    "content": r.document.content,
                    "metadata": r.document.metadata
                }
                for r in results
            ],
            "count": len(results)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@vector_router.post("/rag")
async def rag_query(
    request: RAGRequest,
    user: User = Depends(require_auth)
):
    """Retrieval-Augmented Generation query"""
    try:
        from ..core.llm_providers import LLMManager, LLMProvider

        vector_store = VectorStore()
        rag_system = RAGSystem(vector_store)
        llm_manager = LLMManager()

        async def llm_generate(messages):
            return await llm_manager.generate(
                messages,
                provider=LLMProvider(request.provider)
            )

        result = await rag_system.generate_with_context(
            query=request.query,
            llm_generate_func=llm_generate,
            max_context_tokens=request.max_context_tokens,
            system_prompt=request.system_prompt
        )

        return {
            "status": "success",
            "query": request.query,
            "response": result["response"],
            "sources": result["sources"],
            "source_count": len(result["sources"])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@vector_router.get("/stats")
async def vector_stats(user: User = Depends(require_auth)):
    """Get vector store statistics"""
    try:
        vector_store = VectorStore()
        stats = vector_store.get_stats()
        return {"status": "success", **stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Image Generation Endpoints ====================

@image_router.post("/generate")
async def generate_image(
    request: ImageGenerationRequest,
    user: User = Depends(require_auth)
):
    """Generate images using AI"""
    try:
        # Check rate limit
        security = get_security_manager()
        allowed, details = await security.check_request(
            client_id=user.user_id,
            rule_name="image_generations"
        )

        if not allowed:
            raise HTTPException(status_code=429, detail=details)

        # Generate image
        agent = ImageGenerationAgent()
        result = await agent.execute({
            "prompt": request.prompt,
            "provider": request.provider.value,
            "size": request.size.value,
            "style": request.style.value if request.style else None,
            "quality": request.quality,
            "n": request.n,
            "enhance_prompt": request.enhance_prompt,
            "negative_prompt": request.negative_prompt,
            "seed": request.seed
        })

        # Track usage
        tracker = UsageTracker()
        await tracker.record_usage(
            ResourceType.IMAGE_GENERATION,
            request.n,
            request.provider.value,
            user_id=user.user_id,
            metadata={"size": request.size.value}
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@image_router.get("/providers")
async def list_image_providers():
    """List available image generation providers"""
    agent = ImageGenerationAgent()
    return agent.get_info()


# ==================== Usage Tracking Endpoints ====================

@usage_router.post("/record")
async def record_usage(
    request: UsageRecordRequest,
    user: User = Depends(require_auth)
):
    """Record resource usage"""
    tracker = UsageTracker()
    record = await tracker.record_usage(
        request.resource_type,
        request.quantity,
        request.provider,
        session_id=request.session_id,
        user_id=user.user_id,
        metadata=request.metadata
    )

    return {
        "status": "success",
        "cost": record.cost,
        "timestamp": record.timestamp.isoformat()
    }


@usage_router.get("/summary")
async def get_usage_summary(
    period: str = "daily",
    user: User = Depends(require_auth)
):
    """Get usage summary"""
    tracker = UsageTracker()
    summary = await tracker.get_usage_summary(period, user.user_id)
    return {"status": "success", **summary}


@usage_router.get("/forecast")
async def get_cost_forecast(
    period: str = "monthly",
    user: User = Depends(require_auth)
):
    """Get cost forecast"""
    tracker = UsageTracker()
    forecast = await tracker.get_cost_forecast(period, user.user_id)
    return {"status": "success", **forecast}


@usage_router.post("/budget")
async def set_budget_limit(
    request: BudgetLimitRequest,
    user: User = Depends(require_permission(Permission.MANAGE_SYSTEM))
):
    """Set budget limit"""
    tracker = UsageTracker()
    limit = BudgetLimit(
        limit_amount=request.limit_amount,
        period=request.period,
        resource_types=request.resource_types,
        user_id=user.user_id,
        alert_threshold=request.alert_threshold,
        hard_limit=request.hard_limit
    )
    tracker.add_budget_limit(limit)

    return {"status": "success", "message": "Budget limit set"}


# ==================== Multi-Modal Endpoints ====================

@multimodal_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(require_auth)
):
    """Upload file for multi-modal chat"""
    try:
        # Check rate limit
        security = get_security_manager()
        allowed, details = await security.check_request(
            client_id=user.user_id,
            rule_name="file_uploads"
        )

        if not allowed:
            raise HTTPException(status_code=429, detail=details)

        # Read file
        content = await file.read()

        # Process file
        manager = MultiModalManager()
        media_file = await manager.upload_file(
            filename=file.filename,
            content=content,
            session_id=None  # TODO: Get from session
        )

        return {
            "status": "success",
            "file_id": media_file.file_id,
            "filename": media_file.filename,
            "file_type": media_file.file_type.value,
            "size_bytes": media_file.size_bytes,
            "metadata": media_file.metadata,
            "has_text": bool(media_file.text_content),
            "text_preview": media_file.text_content[:200] if media_file.text_content else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@multimodal_router.get("/{file_id}")
async def get_file(
    file_id: str,
    user: User = Depends(require_auth)
):
    """Get file information"""
    manager = MultiModalManager()
    media_file = await manager.get_file(file_id)

    if not media_file:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "file_id": media_file.file_id,
        "filename": media_file.filename,
        "file_type": media_file.file_type.value,
        "size_bytes": media_file.size_bytes,
        "metadata": media_file.metadata
    }


@multimodal_router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    user: User = Depends(require_auth)
):
    """Delete uploaded file"""
    manager = MultiModalManager()
    success = await manager.delete_file(file_id)

    if not success:
        raise HTTPException(status_code=404, detail="File not found")

    return {"status": "success", "message": "File deleted"}


# ==================== Analytics Endpoints ====================

@analytics_router.get("/health")
async def system_health():
    """Get system health status"""
    monitoring = get_monitoring()
    health = await monitoring.get_system_health()

    return {
        "status": health.status,
        "uptime_seconds": health.uptime_seconds,
        "active_sessions": health.active_sessions,
        "requests_per_minute": health.requests_per_minute,
        "average_response_time_ms": health.average_response_time_ms,
        "error_rate_percent": health.error_rate_percent,
        "agent_health": health.agent_health,
        "llm_provider_health": health.llm_provider_health
    }


@analytics_router.get("/dashboard")
async def dashboard_data(
    user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get comprehensive dashboard data"""
    monitoring = get_monitoring()
    data = await monitoring.get_dashboard_data()
    return data


@analytics_router.get("/agents")
async def agent_statistics(
    hours: int = 24,
    user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get agent execution statistics"""
    monitoring = get_monitoring()
    stats = monitoring.agents.get_all_agents_stats(hours)
    return {"status": "success", "agents": stats}


# ==================== Plugin Endpoints ====================

@plugin_router.get("")
async def list_plugins(
    status: Optional[PluginStatus] = None,
    user: User = Depends(require_auth)
):
    """List all plugins"""
    manager = get_plugin_manager()
    plugins = manager.list_plugins(status)

    return {
        "status": "success",
        "plugins": [
            {
                "plugin_id": p.plugin_id,
                "name": p.metadata.name,
                "version": p.metadata.version,
                "author": p.metadata.author,
                "description": p.metadata.description,
                "status": p.status.value,
                "capabilities": p.metadata.capabilities,
                "tags": p.metadata.tags
            }
            for p in plugins
        ],
        "count": len(plugins)
    }


@plugin_router.post("/{plugin_id}/load")
async def load_plugin(
    plugin_id: str,
    request: PluginLoadRequest,
    user: User = Depends(require_permission(Permission.INSTALL_PLUGIN))
):
    """Load a plugin"""
    manager = get_plugin_manager()
    success = await manager.load_plugin(plugin_id, request.config)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to load plugin")

    return {"status": "success", "plugin_id": plugin_id}


@plugin_router.post("/{plugin_id}/unload")
async def unload_plugin(
    plugin_id: str,
    user: User = Depends(require_permission(Permission.MANAGE_PLUGIN))
):
    """Unload a plugin"""
    manager = get_plugin_manager()
    success = await manager.unload_plugin(plugin_id)

    if not success:
        raise HTTPException(status_code=404, detail="Plugin not found")

    return {"status": "success", "plugin_id": plugin_id}


@plugin_router.post("/{plugin_id}/execute")
async def execute_plugin(
    plugin_id: str,
    request: PluginExecuteRequest,
    user: User = Depends(require_permission(Permission.EXECUTE_AGENT))
):
    """Execute plugin agent"""
    manager = get_plugin_manager()
    plugin_info = manager.get_plugin(plugin_id)

    if not plugin_info:
        raise HTTPException(status_code=404, detail="Plugin not found")

    result = await manager.execute_agent(plugin_info.metadata.name, request.task)
    return result


# ==================== Authentication Endpoints ====================

@auth_router.post("/register")
async def register_user(request: UserRegistration):
    """Register new user"""
    try:
        auth_manager = get_auth_manager()
        user = await auth_manager.create_user(
            request.username,
            request.email,
            request.password,
            request.role
        )

        return {
            "status": "success",
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/login")
async def login(request: UserLogin):
    """Login user"""
    auth_manager = get_auth_manager()
    user = await auth_manager.authenticate_user(request.username, request.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session = await auth_manager.create_session(user)

    return {
        "status": "success",
        "token": session.token,
        "expires_at": session.expires_at.isoformat(),
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value
        }
    }


@auth_router.post("/api-keys")
async def create_api_key(
    request: APIKeyRequest,
    user: User = Depends(require_auth)
):
    """Create API key"""
    auth_manager = get_auth_manager()
    api_key_obj, plain_key = await auth_manager.create_api_key(
        user,
        request.name,
        expires_in_days=request.expires_in_days,
        rate_limit=request.rate_limit
    )

    return {
        "status": "success",
        "api_key": plain_key,  # Only shown once!
        "key_id": api_key_obj.key_id,
        "name": api_key_obj.name,
        "expires_at": api_key_obj.expires_at.isoformat() if api_key_obj.expires_at else None,
        "warning": "Save this key! It will not be shown again."
    }


@auth_router.get("/api-keys")
async def list_api_keys(user: User = Depends(require_auth)):
    """List user's API keys"""
    auth_manager = get_auth_manager()
    keys = await auth_manager.list_user_api_keys(user.user_id)

    return {
        "status": "success",
        "api_keys": [
            {
                "key_id": k.key_id,
                "name": k.name,
                "created_at": k.created_at.isoformat(),
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "last_used": k.last_used.isoformat() if k.last_used else None,
                "is_active": k.is_active
            }
            for k in keys
        ]
    }


@auth_router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: User = Depends(require_auth)
):
    """Revoke API key"""
    auth_manager = get_auth_manager()
    success = await auth_manager.revoke_api_key(key_id)

    if not success:
        raise HTTPException(status_code=404, detail="API key not found")

    return {"status": "success", "message": "API key revoked"}


# ==================== Workflow Endpoints ====================

@workflow_router.get("/templates")
async def list_workflow_templates(
    category: Optional[str] = None,
    user: User = Depends(require_auth)
):
    """List workflow templates"""
    library = get_workflow_library()
    templates = library.list_templates(category=category, public_only=not user)

    return {
        "status": "success",
        "templates": [
            {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "tags": t.tags,
                "step_count": len(t.steps),
                "author": t.author,
                "version": t.version
            }
            for t in templates
        ],
        "count": len(templates)
    }


@workflow_router.post("/execute")
async def execute_workflow(
    request: WorkflowExecutionRequest,
    user: User = Depends(require_auth),
    background_tasks: BackgroundTasks = None
):
    """Execute workflow"""
    library = get_workflow_library()
    template = library.get_template(request.template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    engine = WorkflowEngine()
    execution = await engine.execute_workflow(
        template,
        request.input_data,
        user_id=user.user_id
    )

    return {
        "status": "success",
        "execution_id": execution.execution_id,
        "workflow_status": execution.status.value,
        "started_at": execution.started_at.isoformat(),
        "results": execution.step_results
    }


@workflow_router.get("/executions/{execution_id}")
async def get_execution_status(
    execution_id: str,
    user: User = Depends(require_auth)
):
    """Get workflow execution status"""
    engine = WorkflowEngine()
    execution = engine.get_execution_status(execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return {
        "execution_id": execution.execution_id,
        "workflow_name": execution.workflow_name,
        "status": execution.status.value,
        "started_at": execution.started_at.isoformat(),
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "current_step": execution.current_step,
        "step_results": execution.step_results,
        "output_data": execution.output_data
    }


# Export all routers
all_routers = [
    vector_router,
    image_router,
    usage_router,
    multimodal_router,
    analytics_router,
    plugin_router,
    auth_router,
    workflow_router
]
